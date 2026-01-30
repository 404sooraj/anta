"""Configuration module for response pipeline."""

import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Config:
    """Configuration settings for the response pipeline."""
    
    # API Keys
    GEMINI_API_KEY: Optional[str] = os.getenv("GEMINI_API_KEY")
    
    # Model Configuration (set GEMINI_MODEL_NAME in .env)
    # Options: gemini-1.5-flash, gemini-1.5-pro, gemini-2.5-flash, etc.
    GEMINI_MODEL_NAME: str = os.getenv("GEMINI_MODEL_NAME", "gemini-1.5-flash")
    GEMINI_TEMPERATURE: float = float(os.getenv("GEMINI_TEMPERATURE", "0.7"))
    GEMINI_MAX_TOKENS: Optional[int] = (
        int(os.getenv("GEMINI_MAX_TOKENS")) if os.getenv("GEMINI_MAX_TOKENS") else None
    )
    
    @classmethod
    def validate(cls) -> bool:
        """
        Validate that required configuration is present.
        
        Returns:
            True if configuration is valid, False otherwise.
        """
        if not cls.GEMINI_API_KEY:
            return False
        return True
    
    @classmethod
    def get_api_key(cls) -> str:
        """
        Get the Gemini API key.
        
        Returns:
            The API key.
            
        Raises:
            ValueError: If API key is not configured.
        """
        if not cls.GEMINI_API_KEY:
            raise ValueError(
                "GEMINI_API_KEY not configured. "
                "Please set it in environment variables or .env file."
            )
        return cls.GEMINI_API_KEY
