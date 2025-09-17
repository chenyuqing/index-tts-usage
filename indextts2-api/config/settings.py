# IndexTTS2 API Service Configuration

class Config:
    """Base configuration class"""

    # Server settings
    HOST = "0.0.0.0"
    PORT = 7861
    DEBUG = False

    # Model settings
    CHECKPOINT_DIR = "./checkpoints"
    CONFIG_FILE = "config.yaml"

    # Audio settings
    SAMPLE_RATE = 22050
    MAX_AUDIO_DURATION = 15  # seconds

    # Processing settings
    USE_HALF_PRECISION = True
    DEVICE = "auto"  # auto, cpu, cuda

    # API settings
    MAX_TEXT_LENGTH = 500
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

    # CORS settings
    CORS_ORIGINS = ["*"]
    CORS_METHODS = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    CORS_HEADERS = ["*"]


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    DEVICE = "auto"


class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    USE_HALF_PRECISION = True


# Configuration mapping
config_map = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}


def get_config(env='default'):
    """Get configuration by environment"""
    return config_map.get(env, DevelopmentConfig)()