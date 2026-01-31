"""Configuration module for response pipeline."""

import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Config:
    """Configuration settings for the response pipeline."""
    
    # API Keys (Bedrock uses AWS credentials; keep optional for compatibility)
    BEDROCK_API_KEY: Optional[str] = os.getenv("BEDROCK_API_KEY")
    
    # Model Configuration (set BEDROCK_MODEL_ID in .env)
    # Options: anthropic.claude-3-haiku-20240307-v1:0, anthropic.claude-3-5-sonnet-20241022-v2:0, etc.
    BEDROCK_MODEL_ID: Optional[str] = os.getenv("BEDROCK_MODEL_ID")
    BEDROCK_REGION: Optional[str] = os.getenv("BEDROCK_REGION") or os.getenv("AWS_REGION")
    BEDROCK_TEMPERATURE: float = float(os.getenv("BEDROCK_TEMPERATURE", "0.7"))
    BEDROCK_MAX_TOKENS: Optional[int] = (
        int(os.getenv("BEDROCK_MAX_TOKENS")) if os.getenv("BEDROCK_MAX_TOKENS") else None
    )
    
    @classmethod
    def validate(cls) -> bool:
        """
        Validate that required configuration is present.
        
        Returns:
            True if configuration is valid, False otherwise.
        """
        if not cls.BEDROCK_MODEL_ID:
            return False
        if not (cls.BEDROCK_REGION or os.getenv("AWS_REGION")):
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
        if not cls.BEDROCK_MODEL_ID:
            raise ValueError(
                "BEDROCK_MODEL_ID not configured. "
                "Please set it in environment variables or .env file."
            )
        if not (cls.BEDROCK_REGION or os.getenv("AWS_REGION")):
            raise ValueError(
                "BEDROCK_REGION or AWS_REGION not configured. "
                "Please set it in environment variables or .env file."
            )
        return cls.BEDROCK_REGION or os.getenv("AWS_REGION", "")
