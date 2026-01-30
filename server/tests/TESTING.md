# Testing Your WebSocket STT Route

## Prerequisites

Install the required dependencies for the test clients:

```bash
pip install websockets sounddevice numpy
```

## Option 1: Test with Live Microphone

1. **Start your server:**
   ```bash
   cd server
   uv run main.py
   ```

2. **In a new terminal, run the test client:**
   ```bash
   cd server
   python test_stt_client.py
   ```

3. **Speak into your microphone:**
   - The client will capture audio and send it to your WebSocket endpoint
   - Speak clearly and pause between sentences
   - The VAD will detect when you stop speaking
   - Transcripts will appear in your terminal

4. **Stop testing:**
   - Press `Ctrl+C` to stop

## Option 2: Test with a WAV File

1. **Start your server:**
   ```bash
   cd server
   uv run main.py
   ```

2. **Run the file-based test client:**
   ```bash
   cd server
   python test_stt_file.py path/to/your/audio.wav
   ```

   **Note:** The WAV file should ideally be:
   - 16kHz sample rate
   - Mono (1 channel)
   - 16-bit PCM format

## Creating a Test Audio File

If you need a test audio file, you can create one with Python:

```python
import sounddevice as sd
import soundfile as sf

# Record 5 seconds of audio
duration = 5  # seconds
sample_rate = 16000

print("Recording... Speak now!")
audio = sd.rec(int(duration * sample_rate), 
               samplerate=sample_rate, 
               channels=1, 
               dtype='int16')
sd.wait()

sf.write('test_audio.wav', audio, sample_rate)
print("Saved to test_audio.wav")
```

## Troubleshooting

### Server won't start
- Make sure you have all dependencies installed
- Check that OpenAI API key is set in your environment

### No audio being captured
- Check your microphone permissions
- Verify microphone is selected in system settings
- Try listing available devices:
  ```python
  import sounddevice as sd
  print(sd.query_devices())
  ```

### WebSocket connection fails
- Ensure server is running on `localhost:8000`
- Check for firewall blocking the connection
- Verify the `/stt/ws/audio` endpoint is correct

### No transcripts appearing
- Check the VAD threshold (currently 0.6) - might need tuning
- Ensure you're speaking clearly with pauses
- Check server logs for VAD confidence values
- Make sure OpenAI API is accessible

## Testing the Health Endpoint

You can also test the basic health endpoint:

```bash
curl http://localhost:8000/stt/health
```

Should return: `{"status":"ok"}`

## Using Browser DevTools

You can also test from a browser console:

```javascript
const ws = new WebSocket('ws://localhost:8000/stt/ws/audio');

ws.onopen = () => {
    console.log('Connected!');
    
    // Request microphone access
    navigator.mediaDevices.getUserMedia({ audio: true })
        .then(stream => {
            const audioContext = new AudioContext({ sampleRate: 16000 });
            const source = audioContext.createMediaStreamSource(stream);
            const processor = audioContext.createScriptProcessor(1600, 1, 1);
            
            source.connect(processor);
            processor.connect(audioContext.destination);
            
            processor.onaudioprocess = (e) => {
                const inputData = e.inputBuffer.getChannelData(0);
                const int16Data = new Int16Array(inputData.length);
                
                for (let i = 0; i < inputData.length; i++) {
                    int16Data[i] = Math.max(-32768, Math.min(32767, inputData[i] * 32768));
                }
                
                ws.send(int16Data.buffer);
            };
        });
};

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log('Transcript:', data.text);
};
```
