"""Main application entry point for the Antaryami TTS Server (Hindi/English Text-to-Speech)."""

from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI
import sys
from pathlib import Path

# Load environment variables from .env file
load_dotenv()

# Add server directory to Python path
server_dir = Path(__file__).parent
if str(server_dir) not in sys.path:
    sys.path.insert(0, str(server_dir))

from modules.tts import routes as tts_routes

tts_router = tts_routes.router

app = FastAPI(
    title="Antaryami TTS Server",
    description="Text-to-Speech server with Hindi/English support",
    version="0.1.0",
)

# Include TTS router
app.include_router(tts_router, prefix="/tts", tags=["TTS"])


@app.get("/")
async def root():
    return {
        "message": "Antaryami TTS Server",
        "endpoints": {
            "websocket": "/tts/ws",
            "docs": "/docs",
        },
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="localhost", port=8000)
