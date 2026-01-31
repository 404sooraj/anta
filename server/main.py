"""Main application entry point for BatterySmart API."""

import os
import logging
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI

# Load environment variables first
load_dotenv()

# Import routers and db
from routers.stt import router as stt_router
from routers.text import router as text_router
from routers.tts import router as tts_router
from routers.batteries import router as batteries_router
from db.connection import get_db, close_client
from db.indexes import create_indexes

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for FastAPI app.
    Handles startup and shutdown events.
    """
    logger.info("Starting up BatterySmart API...")
    
    # Verify API keys
    bedrock_model_id = os.getenv("BEDROCK_MODEL_ID")
    bedrock_region = os.getenv("BEDROCK_REGION") or os.getenv("AWS_REGION")
    assemblyai_key = os.getenv("ASSEMBLYAI_API_KEY")
    cartesia_key = os.getenv("CARTESIA_API_KEY") or os.getenv("CARTESIAN_PRODUCT_API_KEY")
    tts_enabled = os.getenv("CARTESIA_TTS_ENABLED", "true").strip().lower() not in {"0", "false", "no", "off"}
    
    if not bedrock_model_id or not bedrock_region:
        logger.warning("BEDROCK_MODEL_ID or BEDROCK_REGION/AWS_REGION not set - LLM features may not work")
    if not assemblyai_key:
        logger.warning("ASSEMBLYAI_API_KEY not set - STT features will not work")
    if not tts_enabled:
        logger.info("TTS is disabled (CARTESIA_TTS_ENABLED=false)")
    elif not cartesia_key:
        logger.warning("CARTESIA_API_KEY not set - TTS features will not work")

    # MongoDB: connect and attach db to app state for routes/tools
    db = get_db()
    app.state.db = db
    # await create_indexes(db)
    logger.info("✓ MongoDB connected")

    logger.info("✓ Startup complete")

    yield  # Application runs here

    logger.info("Shutting down BatterySmart API...")
    close_client()
    logger.info("✓ Shutdown complete")


# Initialize FastAPI app with lifespan
app = FastAPI(
    title="BatterySmart API",
    description="Complete voice AI system: Speech-to-Text → LLM Processing → Text-to-Speech",
    version="1.0.0",
    lifespan=lifespan,
)


# Include routers
app.include_router(stt_router)
app.include_router(text_router)
app.include_router(tts_router)
app.include_router(batteries_router)


@app.get("/")
async def root():
    """Root endpoint for API health check."""
    return {
        "name": "BatterySmart API", 
        "status": "running",
        "version": "1.0.0",
        "description": "Complete voice AI: STT → LLM → TTS",
        "endpoints": {
            "stt_websocket": "ws://localhost:8000/stt/ws/audio",
            "stt_health": "/stt/health",
            "text_process": "/api/text/process",
            "text_health": "/api/text/health",
            "tts_websocket": "ws://localhost:8000/tts/ws",
            "tts_health": "/tts/health",
            "batteries_put": "PUT /api/batteries/{battery_id}",
            "batteries_get": "GET /api/batteries/{battery_id}",
            "docs": "/docs"
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="localhost", port=8000)
