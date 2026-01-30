"""
STT Router - WebSocket endpoint for real-time audio streaming
Continuously streams audio to AssemblyAI and processes with LLM on silence
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import asyncio

from services.stt import STTService, VADService
from services.llm import LLMService

# =========================
# Router Setup
# =========================
router = APIRouter(prefix="/stt", tags=["stt"])

# =========================
# Constants
# =========================
SILENCE_LIMIT_CHUNKS = 15  # ~0.5s of silence to trigger LLM


# =========================
# WebSocket Endpoint
# =========================
@router.websocket("/ws/audio")
async def audio_websocket(ws: WebSocket):
    """
    WebSocket endpoint for real-time audio streaming.
    
    Flow:
    1. Client connects and sends 512-sample audio chunks (32ms at 16kHz)
    2. Each chunk is:
       - Sent to AssemblyAI for continuous transcription
       - Analyzed by VAD for speech/silence detection
    3. On silence detection after speech:
       - Accumulated transcripts are sent to LLM
       - LLM response is returned to client
    """
    await ws.accept()
    print("✅ WebSocket connected")

    # State tracking
    speaking = False
    silence_chunks = 0
    transcript_buffer = []
    
    # Initialize services
    vad_service = VADService()
    llm_service = LLMService()
    
    # STT service with callbacks
    def on_transcript(text: str):
        print(f"📝 Transcript: {text}")
        transcript_buffer.append(text)
    
    def on_error(error: str):
        print(f"❌ STT Error: {error}")
    
    stt_service = STTService(
        on_transcript=on_transcript,
        on_error=on_error
    )
    
    # Connect to AssemblyAI
    await asyncio.to_thread(stt_service.connect)
    print("🎙️  Connected to AssemblyAI - Ready to receive audio")

    try:
        while True:
            # Receive audio chunk
            audio_bytes = await ws.receive_bytes()

            # Get VAD confidence
            confidence = vad_service.get_confidence(audio_bytes)
            
            # Stream to AssemblyAI continuously
            await asyncio.to_thread(stt_service.stream, audio_bytes)

            # Track speech/silence
            if confidence > vad_service.speech_threshold:
                speaking = True
                silence_chunks = 0
                print(f"🎤 VAD: {confidence:.3f} [SPEECH] | Buffer: {len(transcript_buffer)} transcripts")
            else:
                if speaking:
                    silence_chunks += 1
                    print(f"🔇 VAD: {confidence:.3f} [silence {silence_chunks}/{SILENCE_LIMIT_CHUNKS}]")

            # =========================
            # Silence Detected → Process with LLM
            # =========================
            if speaking and silence_chunks >= SILENCE_LIMIT_CHUNKS:
                print(f"\n🔕 Silence threshold reached - Processing with LLM")
                
                speaking = False
                silence_chunks = 0
                
                # Wait for final transcripts
                await asyncio.sleep(0.5)
                
                if transcript_buffer:
                    # Combine all transcripts
                    full_transcript = " ".join(transcript_buffer)
                    transcript_buffer.clear()
                    
                    print(f"📄 Full transcript: {full_transcript}")
                    
                    # Process with LLM pipeline
                    llm_result = await llm_service.process(full_transcript)
                    
                    print(f"💬 LLM Response: {llm_result.get('response', '')}")
                    print(f"🎯 Intent: {llm_result.get('intent', {}).get('intent', 'unknown')}")
                    
                    # Extract tool names (handle both string lists and dict lists)
                    tool_calls_raw = llm_result.get('tool_calls', [])
                    tool_names = []
                    for tc in tool_calls_raw:
                        if isinstance(tc, dict):
                            tool_names.append(tc.get('name', tc.get('tool_name', 'unknown')))
                        elif isinstance(tc, str):
                            tool_names.append(tc)
                    
                    if tool_names:
                        print(f"🔧 Tools used: {tool_names}")
                    
                    # Send to client
                    await ws.send_json({
                        "type": "llm_response",
                        "transcript": full_transcript,
                        "response": llm_result.get("response", ""),
                        "intent": llm_result.get("intent", {}),
                        "tool_calls": tool_names,
                        "tool_results": llm_result.get("tool_results", [])
                    })
                    
                    print(f"✅ Sent LLM response to client\n")

    except WebSocketDisconnect:
        print("✋ Client disconnected")
    except Exception as e:
        print(f"❌ WebSocket error: {e}")
        import traceback
        traceback.print_exc()
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
