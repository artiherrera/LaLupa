# app/__init__.py
import os
import logging
from pathlib import Path
from flask import Flask, g, request
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from config import config
import time
import json
from datetime import datetime
import hashlib

# Inicializar extensiones
db = SQLAlchemy()
migrate = Migrate()

def setup_logging(app):
    """Configurar el sistema de logging"""
    
    # Crear directorio de logs si no existe
    log_dir = Path('logs')
    log_dir.mkdir(exist_ok=True)
    
    # Configuración del formato de logs
    class JSONFormatter(logging.Formatter):
        def format(self, record):
            log_obj = {
                'timestamp': datetime.utcnow().isoformat(),
                'level': record.levelname,
                'message': record.getMessage(),
                'module': record.module,
                'function': record.funcName
            }
            if hasattr(record, 'extra_fields'):
                log_obj.update(record.extra_fields)
            return json.dumps(log_obj)
    
    # Configurar handlers para diferentes tipos de logs
    from logging.handlers import RotatingFileHandler
    
    # Handler para logs generales
    if not app.debug:
        file_handler = RotatingFileHandler(
            'logs/app.log',
            maxBytes=10240000,  # 10MB
            backupCount=10
        )
        file_handler.setFormatter(JSONFormatter())
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info('Aplicación iniciada')
    
    # Logger para accesos
    access_logger = logging.getLogger('access')
    access_handler = RotatingFileHandler(
        'logs/access.log',
        maxBytes=10240000,
        backupCount=10
    )
    access_handler.setFormatter(JSONFormatter())
    access_logger.addHandler(access_handler)
    access_logger.setLevel(logging.INFO)
    
    # Logger para búsquedas
    search_logger = logging.getLogger('search')
    search_handler = RotatingFileHandler(
        'logs/search.log',
        maxBytes=10240000,
        backupCount=10
    )
    search_handler.setFormatter(JSONFormatter())
    search_logger.addHandler(search_handler)
    search_logger.setLevel(logging.INFO)
    
    # Logger para errores
    error_logger = logging.getLogger('error')
    error_handler = RotatingFileHandler(
        'logs/error.log',
        maxBytes=10240000,
        backupCount=10
    )
    error_handler.setFormatter(JSONFormatter())
    error_handler.setLevel(logging.ERROR)
    error_logger.addHandler(error_handler)
    
    return app

def log_request():
    """Log cada request"""
    g.start_time = time.time()
    
    # Crear fingerprint anónimo del usuario
    user_agent = request.headers.get('User-Agent', '')
    ip = request.remote_addr
    user_fingerprint = hashlib.md5(f"{ip}{user_agent}".encode()).hexdigest()
    
    access_logger = logging.getLogger('access')
    
    # Información del request
    log_data = {
        'event': 'request_start',
        'method': request.method,
        'path': request.path,
        'endpoint': request.endpoint,
        'ip_hash': hashlib.md5(ip.encode()).hexdigest()[:8],
        'user_fingerprint': user_fingerprint,
        'user_agent': user_agent[:100]  # Limitar longitud
    }
    
    access_logger.info(
        f"Request: {request.method} {request.path}",
        extra={'extra_fields': log_data}
    )

def log_response(response):
    """Log cada response"""
    if hasattr(g, 'start_time'):
        elapsed = time.time() - g.start_time
        
        access_logger = logging.getLogger('access')
        
        log_data = {
            'event': 'request_complete',
            'method': request.method,
            'path': request.path,
            'status_code': response.status_code,
            'response_time': round(elapsed * 1000, 2)  # en ms
        }
        
        access_logger.info(
            f"Response: {response.status_code} in {elapsed:.3f}s",
            extra={'extra_fields': log_data}
        )
    
    return response

def log_search(search_params, results_count):
    """Log búsquedas realizadas"""
    search_logger = logging.getLogger('search')
    
    # Sanitizar parámetros
    safe_params = {k: v for k, v in search_params.items() if v}
    
    log_data = {
        'event': 'search',
        'search_params': safe_params,
        'results_count': results_count,
        'has_filters': bool(any(k != 'q' for k in safe_params.keys()))
    }
    
    search_logger.info(
        f"Search: {safe_params.get('q', 'No query')} - {results_count} results",
        extra={'extra_fields': log_data}
    )

def create_app(config_name=None):
    """Factory para crear la aplicación"""
    
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')
    
    app = Flask(__name__)
    
    # Cargar configuración
    app.config.from_object(config[config_name])
    
    # Inicializar extensiones
    db.init_app(app)
    migrate.init_app(app, db)
    
    # Configurar logging
    setup_logging(app)
    
    # Registrar hooks para logging
    app.before_request(log_request)
    app.after_request(log_response)
    
    # ========== REGISTRAR BLUEPRINTS ==========
    
    # Blueprint principal (rutas de páginas)
    from app.routes import main_bp
    app.register_blueprint(main_bp)
    
    # Blueprint de API de búsqueda - IMPORTANTE: con prefijo /api
    from app.api.search import search_bp
    app.register_blueprint(search_bp, url_prefix='/api')
    
    # ========== MANEJADORES DE ERRORES ==========
    
    @app.errorhandler(404)
    def not_found_error(error):
        error_logger = logging.getLogger('error')
        error_logger.error(f"404 Error: {request.url}")
        return {'error': 'Not found'}, 404
    
    @app.errorhandler(500)
    def internal_error(error):
        error_logger = logging.getLogger('error')
        error_logger.error(f"500 Error: {str(error)}", exc_info=True)
        db.session.rollback()
        return {'error': 'Internal server error'}, 500
    
    @app.errorhandler(400)
    def bad_request_error(error):
        error_logger = logging.getLogger('error')
        error_logger.error(f"400 Error: {request.url} - {str(error)}")
        return {'error': 'Bad request'}, 400
    
    # ========== VERIFICACIÓN DE RUTAS (OPCIONAL - REMOVER EN PRODUCCIÓN) ==========
    
    # Imprimir rutas registradas para debugging
    if app.config.get('DEBUG'):
        print("\n" + "="*50)
        print("📍 RUTAS REGISTRADAS:")
        print("="*50)
        for rule in app.url_map.iter_rules():
            methods = ','.join(sorted(rule.methods - {'OPTIONS', 'HEAD'}))
            if methods:  # Solo mostrar rutas con métodos
                print(f"  {methods:8s} {rule.rule:30s} -> {rule.endpoint}")
        print("="*50 + "\n")
    
    # ========== LOGS DE INICIO ==========
    
    app.logger.info(f'Aplicación iniciada en modo {config_name}')
    
    # Mensaje de confirmación en consola
    print(f"✅ Aplicación Flask iniciada")
    print(f"📁 Modo: {config_name}")
    print(f"📂 Logs guardándose en: logs/")
    print(f"🔍 Para ver métricas ejecuta: python view_metrics.py")
    print(f"🌐 API disponible en: /api/search (POST) y /api/aggregates (POST)")
    
    return app

# Función helper para usar en routes
def track_search(func):
    """Decorador para rastrear búsquedas"""
    from functools import wraps
    
    @wraps(func)
    def decorated_function(*args, **kwargs):
        start_time = time.time()
        
        # Ejecutar la función
        result = func(*args, **kwargs)
        
        # Log de la búsqueda
        execution_time = time.time() - start_time
        
        # Extraer parámetros
        search_params = dict(request.args)
        
        # Contar resultados (ajusta según tu implementación)
        if hasattr(result, '__len__'):
            results_count = len(result)
        elif hasattr(result, 'total'):
            results_count = result.total
        else:
            results_count = 0
        
        # Log con tiempo de ejecución
        search_params['execution_time_ms'] = round(execution_time * 1000, 2)
        log_search(search_params, results_count)
        
        return result
    
    return decorated_function