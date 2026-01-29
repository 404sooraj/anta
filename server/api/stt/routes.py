import io
import numpy as np
import torch
torch.set_num_threads(1)

from fastapi import APIRouter, WebSocket
from silero_vad import load_silero_vad

import assemblyai as aai
from assemblyai.streaming.v3 import (
    StreamingClient,
    StreamingClientOptions,
    StreamingParameters,
    StreamingEvents,
    TurnEvent,
    StreamingError,
)
from typing import Type

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# =========================
# AssemblyAI API Key
# =========================
aai.settings.api_key = os.getenv("ASSEMBLYAI_API_KEY", "")

# =========================
# Router Setup
# =========================
router = APIRouter(prefix="/stt", tags=["stt"])

# =========================
# Load Silero VAD
# =========================
model = load_silero_vad()

# =========================
# Constants
# =========================
SAMPLE_RATE = 16000
SPEECH_THRESHOLD = 0.6
SILENCE_LIMIT_CHUNKS = 15  # ~0.5s of silence
MIN_SPEECH_DURATION = 0.3  # Minimum 0.3s of speech to transcribe


# =========================
# PCM16 → Float32
# =========================
def int2float(sound):
    abs_max = np.abs(sound).max()
    sound = sound.astype("float32")
    if abs_max > 0:
        sound *= 1 / 32768
    return sound.squeeze()


# =========================
# Send Speech to AssemblyAI Streaming
# =========================
def transcribe_with_assemblyai(audio_float32: np.ndarray):
    """Synchronous transcription using AssemblyAI streaming"""
    transcript_text = ""

    client = StreamingClient(
        StreamingClientOptions(
            api_key=aai.settings.api_key,
        )
    )

    def on_turn(self: Type[StreamingClient], event: TurnEvent):
        nonlocal transcript_text
        if event.transcript:
            transcript_text = event.transcript
            print(f"Received transcript: {transcript_text}")

    def on_error(self: Type[StreamingClient], error: StreamingError):
        print(f"AssemblyAI Error: {error}")

    # Register event handlers using the event system
    client.on(StreamingEvents.Turn, on_turn)
    client.on(StreamingEvents.Error, on_error)

    # Connect to streaming service
    client.connect(
        StreamingParameters(
            sample_rate=SAMPLE_RATE,
            format_turns=True
        )
    )

    # Convert float32 → PCM16 bytes
    pcm16 = (audio_float32 * 32767).astype(np.int16).tobytes()
    
    # Stream in chunks of 100ms (1600 samples at 16kHz = 3200 bytes)
    # AssemblyAI requires chunks between 50-1000ms
    chunk_size = 3200  # 100ms at 16kHz, 16-bit PCM
    
    for i in range(0, len(pcm16), chunk_size):
        chunk = pcm16[i:i+chunk_size]
        # Only send if chunk is at least 50ms (1600 bytes)
        if len(chunk) >= 1600:
            client.stream(chunk)

    # Disconnect and wait for processing to complete
    client.disconnect(terminate=True)

    return transcript_text.strip()


# =========================
# WebSocket Route
# =========================
@router.websocket("/ws/audio")
async def audio_websocket(ws: WebSocket):
    await ws.accept()
    print("WebSocket connected")

    speech_buffer = []
    silence_chunks = 0
    speaking = False

    try:
        while True:
            audio_bytes = await ws.receive_bytes()

            audio_int16 = np.frombuffer(audio_bytes, np.int16)
            audio_float32 = int2float(audio_int16)

            audio_tensor = torch.from_numpy(audio_float32)

            # =========================
            # Silero Confidence
            # =========================
            confidence = model(audio_tensor, SAMPLE_RATE).item()
            
            print(f"VAD Confidence: {confidence:.3f} | Speaking: {speaking} | Silence: {silence_chunks}")

            # Speech
            if confidence > SPEECH_THRESHOLD:
                speaking = True
                silence_chunks = 0
                speech_buffer.append(audio_float32)

            # Silence
            else:
                if speaking:
                    silence_chunks += 1

            # =========================
            # Speech End → Send to AssemblyAI
            # =========================
            if speaking and silence_chunks >= SILENCE_LIMIT_CHUNKS:
                print(f"\n🎤 Speech ended! Buffer size: {len(speech_buffer)} chunks")
                
                speaking = False
                silence_chunks = 0

                full_audio = np.concatenate(speech_buffer)
                speech_buffer.clear()
                
                duration = len(full_audio) / SAMPLE_RATE
                print(f"📊 Audio duration: {duration:.2f}s")
                
                # Only transcribe if audio is long enough
                if duration < MIN_SPEECH_DURATION:
                    print(f"⚠️ Audio too short ({duration:.2f}s), skipping transcription")
                    continue
                
                print("Sending to AssemblyAI Streaming...")

                # Run blocking function in thread pool to avoid blocking event loop
                import asyncio
                text = await asyncio.to_thread(transcribe_with_assemblyai, full_audio)
                
                print(f"✅ Transcript received: {text}")

                if text:
                    await ws.send_json({
                        "type": "transcript",
                        "text": text
                    })

    except Exception as e:
        print("WebSocket closed:", e)
