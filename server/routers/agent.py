"""
Agent Router - WebSocket endpoints for call center agents to handle warm handoffs
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from typing import Dict, Optional, List, Any
import asyncio
import json
import logging
import struct
import array
from datetime import datetime, timezone
from dataclasses import dataclass, field
import uuid

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agent", tags=["agent"])


# Audio conversion utilities
def pcm16_to_float32(pcm_bytes: bytes) -> bytes:
    """Convert PCM16 audio to Float32 format for WebSocket playback."""
    # Unpack PCM16 samples (little-endian signed 16-bit integers)
    num_samples = len(pcm_bytes) // 2
    pcm_samples = struct.unpack(f'<{num_samples}h', pcm_bytes)
    
    # Convert to float32 (-1.0 to 1.0)
    float_samples = array.array('f', [s / 32768.0 for s in pcm_samples])
    
    return float_samples.tobytes()


def upsample_audio(audio_bytes: bytes, from_rate: int, to_rate: int) -> bytes:
    """Upsample audio using linear interpolation."""
    if from_rate == to_rate:
        return audio_bytes
    
    # Parse as float32
    num_samples = len(audio_bytes) // 4
    samples = struct.unpack(f'<{num_samples}f', audio_bytes)
    
    # Calculate output length
    ratio = to_rate / from_rate
    out_length = int(num_samples * ratio)
    
    # Linear interpolation
    result = []
    for i in range(out_length):
        src_index = i / ratio
        idx0 = int(src_index)
        idx1 = min(idx0 + 1, num_samples - 1)
        frac = src_index - idx0
        result.append(samples[idx0] * (1 - frac) + samples[idx1] * frac)
    
    return struct.pack(f'<{len(result)}f', *result)


@dataclass
class PendingHandoff:
    """Represents a user waiting for agent connection."""
    user_id: str
    user_ws: WebSocket
    reason: str
    requested_at: datetime
    conversation_history: List[Dict[str, str]]
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))


@dataclass
class ActiveCall:
    """Represents an active call between user and agent."""
    session_id: str
    user_id: str
    agent_id: str
    user_ws: WebSocket
    agent_ws: WebSocket
    started_at: datetime
    conversation_history: List[Dict[str, str]]


class HandoffManager:
    """Manages the queue of pending handoffs and active calls."""
    
    def __init__(self):
        self.pending_handoffs: Dict[str, PendingHandoff] = {}  # session_id -> PendingHandoff
        self.active_calls: Dict[str, ActiveCall] = {}  # session_id -> ActiveCall
        self.available_agents: Dict[str, WebSocket] = {}  # agent_id -> WebSocket
        self._lock = asyncio.Lock()
    
    async def request_handoff(
        self,
        user_id: str,
        user_ws: WebSocket,
        reason: str,
        conversation_history: List[Dict[str, str]]
    ) -> str:
        """Add a user to the handoff queue."""
        async with self._lock:
            handoff = PendingHandoff(
                user_id=user_id,
                user_ws=user_ws,
                reason=reason,
                requested_at=datetime.now(timezone.utc),
                conversation_history=conversation_history,
            )
            self.pending_handoffs[handoff.session_id] = handoff
            logger.info(f"[Handoff] User {user_id} added to queue (session: {handoff.session_id})")
            
            # Notify all available agents about new pending call
            await self._broadcast_to_agents({
                "type": "new_pending_call",
                "session_id": handoff.session_id,
                "user_id": user_id,
                "reason": reason,
                "requested_at": handoff.requested_at.isoformat(),
                "queue_position": len(self.pending_handoffs),
            })
            
            return handoff.session_id
    
    async def register_agent(self, agent_id: str, agent_ws: WebSocket):
        """Register an agent as available."""
        async with self._lock:
            self.available_agents[agent_id] = agent_ws
            logger.info(f"[Handoff] Agent {agent_id} registered")
            
            # Send current queue to agent
            pending_list = [
                {
                    "session_id": h.session_id,
                    "user_id": h.user_id,
                    "reason": h.reason,
                    "requested_at": h.requested_at.isoformat(),
                    "wait_time_seconds": (datetime.now(timezone.utc) - h.requested_at).total_seconds(),
                }
                for h in self.pending_handoffs.values()
            ]
            await agent_ws.send_json({
                "type": "queue_status",
                "pending_calls": pending_list,
                "total_pending": len(pending_list),
            })
    
    async def unregister_agent(self, agent_id: str):
        """Remove an agent from available list."""
        async with self._lock:
            if agent_id in self.available_agents:
                del self.available_agents[agent_id]
                logger.info(f"[Handoff] Agent {agent_id} unregistered")
    
    async def accept_call(self, agent_id: str, agent_ws: WebSocket, session_id: str) -> Optional[ActiveCall]:
        """Agent accepts a pending call."""
        async with self._lock:
            if session_id not in self.pending_handoffs:
                logger.warning(f"[Handoff] Session {session_id} not found in pending")
                return None
            
            handoff = self.pending_handoffs.pop(session_id)
            
            # Create active call
            active_call = ActiveCall(
                session_id=session_id,
                user_id=handoff.user_id,
                agent_id=agent_id,
                user_ws=handoff.user_ws,
                agent_ws=agent_ws,
                started_at=datetime.now(timezone.utc),
                conversation_history=handoff.conversation_history,
            )
            self.active_calls[session_id] = active_call
            
            logger.info(f"[Handoff] Agent {agent_id} accepted call {session_id} from user {handoff.user_id}")
            
            # Notify user that agent connected
            try:
                await handoff.user_ws.send_json({
                    "type": "agent_connected",
                    "message": "You are now connected to a customer service agent.",
                    "session_id": session_id,
                    "agent_id": agent_id,
                })
            except Exception as e:
                logger.error(f"[Handoff] Failed to notify user: {e}")
            
            # Send conversation history to agent
            await agent_ws.send_json({
                "type": "call_accepted",
                "session_id": session_id,
                "user_id": handoff.user_id,
                "reason": handoff.reason,
                "conversation_history": handoff.conversation_history,
                "wait_time_seconds": (datetime.now(timezone.utc) - handoff.requested_at).total_seconds(),
            })
            
            # Notify other agents that call was picked up
            await self._broadcast_to_agents({
                "type": "call_accepted_by_other",
                "session_id": session_id,
            }, exclude_agent=agent_id)
            
            return active_call
    
    async def end_call(self, session_id: str, ended_by: str = "agent"):
        """End an active call."""
        async with self._lock:
            if session_id in self.active_calls:
                call = self.active_calls.pop(session_id)
                logger.info(f"[Handoff] Call {session_id} ended by {ended_by}")
                
                # Notify both parties
                try:
                    await call.user_ws.send_json({
                        "type": "call_ended",
                        "message": "The call with the agent has ended.",
                        "ended_by": ended_by,
                    })
                except Exception:
                    pass
                
                try:
                    await call.agent_ws.send_json({
                        "type": "call_ended",
                        "session_id": session_id,
                        "ended_by": ended_by,
                    })
                except Exception:
                    pass
            
            # Also remove from pending if still there
            if session_id in self.pending_handoffs:
                del self.pending_handoffs[session_id]
    
    async def cancel_handoff(self, session_id: str):
        """Cancel a pending handoff (user disconnected)."""
        async with self._lock:
            if session_id in self.pending_handoffs:
                del self.pending_handoffs[session_id]
                logger.info(f"[Handoff] Handoff {session_id} cancelled")
                
                # Notify agents
                await self._broadcast_to_agents({
                    "type": "call_cancelled",
                    "session_id": session_id,
                })
    
    async def relay_audio_to_agent(self, session_id: str, audio_bytes: bytes):
        """Relay audio from user to agent.
        
        User sends PCM16 at 16kHz. Agent receives as Float32 at 44100Hz for playback.
        """
        if session_id in self.active_calls:
            call = self.active_calls[session_id]
            try:
                # Convert PCM16 to Float32
                float_audio = pcm16_to_float32(audio_bytes)
                # Upsample from 16kHz to 44100Hz
                upsampled = upsample_audio(float_audio, 16000, 44100)
                await call.agent_ws.send_bytes(upsampled)
            except Exception as e:
                logger.error(f"[Handoff] Failed to relay audio to agent: {e}")
    
    async def relay_audio_to_user(self, session_id: str, audio_bytes: bytes):
        """Relay audio from agent to user.
        
        Agent sends PCM16 at 16kHz. User receives as Float32 at 44100Hz for playback.
        """
        if session_id in self.active_calls:
            call = self.active_calls[session_id]
            try:
                # Convert PCM16 to Float32
                float_audio = pcm16_to_float32(audio_bytes)
                # Upsample from 16kHz to 44100Hz
                upsampled = upsample_audio(float_audio, 16000, 44100)
                await call.user_ws.send_bytes(upsampled)
            except Exception as e:
                logger.error(f"[Handoff] Failed to relay audio to user: {e}")
    
    async def relay_message_to_user(self, session_id: str, message: Dict[str, Any]):
        """Relay a JSON message from agent to user."""
        if session_id in self.active_calls:
            call = self.active_calls[session_id]
            try:
                await call.user_ws.send_json(message)
            except Exception as e:
                logger.error(f"[Handoff] Failed to relay message to user: {e}")
    
    async def relay_message_to_agent(self, session_id: str, message: Dict[str, Any]):
        """Relay a JSON message from user to agent."""
        if session_id in self.active_calls:
            call = self.active_calls[session_id]
            try:
                await call.agent_ws.send_json(message)
            except Exception as e:
                logger.error(f"[Handoff] Failed to relay message to agent: {e}")
    
    async def _broadcast_to_agents(self, message: Dict[str, Any], exclude_agent: Optional[str] = None):
        """Broadcast a message to all available agents."""
        for agent_id, agent_ws in list(self.available_agents.items()):
            if agent_id == exclude_agent:
                continue
            try:
                await agent_ws.send_json(message)
            except Exception as e:
                logger.error(f"[Handoff] Failed to broadcast to agent {agent_id}: {e}")
    
    def get_pending_count(self) -> int:
        """Get number of pending handoffs."""
        return len(self.pending_handoffs)
    
    def get_active_count(self) -> int:
        """Get number of active calls."""
        return len(self.active_calls)
    
    def is_user_in_call(self, user_id: str) -> Optional[str]:
        """Check if user is in an active call, return session_id if so."""
        for session_id, call in self.active_calls.items():
            if call.user_id == user_id:
                return session_id
        return None
    
    def get_session_for_user_ws(self, user_ws: WebSocket) -> Optional[str]:
        """Get session_id for a user WebSocket (pending or active)."""
        for session_id, handoff in self.pending_handoffs.items():
            if handoff.user_ws == user_ws:
                return session_id
        for session_id, call in self.active_calls.items():
            if call.user_ws == user_ws:
                return session_id
        return None


# Global handoff manager instance
_handoff_manager: Optional[HandoffManager] = None


def get_handoff_manager() -> HandoffManager:
    """Get or create the global handoff manager."""
    global _handoff_manager
    if _handoff_manager is None:
        _handoff_manager = HandoffManager()
    return _handoff_manager


# =========================
# Agent WebSocket Endpoint
# =========================
@router.websocket("/ws/connect")
async def agent_websocket(ws: WebSocket):
    """
    WebSocket endpoint for call center agents.
    
    Query params:
    - agent_id: Required. The agent's identifier.
    
    Message Types from Agent:
    - {"type": "accept_call", "session_id": "..."} - Accept a pending call
    - {"type": "end_call", "session_id": "..."} - End current call
    - {"type": "message", "session_id": "...", "text": "..."} - Send text message to user
    - Audio bytes - Relay to user in active call
    
    Message Types to Agent:
    - {"type": "queue_status", "pending_calls": [...]} - Current queue on connect
    - {"type": "new_pending_call", ...} - New call added to queue
    - {"type": "call_accepted", ...} - Call accepted, includes conversation history
    - {"type": "call_ended", ...} - Call ended
    - {"type": "user_message", ...} - Message from user
    - Audio bytes - Audio from user
    """
    agent_id = ws.query_params.get("agent_id")
    
    if not agent_id:
        await ws.close(code=4001, reason="agent_id required")
        return
    
    await ws.accept()
    logger.info(f"✅ Agent {agent_id} connected")
    
    manager = get_handoff_manager()
    await manager.register_agent(agent_id, ws)
    
    current_session: Optional[str] = None
    
    try:
        while True:
            message = await ws.receive()
            
            if message["type"] == "websocket.disconnect":
                break
            
            if "bytes" in message:
                # Audio from agent - relay to user
                if current_session:
                    await manager.relay_audio_to_user(current_session, message["bytes"])
            
            elif "text" in message:
                try:
                    data = json.loads(message["text"])
                    msg_type = data.get("type")
                    
                    if msg_type == "accept_call":
                        session_id = data.get("session_id")
                        if session_id:
                            call = await manager.accept_call(agent_id, ws, session_id)
                            if call:
                                current_session = session_id
                            else:
                                await ws.send_json({
                                    "type": "error",
                                    "message": "Call not available or already accepted",
                                })
                    
                    elif msg_type == "end_call":
                        session_id = data.get("session_id") or current_session
                        if session_id:
                            await manager.end_call(session_id, ended_by="agent")
                            current_session = None
                    
                    elif msg_type == "message":
                        # Text message from agent to user
                        session_id = data.get("session_id") or current_session
                        if session_id:
                            await manager.relay_message_to_user(session_id, {
                                "type": "agent_message",
                                "text": data.get("text", ""),
                            })
                    
                    elif msg_type == "ping":
                        await ws.send_json({"type": "pong"})
                    
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON from agent {agent_id}")
    
    except WebSocketDisconnect:
        logger.info(f"✋ Agent {agent_id} disconnected")
    except Exception as e:
        logger.error(f"❌ Agent WebSocket error: {e}")
    finally:
        await manager.unregister_agent(agent_id)
        # End any active call
        if current_session:
            await manager.end_call(current_session, ended_by="agent_disconnect")


# =========================
# REST Endpoints
# =========================
@router.get("/queue/status")
async def get_queue_status():
    """Get current handoff queue status."""
    manager = get_handoff_manager()
    pending = [
        {
            "session_id": h.session_id,
            "user_id": h.user_id,
            "reason": h.reason,
            "requested_at": h.requested_at.isoformat(),
            "wait_time_seconds": (datetime.now(timezone.utc) - h.requested_at).total_seconds(),
        }
        for h in manager.pending_handoffs.values()
    ]
    active = [
        {
            "session_id": c.session_id,
            "user_id": c.user_id,
            "agent_id": c.agent_id,
            "started_at": c.started_at.isoformat(),
            "duration_seconds": (datetime.now(timezone.utc) - c.started_at).total_seconds(),
        }
        for c in manager.active_calls.values()
    ]
    return {
        "pending_calls": pending,
        "active_calls": active,
        "available_agents": list(manager.available_agents.keys()),
    }


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    manager = get_handoff_manager()
    return {
        "status": "ok",
        "service": "agent",
        "pending_calls": manager.get_pending_count(),
        "active_calls": manager.get_active_count(),
        "available_agents": len(manager.available_agents),
    }
