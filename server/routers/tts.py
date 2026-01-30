"""
TTS Router - WebSocket endpoint for text-to-speech streaming
"""
import json
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from services.tts import TTSService

logger = logging.getLogger(__name__)

# =========================
# Router Setup
# =========================
router = APIRouter(prefix="/tts", tags=["tts"])

# =========================
# Initialize TTS Service
# =========================
_tts_service = None

def get_tts_service() -> TTSService:
    """Get or create TTS service instance"""
    global _tts_service
    if _tts_service is None:
        _tts_service = TTSService()
    return _tts_service


# =========================
# WebSocket Endpoint
# =========================
@router.websocket("/ws")
async def tts_websocket(websocket: WebSocket):
    """
    WebSocket endpoint for streaming TTS.
    
    Endpoint: ws://localhost:8000/tts/ws
    
    Client sends:
    - New format: {"transcript": "...", "context_id": "...", "continue": true/false, "language": "...", "voice_id": "..."}
    - Legacy format: {"text": "...", "language": "auto|hi|en", "voice_id": "..."}
    
    Server responds:
    - Status messages: {"status": "processing|complete", "type": "status", "chunks": N}
    - Audio chunks: raw bytes (PCM float32, 44100 Hz, mono)
    - Error messages: {"error": "...", "type": "error"}
    """
    await websocket.accept()
    logger.info("TTS WebSocket connected")
    
    tts_service = get_tts_service()
    
    try:
        while True:
            # Receive text chunk from client
            data = await websocket.receive_text()
            
            try:
                # Parse JSON message
                message = json.loads(data)
                
                # Check if this is new format (with context_id) or legacy format
                context_id = message.get("context_id")
                continue_flag = message.get("continue", False)
                transcript = message.get("transcript", "")
                text = message.get("text", "")  # Legacy format
                
                # Determine which format we're using
                if context_id is not None:
                    # New format: context-based streaming
                    language = message.get("language", "auto")
                    voice_id = message.get("voice_id", None)
                    
                    # Allow empty transcript for closing context
                    if transcript == "" and not continue_flag:
                        await websocket.send_json({
                            "status": "complete",
                            "type": "status"
                        })
                        continue
                    
                    if not transcript:
                        await websocket.send_json({
                            "error": "No transcript provided",
                            "type": "error"
                        })
                        continue
                    
                    # Send acknowledgment
                    await websocket.send_json({
                        "status": "processing",
                        "type": "status"
                    })
                    
                    # Stream TTS audio chunks using context-based method
                    chunk_count = 0
                    async for audio_chunk in tts_service.stream_tts_chunk(
                        transcript=transcript,
                        context_id=context_id,
                        continue_flag=continue_flag,
                        language=language,
                        voice_id=voice_id,
                    ):
                        await websocket.send_bytes(audio_chunk)
                        chunk_count += 1
                    
                    # Send completion message
                    await websocket.send_json({
                        "status": "complete",
                        "chunks": chunk_count,
                        "type": "status"
                    })
                
                else:
                    # Legacy format: backward compatibility
                    if not text:
                        await websocket.send_json({
                            "error": "No text provided",
                            "type": "error"
                        })
                        continue
                    
                    language = message.get("language", "auto")
                    voice_id = message.get("voice_id", None)
                    
                    # Send acknowledgment
                    await websocket.send_json({
                        "status": "processing",
                        "type": "status"
                    })
                    
                    # Stream TTS audio chunks
                    chunk_count = 0
                    async for audio_chunk in tts_service.stream_tts(
                        text=text,
                        language=language,
                        voice_id=voice_id,
                    ):
                        await websocket.send_bytes(audio_chunk)
                        chunk_count += 1
                    
                    # Send completion message
                    await websocket.send_json({
                        "status": "complete",
                        "chunks": chunk_count,
                        "type": "status"
                    })
            
            except json.JSONDecodeError:
                # Treat as plain text (legacy support)
                text = data.strip()
                if not text:
                    continue
                
                # Send acknowledgment
                await websocket.send_json({
                    "status": "processing",
                    "type": "status"
                })
                
                # Stream TTS with auto-detected language
                chunk_count = 0
                async for audio_chunk in tts_service.stream_tts(text=text, language="auto"):
                    await websocket.send_bytes(audio_chunk)
                    chunk_count += 1
                
                # Send completion message
                await websocket.send_json({
                    "status": "complete",
                    "chunks": chunk_count,
                    "type": "status"
                })
            
            except Exception as e:
                logger.error(f"Error processing TTS request: {e}")
                await websocket.send_json({
                    "error": str(e),
                    "type": "error"
                })
    
    except WebSocketDisconnect:
        logger.info("TTS WebSocket disconnected")
    except Exception as e:
        logger.error(f"TTS WebSocket error: {e}")
    finally:
        # Cleanup any active contexts for this connection
        logger.info("TTS WebSocket closed")


# =========================
# Health Check
# =========================
@router.get("/health")
async def health_check():
    """Health check endpoint for TTS service"""
    return {"status": "ok", "service": "tts"}
