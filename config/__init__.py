# app/config.py
import os
from datetime import timedelta

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
    
    # ===== CONFIGURACIÓN DE LOGGING =====
    # Directorio de logs
    LOG_DIR = 'logs'
    LOG_TO_STDOUT = os.environ.get('LOG_TO_STDOUT', 'false').lower() == 'true'
    
    # Niveles de logging
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    
    # Configuración de archivos de log
    LOG_FILE_MAX_BYTES = 10485760  # 10MB
    LOG_FILE_BACKUP_COUNT = 10
    
    # Tipos de logs a mantener
    LOG_TYPES = {
        'app': {
            'filename': 'app.log',
            'level': 'INFO',
            'backup_count': 10
        },
        'access': {
            'filename': 'access.log',
            'level': 'INFO',
            'backup_count': 30  # Más histórico para análisis de uso
        },
        'search': {
            'filename': 'search.log',
            'level': 'INFO',
            'backup_count': 20
        },
        'error': {
            'filename': 'error.log',
            'level': 'ERROR',
            'backup_count': 10
        },
        'performance': {
            'filename': 'performance.log',
            'level': 'INFO',
            'backup_count': 15
        }
    }
    
    # Configuración de métricas
    METRICS_ENABLED = True
    METRICS_TRACK_UNIQUE_USERS = True
    METRICS_ANONYMIZE_IPS = True  # Hash IPs for privacy
    METRICS_SESSION_TIMEOUT = timedelta(minutes=30)  # Para calcular sesiones
    
    # Configuración de tracking
    TRACK_USER_AGENTS = True
    TRACK_SEARCH_TERMS = True
    TRACK_RESPONSE_TIME = True
    TRACK_DATABASE_QUERIES = False  # Activar solo en desarrollo
    
    # Alertas y monitoreo
    ALERT_ON_SLOW_REQUESTS = True
    SLOW_REQUEST_THRESHOLD_MS = 1000  # 1 segundo
    ALERT_ON_HIGH_ERROR_RATE = True
    ERROR_RATE_THRESHOLD = 0.05  # 5% de errores
    
    # Privacidad y seguridad en logs
    LOG_SANITIZE_FIELDS = ['password', 'token', 'api_key', 'secret', 'rfc']
    LOG_EXCLUDE_PATHS = ['/health', '/metrics', '/static']  # No loggear estos paths
    
    # Retención de logs
    LOG_RETENTION_DAYS = 90  # Días a mantener logs antes de archivar
    LOG_ARCHIVE_ENABLED = False  # Activar en producción si se necesita

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
    
    # ===== LOGGING EN DESARROLLO =====
    LOG_LEVEL = 'DEBUG'
    TRACK_DATABASE_QUERIES = True  # Ver queries SQL en logs
    LOG_TO_STDOUT = True  # También mostrar logs en consola
    
    # Más verbose en desarrollo
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
    
    # Métricas más detalladas en desarrollo
    METRICS_INCLUDE_DEBUG = True
    METRICS_SAMPLE_RATE = 1.0  # Loggear todo (100%)

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
    
    # ===== LOGGING EN PRODUCCIÓN =====
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'WARNING')
    TRACK_DATABASE_QUERIES = False  # No loggear queries en producción
    
    # Logs más compactos en producción
    LOG_FORMAT = 'json'  # Usar formato JSON estructurado
    
    # Configuración de métricas para producción
    METRICS_SAMPLE_RATE = 0.1  # Samplear 10% de requests para reducir volumen
    METRICS_INCLUDE_DEBUG = False
    
    # Alertas activas en producción
    ALERT_EMAIL_ENABLED = True
    ALERT_EMAIL_TO = os.environ.get('ALERT_EMAIL', 'admin@example.com')
    ALERT_EMAIL_FROM = 'noreply@contratos.gob.mx'
    
    # Integración con servicios externos (opcional)
    SENTRY_DSN = os.environ.get('SENTRY_DSN')  # Para error tracking
    DATADOG_API_KEY = os.environ.get('DATADOG_API_KEY')  # Para métricas
    
    # Archivado de logs antiguos
    LOG_ARCHIVE_ENABLED = True
    LOG_ARCHIVE_COMPRESSION = 'gzip'
    LOG_ARCHIVE_PATH = '/var/log/contratos/archive'
    
    # Rate limiting para logs (evitar flood)
    LOG_RATE_LIMIT_ENABLED = True
    LOG_RATE_LIMIT_PER_MINUTE = 1000

class TestingConfig(Config):
    """Configuración para tests"""
    TESTING = True
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    
    # ===== LOGGING EN TESTS =====
    LOG_LEVEL = 'ERROR'  # Solo errores en tests
    LOG_TO_STDOUT = False  # No mostrar logs en tests
    METRICS_ENABLED = False  # Desactivar métricas en tests
    
    # Configuración específica para tests
    LOG_DIR = 'test_logs'
    LOG_FILE_MAX_BYTES = 1048576  # 1MB para tests

# Diccionario de configuraciones
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}

# Función helper para obtener configuración actual
def get_config():
    """Obtiene la configuración basada en la variable de entorno FLASK_ENV"""
    env = os.environ.get('FLASK_ENV', 'development')
    return config.get(env, config['default'])