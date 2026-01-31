"""
STT Service - Soniox Streaming Integration
Handles continuous audio streaming to Soniox WebSocket API
"""
import json
import asyncio
from typing import Callable, Optional
from websockets.sync.client import connect, ClientConnection
import os
from dotenv import load_dotenv
import threading
import logging

load_dotenv()

logger = logging.getLogger(__name__)

# =========================
# Configuration
# =========================
SAMPLE_RATE = 16000
SONIOX_WEBSOCKET_URL = "wss://stt-rt.soniox.com/transcribe-websocket"
SONIOX_API_KEY = os.getenv("SONIOX_API_KEY", "")


# =========================
# STT Service
# =========================
class STTService:
    """Manages continuous streaming to Soniox WebSocket API"""
    
    def __init__(
        self,
        on_transcript: Optional[Callable[[str, str], None]] = None,
        on_partial_transcript: Optional[Callable[[str, str], None]] = None,
        on_error: Optional[Callable[[str], None]] = None
    ):
        self.ws: Optional[ClientConnection] = None
        self.on_transcript_callback = on_transcript
        self.on_partial_transcript_callback = on_partial_transcript
        self.on_error_callback = on_error
        self.receive_thread: Optional[threading.Thread] = None
        self.running = False
        
    def connect(self):
        """Connect to Soniox WebSocket API"""
        try:
            # Connect to Soniox WebSocket
            self.ws = connect(SONIOX_WEBSOCKET_URL)
            
            # Send initial configuration
            config = {
                "api_key": SONIOX_API_KEY,
                "model": "stt-rt-v3",
                "audio_format": "pcm_s16le",
                "sample_rate": SAMPLE_RATE,
                "num_channels": 1,
                "language_hints": ["en", "hi"],  # Support English and Hindi
                "enable_language_identification": True,  # Identify which language is spoken
                "enable_endpoint_detection": False,  # We handle this with VAD
            }
            
            self.ws.send(json.dumps(config))
            logger.info("✓ Connected to Soniox WebSocket API")
            
            # Start thread to receive messages
            self.running = True
            self.receive_thread = threading.Thread(target=self._receive_messages, daemon=True)
            self.receive_thread.start()
            
        except Exception as e:
            logger.error(f"Failed to connect to Soniox: {e}")
            if self.on_error_callback:
                self.on_error_callback(str(e))
            raise
    
    def _receive_messages(self):
        """Receive and process messages from Soniox WebSocket (runs in thread)"""
        try:
            while self.running and self.ws:
                try:
                    message = self.ws.recv()
                    if not message:
                        continue
                    
                    # Parse JSON response
                    response = json.loads(message)
                    
                    # Handle errors
                    if response.get("error_code"):
                        error_msg = f"{response.get('error_code')}: {response.get('error_message', 'Unknown error')}"
                        logger.error(f"Soniox error: {error_msg}")
                        if self.on_error_callback:
                            self.on_error_callback(error_msg)
                        continue
                    
                    # Process tokens
                    tokens = response.get("tokens", [])
                    if tokens:
                        # Separate final and non-final tokens
                        final_text = ""
                        partial_text = ""
                        detected_language = "en"  # Default to English
                        
                        for token in tokens:
                            text = token.get("text", "")
                            # Get language from first token with language info
                            if token.get("language") and detected_language == "en":
                                detected_language = token.get("language")
                            
                            if token.get("is_final"):
                                final_text += text
                            else:
                                partial_text += text
                        
                        # Send partial transcripts (non-final tokens) with language
                        if partial_text and self.on_partial_transcript_callback:
                            self.on_partial_transcript_callback(partial_text.strip(), detected_language)
                        
                        # Send final transcripts with language
                        if final_text and self.on_transcript_callback:
                            self.on_transcript_callback(final_text.strip(), detected_language)
                    
                    # Check if session finished
                    if response.get("finished"):
                        logger.info("Soniox session finished")
                        break
                        
                except Exception as e:
                    if self.running:
                        logger.error(f"Error receiving message: {e}")
                        if self.on_error_callback:
                            self.on_error_callback(str(e))
                    break
                    
        except Exception as e:
            logger.error(f"Receive thread error: {e}")
            if self.on_error_callback:
                self.on_error_callback(str(e))
    
    def stream(self, audio_bytes: bytes):
        """Stream audio chunk to Soniox"""
        if not self.ws or not self.running:
            return
        
        try:
            # Send raw audio bytes
            self.ws.send(audio_bytes)
        except Exception as e:
            logger.error(f"Error streaming audio: {e}")
            if self.on_error_callback:
                self.on_error_callback(str(e))
    
    def disconnect(self):
        """Disconnect from Soniox"""
        self.running = False
        
        if self.ws:
            try:
                # Send empty string to signal end of audio
                self.ws.send("")
                self.ws.close()
            except Exception as e:
                logger.warning(f"Error disconnecting: {e}")
            finally:
                self.ws = None
        
        # Wait for receive thread to finish
        if self.receive_thread and self.receive_thread.is_alive():
            self.receive_thread.join(timeout=2.0)
