import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables (single place for the app)
load_dotenv()


def convert_to_float(value: Optional[str]) -> Optional[float]:
    return float(value) if value is not None else None


def convert_to_int(value: Optional[str]) -> Optional[int]:
    return int(value) if value is not None else None


def convert_to_bool(value: Optional[str]) -> Optional[bool]:
    if value is None:
        return None
    return value.strip().lower() in {"true", "1", "yes", "y"}


class ConfigEnv:
    # ----- Gemini -----
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    GEMINI_MODEL_NAME = os.getenv("GEMINI_MODEL_NAME")
    GEMINI_TEMPERATURE = convert_to_float(os.getenv("GEMINI_TEMPERATURE"))
    GEMINI_MAX_TOKENS = convert_to_int(os.getenv("GEMINI_MAX_TOKENS"))

    # ----- Bedrock / AWS -----
    BEDROCK_API_KEY = os.getenv("BEDROCK_API_KEY", "")
    BEDROCK_MODEL_ID = os.getenv("BEDROCK_MODEL_ID")
    BEDROCK_REGION = os.getenv("BEDROCK_REGION")
    BEDROCK_TEMPERATURE = convert_to_float(os.getenv("BEDROCK_TEMPERATURE", "0.7")) or 0.7
    BEDROCK_MAX_TOKENS = convert_to_int(os.getenv("BEDROCK_MAX_TOKENS"))
    AWS_REGION = os.getenv("AWS_REGION")
    AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")

    # ----- Cartesia -----
    CARTESIA_API_KEY = os.getenv("CARTESIA_API_KEY")
    CARTESIAN_PRODUCT_API_KEY = os.getenv("CARTESIAN_PRODUCT_API_KEY")
    CARTESIA_TTS_ENABLED = convert_to_bool(os.getenv("CARTESIA_TTS_ENABLED", "true"))
    CARTESIA_MODEL_ID = os.getenv("CARTESIA_MODEL_ID")
    CARTESIA_TEMPERATURE = convert_to_float(os.getenv("CARTESIA_TEMPERATURE"))
    CARTESIA_MAX_TOKENS = convert_to_int(os.getenv("CARTESIA_MAX_TOKENS"))
    CARTESIA_LANGUAGE = os.getenv("CARTESIA_LANGUAGE")
    CARTESIA_VOICE = os.getenv("CARTESIA_VOICE")
    CARTESIA_VOICE_SPEED = os.getenv("CARTESIA_VOICE_SPEED")
    CARTESIA_VOICE_PITCH = os.getenv("CARTESIA_VOICE_PITCH")

    # ----- Twilio -----
    TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
    TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
    TWILIO_WEBSOCKET_URL = os.getenv(
        "TWILIO_WEBSOCKET_URL", "wss://your-domain.com/twilio/media"
    )

    # ----- MongoDB -----
    MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")

    # ----- STT -----
    SONIOX_API_KEY = os.getenv("SONIOX_API_KEY")
    ASSEMBLYAI_API_KEY = os.getenv("ASSEMBLYAI_API_KEY", "")

    # ----- Feature flags -----
    _ide = (os.getenv("INTENT_DETECTION_ENABLED", "true") or "").strip().lower()
    INTENT_DETECTION_ENABLED = _ide not in {"0", "false", "no", "off"}

    REQUIRED = [
        # "GEMINI_API_KEY",
        "TWILIO_ACCOUNT_SID",
        "TWILIO_AUTH_TOKEN",
        "MONGODB_URL",
        "CARTESIA_API_KEY",
        "CARTESIA_TTS_ENABLED",
        "CARTESIA_MODEL_ID",
        "CARTESIA_TEMPERATURE",
        "CARTESIA_MAX_TOKENS",
        "CARTESIA_LANGUAGE",
        "CARTESIA_VOICE",
        "CARTESIA_VOICE_SPEED",
        "CARTESIA_VOICE_PITCH",
    ]

    @classmethod
    def get_bedrock_region(cls) -> str:
        """Return BEDROCK_REGION or AWS_REGION fallback, or empty string."""
        return (cls.BEDROCK_REGION or cls.AWS_REGION or "") or ""

    @classmethod
    def get_cartesia_api_key(cls) -> Optional[str]:
        """Return CARTESIA_API_KEY or CARTESIAN_PRODUCT_API_KEY fallback."""
        return cls.CARTESIA_API_KEY or cls.CARTESIAN_PRODUCT_API_KEY

    @classmethod
    def validate(cls) -> None:
        missing = [key for key in cls.REQUIRED if getattr(cls, key) is None]
        if missing:
            raise RuntimeError(f"Missing required env vars: {', '.join(missing)}")
