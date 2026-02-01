"""
Greeting audio service - loads and caches the fixed call-start WAV,
converts to mulaw 8kHz (Twilio) or float32 44100 Hz (app).
"""
import audioop
import logging
import os
from pathlib import Path
from typing import Generator, List, Optional, Tuple

import numpy as np
import soundfile as sf

logger = logging.getLogger(__name__)

DEFAULT_FILENAME = "cartesia_audio_2026-02-01T10_08_31+05_30.wav"
TWILIO_CHUNK_MS = 20
TWILIO_SAMPLE_RATE = 8000
APP_SAMPLE_RATE = 44100

# (samples_float32, sample_rate) or None if load failed
_cached: Optional[Tuple[np.ndarray, int]] = None


def _get_greeting_path() -> Path:
    """Resolve path to greeting WAV: env GREETING_AUDIO_PATH or project root default."""
    env_path = os.getenv("GREETING_AUDIO_PATH")
    if env_path:
        return Path(env_path)
    # server/services/greeting_audio.py -> server -> project root
    project_root = Path(__file__).resolve().parent.parent.parent
    return project_root / DEFAULT_FILENAME


def _load_greeting() -> Optional[Tuple[np.ndarray, int]]:
    """Load WAV once; return (float32 mono samples, sample_rate) or None."""
    global _cached
    if _cached is not None:
        return _cached
    path = _get_greeting_path()
    if not path.exists():
        logger.warning("Greeting audio file not found: %s", path)
        _cached = None
        return None
    try:
        data, sr = sf.read(path, dtype="float32")
        if data.ndim > 1:
            data = data[:, 0]
        data = np.ascontiguousarray(data, dtype=np.float32)
        _cached = (data, int(sr))
        logger.info("Loaded greeting audio: %s (rate=%d, samples=%d)", path, sr, len(data))
        return _cached
    except Exception as e:
        logger.exception("Failed to load greeting audio %s: %s", path, e)
        _cached = None
        return None


def get_greeting_mulaw_8k_chunks() -> List[bytes]:
    """
    Return greeting as 20ms mulaw 8kHz chunks for Twilio media.
    Each chunk is 160 bytes (160 samples at 8kHz).
    """
    loaded = _load_greeting()
    if loaded is None:
        return []
    samples, sr = loaded
    # float32 [-1,1] -> PCM16
    pcm16 = (np.clip(samples, -1.0, 1.0) * 32767).astype(np.int16)
    pcm_bytes = pcm16.tobytes()
    # Resample to 8kHz if needed
    if sr != TWILIO_SAMPLE_RATE:
        pcm_bytes, _ = audioop.ratecv(
            pcm_bytes, 2, 1, sr, TWILIO_SAMPLE_RATE, None
        )
    # Convert to mulaw
    mulaw_bytes = audioop.lin2ulaw(pcm_bytes, 2)
    # Chunk: 20ms = 160 samples at 8kHz = 160 bytes
    chunk_size = 160
    chunks = []
    for i in range(0, len(mulaw_bytes), chunk_size):
        chunk = mulaw_bytes[i : i + chunk_size]
        if chunk:
            chunks.append(bytes(chunk))
    return chunks


def get_greeting_float32_44100_chunks(chunk_size: int = 4096) -> Generator[bytes, None, None]:
    """
    Yield greeting as float32 44100 Hz chunks (bytes) for app WebSocket.
    Each chunk is chunk_size samples as float32 little-endian.
    """
    loaded = _load_greeting()
    if loaded is None:
        return
    samples, sr = loaded
    if sr != APP_SAMPLE_RATE:
        # Resample to 44100 using linear interpolation
        n_old = len(samples)
        n_new = int(round(n_old * APP_SAMPLE_RATE / sr))
        old_indices = np.arange(n_old, dtype=np.float64)
        new_indices = np.linspace(0, n_old - 1, n_new, dtype=np.float64)
        samples = np.interp(new_indices, old_indices, samples).astype(np.float32)
    for i in range(0, len(samples), chunk_size):
        chunk = samples[i : i + chunk_size]
        if len(chunk) == 0:
            continue
        yield chunk.tobytes()
