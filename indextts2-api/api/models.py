"""Data models for IndexTTS2 API service"""

from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum


class AudioFormat(str, Enum):
    """Supported audio formats"""
    WAV = "wav"
    MP3 = "mp3"
    FLAC = "flac"


class Language(str, Enum):
    """Supported languages"""
    ZH = "zh"  # Chinese
    EN = "en"  # English
    YUE = "yue"  # Cantonese


class Emotion(str, Enum):
    """Supported emotions"""
    HAPPY = "happy"
    SAD = "sad"
    ANGRY = "angry"
    NEUTRAL = "neutral"
    SURPRISED = "surprised"


class TTSStrategy(str, Enum):
    """TTS generation strategies"""
    AUTO = "auto"
    FAST = "fast"
    QUALITY = "quality"


class VoiceCloneRequest(BaseModel):
    """Voice cloning request model"""
    text: str = Field(..., description="Text to synthesize", min_length=1, max_length=500)
    reference_audio: str = Field(..., description="Path or URL to reference audio file")
    language: Language = Field(default=Language.ZH, description="Target language")
    emotion: Optional[Emotion] = Field(default=None, description="Desired emotion")
    strategy: TTSStrategy = Field(default=TTSStrategy.AUTO, description="Generation strategy")
    speed: float = Field(default=1.0, description="Speech speed factor", ge=0.5, le=2.0)
    pitch: float = Field(default=1.0, description="Pitch adjustment factor", ge=0.5, le=2.0)


class TTSRequest(BaseModel):
    """Standard TTS request model"""
    text: str = Field(..., description="Text to synthesize", min_length=1, max_length=500)
    language: Language = Field(default=Language.ZH, description="Target language")
    voice_id: Optional[str] = Field(default=None, description="Voice ID for synthesis")
    emotion: Optional[Emotion] = Field(default=None, description="Desired emotion")
    speed: float = Field(default=1.0, description="Speech speed factor", ge=0.5, le=2.0)
    pitch: float = Field(default=1.0, description="Pitch adjustment factor", ge=0.5, le=2.0)
    format: AudioFormat = Field(default=AudioFormat.WAV, description="Output audio format")


class VoiceAnalysisResponse(BaseModel):
    """Voice analysis response model"""
    speaker_id: str = Field(..., description="Unique speaker identifier")
    emotion: Optional[str] = Field(default=None, description="Detected emotion")
    confidence: float = Field(..., description="Analysis confidence score", ge=0.0, le=1.0)
    features: dict = Field(..., description="Extracted voice features")


class TTSResponse(BaseModel):
    """TTS generation response model"""
    success: bool = Field(..., description="Request success status")
    audio_url: Optional[str] = Field(default=None, description="URL to generated audio")
    audio_data: Optional[str] = Field(default=None, description="Base64 encoded audio data")
    duration: float = Field(..., description="Audio duration in seconds")
    speaker_id: Optional[str] = Field(default=None, description="Speaker ID used")
    processing_time: float = Field(..., description="Processing time in seconds")
    message: str = Field(..., description="Response message")


class ErrorResponse(BaseModel):
    """Error response model"""
    success: bool = Field(default=False, description="Request success status")
    error: str = Field(..., description="Error message")
    error_code: str = Field(..., description="Error code")
    details: Optional[dict] = Field(default=None, description="Additional error details")


class HealthResponse(BaseModel):
    """Service health response model"""
    status: str = Field(..., description="Service status")
    version: str = Field(..., description="API version")
    model_loaded: bool = Field(..., description="Model loading status")
    device: str = Field(..., description="Computing device")
    memory_usage: dict = Field(..., description="Memory usage info")


class ModelInfo(BaseModel):
    """Model information response model"""
    name: str = Field(..., description="Model name")
    version: str = Field(..., description="Model version")
    supported_languages: List[str] = Field(..., description="Supported languages")
    supported_emotions: List[str] = Field(..., description="Supported emotions")
    capabilities: List[str] = Field(..., description="Model capabilities")