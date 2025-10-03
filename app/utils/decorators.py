# app/decorators.py
from functools import wraps
from flask import g
import time
from app.utils.activity_tracker import ActivityTracker

def track_activity(func):
    """Decorador para rastrear actividad en endpoints específicos"""
    @wraps(func)
    def decorated_function(*args, **kwargs):
        g.start_time = time.time()
        
        try:
            result = func(*args, **kwargs)
            
            # Log específico según el endpoint
            if 'contract' in func.__name__:
                contract_id = kwargs.get('id')
                if contract_id:
                    ActivityTracker.log_contract_view(contract_id)
                    
            return result
            
        except Exception as e:
            ActivityTracker.log_error(e, error_type='endpoint_error')
            raise
            
    return decorated_function

def track_search(func):
    """Decorador específico para rastrear búsquedas"""
    @wraps(func)
    def decorated_function(*args, **kwargs):
        start_time = time.time()
        
        result = func(*args, **kwargs)
        
        execution_time = time.time() - start_time
        
        # Extraer parámetros de búsqueda del request
        from flask import request
        search_params = dict(request.args)
        
        # Asumir que result tiene info sobre cantidad de resultados
        results_count = len(result) if hasattr(result, '__len__') else 0
        
        ActivityTracker.log_search(search_params, results_count, execution_time)
        
        return result
        
    return decorated_function