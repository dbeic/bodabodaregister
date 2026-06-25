"""
Configuration module for the Bodaboda Registration Application
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Base configuration class"""
    # Flask configuration
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'
    
    # Database configuration
    DATABASE_URL = os.environ.get('DATABASE_URL')
    
    # Application configuration
    APP_NAME = os.environ.get('APP_NAME', 'Bodaboda SACCO Registration')
    GROUP_NAME = os.environ.get('GROUP_NAME', 'Bodaboda SACCO')
    
    # File upload configuration
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads')
    BADGE_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'badges')
    QR_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'qr')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
    
    # Badge configuration
    BADGE_WIDTH = 900
    BADGE_HEIGHT = 570
    BADGE_BG_COLOR = (25, 55, 85)  # Dark Blue
    BADGE_ACCENT_COLOR = (212, 175, 55)  # Gold
    BADGE_TEXT_COLOR = (255, 255, 255)  # White
    
    # Session configuration
    SESSION_TYPE = 'filesystem'
    SESSION_PERMANENT = False
    
    # Ensure directories exist
    @staticmethod
    def ensure_directories():
        """Create necessary directories if they don't exist"""
        directories = [
            Config.UPLOAD_FOLDER,
            Config.BADGE_FOLDER,
            Config.QR_FOLDER
        ]
        for directory in directories:
            if not os.path.exists(directory):
                os.makedirs(directory)

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    
class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    DEBUG = True

# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}

# Ensure directories on import
Config.ensure_directories()
