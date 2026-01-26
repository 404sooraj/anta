from fastapi import FastAPI
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add server directory to Python path
server_dir = Path(__file__).parent
if str(server_dir) not in sys.path:
    sys.path.insert(0, str(server_dir))

# Import using importlib to handle module names with dots
import importlib.util

# Load the routes module directly from file path
routes_path = server_dir / "modules" / "tts" / "tts.routes.py"
spec = importlib.util.spec_from_file_location("tts_routes", routes_path)
_routes_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(_routes_module)
tts_router = _routes_module.router

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
