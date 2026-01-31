"""
STT Router - WebSocket endpoint for real-time audio streaming
Continuously streams audio to AssemblyAI and processes with LLM on silence,
then streams TTS response back to client
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import asyncio
import json

from services.stt import STTService, VADService
from services.llm import LLMService
from services.tts import TTSService

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

    # State tracking
    speaking = False
    silence_chunks = 0
    transcript_buffer = []
    tts_task = None  # Track active TTS streaming task
    processing_llm = False  # Track if LLM is currently processing
    waiting_for_transcript = False  # Flag to indicate we're waiting for final transcript
    vad_buffer = b""  # Buffer for VAD (needs at least VAD_MIN_BYTES per call)
    
    # Get event loop for scheduling tasks from callback thread
    loop = asyncio.get_event_loop()
    
    # Initialize services
    vad_service = VADService()
    llm_service = LLMService()
    tts_service = TTSService()
    
    # STT service with callbacks
    def on_transcript(text: str):
        nonlocal waiting_for_transcript, tts_task
        
        # Deduplicate - only add if not already the last item
        if not transcript_buffer or transcript_buffer[-1] != text:
            print(f"📝 Transcript: {text}")
            transcript_buffer.append(text)
            
            # If we're waiting for transcript after silence, process now
            # Use call_soon_threadsafe since this callback runs in AssemblyAI's thread
            if waiting_for_transcript and not processing_llm:
                print(f"✅ Transcript received after silence - Processing now!")
                waiting_for_transcript = False
                
                # Schedule task creation on the event loop
                def create_task():
                    nonlocal tts_task
                    tts_task = asyncio.create_task(process_and_respond())
                
                loop.call_soon_threadsafe(create_task)
        else:
            print(f"⏭️  Skipping duplicate transcript: {text}")
    
    def on_error(error: str):
        print(f"❌ STT Error: {error}")
    
    stt_service = STTService(
        on_transcript=on_transcript,
        on_error=on_error
    )
    
    # Connect to AssemblyAI
    await asyncio.to_thread(stt_service.connect)
    print("🎙️  Connected to AssemblyAI - Ready to receive audio")

    async def process_and_respond():
        """Process transcript with LLM and stream TTS response"""
        nonlocal processing_llm, tts_task
        
        if not transcript_buffer:
            print("⚠️  process_and_respond called but transcript_buffer is empty")
            return
        
        processing_llm = True
        
        try:
            # Combine all transcripts
            full_transcript = " ".join(transcript_buffer)
            transcript_buffer.clear()
            
            print(f"📄 Full transcript: {full_transcript}")
            
            # Process with LLM pipeline
            print(f"🤖 Calling LLM service...")
            llm_result = await llm_service.process(full_transcript)
            
            response_text = llm_result.get('response', '')
            print(f"💬 LLM Response: {response_text}")
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
            
            # Send LLM metadata to client
            await ws.send_json({
                "type": "llm_response",
                "transcript": full_transcript,
                "response": response_text,
                "intent": llm_result.get("intent", {}),
                "tool_calls": tool_names,
                "tool_results": llm_result.get("tool_results", [])
            })
            
            print(f"✅ Sent LLM response metadata to client")
            
            # Stream TTS Response
            if response_text and response_text.strip():
                print(f"🔊 Starting TTS streaming...")
                
                # Signal audio start
                await ws.send_json({"type": "audio_start"})
                
                # Stream TTS audio chunks
                audio_chunk_count = 0
                try:
                    async for audio_chunk in tts_service.stream_tts(
                        text=response_text,
                        language="auto"
                    ):
                        # Check if task was cancelled (interrupted)
                        if asyncio.current_task().cancelled():
                            print("⚠️  TTS streaming interrupted")
                            await ws.send_json({"type": "interrupted"})
                            return
                        
                        await ws.send_bytes(audio_chunk)
                        audio_chunk_count += 1
                    
                    # Signal audio end
                    await ws.send_json({"type": "audio_end"})
                    print(f"✅ TTS streaming complete ({audio_chunk_count} chunks)\n")
                
                except asyncio.CancelledError:
                    print("⚠️  TTS streaming cancelled by interruption")
                    await ws.send_json({"type": "interrupted"})
                    raise
            
        finally:
            processing_llm = False
            tts_task = None

    try:
        while True:
            # Receive audio chunk
            audio_bytes = await ws.receive_bytes()

            # Stream to AssemblyAI immediately (no buffering)
            await asyncio.to_thread(stt_service.stream, audio_bytes)

            # Buffer for VAD; Silero requires at least 512 samples (1024 bytes) per chunk
            vad_buffer += audio_bytes
            while len(vad_buffer) >= VAD_MIN_BYTES:
                chunk = vad_buffer[:VAD_MIN_BYTES]
                vad_buffer = vad_buffer[VAD_MIN_BYTES:]
                confidence = vad_service.get_confidence(chunk)

                # Check if new speech detected during TTS playback
                if confidence > vad_service.speech_threshold:
                    # If TTS is currently playing, interrupt it
                    if tts_task and not tts_task.done():
                        print("🛑 Interrupting TTS - New speech detected")
                        tts_task.cancel()
                        try:
                            await tts_task
                        except asyncio.CancelledError:
                            pass
                        tts_task = None

                    speaking = True
                    silence_chunks = 0
                    print(f"🎤 VAD: {confidence:.3f} [SPEECH] | Buffer: {len(transcript_buffer)} transcripts")
                else:
                    # Silence detected
                    if speaking:
                        silence_chunks += 1
                        print(f"🔇 VAD: {confidence:.3f} [silence {silence_chunks}/{SILENCE_LIMIT_CHUNKS}]")

                # Process immediately after silence threshold (only if not already processing)
                if speaking and silence_chunks >= SILENCE_LIMIT_CHUNKS and not processing_llm:
                    print(f"\n🔕 Silence threshold reached - Waiting for transcript...")

                    speaking = False
                    silence_chunks = 0
                    waiting_for_transcript = True

                    # If transcript already in buffer, process immediately
                    if transcript_buffer:
                        print(f"📋 Transcript already available - Processing now!")
                        waiting_for_transcript = False
                        tts_task = asyncio.create_task(process_and_respond())

    except WebSocketDisconnect:
        print("✋ Client disconnected")
        if tts_task and not tts_task.done():
            tts_task.cancel()
    except Exception as e:
        print(f"❌ WebSocket error: {e}")
        import traceback
        traceback.print_exc()
        if tts_task and not tts_task.done():
            tts_task.cancel()
    finally:
        # Cleanup
        await asyncio.to_thread(stt_service.disconnect)
        print("🔌 Disconnected from AssemblyAI")


# =========================
# Health Check
# =========================
@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok", "service": "stt"}
