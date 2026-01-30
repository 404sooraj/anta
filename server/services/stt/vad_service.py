"""
VAD Service - Silero VAD Integration
Handles voice activity detection for silence detection
"""
import numpy as np
import torch
from silero_vad import load_silero_vad

torch.set_num_threads(1)

# =========================
# Configuration
# =========================
SAMPLE_RATE = 16000
SPEECH_THRESHOLD = 0.6


# =========================
# VAD Service
# =========================
class VADService:
    """Voice Activity Detection using Silero VAD"""
    
    def __init__(self, speech_threshold: float = SPEECH_THRESHOLD):
        self.model = load_silero_vad()
        self.speech_threshold = speech_threshold
    
    def int2float(self, sound: np.ndarray) -> np.ndarray:
        """Convert PCM16 to Float32"""
        abs_max = np.abs(sound).max()
        sound = sound.astype("float32")
        if abs_max > 0:
            sound *= 1 / 32768
        return sound.squeeze()
    
    def get_confidence(self, audio_bytes: bytes) -> float:
        """Get VAD confidence for audio chunk"""
        audio_int16 = np.frombuffer(audio_bytes, np.int16)
        audio_float32 = self.int2float(audio_int16)
        audio_tensor = torch.from_numpy(audio_float32)
        
        confidence = self.model(audio_tensor, SAMPLE_RATE).item()
        return confidence
    
    def is_speech(self, audio_bytes: bytes) -> bool:
        """Check if audio chunk contains speech"""
        return self.get_confidence(audio_bytes) > self.speech_threshold
