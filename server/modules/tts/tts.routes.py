"""
TTS Routes - FastAPI router definitions for TTS endpoints.
"""
import sys
import importlib.util
from pathlib import Path
from fastapi import APIRouter, WebSocket

# Load controller module from file path
_current_dir = Path(__file__).parent
controller_path = _current_dir / "tts.controller.py"
spec = importlib.util.spec_from_file_location("tts_controller", controller_path)
_controller_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(_controller_module)
handle_tts_websocket = _controller_module.handle_tts_websocket

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
