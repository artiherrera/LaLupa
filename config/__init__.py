import os

class Config:
    """Configuración base"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # Database
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_RECORD_QUERIES = True
    
    # JSON
    JSON_AS_ASCII = False
    JSON_SORT_KEYS = False
    
    # Pagination
    CONTRACTS_PER_PAGE = 50
    MAX_CONTRACTS_PER_PAGE = 100
    
    # Cache
    CACHE_TYPE = 'simple'
    CACHE_DEFAULT_TIMEOUT = 300

class DevelopmentConfig(Config):
    """Configuración de desarrollo"""
    DEBUG = True
    TESTING = False
    
    # Database - Usando tu conexión de DigitalOcean
    DB_USER = os.getenv('DB_USER', 'lalupa')
    DB_PASSWORD = os.getenv('DB_PASSWORD', 'Kx9mP!7Nq3Lw5Rv_')
    DB_HOST = os.getenv('DB_HOST', 'db-postgresql-nyc1-16758-do-user-15464590-0.k.db.ondigitalocean.com')
    DB_PORT = os.getenv('DB_PORT', '25060')
    DB_NAME = os.getenv('DB_NAME', 'defaultdb')
    
    # Importante: sslmode=require para DigitalOcean
    SQLALCHEMY_DATABASE_URI = f'postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?sslmode=require'
    
    # Development specific
    SQLALCHEMY_ECHO = False  # Set to True to see SQL queries

class ProductionConfig(Config):
    """Configuración de producción"""
    DEBUG = False
    TESTING = False
    
    # Database from environment variable
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    
    # Security
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # Performance - Importante para DigitalOcean
    SQLALCHEMY_POOL_SIZE = 10
    SQLALCHEMY_POOL_RECYCLE = 3600
    SQLALCHEMY_POOL_TIMEOUT = 30
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 3600,
        'connect_args': {
            'connect_timeout': 10,
            'options': '-c statement_timeout=30000'  # 30 segundos timeout
        }
    }

class TestingConfig(Config):
    """Configuración para tests"""
    TESTING = True
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False

# Diccionario de configuraciones
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
