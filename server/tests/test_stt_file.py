"""
WebSocket Audio Client - File-based Testing
Sends a WAV file to the WebSocket endpoint for testing
"""
import asyncio
import websockets
import wave
import json
import sys

WEBSOCKET_URL = "ws://localhost:8000/stt/ws/audio"
CHUNK_SIZE = 1600  # 100ms of audio at 16kHz


async def send_wav_file(filepath):
    """Send a WAV file through WebSocket"""
    try:
        # Open WAV file
        with wave.open(filepath, 'rb') as wf:
            print(f"📁 File: {filepath}")
            print(f"📊 Channels: {wf.getnchannels()}")
            print(f"📊 Sample Rate: {wf.getframerate()}Hz")
            print(f"📊 Sample Width: {wf.getsampwidth()} bytes")
            print(f"⏱️  Duration: {wf.getnframes() / wf.getframerate():.2f}s")
            
            if wf.getframerate() != 16000:
                print("\n⚠️  Warning: File sample rate is not 16kHz!")
                print("   Consider resampling the file for best results.")
            
            if wf.getnchannels() != 1:
                print("\n⚠️  Warning: File is not mono!")
                print("   Only the first channel will be used.")
            
            print(f"\n🔌 Connecting to {WEBSOCKET_URL}...")
            
            async with websockets.connect(WEBSOCKET_URL) as ws:
                print("✅ Connected!\n")
                print("📤 Sending audio chunks...")
                
                # Task to receive transcripts
                async def receive_transcripts():
                    try:
                        while True:
                            message = await ws.recv()
                            data = json.loads(message)
                            
                            if data.get("type") == "transcript":
                                print(f"\n🎤 TRANSCRIPT: {data.get('text')}\n")
                    except websockets.exceptions.ConnectionClosed:
                        pass
                
                receive_task = asyncio.create_task(receive_transcripts())
                
                # Send audio chunks
                chunk_count = 0
                while True:
                    audio_data = wf.readframes(CHUNK_SIZE)
                    if not audio_data:
                        break
                    
                    await ws.send(audio_data)
                    chunk_count += 1
                    
                    if chunk_count % 10 == 0:
                        print(f"Sent {chunk_count} chunks...")
                    
                    # Small delay to simulate real-time streaming
                    await asyncio.sleep(0.1)
                
                print(f"\n✅ Sent {chunk_count} total chunks")
                print("⏳ Waiting for final transcripts...")
                
                # Wait a bit for final transcripts
                await asyncio.sleep(3)
                
                receive_task.cancel()
                
    except FileNotFoundError:
        print(f"❌ File not found: {filepath}")
    except Exception as e:
        print(f"❌ Error: {e}")


async def main():
    print("=" * 60)
    print("WebSocket Audio Client - File Testing")
    print("=" * 60)
    print()
    
    if len(sys.argv) < 2:
        print("Usage: python test_stt_file.py <audio_file.wav>")
        print("\nExample:")
        print("  python test_stt_file.py test_audio.wav")
        return
    
    audio_file = sys.argv[1]
    await send_wav_file(audio_file)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nExiting...")
