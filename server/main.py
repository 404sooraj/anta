"""Main application entry point for Antaryami Response Pipeline API."""

import os
import logging
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI

from api.routes import router
from modules.response.response import ResponsePipeline

# Load environment variables
load_dotenv()

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
    # Startup: Initialize pipeline once
    logger.info("Starting up application...")
    
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logger.error("GEMINI_API_KEY environment variable not set!")
        raise ValueError("GEMINI_API_KEY must be set in environment variables")
    
    # Initialize pipeline and store in app state
    app.state.pipeline = ResponsePipeline(api_key=api_key)
    logger.info("✓ Pipeline initialized successfully")
    
    yield  # Application runs here
    
    # Shutdown: Cleanup if needed
    logger.info("Shutting down application...")
    logger.info("✓ Shutdown complete")


# Initialize FastAPI app with lifespan
app = FastAPI(
    title="Antaryami Response Pipeline API",
    description="API for processing text through intent detection, LLM tool calling, and response generation",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/")
async def root():
    """Root endpoint for API health check."""
    return {"message": "Antaryami Response Pipeline API", "status": "running"}


# Include API routes
app.include_router(router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="localhost", port=8000)
