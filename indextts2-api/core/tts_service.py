"""Core TTS service implementation"""

import os
import time
import logging
from typing import Optional, Dict, Any
import numpy as np
import soundfile as sf
import tempfile
from pathlib import Path

# Import IndexTTS2 components
try:
    from indextts.infer_v2 import IndexTTS2
    from indextts.utils.common import get_device
    from omegaconf import OmegaConf
except ImportError as e:
    logging.error(f"Failed to import IndexTTS2: {e}")
    raise

logger = logging.getLogger(__name__)


class TTSService:
    """Core TTS service for voice cloning and synthesis"""

    def __init__(self, checkpoint_dir: str = "./checkpoints"):
        """Initialize TTS service"""
        self.checkpoint_dir = Path(checkpoint_dir)
        self.model = None
        self.config = None
        self.device = None
        self.is_initialized = False

        # Initialize on first use
        self._initialize()

    def _initialize(self):
        """Initialize the TTS model"""
        if self.is_initialized:
            return

        try:
            # Load configuration
            config_path = self.checkpoint_dir / "config.yaml"
            if not config_path.exists():
                raise FileNotFoundError(f"Config file not found: {config_path}")

            self.config = OmegaConf.load(config_path)

            # Get device
            self.device = get_device()

            # Initialize IndexTTS2 model
            self.model = IndexTTS2(
                config_path=str(config_path),
                checkpoint_dir=str(self.checkpoint_dir),
                device=self.device
            )

            self.is_initialized = True
            logger.info(f"IndexTTS2 model initialized successfully on {self.device}")

        except Exception as e:
            logger.error(f"Failed to initialize TTS service: {e}")
            raise

    def health_check(self) -> Dict[str, Any]:
        """Perform health check"""
        return {
            "model_loaded": self.is_initialized,
            "device": str(self.device),
            "checkpoint_dir": str(self.checkpoint_dir),
            "config_loaded": self.config is not None
        }

    def clone_voice(self, text: str, reference_audio: str, **kwargs) -> Dict[str, Any]:
        """
        Clone voice from reference audio and generate speech

        Args:
            text: Text to synthesize
            reference_audio: Path to reference audio file
            **kwargs: Additional parameters (emotion, speed, pitch, etc.)

        Returns:
            Dictionary containing generated audio and metadata
        """
        start_time = time.time()

        try:
            # Validate inputs
            if not os.path.exists(reference_audio):
                raise FileNotFoundError(f"Reference audio not found: {reference_audio}")

            if len(text) > 500:
                raise ValueError("Text too long (max 500 characters)")

            # Generate voice-cloned audio
            result = self.model.infer(
                text=text,
                ref_audio=reference_audio,
                emotion=kwargs.get('emotion'),
                speed=kwargs.get('speed', 1.0),
                pitch=kwargs.get('pitch', 1.0)
            )

            # Save to temporary file
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                sf.write(f.name, result['audio'], result['sample_rate'])
                audio_path = f.name

            processing_time = time.time() - start_time

            return {
                "success": True,
                "audio_path": audio_path,
                "duration": len(result['audio']) / result['sample_rate'],
                "sample_rate": result['sample_rate'],
                "processing_time": processing_time,
                "speaker_id": self._extract_speaker_id(result),
                "message": "Voice cloning completed successfully"
            }

        except Exception as e:
            logger.error(f"Voice cloning failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "processing_time": time.time() - start_time,
                "message": "Voice cloning failed"
            }

    def synthesize_speech(self, text: str, voice_id: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """
        Synthesize speech with optional voice characteristics

        Args:
            text: Text to synthesize
            voice_id: Optional voice identifier
            **kwargs: Additional parameters

        Returns:
            Dictionary containing generated audio and metadata
        """
        start_time = time.time()

        try:
            # For standard TTS, use default voice if no voice_id provided
            if voice_id is None:
                # Use a default reference voice
                default_voice = self._get_default_voice()
                reference_audio = default_voice
            else:
                # Load voice characteristics from voice_id
                reference_audio = self._load_voice_characteristics(voice_id)

            # Generate speech
            result = self.model.infer(
                text=text,
                ref_audio=reference_audio,
                emotion=kwargs.get('emotion'),
                speed=kwargs.get('speed', 1.0),
                pitch=kwargs.get('pitch', 1.0)
            )

            # Save to temporary file
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                sf.write(f.name, result['audio'], result['sample_rate'])
                audio_path = f.name

            processing_time = time.time() - start_time

            return {
                "success": True,
                "audio_path": audio_path,
                "duration": len(result['audio']) / result['sample_rate'],
                "sample_rate": result['sample_rate'],
                "processing_time": processing_time,
                "message": "Speech synthesis completed successfully"
            }

        except Exception as e:
            logger.error(f"Speech synthesis failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "processing_time": time.time() - start_time,
                "message": "Speech synthesis failed"
            }

    def analyze_voice(self, audio_path: str) -> Dict[str, Any]:
        """
        Analyze voice characteristics from audio

        Args:
            audio_path: Path to audio file

        Returns:
            Dictionary containing voice analysis results
        """
        try:
            # Extract voice features using IndexTTS2
            features = self.model.extract_features(audio_path)

            return {
                "success": True,
                "speaker_id": self._extract_speaker_id(features),
                "features": features,
                "confidence": features.get('confidence', 0.0),
                "emotion": features.get('emotion', 'neutral'),
                "message": "Voice analysis completed"
            }

        except Exception as e:
            logger.error(f"Voice analysis failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Voice analysis failed"
            }

    def _extract_speaker_id(self, result: Dict[str, Any]) -> str:
        """Extract speaker ID from model result"""
        # Generate a unique speaker ID based on voice characteristics
        if 'speaker_embedding' in result:
            embedding = result['speaker_embedding']
            # Create hash of embedding for speaker ID
            embedding_hash = hash(tuple(embedding.flatten()))
            return f"speaker_{abs(embedding_hash):016x}"
        else:
            return f"speaker_{int(time.time())}"

    def _get_default_voice(self) -> str:
        """Get default reference voice"""
        # Look for default voice in examples directory
        examples_dir = Path("./examples")
        if examples_dir.exists():
            voice_files = list(examples_dir.glob("voice_*.wav"))
            if voice_files:
                return str(voice_files[0])

        # Fallback to first available voice
        raise FileNotFoundError("No default voice found")

    def _load_voice_characteristics(self, voice_id: str) -> str:
        """Load voice characteristics from voice_id"""
        # This would typically load from a voice database
        # For now, we'll use the default voice
        return self._get_default_voice()

    def cleanup(self):
        """Cleanup temporary files"""
        # Implementation for cleaning up temporary audio files
        pass


# Global service instance
_tts_service = None


def get_tts_service() -> TTSService:
    """Get global TTS service instance"""
    global _tts_service
    if _tts_service is None:
        _tts_service = TTSService()
    return _tts_service