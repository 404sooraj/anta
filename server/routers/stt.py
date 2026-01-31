"""
STT Router - WebSocket endpoint for real-time audio streaming
Continuously streams audio to AssemblyAI and processes with LLM on silence,
then streams TTS response back to client
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import asyncio
import json
import uuid
import logging
from typing import Literal, cast, Any, Dict, List, Optional
from datetime import datetime

import jwt

from services.stt import STTService, VADService
from services.llm import LLMService
from services.tts import TTSService
from modules.config import ConfigEnv
from modules.response.tool_registry import get_registry
from routers.agent import get_handoff_manager

TTSLanguage = Literal["hi", "en", "auto"]

logger = logging.getLogger(__name__)

def normalize_tts_language(lang: str) -> TTSLanguage:
    if lang in ("hi", "en"):
        return cast(TTSLanguage, lang)
    return "auto"

def serialize_for_json(obj: Any) -> Any:
    """Recursively serialize datetime objects and other non-JSON types."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, dict):
        return {key: serialize_for_json(val) for key, val in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [serialize_for_json(item) for item in obj]
    elif hasattr(obj, "isoformat"):  # Handle other date/time types
        return obj.isoformat()
    return obj


# =========================
# Router Setup
# =========================
router = APIRouter(prefix="/stt", tags=["stt"])

# =========================
# Constants
# =========================
SILENCE_LIMIT_CHUNKS = 15  # ~0.5s of silence to trigger LLM
# Silero VAD requires at least 512 samples (32ms at 16kHz) per chunk
VAD_MIN_SAMPLES = 512
VAD_MIN_BYTES = VAD_MIN_SAMPLES * 2  # PCM16


# =========================
# WebSocket Endpoint
# =========================
@router.websocket("/ws/audio")
async def audio_websocket(ws: WebSocket):
    """
    WebSocket endpoint for real-time audio streaming with integrated TTS response.
    
    Flow:
    1. Client connects and sends 512-sample audio chunks (32ms at 16kHz)
    2. Each chunk is:
       - Sent to AssemblyAI for continuous transcription
       - Analyzed by VAD for speech/silence detection
    3. On silence detection after speech:
       - Accumulated transcripts are sent to LLM immediately
       - LLM response is streamed through TTS
       - TTS audio is sent back to client
    4. If new speech detected during TTS:
       - TTS playback is interrupted and cancelled
       - New speech is processed immediately
    
    Message Types Sent to Client:
    - {"type": "transcript", "text": "..."} - Partial transcripts
    - {"type": "llm_response", "transcript": "...", "response": "...", "intent": {...}, ...} - LLM result
    - {"type": "audio_start"} - Indicates TTS audio streaming begins
    - Audio bytes (raw PCM float32 at 44100Hz) - TTS audio chunks
    - {"type": "audio_end"} - Indicates TTS audio streaming complete
    - {"type": "interrupted"} - TTS was interrupted by new speech
    """
    await ws.accept()
    print("✅ WebSocket connected")

    user_id = None

    async def send_user_info():
        """Fetch basic user info via tool call when the call connects."""
        nonlocal user_id
        token = ws.query_params.get("token")
        user_id_param = ws.query_params.get("user_id")

        if token and ConfigEnv.AUTH_JWT_SECRET:
            try:
                payload = jwt.decode(
                    token,
                    ConfigEnv.AUTH_JWT_SECRET,
                    algorithms=["HS256"],
                )
                decoded_user = payload.get("sub")
                if decoded_user:
                    user_id = decoded_user
                    logger.info(f"[STT] user_id from JWT: {user_id}")
            except Exception as exc:
                logger.warning("Failed to decode JWT token: %s", exc)

        if user_id_param and not user_id:
            user_id = user_id_param
            logger.info(f"[STT] user_id from query param: {user_id}")

        if not user_id:
            await ws.send_json({
                "type": "user_info",
                "status": "error",
                "message": "Missing user identifier",
            })
            return

        try:
            registry = get_registry()
            result = await registry.execute_tool("getUserInfo", {"userId": user_id})
            await ws.send_json({
                "type": "user_info",
                "user_id": user_id,
                "result": result,
            })
        except Exception as exc:
            await ws.send_json({
                "type": "user_info",
                "user_id": user_id,
                "status": "error",
                "message": str(exc),
            })

    await send_user_info()
    print(f"🔑 After send_user_info: user_id = {user_id}")

    # State tracking
    conversation_history = []  # Store conversation: [{"role": "user", "text": "..."}, {"role": "assistant", "text": "..."}]
    tts_task = None  # Track active TTS streaming task
    detected_language = "en"  # Track detected language from STT
    processing_lock = asyncio.Lock()  # Prevent concurrent LLM calls
    
    # Handoff state
    handoff_manager = get_handoff_manager()
    handoff_session_id: Optional[str] = None  # Track if user is in handoff queue or active call
    is_agent_connected = False  # Track if agent has joined the call
    
    async def check_agent_connected():
        """Check if an agent has connected to this user's call."""
        nonlocal is_agent_connected, handoff_session_id
        if handoff_session_id and handoff_session_id in handoff_manager.active_calls:
            if not is_agent_connected:
                is_agent_connected = True
                print(f"🎧 Agent connected to session {handoff_session_id}")
            return True
        is_agent_connected = False
        return False
    
    # Utterance accumulation state
    current_utterance_parts = []  # Accumulate transcripts from same utterance
    utterance_timer_task = None  # Timer to finalize utterance after pause
    UTTERANCE_TIMEOUT = 1.0  # Seconds to wait before finalizing utterance
    
    # Get event loop for scheduling tasks from callback thread
    loop = asyncio.get_event_loop()
    
    # Initialize services
    vad_service = VADService()
    llm_service = LLMService()
    tts_service = TTSService()
    
    async def finalize_utterance():
        """Finalize accumulated utterance and trigger LLM processing"""
        nonlocal current_utterance_parts, tts_task, is_agent_connected
        
        if not current_utterance_parts:
            return
        
        # Combine all parts into one user message
        full_text = " ".join(current_utterance_parts).strip()
        current_utterance_parts.clear()
        
        if not full_text:
            return
        
        print(f"✅ Utterance finalized: {full_text}")
        
        # Check if agent is connected - if so, just relay transcript, don't process with LLM
        if await check_agent_connected() and handoff_session_id:
            print(f"🎧 Agent connected - skipping LLM, relaying transcript")
            # Send transcript to agent for display
            await handoff_manager.relay_message_to_agent(handoff_session_id, {
                "type": "user_transcript",
                "text": full_text,
                "language": detected_language,
            })
            # Add to conversation history for record keeping
            conversation_history.append({
                "role": "user",
                "text": full_text
            })
            return
        
        # Cancel any ongoing TTS if user spoke
        if tts_task and not tts_task.done():
            print("🛑 Interrupting previous response - New user utterance")
            tts_task.cancel()
            try:
                await tts_task
            except asyncio.CancelledError:
                pass
        
        # Add to conversation history as user message
        conversation_history.append({
            "role": "user",
            "text": full_text
        })
        
        # Trigger LLM processing
        tts_task = asyncio.create_task(process_and_respond())
    
    # STT service with callbacks
    def on_partial_transcript(text: str, language: str):
        """Handle streaming partial transcripts for real-time feedback"""
        nonlocal detected_language, current_utterance_parts
        
        # Log language changes
        if detected_language != language:
            print(f"🌐 Language changed: {detected_language} → {language}")
        
        # Store detected language
        detected_language = language
        
        # Send partial transcripts to client for real-time display
        # Include accumulated text so far
        accumulated = " ".join(current_utterance_parts)
        full_partial = (accumulated + " " + text).strip() if accumulated else text
        
        # Use call_soon_threadsafe since this callback runs in Soniox's thread
        async def send_partial():
            await ws.send_json({
                "type": "partial_transcript",
                "text": full_partial,
                "language": language
            })
            # Also send to agent if connected
            if is_agent_connected and handoff_session_id:
                await handoff_manager.relay_message_to_agent(handoff_session_id, {
                    "type": "user_transcript",
                    "text": full_partial,
                    "language": language,
                })
        
        loop.call_soon_threadsafe(lambda: asyncio.create_task(send_partial()))
    
    def on_transcript(text: str, language: str):
        nonlocal detected_language, current_utterance_parts, utterance_timer_task
        
        # Log language changes
        if detected_language != language:
            print(f"🌐 Language changed: {detected_language} → {language}")
        
        # Store detected language
        detected_language = language
        
        # Accumulate transcript part
        print(f"📝 Final Transcript ({language}): {text}")
        current_utterance_parts.append(text)
        
        # Cancel existing timer if any
        if utterance_timer_task and not utterance_timer_task.done():
            utterance_timer_task.cancel()
        
        # Start new timer to finalize utterance after pause
        # Use call_soon_threadsafe since this callback runs in Soniox's thread
        def schedule_timer():
            nonlocal utterance_timer_task
            
            async def timer():
                await asyncio.sleep(UTTERANCE_TIMEOUT)
                await finalize_utterance()
            
            utterance_timer_task = asyncio.create_task(timer())
        
        loop.call_soon_threadsafe(schedule_timer)
    

    def on_error(error: str):
        print(f"❌ STT Error: {error}")
    
    stt_service = STTService(
        on_transcript=on_transcript,
        on_partial_transcript=on_partial_transcript,
        on_error=on_error
    )
    
    # Connect to Soniox
    await asyncio.to_thread(stt_service.connect)
    print("🎙️  Connected to Soniox - Ready to receive audio")

    async def process_and_respond():
        """Process transcript with LLM and stream TTS response"""
        nonlocal tts_task, user_id, conversation_history, handoff_session_id, is_agent_connected
        
        # Use lock to prevent concurrent processing
        async with processing_lock:
            # Get the last user message from history
            if not conversation_history or conversation_history[-1]["role"] != "user":
                print("⚠️  No user message to process")
                return
            
            full_transcript = conversation_history[-1]["text"]
            print(f"🔐 process_and_respond: user_id = {user_id}")
            print(f"📄 Processing transcript: {full_transcript}")
            
            # Add user message to conversation history
            conversation_history.append({
                "role": "user",
                "text": full_transcript
            })
            
            # Process with LLM pipeline (streaming)
            print(f"🤖 Calling LLM service (streaming) with conversation context ({len(conversation_history)} turns)...")
            print(f"🔑 user_id being passed to LLM: {user_id}")
            llm_result = await llm_service.process_stream(
                full_transcript,
                conversation_history,
                user_id=user_id,
            )

            stream = llm_result.get("stream")
            print(f"🎯 Intent: {llm_result.get('intent', {}).get('intent', 'unknown')}")

            # Extract tool names
            tool_calls_raw = llm_result.get('tool_calls', [])
            tool_names = []
            for tc in tool_calls_raw:
                if isinstance(tc, dict):
                    tool_names.append(tc.get('name', tc.get('tool_name', 'unknown')))
                elif isinstance(tc, str):
                    tool_names.append(tc)

            if tool_names:
                print(f"🔧 Tools used: {tool_names}")
            
            # Check if requestHumanAgent tool was called
            tool_results = llm_result.get("tool_results", [])
            for result in tool_results:
                if isinstance(result, dict) and result.get("tool_name") == "requestHumanAgent":
                    tool_output = result.get("result", {})
                    # The tool returns {"status": "ok", "action": "handoff_requested", "data": {...}}
                    if isinstance(tool_output, dict) and tool_output.get("action") == "handoff_requested":
                        # Add user to handoff queue
                        handoff_data = tool_output.get("data", {})
                        reason = handoff_data.get("reason", "User requested human agent")
                        print(f"📞 Handoff requested: {reason}")
                        
                        if user_id and not handoff_session_id:
                            handoff_session_id = await handoff_manager.request_handoff(
                                user_id=user_id,
                                user_ws=ws,
                                reason=reason,
                                conversation_history=conversation_history.copy(),
                            )
                            
                            # Notify client about handoff queue
                            await ws.send_json({
                                "type": "handoff_queued",
                                "session_id": handoff_session_id,
                                "message": "You have been added to the queue. A customer service agent will be with you shortly.",
                            })
                            print(f"✅ User {user_id} added to handoff queue (session: {handoff_session_id})")

            # Notify client that LLM streaming is starting
            await ws.send_json(serialize_for_json({
                "type": "llm_start",
                "transcript": full_transcript,
                "intent": llm_result.get("intent", {}),
                "tool_calls": tool_names,
                "tool_results": llm_result.get("tool_results", []),
                "conversation_history": conversation_history[-10:],
            }))

            async def stream_with_last(async_iter):
                it = async_iter.__aiter__()
                try:
                    prev = await it.__anext__()
                except StopAsyncIteration:
                    return
                while True:
                    try:
                        curr = await it.__anext__()
                        yield prev, False
                        prev = curr
                    except StopAsyncIteration:
                        yield prev, True
                        return

            response_text = ""
            tts_context_id = f"tts-{uuid.uuid4()}"
            tts_started = False
            audio_chunk_count = 0

            if stream:
                async for text_chunk, is_last in stream_with_last(stream):
                    # Check for interruption
                    current_task = asyncio.current_task()
                    if current_task and current_task.cancelled():
                        print("⚠️  LLM streaming interrupted")
                        await ws.send_json({"type": "interrupted"})
                        return

                    response_text += text_chunk
                    await ws.send_json({
                        "type": "response_stream",
                        "text": response_text.strip()
                    })

                    if tts_service.enabled and text_chunk.strip():
                        if not tts_started:
                            await ws.send_json({"type": "audio_start"})
                            tts_started = True

                        try:
                            tts_language = normalize_tts_language(detected_language)
                            print(f"🔊 TTS using language: {tts_language} (detected: {detected_language})")
                            async for audio_chunk in tts_service.stream_tts_chunk(
                                transcript=text_chunk,
                                context_id=tts_context_id,
                                continue_flag=not is_last,
                                language=tts_language,
                            ):
                                current_task = asyncio.current_task()
                                if current_task and current_task.cancelled():
                                    print("⚠️  TTS streaming interrupted")
                                    await ws.send_json({"type": "interrupted"})
                                    return

                                await ws.send_bytes(audio_chunk)
                                audio_chunk_count += 1
                        except asyncio.CancelledError:
                            print("⚠️  TTS streaming cancelled by interruption")
                            await ws.send_json({"type": "interrupted"})
                            raise

                if tts_started:
                    await ws.send_json({"type": "audio_end"})
                    print(f"✅ TTS streaming complete ({audio_chunk_count} chunks)\n")

            # Add assistant response to conversation history
            conversation_history.append({
                "role": "assistant",
                "text": response_text
            })

            # Send final LLM metadata to client
            await ws.send_json(serialize_for_json({
                "type": "llm_response",
                "transcript": full_transcript,
                "response": response_text,
                "intent": llm_result.get("intent", {}),
                "tool_calls": tool_names,
                "tool_results": llm_result.get("tool_results", []),
                "conversation_history": conversation_history[-10:]
            }))

            print("✅ Sent final LLM response metadata to client")

    try:
        while True:
            # Receive message (could be audio bytes or JSON)
            message = await ws.receive()
            
            if message["type"] == "websocket.disconnect":
                break
            
            if "bytes" in message:
                audio_bytes = message["bytes"]
                
                # Check if agent is connected
                agent_connected = await check_agent_connected()
                
                if agent_connected and handoff_session_id:
                    # Relay audio to agent
                    await handoff_manager.relay_audio_to_agent(handoff_session_id, audio_bytes)
                
                # Always stream to Soniox for transcription (useful for agent to see transcript)
                try:
                    await asyncio.to_thread(stt_service.stream, audio_bytes)
                except Exception as e:
                    print(f"⚠️  STT streaming error: {e}")
                    # Continue processing, don't crash on STT errors
            
            elif "text" in message:
                # Handle JSON messages from client
                try:
                    data = json.loads(message["text"])
                    msg_type = data.get("type")
                    
                    if msg_type == "ping":
                        await ws.send_json({"type": "pong"})
                except json.JSONDecodeError:
                    pass

    except WebSocketDisconnect:
        print("✋ Client disconnected")
        if tts_task and not tts_task.done():
            tts_task.cancel()
        # Clean up handoff if user was in queue or call
        if handoff_session_id:
            await handoff_manager.cancel_handoff(handoff_session_id)
            await handoff_manager.end_call(handoff_session_id, ended_by="user_disconnect")
    except Exception as e:
        print(f"❌ WebSocket error: {e}")
        import traceback
        traceback.print_exc()
        if tts_task and not tts_task.done():
            tts_task.cancel()
        # Clean up handoff on error
        if handoff_session_id:
            await handoff_manager.cancel_handoff(handoff_session_id)
            await handoff_manager.end_call(handoff_session_id, ended_by="error")
    finally:
        # Cleanup
        try:
            await asyncio.to_thread(stt_service.disconnect)
            print("🔌 Disconnected from Soniox")
        except Exception as e:
            print(f"⚠️  Error disconnecting from Soniox: {e}")


# =========================
# Health Check
# =========================
@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok", "service": "stt"}
