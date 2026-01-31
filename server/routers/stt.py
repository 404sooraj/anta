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
from typing import Literal, cast

import jwt

from services.stt import STTService, VADService
from services.llm import LLMService
from services.tts import TTSService
from modules.config import ConfigEnv
from modules.response.tool_registry import get_registry

TTSLanguage = Literal["hi", "en", "auto"]

logger = logging.getLogger(__name__)

def normalize_tts_language(lang: str) -> TTSLanguage:
    if lang in ("hi", "en"):
        return cast(TTSLanguage, lang)
    return "auto"


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

    async def send_user_info():
        """Fetch basic user info via tool call when the call connects."""
        token = ws.query_params.get("token")
        user_id = ws.query_params.get("user_id")

        if token and ConfigEnv.AUTH_JWT_SECRET:
            try:
                payload = jwt.decode(
                    token,
                    ConfigEnv.AUTH_JWT_SECRET,
                    algorithms=["HS256"],
                )
                user_id = payload.get("sub") or user_id
            except Exception as exc:
                logger.warning("Failed to decode JWT token: %s", exc)

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

    # State tracking
    speaking = False
    silence_chunks = 0
    transcript_buffer = []
    conversation_history = []  # Store conversation: [{"role": "user", "text": "..."}, {"role": "assistant", "text": "..."}]
    tts_task = None  # Track active TTS streaming task
    processing_llm = False  # Track if LLM is currently processing
    waiting_for_transcript = False  # Flag to indicate we're waiting for final transcript
    vad_buffer = b""  # Buffer for VAD (needs at least VAD_MIN_BYTES per call)
    detected_language = "en"  # Track detected language from STT
    
    # Get event loop for scheduling tasks from callback thread
    loop = asyncio.get_event_loop()
    
    # Initialize services
    vad_service = VADService()
    llm_service = LLMService()
    tts_service = TTSService()
    
    # STT service with callbacks
    def on_partial_transcript(text: str, language: str):
        """Handle streaming partial transcripts for real-time feedback"""
        nonlocal detected_language
        # Store detected language
        detected_language = language
        
        # Send partial transcripts to client for real-time display
        # Use call_soon_threadsafe since this callback runs in Soniox's thread
        async def send_partial():
            await ws.send_json({
                "type": "partial_transcript",
                "text": text,
                "language": language
            })
        
        loop.call_soon_threadsafe(lambda: asyncio.create_task(send_partial()))
    
    def on_transcript(text: str, language: str):
        nonlocal waiting_for_transcript, tts_task, detected_language
        
        # Store detected language
        detected_language = language
        
        # Deduplicate - only add if not already the last item
        if not transcript_buffer or transcript_buffer[-1] != text:
            print(f"📝 Final Transcript ({language}): {text}")
            transcript_buffer.append(text)
            
            # If we're waiting for transcript after silence, process now
            # Use call_soon_threadsafe since this callback runs in Soniox's thread
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
        on_partial_transcript=on_partial_transcript,
        on_error=on_error
    )
    
    # Connect to Soniox
    await asyncio.to_thread(stt_service.connect)
    print("🎙️  Connected to Soniox - Ready to receive audio")

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
            
            # Add user message to conversation history
            conversation_history.append({
                "role": "user",
                "text": full_transcript
            })
            
            # Process with LLM pipeline (streaming)
            print(f"🤖 Calling LLM service (streaming) with conversation context ({len(conversation_history)} turns)...")
            llm_result = await llm_service.process_stream(full_transcript, conversation_history)

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

            # Notify client that LLM streaming is starting
            await ws.send_json({
                "type": "llm_start",
                "transcript": full_transcript,
                "intent": llm_result.get("intent", {}),
                "tool_calls": tool_names,
                "tool_results": llm_result.get("tool_results", []),
                "conversation_history": conversation_history[-10:],
            })

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
            if response_text.strip():
                conversation_history.append({
                    "role": "assistant",
                    "text": response_text
                })

            # Send final LLM metadata to client
            await ws.send_json({
                "type": "llm_response",
                "transcript": full_transcript,
                "response": response_text,
                "intent": llm_result.get("intent", {}),
                "tool_calls": tool_names,
                "tool_results": llm_result.get("tool_results", []),
                "conversation_history": conversation_history[-10:]
            })

            print("✅ Sent final LLM response metadata to client")
            
        finally:
            processing_llm = False
            tts_task = None

    try:
        while True:
            # Receive audio chunk
            audio_bytes = await ws.receive_bytes()

            # Stream to AssemblyAI immediately (no buffering)
            try:
                await asyncio.to_thread(stt_service.stream, audio_bytes)
            except Exception as e:
                print(f"⚠️  STT streaming error: {e}")
                # Continue processing, don't crash on STT errors

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

                    # If this is the START of new speech (wasn't speaking before)
                    if not speaking:
                        print("🎤 New speech started")

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
                    waiting_for_transcript = True

                    # If transcript already in buffer, process immediately
                    if transcript_buffer:
                        print(f"📋 Transcript already available - Processing now!")
                        waiting_for_transcript = False
                        tts_task = asyncio.create_task(process_and_respond())
                    
                    # Reset silence_chunks to prevent infinite counting
                    silence_chunks = 0

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
