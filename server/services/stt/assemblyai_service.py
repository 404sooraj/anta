"""
STT Service - AssemblyAI Streaming Integration
Handles continuous audio streaming to AssemblyAI
"""
import assemblyai as aai
from assemblyai.streaming.v3 import (
    StreamingClient,
    StreamingClientOptions,
    StreamingParameters,
    StreamingEvents,
    TurnEvent,
    StreamingError,
)
from typing import Type, Callable, Optional
import os
from dotenv import load_dotenv

load_dotenv()

# =========================
# Configuration
# =========================
SAMPLE_RATE = 16000
aai.settings.api_key = os.getenv("ASSEMBLYAI_API_KEY", "")


# =========================
# STT Service
# =========================
class STTService:
    """Manages continuous streaming to AssemblyAI"""
    
    def __init__(
        self,
        on_transcript: Optional[Callable[[str], None]] = None,
        on_error: Optional[Callable[[str], None]] = None
    ):
        self.client: Optional[StreamingClient] = None
        self.on_transcript_callback = on_transcript
        self.on_error_callback = on_error
        self.audio_buffer = bytearray()  # Buffer for accumulating chunks
        self.min_chunk_size = 1600  # 50ms at 16kHz = 800 samples = 1600 bytes
        
    def create_client(self) -> StreamingClient:
        """Create and configure AssemblyAI streaming client"""
        # Capture callbacks in closure
        transcript_callback = self.on_transcript_callback
        error_callback = self.on_error_callback
        
        client = StreamingClient(
            StreamingClientOptions(
                api_key=aai.settings.api_key,
            )
        )
        
        def on_turn(self: Type[StreamingClient], event: TurnEvent):
            # Only process final transcripts (not partial updates)
            if event.transcript and event.end_of_turn and transcript_callback:
                transcript_callback(event.transcript)
        
        def on_error(self: Type[StreamingClient], error: StreamingError):
            if error_callback:
                error_callback(str(error))
        
        client.on(StreamingEvents.Turn, on_turn)
        client.on(StreamingEvents.Error, on_error)
        
        return client
    
    def connect(self):
        """Connect to AssemblyAI streaming service"""
        self.client = self.create_client()
        self.client.connect(
            StreamingParameters(
                sample_rate=SAMPLE_RATE,
                format_turns=True
            )
        )
    
    def stream(self, audio_bytes: bytes):
        """Stream audio chunk to AssemblyAI (buffers to meet 50ms minimum)"""
        if not self.client:
            return
        
        # Add to buffer
        self.audio_buffer.extend(audio_bytes)
        
        # Send when we have at least 50ms worth of audio
        while len(self.audio_buffer) >= self.min_chunk_size:
            # Extract chunk (100ms = 3200 bytes for better efficiency)
            chunk_size = min(3200, len(self.audio_buffer))
            chunk = bytes(self.audio_buffer[:chunk_size])
            del self.audio_buffer[:chunk_size]
            
            # Send to AssemblyAI
            self.client.stream(chunk)
    
    def disconnect(self):
        """Disconnect from AssemblyAI"""
        if self.client:
            # Flush any remaining buffer
            if len(self.audio_buffer) >= self.min_chunk_size:
                self.client.stream(bytes(self.audio_buffer))
            self.audio_buffer.clear()
            
            self.client.disconnect(terminate=True)
            self.client = None
