# app/utils/activity_tracker.py
from flask import request, g, session
from datetime import datetime
import logging
import hashlib
from user_agents import parse
from functools import wraps
import time

access_logger = logging.getLogger('access')
search_logger = logging.getLogger('search')

class ActivityTracker:
    """Rastrea actividad de usuarios en la plataforma"""
    
    @staticmethod
    def get_user_fingerprint():
        """Genera un fingerprint único para el usuario (anónimo)"""
        user_agent = request.headers.get('User-Agent', '')
        ip = request.remote_addr
        # Hash para anonimizar
        fingerprint = hashlib.md5(f"{ip}{user_agent}".encode()).hexdigest()
        return fingerprint
    
    @staticmethod
    def get_request_context():
        """Obtiene contexto de la petición actual"""
        user_agent = parse(request.headers.get('User-Agent', ''))
        
        return {
            'ip_hash': hashlib.md5(request.remote_addr.encode()).hexdigest()[:8],
            'method': request.method,
            'path': request.path,
            'endpoint': request.endpoint,
            'referrer': request.referrer,
            'browser': user_agent.browser.family,
            'browser_version': user_agent.browser.version_string,
            'os': user_agent.os.family,
            'device': user_agent.device.family,
            'is_mobile': user_agent.is_mobile,
            'is_bot': user_agent.is_bot,
            'session_id': session.get('session_id'),
            'user_fingerprint': ActivityTracker.get_user_fingerprint()
        }
    
    @staticmethod
    def log_request():
        """Log de cada request HTTP"""
        g.start_time = time.time()
        
        context = ActivityTracker.get_request_context()
        
        access_logger.info(
            f"Request iniciado",
            extra={'extra_fields': {
                'event': 'request_start',
                **context
            }}
        )
    
    @staticmethod
    def log_response(response):
        """Log de cada response HTTP"""
        if hasattr(g, 'start_time'):
            elapsed = time.time() - g.start_time
        else:
            elapsed = 0
            
        context = ActivityTracker.get_request_context()
        
        access_logger.info(
            f"Request completado",
            extra={'extra_fields': {
                'event': 'request_complete',
                'status_code': response.status_code,
                'response_time': round(elapsed * 1000, 2),  # en ms
                **context
            }}
        )
        
        return response
    
    @staticmethod
    def log_search(search_params, results_count, execution_time):
        """Log de búsquedas realizadas"""
        context = ActivityTracker.get_request_context()
        
        # Sanitizar parámetros sensibles si los hay
        safe_params = {
            k: v for k, v in search_params.items() 
            if k not in ['password', 'token', 'api_key']
        }
        
        search_logger.info(
            f"Búsqueda realizada",
            extra={'extra_fields': {
                'event': 'search',
                'search_params': safe_params,
                'results_count': results_count,
                'execution_time_ms': round(execution_time * 1000, 2),
                'has_filters': bool(any(v for k, v in safe_params.items() if k != 'q')),
                **context
            }}
        )
    
    @staticmethod
    def log_contract_view(contract_id, contract_data=None):
        """Log cuando se visualiza un contrato específico"""
        context = ActivityTracker.get_request_context()
        
        log_data = {
            'event': 'contract_view',
            'contract_id': contract_id,
            **context
        }
        
        if contract_data:
            log_data.update({
                'institucion': contract_data.get('siglas_institucion'),
                'tipo_procedimiento': contract_data.get('tipo_procedimiento'),
                'importe': contract_data.get('importe'),
                'anio': contract_data.get('anio_fuente')
            })
        
        access_logger.info(
            f"Contrato visualizado",
            extra={'extra_fields': log_data}
        )
    
    @staticmethod
    def log_export(format_type, filters, count):
        """Log de exportaciones de datos"""
        context = ActivityTracker.get_request_context()
        
        access_logger.info(
            f"Datos exportados",
            extra={'extra_fields': {
                'event': 'export',
                'format': format_type,
                'filters': filters,
                'records_count': count,
                **context
            }}
        )
    
    @staticmethod
    def log_error(error, error_type='general'):
        """Log de errores con contexto"""
        context = ActivityTracker.get_request_context()
        
        logging.getLogger('app').error(
            f"Error: {str(error)}",
            extra={'extra_fields': {
                'event': 'error',
                'error_type': error_type,
                'error_message': str(error),
                'error_class': error.__class__.__name__,
                **context
            }},
            exc_info=True
        )
