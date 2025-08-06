"""
Configuration settings for the OneFantasy application.
"""
import os
from typing import Dict, Any

class Config:
    """Base configuration class."""
    
    # Flask settings
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    
    # Firebase settings
    FIREBASE_KEY_PATH = os.environ.get('FIREBASE_KEY_PATH', '/app/firebase-key.json')
    FIREBASE_PROJECT_ID = os.environ.get('FIREBASE_PROJECT_ID', 'onefantasy-app')
    
    # API settings
    FPL_API_BASE_URL = 'https://fantasy.premierleague.com/api'
    FPL_BOOTSTRAP_URL = f'{FPL_API_BASE_URL}/bootstrap-static/'
    FPL_FIXTURES_URL = f'{FPL_API_BASE_URL}/fixtures/'
    
    # CORS settings
    CORS_ORIGINS = [
        'http://localhost:3000',
        'http://frontend:3000',
        'http://127.0.0.1:3000'
    ]
    
    # SocketIO settings
    SOCKETIO_CORS_ALLOWED_ORIGINS = CORS_ORIGINS
    SOCKETIO_ASYNC_MODE = 'eventlet'
    
    # Draft settings
    DEFAULT_PICK_TIME_SECONDS = 120  # 2 minutes per pick
    MAX_LEAGUE_SIZE = 18
    MIN_LEAGUE_SIZE = 6
    DEFAULT_ROSTER_SIZE = 15
    DEFAULT_STARTING_LINEUP_SIZE = 11
    
    # Waiver settings
    DEFAULT_WAIVER_BUDGET = 100
    WAIVER_CLEAR_TIME_HOURS = 24
    
    # Cache settings
    PLAYER_DATA_CACHE_HOURS = 6
    
    # Logging
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    
    @staticmethod
    def get_firebase_config() -> Dict[str, Any]:
        """Get Firebase configuration."""
        return {
            'type': 'service_account',
            'project_id': Config.FIREBASE_PROJECT_ID,
            'private_key_id': os.environ.get('FIREBASE_PRIVATE_KEY_ID'),
            'private_key': os.environ.get('FIREBASE_PRIVATE_KEY', '').replace('\\n', '\n'),
            'client_email': os.environ.get('FIREBASE_CLIENT_EMAIL'),
            'client_id': os.environ.get('FIREBASE_CLIENT_ID'),
            'auth_uri': 'https://accounts.google.com/o/oauth2/auth',
            'token_uri': 'https://oauth2.googleapis.com/token',
            'auth_provider_x509_cert_url': 'https://www.googleapis.com/oauth2/v1/certs',
            'client_x509_cert_url': os.environ.get('FIREBASE_CLIENT_CERT_URL')
        }

class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True

class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    SECRET_KEY = os.environ.get('SECRET_KEY')
    
    @staticmethod
    def validate_production_config():
        """Validate required production environment variables."""
        required_vars = [
            'SECRET_KEY',
            'FIREBASE_PROJECT_ID',
            'FIREBASE_PRIVATE_KEY',
            'FIREBASE_CLIENT_EMAIL'
        ]
        
        missing = [var for var in required_vars if not os.environ.get(var)]
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")

# Configuration mapping
config_map = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}

def get_config():
    """Get configuration based on environment."""
    env = os.environ.get('FLASK_ENV', 'development')
    return config_map.get(env, DevelopmentConfig)