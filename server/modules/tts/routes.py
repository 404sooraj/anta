"""
TTS Routes - FastAPI router definitions for TTS endpoints.
"""
from fastapi import APIRouter, WebSocket

from .controller import handle_tts_websocket

router = APIRouter()


@router.websocket("/ws")
async def tts_websocket(websocket: WebSocket):
    """
    WebSocket endpoint for streaming TTS.
    
    Endpoint: ws://localhost:8000/tts/ws
    
    Client sends:
    - JSON: {"text": "Hello", "language": "auto|hi|en", "voice_id": "..."}
    - Or plain text: "Hello"
    
    Server responds:
    - Status messages: {"status": "processing|complete", "type": "status"}
    - Audio chunks: raw bytes (PCM float32, 44100 Hz, mono)
    - Error messages: {"error": "...", "type": "error"}
    """
    await handle_tts_websocket(websocket)
