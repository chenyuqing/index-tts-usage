"""API routes for IndexTTS2 service"""

import os
import time
import logging
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import base64
import tempfile
from pathlib import Path

from .models import (
    TTSStrategy, AudioFormat,
    VoiceCloneRequest, TTSRequest,
    VoiceAnalysisResponse, TTSResponse,
    ErrorResponse, HealthResponse, ModelInfo
)
from core.tts_service import get_tts_service
from config.settings import get_config

logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

# Initialize config
config = get_config()


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    try:
        tts_service = get_tts_service()
        health_info = tts_service.health_check()

        return HealthResponse(
            status="healthy",
            version="1.0.0",
            model_loaded=health_info["model_loaded"],
            device=health_info["device"],
            memory_usage={"available": "N/A", "used": "N/A"}
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unavailable")


@router.get("/models", response_model=ModelInfo)
async def get_model_info():
    """Get model information"""
    return ModelInfo(
        name="IndexTTS2",
        version="2.0",
        supported_languages=["zh", "en", "yue"],
        supported_emotions=["happy", "sad", "angry", "neutral", "surprised"],
        capabilities=["voice_cloning", "emotion_control", "duration_control"]
    )


@router.post("/tts", response_model=TTSResponse)
async def text_to_speech(request: TTSRequest):
    """Standard text-to-speech endpoint"""
    try:
        tts_service = get_tts_service()

        # Convert request parameters
        params = {
            "emotion": request.emotion.value if request.emotion else None,
            "speed": request.speed,
            "pitch": request.pitch
        }

        # Generate speech
        result = tts_service.synthesize_speech(
            text=request.text,
            voice_id=request.voice_id,
            **params
        )

        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["message"])

        # Read audio file and encode as base64
        audio_path = result["audio_path"]
        with open(audio_path, "rb") as f:
            audio_data = base64.b64encode(f.read()).decode()

        # Cleanup temporary file
        os.unlink(audio_path)

        return TTSResponse(
            success=True,
            audio_data=audio_data,
            duration=result["duration"],
            speaker_id=result.get("speaker_id"),
            processing_time=result["processing_time"],
            message="TTS generation completed successfully"
        )

    except Exception as e:
        logger.error(f"TTS generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/clone-voice", response_model=TTSResponse)
async def clone_voice(
    text: str = Form(...),
    reference_audio: UploadFile = File(...),
    language: str = Form("zh"),
    emotion: str = Form(None),
    speed: float = Form(1.0),
    pitch: float = Form(1.0)
):
    """Voice cloning endpoint with file upload"""
    try:
        tts_service = get_tts_service()

        # Save uploaded audio file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
            content = await reference_audio.read()
            f.write(content)
            temp_audio_path = f.name

        # Clone voice
        result = tts_service.clone_voice(
            text=text,
            reference_audio=temp_audio_path,
            emotion=emotion,
            speed=speed,
            pitch=pitch
        )

        # Cleanup temporary reference audio
        os.unlink(temp_audio_path)

        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["message"])

        # Read generated audio and encode as base64
        audio_path = result["audio_path"]
        with open(audio_path, "rb") as f:
            audio_data = base64.b64encode(f.read()).decode()

        # Cleanup temporary generated audio
        os.unlink(audio_path)

        return TTSResponse(
            success=True,
            audio_data=audio_data,
            duration=result["duration"],
            speaker_id=result.get("speaker_id"),
            processing_time=result["processing_time"],
            message="Voice cloning completed successfully"
        )

    except Exception as e:
        logger.error(f"Voice cloning failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze-voice", response_model=VoiceAnalysisResponse)
async def analyze_voice(reference_audio: UploadFile = File(...)):
    """Analyze voice characteristics"""
    try:
        tts_service = get_tts_service()

        # Save uploaded audio file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
            content = await reference_audio.read()
            f.write(content)
            temp_audio_path = f.name

        # Analyze voice
        result = tts_service.analyze_voice(temp_audio_path)

        # Cleanup temporary file
        os.unlink(temp_audio_path)

        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["message"])

        return VoiceAnalysisResponse(
            speaker_id=result["speaker_id"],
            emotion=result.get("emotion"),
            confidence=result["confidence"],
            features=result["features"]
        )

    except Exception as e:
        logger.error(f"Voice analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/audio/{audio_id}")
async def get_audio(audio_id: str):
    """Get generated audio file by ID"""
    try:
        # This would typically retrieve audio from a database or file system
        # For now, we'll return a 404
        raise HTTPException(status_code=404, detail="Audio not found")
    except Exception as e:
        logger.error(f"Failed to retrieve audio: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Error handlers
@router.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """HTTP exception handler"""
    return ErrorResponse(
        error=exc.detail,
        error_code=str(exc.status_code)
    )


@router.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """General exception handler"""
    logger.error(f"Unhandled exception: {exc}")
    return ErrorResponse(
        error="Internal server error",
        error_code="500"
    )


# CORS middleware setup
def setup_cors(app):
    """Setup CORS middleware"""
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=config.CORS_METHODS,
        allow_headers=config.CORS_HEADERS,
    )