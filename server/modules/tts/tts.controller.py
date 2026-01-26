"""
TTS Controller - Handles WebSocket connections for TTS streaming.
"""
import json
from typing import Optional

from fastapi import WebSocket, WebSocketDisconnect

import sys
import importlib.util
from pathlib import Path

# Load service module from file path
_current_dir = Path(__file__).parent
service_path = _current_dir / "tts.service.py"
spec = importlib.util.spec_from_file_location("tts_service", service_path)
_service_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(_service_module)
get_tts_service = _service_module.get_tts_service


async def handle_tts_websocket(websocket: WebSocket):
    """
    Handle WebSocket connection for streaming TTS.
    
    Protocol:
    - New format (with context): {"transcript": "...", "context_id": "...", "continue": true/false, "language": "...", "voice_id": "..."}
    - Legacy format (backward compatible): {"text": "...", "language": "auto|hi|en", "voice_id": "..."}
    - Server streams audio chunks back as bytes
    - Client can send multiple text chunks
    - Client closes connection when done
    
    Args:
        websocket: WebSocket connection
    """
    await websocket.accept()
    
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
                        # Closing context with empty transcript
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
                        # Send audio chunk
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
                    
                    # Stream TTS audio chunks using legacy method
                    chunk_count = 0
                    async for audio_chunk in tts_service.stream_tts(
                        text=text,
                        language=language,
                        voice_id=voice_id,
                    ):
                        # Send audio chunk
                        await websocket.send_bytes(audio_chunk)
                        chunk_count += 1
                    
                    # Send completion message
                    await websocket.send_json({
                        "status": "complete",
                        "chunks": chunk_count,
                        "type": "status"
                    })
            
            except json.JSONDecodeError:
                # If not JSON, treat as plain text (legacy format)
                if data.strip():
                    await websocket.send_json({
                        "status": "processing",
                        "type": "status"
                    })
                    
                    chunk_count = 0
                    async for audio_chunk in tts_service.stream_tts(text=data):
                        await websocket.send_bytes(audio_chunk)
                        chunk_count += 1
                    
                    await websocket.send_json({
                        "status": "complete",
                        "chunks": chunk_count,
                        "type": "status"
                    })
            
            except Exception as e:
                # Send error message
                await websocket.send_json({
                    "error": str(e),
                    "type": "error"
                })
    
    except WebSocketDisconnect:
        # Client disconnected normally
        pass
    
    except Exception as e:
        # Unexpected error
        try:
            await websocket.send_json({
                "error": f"Server error: {str(e)}",
                "type": "error"
            })
        except:
            pass  # Connection may already be closed
    
    finally:
        # Cleanup if needed
        try:
            await websocket.close()
        except:
            pass
