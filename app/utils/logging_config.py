# app/utils/logging_config.py
import logging
import logging.handlers
import json
from datetime import datetime
from flask import request, g
from functools import wraps
import os
from pathlib import Path

class StructuredFormatter(logging.Formatter):
    """Formateador para logs estructurados en JSON"""
    def format(self, record):
        log_obj = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Agregar campos extra si existen
        if hasattr(record, 'extra_fields'):
            log_obj.update(record.extra_fields)
            
        return json.dumps(log_obj, ensure_ascii=False)

def setup_logging(app):
    """Configurar el sistema de logging para la aplicación"""
    
    # Crear directorio de logs si no existe
    log_dir = Path('logs')
    log_dir.mkdir(exist_ok=True)
    
    # Configurar logger principal
    app.logger.setLevel(logging.INFO)
    
    # Handler para archivo de logs general
    file_handler = logging.handlers.RotatingFileHandler(
        'logs/app.log',
        maxBytes=10485760,  # 10MB
        backupCount=10
    )
    file_handler.setFormatter(StructuredFormatter())
    app.logger.addHandler(file_handler)
    
    # Handler separado para logs de acceso/uso
    access_logger = logging.getLogger('access')
    access_handler = logging.handlers.RotatingFileHandler(
        'logs/access.log',
        maxBytes=10485760,
        backupCount=30  # Mantener más histórico de acceso
    )
    access_handler.setFormatter(StructuredFormatter())
    access_logger.addHandler(access_handler)
    access_logger.setLevel(logging.INFO)
    
    # Handler para logs de búsquedas
    search_logger = logging.getLogger('search')
    search_handler = logging.handlers.RotatingFileHandler(
        'logs/search.log',
        maxBytes=10485760,
        backupCount=20
    )
    search_handler.setFormatter(StructuredFormatter())
    search_logger.addHandler(search_handler)
    search_logger.setLevel(logging.INFO)
    
    # Handler para logs de errores
    error_handler = logging.handlers.RotatingFileHandler(
        'logs/error.log',
        maxBytes=10485760,
        backupCount=10
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(StructuredFormatter())
    app.logger.addHandler(error_handler)
    
    return app
