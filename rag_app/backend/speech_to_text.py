import os
import logging
from groq import Groq

logger = logging.getLogger(__name__)

class SpeechToText:
    """Speech to text using Groq Whisper API"""
    
    def __init__(self, api_key: str):
        """Initialize Groq client"""
        logger.info("Initializing Groq Whisper API client...")
        self.client = Groq(api_key=api_key)
        logger.info("✅ Groq Whisper client initialized successfully")
    
    def transcribe(self, audio_path: str) -> dict:
        """Transcribe audio file to text using Groq Whisper API"""
        try:
            # Check file exists
            if not os.path.exists(audio_path):
                raise FileNotFoundError(f"Audio file not found: {audio_path}")
            
            file_size = os.path.getsize(audio_path)
            logger.info(f"📂 Audio file: {os.path.basename(audio_path)}")
            logger.info(f"📊 File size: {file_size} bytes ({file_size/1024:.2f} KB)")
            
            if file_size < 1000:
                raise ValueError(f"Audio file too small: {file_size} bytes")
            
            # Read and send to Groq
            with open(audio_path, "rb") as audio_file:
                audio_data = audio_file.read()
                logger.info(f"📤 Sending {len(audio_data)} bytes to Groq Whisper API...")
                
                # Add language detection and longer prompt
                transcription = self.client.audio.transcriptions.create(
                    file=(os.path.basename(audio_path), audio_data),
                    model="whisper-large-v3",
                    response_format="verbose_json",  # Get more details
                    temperature=0.0
                )
            
            text = transcription.text.strip()
            logger.info(f"✅ Transcription result: '{text}'")
            logger.info(f"📏 Text length: {len(text)} characters")
            
            # Log additional info if available
            if hasattr(transcription, 'language'):
                logger.info(f"🌍 Detected language: {transcription.language}")
            if hasattr(transcription, 'duration'):
                logger.info(f"⏱️ Audio duration: {transcription.duration}s")
            
            return {
                "success": True,
                "text": text
            }
        
        except Exception as e:
            logger.error(f"❌ Transcription error: {str(e)}")
            logger.error(f"📋 Error type: {type(e).__name__}")
            return {
                "success": False,
                "error": str(e)
            }