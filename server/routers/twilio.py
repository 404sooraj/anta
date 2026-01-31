"""
Twilio Voice Router - Bi-directional Media Streams
Handles incoming Twilio voice calls and establishes WebSocket streams
for real-time audio processing with STT, LLM, and TTS pipeline
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import Response
import asyncio
import json
import base64
import audioop
import logging
import numpy as np

from modules.config import ConfigEnv
from services.stt import STTService, VADService
from services.llm import LLMService
from services.tts import TTSService

# =========================
# Router Setup
# =========================
router = APIRouter(prefix="/twilio", tags=["twilio"])
logger = logging.getLogger(__name__)

# =========================
# Twilio Configuration
# =========================
TWILIO_ACCOUNT_SID = ConfigEnv.TWILIO_ACCOUNT_SID or ""
TWILIO_AUTH_TOKEN = ConfigEnv.TWILIO_AUTH_TOKEN or ""
TWILIO_WEBSOCKET_URL = ConfigEnv.TWILIO_WEBSOCKET_URL or "wss://your-domain.com/twilio/media"

# =========================
# Constants
# =========================
# Twilio sends mulaw audio at 8kHz
TWILIO_SAMPLE_RATE = 8000
TWILIO_ENCODING = "audio/x-mulaw"

# Convert to 16kHz PCM16 for Soniox
TARGET_SAMPLE_RATE = 16000

# VAD settings
SILENCE_LIMIT_CHUNKS = 15  # ~0.5s of silence
VAD_MIN_SAMPLES = 512
VAD_MIN_BYTES = VAD_MIN_SAMPLES * 2  # PCM16


# =========================
# TwiML Endpoint
# =========================
@router.api_route("/voice", methods=["GET", "POST"])
async def voice_webhook(request: Request):
    """
    Twilio Voice Webhook - Returns TwiML to start media stream
    Called when an incoming call arrives
    Supports both GET and POST methods
    """
    # Get parameters from query string (GET) or form data (POST)
    if request.method == "GET":
        params = request.query_params
    else:
        params = await request.form()
    
    call_sid = params.get("CallSid", "Unknown")
    from_number = params.get("From", "Unknown")
    
    logger.info(f"📞 Incoming call from {from_number}, CallSid: {call_sid}")
    
    # Use WebSocket URL from environment or default
    ws_url = TWILIO_WEBSOCKET_URL
    
    # Generate TwiML to connect bidirectional media stream
    twiml = f'''<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say>Hello! I'm your voice assistant. Please speak after the beep.</Say>
    <Pause length="1"/>
    <Connect>
        <Stream url="{ws_url}">
            <Parameter name="callSid" value="{call_sid}"/>
            <Parameter name="from" value="{from_number}"/>
        </Stream>
    </Connect>
</Response>'''
    
    return Response(content=twiml, media_type="application/xml")


# =========================
# Media Stream WebSocket
# =========================
@router.websocket("/media")
async def media_stream(ws: WebSocket):
    """
    Twilio Media Stream WebSocket endpoint for bi-directional audio
    
    Receives from Twilio:
    - connected: Connection established
    - start: Stream metadata (callSid, streamSid, etc.)
    - media: Audio chunks (mulaw, 8kHz, base64 encoded)
    - stop: Stream ended
    
    Sends to Twilio:
    - media: Audio chunks (mulaw, 8kHz, base64 encoded) for TTS playback
    - mark: Markers to track playback completion
    """
    await ws.accept()
    logger.info("✅ Twilio WebSocket connected")
    
    # State tracking
    stream_sid = None
    call_sid = None
    speaking = False
    silence_chunks = 0
    transcript_buffer = []
    conversation_history = []
    tts_task = None
    processing_llm = False
    waiting_for_transcript = False
    vad_buffer = b""
    detected_language = "en"  # Track detected language from STT
    
    # Get event loop for thread-safe task creation
    loop = asyncio.get_event_loop()
    
    # Initialize services
    vad_service = VADService()
    llm_service = LLMService()
    tts_service = TTSService()
    
    # STT service with callbacks
    def on_partial_transcript(text: str, language: str):
        """Handle streaming partial transcripts"""
        nonlocal detected_language
        # Store detected language
        detected_language = language
        
        async def send_partial():
            logger.info(f"📝 Partial ({language}): {text}")
        
        loop.call_soon_threadsafe(lambda: asyncio.create_task(send_partial()))
    
    def on_transcript(text: str, language: str):
        nonlocal waiting_for_transcript, tts_task, detected_language
        
        # Store detected language
        detected_language = language
        
        if not transcript_buffer or transcript_buffer[-1] != text:
            logger.info(f"📝 Final Transcript ({language}): {text}")
            transcript_buffer.append(text)
            
            if waiting_for_transcript and not processing_llm:
                logger.info(f"✅ Transcript received - Processing now!")
                waiting_for_transcript = False
                
                def create_task():
                    nonlocal tts_task
                    tts_task = asyncio.create_task(process_and_respond())
                
                loop.call_soon_threadsafe(create_task)
    
    def on_error(error: str):
        logger.error(f"❌ STT Error: {error}")
    
    stt_service = STTService(
        on_transcript=on_transcript,
        on_partial_transcript=on_partial_transcript,
        on_error=on_error
    )
    
    # Connect to Soniox
    await asyncio.to_thread(stt_service.connect)
    logger.info("🎙️ Connected to Soniox")

    async def process_and_respond():
        """Process transcript with LLM and stream TTS response to Twilio"""
        nonlocal processing_llm, tts_task, stream_sid
        
        if not transcript_buffer:
            return
        
        processing_llm = True
        
        try:
            full_transcript = " ".join(transcript_buffer)
            transcript_buffer.clear()
            
            logger.info(f"📄 Processing: {full_transcript}")
            
            # Add to conversation history
            conversation_history.append({"role": "user", "text": full_transcript})
            
            # Process with LLM
            llm_result = await llm_service.process(full_transcript, conversation_history)
            response_text = llm_result.get('response', '')
            
            logger.info(f"💬 LLM Response: {response_text}")
            
            # Add to conversation history
            conversation_history.append({"role": "assistant", "text": response_text})
            
            # Stream TTS Response back to Twilio
            if response_text and response_text.strip() and stream_sid:
                logger.info(f"🔊 Streaming TTS to Twilio...")
                
                try:
                    # Generate TTS audio chunks (PCM float32 44100Hz)
                    async for audio_chunk in tts_service.stream_tts(
                        text=response_text,
                        language=detected_language
                    ):
                        if asyncio.current_task().cancelled():
                            logger.warning("⚠️ TTS interrupted")
                            return
                        
                        # Convert audio_chunk to the right format
                        # TTS returns bytes (PCM float32 44100Hz)
                        if isinstance(audio_chunk, bytes):
                            # Already bytes, convert to numpy array
                            audio_array = np.frombuffer(audio_chunk, dtype=np.float32)
                        else:
                            # Already numpy array
                            audio_array = audio_chunk
                        
                        # Convert Float32 to PCM16
                        audio_int16 = (audio_array * 32767).astype(np.int16)
                        pcm_bytes = audio_int16.tobytes()
                        
                        # 2. Resample from 44100Hz to 8000Hz
                        resampled, _ = audioop.ratecv(
                            pcm_bytes, 
                            2,  # 2 bytes per sample (int16)
                            1,  # mono
                            44100,  # from rate
                            8000,  # to rate
                            None
                        )
                        
                        # 3. Convert to mulaw
                        mulaw_audio = audioop.lin2ulaw(resampled, 2)
                        
                        # 4. Encode to base64
                        payload = base64.b64encode(mulaw_audio).decode('utf-8')
                        
                        # 5. Send to Twilio
                        await ws.send_json({
                            "event": "media",
                            "streamSid": stream_sid,
                            "media": {
                                "payload": payload
                            }
                        })
                    
                    # Send mark to know when playback is done
                    await ws.send_json({
                        "event": "mark",
                        "streamSid": stream_sid,
                        "mark": {
                            "name": "end_of_response"
                        }
                    })
                    
                    logger.info(f"✅ TTS streaming complete\n")
                
                except asyncio.CancelledError:
                    logger.warning("⚠️ TTS cancelled")
                    raise
        
        finally:
            processing_llm = False
            tts_task = None

    try:
        while True:
            message = await ws.receive_text()
            data = json.loads(message)
            
            event_type = data.get("event")
            
            # Handle connection established
            if event_type == "connected":
                logger.info(f"🔗 Twilio connected: {data}")
            
            # Handle stream start - get metadata
            elif event_type == "start":
                stream_sid = data.get("streamSid")
                call_sid = data.get("start", {}).get("callSid")
                logger.info(f"🎬 Stream started - StreamSid: {stream_sid}, CallSid: {call_sid}")
            
            # Handle incoming audio media
            elif event_type == "media":
                media = data.get("media", {})
                payload = media.get("payload")
                
                if payload:
                    # Decode base64 mulaw audio
                    mulaw_audio = base64.b64decode(payload)
                    
                    # Convert mulaw to linear PCM16
                    pcm_audio = audioop.ulaw2lin(mulaw_audio, 2)
                    
                    # Resample from 8kHz to 16kHz for Soniox
                    resampled, _ = audioop.ratecv(
                        pcm_audio,
                        2,  # 2 bytes per sample
                        1,  # mono
                        8000,  # from rate
                        16000,  # to rate
                        None
                    )
                    
                    # Stream to Soniox
                    try:
                        await asyncio.to_thread(stt_service.stream, resampled)
                    except Exception as e:
                        logger.error(f"⚠️ STT streaming error: {e}")
                    
                    # VAD processing
                    vad_buffer += resampled
                    while len(vad_buffer) >= VAD_MIN_BYTES:
                        chunk = vad_buffer[:VAD_MIN_BYTES]
                        vad_buffer = vad_buffer[VAD_MIN_BYTES:]
                        confidence = vad_service.get_confidence(chunk)
                        
                        # Check for speech
                        if confidence > vad_service.speech_threshold:
                            # Interrupt TTS if playing
                            if tts_task and not tts_task.done():
                                logger.info("🛑 Interrupting TTS")
                                tts_task.cancel()
                                try:
                                    await tts_task
                                except asyncio.CancelledError:
                                    pass
                                tts_task = None
                            
                            # Clear old transcripts on new speech
                            if not speaking:
                                logger.info("🎤 New speech started")
                                transcript_buffer.clear()
                                waiting_for_transcript = False
                            
                            speaking = True
                            silence_chunks = 0
                        else:
                            # Silence detected
                            if speaking:
                                silence_chunks += 1
                        
                        # Process after silence threshold
                        if speaking and silence_chunks >= SILENCE_LIMIT_CHUNKS and not processing_llm:
                            logger.info(f"🔕 Silence detected - Waiting for transcript...")
                            speaking = False
                            waiting_for_transcript = True
                            
                            if transcript_buffer:
                                logger.info(f"📋 Transcript ready - Processing now!")
                                waiting_for_transcript = False
                                tts_task = asyncio.create_task(process_and_respond())
                            
                            # Reset silence_chunks to prevent infinite counting
                            silence_chunks = 0
            
            # Handle stream stop
            elif event_type == "stop":
                logger.info(f"🛑 Stream stopped: {data}")
                break
            
            # Handle mark (playback confirmation)
            elif event_type == "mark":
                mark_name = data.get("mark", {}).get("name")
                logger.info(f"✅ Mark received: {mark_name}")
    
    except WebSocketDisconnect:
        logger.info("✋ Twilio disconnected")
        if tts_task and not tts_task.done():
            tts_task.cancel()
    except Exception as e:
        logger.error(f"❌ WebSocket error: {e}", exc_info=True)
        if tts_task and not tts_task.done():
            tts_task.cancel()
    finally:
        # Cleanup
        try:
            await asyncio.to_thread(stt_service.disconnect)
            logger.info("🔌 Disconnected from Soniox")
        except Exception as e:
            logger.warning(f"⚠️ Error disconnecting: {e}")


# =========================
# Status Callback
# =========================
@router.post("/status")
async def stream_status(request: Request):
    """
    Receives status callbacks from Twilio about stream state
    """
    form_data = await request.form()
    logger.info(f"📊 Stream status: {dict(form_data)}")
    return {"status": "ok"}
