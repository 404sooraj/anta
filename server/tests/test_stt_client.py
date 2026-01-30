"""
WebSocket Audio Client for Testing STT → LLM → TTS Pipeline
Captures audio from microphone, sends to server, receives TTS audio response and plays it
"""
import asyncio
import websockets
import sounddevice as sd
import numpy as np
import json
import queue
import threading

# =========================
# Configuration
# =========================
WEBSOCKET_URL = "ws://127.0.0.1:8000/stt/ws/audio"
INPUT_SAMPLE_RATE = 16000  # STT input
OUTPUT_SAMPLE_RATE = 44100  # TTS output
CHANNELS = 1
CHUNK_SIZE = 512  # Silero VAD requires exactly 512 samples for 16kHz (32ms chunks)

# =========================
# Audio Stream Handler
# =========================
class AudioStreamer:
    def __init__(self):
        self.websocket = None
        self.input_stream = None
        self.output_stream = None
        self.running = False
        self.audio_playback_queue = queue.Queue()
        self.playing_audio = False
        self.stop_playback = threading.Event()  # Signal to stop audio playback
        
    async def receive_messages(self):
        """Listen for transcripts, LLM responses, and TTS audio from server"""
        try:
            while self.running:
                message = await self.websocket.recv()
                
                # Check if it's JSON or raw audio bytes
                if isinstance(message, bytes):
                    # Raw audio bytes from TTS
                    if self.playing_audio:
                        # Convert bytes to float32 numpy array
                        audio_data = np.frombuffer(message, dtype=np.float32)
                        self.audio_playback_queue.put(audio_data)
                else:
                    # JSON message
                    try:
                        data = json.loads(message)
                        
                        if data.get("type") == "llm_response":
                            print(f"\n" + "="*70)
                            print(f"🎤 TRANSCRIPT: {data.get('transcript')}")
                            print(f"🎯 INTENT: {data.get('intent', {}).get('intent', 'unknown')}")
                            
                            # Show tool usage if any
                            if data.get('tool_calls'):
                                print(f"🔧 TOOLS USED: {', '.join(data.get('tool_calls', []))}")
                            
                            print(f"\n🤖 RESPONSE:\n{data.get('response')}")
                            print("="*70)
                        
                        elif data.get("type") == "audio_start":
                            print("\n🔊 Receiving TTS audio...", flush=True)
                            self.playing_audio = True
                            # Start audio playback in separate thread
                            threading.Thread(target=self._play_audio, daemon=True).start()
                        
                        elif data.get("type") == "audio_end":
                            print("✅ TTS audio complete\n")
                            # Signal end of audio
                            self.audio_playback_queue.put(None)
                            self.playing_audio = False
                        
                        elif data.get("type") == "interrupted":
                            print("⚠️  TTS interrupted - New speech detected\n")
                            # Signal audio playback thread to stop immediately
                            self.stop_playback.set()
                            # Clear playback queue
                            while not self.audio_playback_queue.empty():
                                try:
                                    self.audio_playback_queue.get_nowait()
                                except:
                                    break
                            self.playing_audio = False
                    
                    except json.JSONDecodeError:
                        print(f"Received non-JSON text: {message}")
        
        except websockets.exceptions.ConnectionClosed:
            print("Connection closed by server")
        except Exception as e:
            print(f"Error receiving message: {e}")
    
    def _play_audio(self):
        """Play audio from queue (runs in separate thread)"""
        try:
            self.stop_playback.clear()
            with sd.OutputStream(
                samplerate=OUTPUT_SAMPLE_RATE,
                channels=CHANNELS,
                dtype='float32'
            ) as stream:
                while True:
                    # Check if we should stop
                    if self.stop_playback.is_set():
                        print("🛑 Audio playback stopped by interruption")
                        break
                    
                    try:
                        # Use timeout to allow checking stop signal
                        audio_chunk = self.audio_playback_queue.get(timeout=0.1)
                        if audio_chunk is None:  # End signal
                            break
                        stream.write(audio_chunk)
                    except queue.Empty:
                        continue
        except Exception as e:
            print(f"Audio playback error: {e}")
    
    async def start_streaming(self):
        """Main streaming loop"""
        print(f"Connecting to {WEBSOCKET_URL}...")
        
        try:
            async with websockets.connect(WEBSOCKET_URL) as websocket:
                self.websocket = websocket
                self.running = True
                
                print("✅ Connected to WebSocket!")
                print(f"🎙️  Recording audio at {INPUT_SAMPLE_RATE}Hz...")
                print("🔊 Will play TTS responses at 44100Hz")
                print("Speak into your microphone. Press Ctrl+C to stop.\n")
                
                # Create async queue for audio
                audio_queue = asyncio.Queue()
                
                # Get the current event loop reference
                loop = asyncio.get_running_loop()
                
                def sync_callback(indata, frames, time_info, status):
                    """Sync callback that puts data in async queue"""
                    if status:
                        print(f"Audio status: {status}")
                    
                    # Convert float32 to int16 PCM
                    audio_int16 = (indata[:, 0] * 32768).astype(np.int16)
                    audio_bytes = audio_int16.tobytes()
                    
                    # Use call_soon_threadsafe to schedule the coroutine
                    loop.call_soon_threadsafe(audio_queue.put_nowait, audio_bytes)
                
                # Start audio input stream
                self.input_stream = sd.InputStream(
                    samplerate=INPUT_SAMPLE_RATE,
                    channels=CHANNELS,
                    dtype='float32',
                    blocksize=CHUNK_SIZE,
                    callback=sync_callback
                )
                
                with self.input_stream:
                    # Create tasks for sending and receiving
                    send_task = asyncio.create_task(self.send_audio(audio_queue))
                    receive_task = asyncio.create_task(self.receive_messages())
                    
                    # Wait for both tasks (cancel on first exception)
                    try:
                        await asyncio.gather(send_task, receive_task)
                    except Exception as e:
                        print(f"Task error: {e}")
                        send_task.cancel()
                        receive_task.cancel()
                    
        except KeyboardInterrupt:
            print("\n\n👋 Stopping...")
        except websockets.exceptions.ConnectionClosed as e:
            print(f"Connection closed: {e}")
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.running = False
    
    async def send_audio(self, audio_queue):
        """Send audio from queue to WebSocket"""
        try:
            while self.running:
                audio_bytes = await audio_queue.get()
                await self.websocket.send(audio_bytes)
        except Exception as e:
            print(f"Error in send_audio: {e}")
            self.running = False


# =========================
# Simple Test Function
# =========================
async def test_connection():
    """Simple test to check if WebSocket endpoint is reachable"""
    try:
        async with websockets.connect(WEBSOCKET_URL) as ws:
            print("✅ WebSocket connection successful!")
            print("Server is ready to receive audio.")
            return True
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print("Make sure the server is running: uv run main.py")
        return False


# =========================
# Main
# =========================
async def main():
    print("=" * 50)
    print("WebSocket Audio Client")
    print("=" * 50)
    
    # Test connection first
    if not await test_connection():
        return
    
    print("\nStarting audio streaming...")
    print("Tip: Speak clearly and wait for pauses to be detected.\n")
    
    # Start streaming
    streamer = AudioStreamer()
    await streamer.start_streaming()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nExiting...")
