"""Main application entry point for BatterySmart API."""

import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import config first (loads .env); then routers and db
from modules.config import ConfigEnv
from routers.stt import router as stt_router
from routers.text import router as text_router
from routers.tts import router as tts_router
from routers.twilio import router as twilio_router
from routers.batteries import router as batteries_router
from routers.auth import router as auth_router
from routers.call_transcripts import router as call_transcripts_router
from routers.location import router as location_router
from routers.agent import router as agent_router
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
    # gemini_model_name = ConfigEnv.GEMINI_MODEL_NAME
    soniox_key = ConfigEnv.SONIOX_API_KEY
    cartesia_key = ConfigEnv.CARTESIA_API_KEY
    tts_enabled = ConfigEnv.CARTESIA_TTS_ENABLED
    twilio_account_sid = ConfigEnv.TWILIO_ACCOUNT_SID
    twilio_auth_token = ConfigEnv.TWILIO_AUTH_TOKEN
    twilio_ws_url = ConfigEnv.TWILIO_WEBSOCKET_URL
    
    # MongoDB: connect and attach db to app state for routes/tools
    db = get_db()
    app.state.db = db
    await create_indexes(db)
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

frontend_origin = os.getenv("FRONTEND_ORIGIN", "http://localhost:3000")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Include routers
app.include_router(stt_router)
app.include_router(text_router)
app.include_router(tts_router)
app.include_router(twilio_router)
app.include_router(batteries_router)
app.include_router(auth_router)
app.include_router(call_transcripts_router)
app.include_router(location_router)
app.include_router(agent_router)


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
            "twilio_voice": "/twilio/voice",
            "twilio_media_stream": "ws://localhost:8000/twilio/media",
            "batteries_put": "PUT /api/batteries/{battery_id}",
            "batteries_get": "GET /api/batteries/{battery_id}",
            "call_transcripts_list": "GET /api/calls/transcripts",
            "call_transcript_get": "GET /api/calls/transcripts/{call_id}",
            "call_analytics": "GET /api/calls/analytics/summary",
            "agent_websocket": "ws://localhost:8000/agent/ws/connect",
            "agent_queue_status": "/agent/queue/status",
            "agent_health": "/agent/health",
            "docs": "/docs"
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="localhost", port=8000)
