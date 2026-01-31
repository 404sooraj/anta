"""
TTS utility functions for language detection and voice management.
"""
import re
from typing import Literal


def detect_language(text: str) -> Literal["hi", "en"]:
    """
    Detect if text is Hindi or English based on character patterns.
    
    Args:
        text: Input text to analyze
        
    Returns:
        "hi" for Hindi, "en" for English
    """
    if not text or not text.strip():
        return "en"  # Default to English
    
    # Check for Devanagari script (Hindi) - Unicode range: U+0900 to U+097F
    devanagari_pattern = re.compile(r'[\u0900-\u097F]')
    
    # Count Devanagari characters
    devanagari_count = len(devanagari_pattern.findall(text))
    total_chars = len([c for c in text if c.isalpha()])
    
    # If more than 30% of alphabetic characters are Devanagari, consider it Hindi
    if total_chars > 0 and (devanagari_count / total_chars) > 0.3:
        return "hi"
    
    return "en"


def get_default_voice_id(language: Literal["hi", "en"]) -> str:
    """
    Get default voice ID for a given language.
    
    Args:
        language: Language code ("hi" or "en")
        
    Returns:
        Default voice ID for the language
        
    Note:
        To get actual voice IDs:
        1. List available voices: client.voices.list()
        2. Or localize an English voice to Hindi using client.voices.localize()
    """
    # Default voice IDs - REPLACE THESE with actual Cartesia voice IDs
    # To list available voices, use: client.voices.list()
    # To localize a voice to Hindi: client.voices.localize(voice_id="...", language="hi", ...)
    default_voices = {
        "en": "f9836c6e-a0bd-460e-9d3c-f7299fa60f94",  # Example English voice - REPLACE
        "hi": "faf0731e-dfb9-4cfc-8119-259a79b27e12",  # Use same voice for now - Cartesia supports multilingual
    }
    
    return default_voices.get(language, default_voices["en"])


def split_mixed_text(text: str) -> list[tuple[str, Literal["hi", "en"]]]:
    """
    Split text into segments by language (Hindi/English).
    
    Args:
        text: Input text that may contain both Hindi and English
        
    Returns:
        List of tuples (text_segment, language)
    """
    if not text:
        return []
    
    segments = []
    current_segment = ""
    current_lang = None
    
    for char in text:
        is_devanagari = bool(re.match(r'[\u0900-\u097F]', char))
        char_lang = "hi" if is_devanagari else "en"
        
        if current_lang is None:
            current_lang = char_lang
            current_segment = char
        elif current_lang == char_lang:
            current_segment += char
        else:
            # Language changed, save current segment and start new one
            if current_segment.strip():
                segments.append((current_segment, current_lang))
            current_segment = char
            current_lang = char_lang
    
    # Add final segment
    if current_segment.strip():
        segments.append((current_segment, current_lang))
    
    return segments if segments else [("", "en")]
