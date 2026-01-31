"""
TTS Service - Business logic for text-to-speech generation using Cartesia.
"""
import asyncio
from typing import AsyncGenerator, Literal, Optional, Any, Dict

from cartesia import AsyncCartesia
from cartesia.tts import OutputFormat_RawParams
from cartesia.tts.types import WebSocketResponse, WebSocketResponse_Done, WebSocketResponse_Error
from cartesia.core.pydantic_utilities import parse_obj_as

from modules.config import ConfigEnv
from services.tts import utils


class TTSService:
    """Service for handling TTS operations with Cartesia."""

    def __init__(self):
        """Initialize Cartesia client."""
        self.enabled = bool(ConfigEnv.CARTESIA_TTS_ENABLED)

        api_key = ConfigEnv.get_cartesia_api_key()

        if self.enabled and not api_key:
            raise ValueError(
                "Cartesia API key not found. Set CARTESIA_API_KEY or CARTESIAN_PRODUCT_API_KEY environment variable."
            )

        self.client = AsyncCartesia(api_key=api_key) if self.enabled else None
        self.model_id = "sonic-2"  # Cartesia model for TTS
        # Track active WebSocket contexts: {context_id: {"ws": websocket, "config": {...}}}
        self.active_contexts: Dict[str, Dict[str, Any]] = {}

    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable TTS at runtime."""
        self.enabled = enabled

    def ensure_enabled(self) -> bool:
        return self.enabled
    
    async def stream_tts(
        self,
        text: str,
        language: Optional[Literal["hi", "en", "auto"]] = "auto",
        voice_id: Optional[str] = None,
    ) -> AsyncGenerator[bytes, None]:
        """
        Stream TTS audio for given text.
        
        Args:
            text: Text to convert to speech
            language: Language code ("hi", "en", or "auto" for auto-detect)
            voice_id: Optional voice ID (uses default if not provided)
            
        Yields:
            Audio chunks as bytes (PCM float32 little-endian format)
        """
        if not text or not text.strip():
            return

        if not self.ensure_enabled():
            return
        
        # Determine language
        if language == "auto":
            detected_lang = utils.detect_language(text)
        else:
            detected_lang = language
        
        # Get voice ID
        if not voice_id:
            voice_id = utils.get_default_voice_id(detected_lang)
        
        # Connect to Cartesia WebSocket
        ws = await self.client.tts.websocket()
        
        try:
            # Configure output format for low-latency streaming
            output_format: OutputFormat_RawParams = {
                "container": "raw",
                "encoding": "pcm_f32le",
                "sample_rate": 44100,
            }
            
            # Generate speech with streaming
            output_generate = await ws.send(
                model_id=self.model_id,
                transcript=text,
                voice={"id": voice_id},
                language=detected_lang,
                output_format=output_format,
                stream=True,
            )
            
            # Stream audio chunks
            async for output in output_generate:
                if output.audio is not None:
                    yield output.audio
        
        finally:
            # Clean up WebSocket connection
            await ws.close()
    
    async def stream_tts_mixed(
        self,
        text: str,
        voice_id: Optional[str] = None,
    ) -> AsyncGenerator[bytes, None]:
        """
        Stream TTS for mixed Hindi/English text by processing segments separately.
        
        Args:
            text: Text that may contain both Hindi and English
            voice_id: Optional voice ID (uses default if not provided)
            
        Yields:
            Audio chunks as bytes
        """
        segments = utils.split_mixed_text(text)

        if not self.ensure_enabled():
            return
        
        for segment_text, segment_lang in segments:
            if not segment_text.strip():
                continue
            
            # Get voice for this language
            segment_voice_id = voice_id or utils.get_default_voice_id(segment_lang)
            
            # Stream TTS for this segment
            async for audio_chunk in self.stream_tts(
                segment_text,
                language=segment_lang,
                voice_id=segment_voice_id,
            ):
                yield audio_chunk
    
    async def stream_tts_chunk(
        self,
        transcript: str,
        context_id: str,
        continue_flag: bool,
        language: Optional[Literal["hi", "en", "auto"]] = "auto",
        voice_id: Optional[str] = None,
    ) -> AsyncGenerator[bytes, None]:
        """
        Stream a single transcript chunk on a context.
        Maintains WebSocket connection across chunks with same context_id.
        
        Args:
            transcript: Text chunk to convert to speech
            context_id: Unique identifier for the streaming context
            continue_flag: True if more chunks will follow, False for final chunk
            language: Language code ("hi", "en", or "auto" for auto-detect)
            voice_id: Optional voice ID (uses default if not provided)
            
        Yields:
            Audio chunks as bytes (PCM float32 little-endian format)
        """
        if not self.ensure_enabled():
            return
        # Determine language
        if language == "auto":
            detected_lang = utils.detect_language(transcript)
        else:
            detected_lang = language
        
        # Get voice ID
        if not voice_id:
            voice_id = utils.get_default_voice_id(detected_lang)
        
        # Configure output format for low-latency streaming
        output_format: OutputFormat_RawParams = {
            "container": "raw",
            "encoding": "pcm_f32le",
            "sample_rate": 44100,
        }
        
        # Get or create WebSocket for this context
        if context_id not in self.active_contexts:
            # Create new WebSocket connection
            ws = await self.client.tts.websocket()
            # Create new context (the SDK's context() method creates if doesn't exist)
            ctx = ws.context(context_id)
            
            self.active_contexts[context_id] = {
                "ws": ws,
                "ctx": ctx,
                "config": {
                    "model_id": self.model_id,
                    "voice": {"id": voice_id},
                    "language": detected_lang,
                    "output_format": output_format,
                }
            }
        else:
            # Use existing context - verify parameters match
            context_data = self.active_contexts[context_id]
            existing_config = context_data["config"]
            ws = context_data["ws"]
            ctx = context_data["ctx"]
            
            # Ensure all parameters match (except transcript, continue, duration)
            if (existing_config["voice"]["id"] != voice_id or 
                existing_config["language"] != detected_lang):
                # Parameters don't match - close old context and create new
                try:
                    await ctx.cancel()
                    await ws.close()
                except:
                    pass
                ws = await self.client.tts.websocket()
                ctx = ws.context(context_id)
                self.active_contexts[context_id] = {
                    "ws": ws,
                    "ctx": ctx,
                    "config": {
                        "model_id": self.model_id,
                        "voice": {"id": voice_id},
                        "language": detected_lang,
                        "output_format": output_format,
                    }
                }
        
        try:
            config = self.active_contexts[context_id]["config"]
            
            # The SDK's high-level send() method doesn't support continue_ parameter
            # We need to use the context API directly to pass continue_
            # Use the context's send method which supports continue_ parameter
            await ctx.send(
                model_id=config["model_id"],
                transcript=transcript,
                voice=config["voice"],
                language=config["language"],
                output_format=config["output_format"],
                context_id=context_id,
                continue_=continue_flag,  # SDK uses continue_ (with underscore)
                stream=True,
            )
            
            # For intermediate chunks (continue_=True), we need to get audio without waiting for done
            # For final chunks (continue_=False), receive() will get done and close context
            # The issue: receive() waits for done message, which won't come for intermediate chunks
            # Solution: Use receive() but handle the case where it doesn't get done
            # Actually, receive() will yield chunks until done, so for continue_=True it will block
            # We need a different approach - get messages directly from the WebSocket queue
            
            # For intermediate chunks (continue_=True), receive() will block waiting for done
            # For final chunks (continue_=False), receive() will get done and close context
            # Solution: For intermediate chunks, get messages directly from queue
            # For final chunks, use receive() which will properly close the context
            
            if continue_flag:
                # Intermediate chunk - get messages directly from queue without waiting for done
                # This allows us to get audio and return without blocking forever
                chunk_received = False
                timeout_per_chunk = 10.0  # Wait up to 10 seconds for audio chunks
                
                # Get messages until we have audio, with a reasonable timeout
                # We'll try to get multiple audio chunks if available, but won't wait for done
                while True:
                    try:
                        # Get message with timeout
                        response = await ws._get_message(context_id, timeout=timeout_per_chunk, flush_id=-1)
                        
                        # Parse the response
                        response_obj = parse_obj_as(WebSocketResponse, response)
                        
                        if isinstance(response_obj, WebSocketResponse_Error):
                            raise RuntimeError(f"Error generating audio:\n{response_obj.error}")
                        
                        if isinstance(response_obj, WebSocketResponse_Done):
                            # Unexpected done for intermediate chunk - this shouldn't happen
                            # but if it does, we're done
                            break
                        
                        # Convert response to output format and yield audio
                        output = ws._convert_response(response_obj, include_context_id=True)
                        if output.audio is not None:
                            yield output.audio
                            chunk_received = True
                            
                        # For intermediate chunks, after getting audio, check if more is available
                        # Use a very short timeout to avoid blocking
                        try:
                            # Check if queue has more items without blocking
                            if context_id in ws._context_queues and len(ws._context_queues[context_id]) > 0:
                                queue = ws._context_queues[context_id][-1]
                                if not queue.empty():
                                    # More messages available, continue loop
                                    continue
                        except (ValueError, KeyError, IndexError):
                            pass
                        
                        # If we got audio and no more is immediately available, break
                        # This allows the next chunk to be sent
                        if chunk_received:
                            break
                            
                    except asyncio.TimeoutError:
                        if chunk_received:
                            # Got at least one chunk, that's enough for intermediate
                            break
                        # No chunks received yet - this might be an error
                        raise RuntimeError("Timeout waiting for audio chunk")
                    except ValueError as e:
                        if "not found" in str(e).lower():
                            if chunk_received:
                                # Context might have been closed, but we got audio
                                break
                            raise RuntimeError(f"Context error: {e}")
                        raise
            else:
                # Final chunk - use receive() which will properly handle done message and close context
                output_generate = ctx.receive()
                async for output in output_generate:
                    if output.audio is not None:
                        yield output.audio
            
            # If this is the final chunk, clean up our tracking
            if not continue_flag:
                if context_id in self.active_contexts:
                    del self.active_contexts[context_id]
        
        except Exception as e:
            # On error, clean up context
            if context_id in self.active_contexts:
                try:
                    await self.active_contexts[context_id]["ws"].close()
                except:
                    pass
                del self.active_contexts[context_id]
            raise
    
    async def close(self):
        """Close the Cartesia client and all active contexts."""
        # Close all active contexts
        for context_id, context_data in list(self.active_contexts.items()):
            try:
                await context_data["ws"].close()
            except:
                pass
        self.active_contexts.clear()
        
        # Close the client
        await self.client.close()


# Singleton instance
_tts_service: Optional[TTSService] = None


def get_tts_service() -> TTSService:
    """Get or create TTS service instance."""
    global _tts_service
    if _tts_service is None:
        _tts_service = TTSService()
    return _tts_service
