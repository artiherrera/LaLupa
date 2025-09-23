# app/utils/metrics.py
from datetime import datetime, timedelta
from collections import Counter, defaultdict
import json
from pathlib import Path
import pandas as pd

class PlatformMetrics:
    """Analiza métricas de uso de la plataforma"""
    
    @staticmethod
    def parse_logs(log_file, start_date=None, end_date=None):
        """Parsea archivo de logs y filtra por fecha"""
        logs = []
        
        with open(log_file, 'r') as f:
            for line in f:
                try:
                    log_entry = json.loads(line)
                    log_time = datetime.fromisoformat(log_entry['timestamp'])
                    
                    if start_date and log_time < start_date:
                        continue
                    if end_date and log_time > end_date:
                        continue
                        
                    logs.append(log_entry)
                except:
                    continue
                    
        return logs
    
    @staticmethod
    def get_usage_metrics(days=7):
        """Obtiene métricas de uso de los últimos N días"""
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Parsear logs de acceso
        access_logs = PlatformMetrics.parse_logs(
            'logs/access.log',
            start_date,
            end_date
        )
        
        # Parsear logs de búsqueda
        search_logs = PlatformMetrics.parse_logs(
            'logs/search.log',
            start_date,
            end_date
        )
        
        metrics = {
            'period': f'{days} días',
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'general': PlatformMetrics._calculate_general_metrics(access_logs),
            'searches': PlatformMetrics._calculate_search_metrics(search_logs),
            'performance': PlatformMetrics._calculate_performance_metrics(access_logs),
            'users': PlatformMetrics._calculate_user_metrics(access_logs),
            'content': PlatformMetrics._calculate_content_metrics(access_logs)
        }
        
        return metrics
    
    @staticmethod
    def _calculate_general_metrics(logs):
        """Calcula métricas generales"""
        total_requests = len(logs)
        unique_users = len(set(l.get('user_fingerprint') for l in logs if l.get('user_fingerprint')))
        
        # Contador de endpoints más visitados
        endpoints = Counter(l.get('endpoint') for l in logs if l.get('endpoint'))
        
        # Análisis por dispositivo
        devices = Counter(l.get('is_mobile') for l in logs)
        
        return {
            'total_requests': total_requests,
            'unique_users': unique_users,
            'avg_requests_per_user': round(total_requests / unique_users, 2) if unique_users > 0 else 0,
            'top_endpoints': dict(endpoints.most_common(10)),
            'mobile_percentage': round((devices.get(True, 0) / total_requests * 100), 2) if total_requests > 0 else 0
        }
    
    @staticmethod
    def _calculate_search_metrics(logs):
        """Calcula métricas de búsquedas"""
        total_searches = len(logs)
        
        # Búsquedas con filtros vs sin filtros
        filtered_searches = sum(1 for l in logs if l.get('has_filters'))
        
        # Promedio de resultados
        results_counts = [l.get('results_count', 0) for l in logs]
        avg_results = sum(results_counts) / len(results_counts) if results_counts else 0
        
        # Búsquedas sin resultados
        no_results = sum(1 for count in results_counts if count == 0)
        
        # Términos más buscados (si hay campo 'q' en search_params)
        search_terms = []
        for log in logs:
            params = log.get('search_params', {})
            if params.get('q'):
                search_terms.append(params['q'].lower())
        
        top_terms = Counter(search_terms).most_common(20)
        
        return {
            'total_searches': total_searches,
            'filtered_searches': filtered_searches,
            'filter_usage_rate': round((filtered_searches / total_searches * 100), 2) if total_searches > 0 else 0,
            'avg_results_per_search': round(avg_results, 2),
            'no_results_searches': no_results,
            'no_results_rate': round((no_results / total_searches * 100), 2) if total_searches > 0 else 0,
            'top_search_terms': dict(top_terms)
        }
    
    @staticmethod
    def _calculate_performance_metrics(logs):
        """Calcula métricas de rendimiento"""
        response_times = [l.get('response_time', 0) for l in logs if l.get('response_time')]
        
        if not response_times:
            return {}
            
        return {
            'avg_response_time_ms': round(sum(response_times) / len(response_times), 2),
            'median_response_time_ms': round(sorted(response_times)[len(response_times)//2], 2),
            'p95_response_time_ms': round(sorted(response_times)[int(len(response_times) * 0.95)], 2),
            'p99_response_time_ms': round(sorted(response_times)[int(len(response_times) * 0.99)], 2),
            'slow_requests_count': sum(1 for t in response_times if t > 1000),  # >1 segundo
        }
    
    @staticmethod
    def _calculate_user_metrics(logs):
        """Calcula métricas de usuarios"""
        # Agrupar por usuario
        user_activity = defaultdict(list)
        for log in logs:
            if log.get('user_fingerprint'):
                user_activity[log['user_fingerprint']].append(log)
        
        # Calcular sesiones por usuario
        sessions_per_user = []
        for user_logs in user_activity.values():
            # Agrupar por sesión (requests con < 30 min de diferencia)
            sessions = 1
            user_logs.sort(key=lambda x: x['timestamp'])
            
            for i in range(1, len(user_logs)):
                time_diff = (datetime.fromisoformat(user_logs[i]['timestamp']) - 
                           datetime.fromisoformat(user_logs[i-1]['timestamp']))
                if time_diff.seconds > 1800:  # 30 minutos
                    sessions += 1
            
            sessions_per_user.append(sessions)
        
        # Navegadores y SO más comunes
        browsers = Counter(l.get('browser') for l in logs if l.get('browser'))
        os_systems = Counter(l.get('os') for l in logs if l.get('os'))
        
        return {
            'total_unique_users': len(user_activity),
            'avg_sessions_per_user': round(sum(sessions_per_user) / len(sessions_per_user), 2) if sessions_per_user else 0,
            'returning_users': sum(1 for s in sessions_per_user if s > 1),
            'top_browsers': dict(browsers.most_common(5)),
            'top_os': dict(os_systems.most_common(5))
        }
    
    @staticmethod
    def _calculate_content_metrics(logs):
        """Calcula métricas de contenido"""
        # Filtrar solo eventos de visualización de contratos
        contract_views = [l for l in logs if l.get('event') == 'contract_view']
        
        # Instituciones más consultadas
        instituciones = Counter(l.get('institucion') for l in contract_views if l.get('institucion'))
        
        # Tipos de procedimiento más vistos
        tipos = Counter(l.get('tipo_procedimiento') for l in contract_views if l.get('tipo_procedimiento'))
        
        return {
            'total_contract_views': len(contract_views),
            'unique_contracts_viewed': len(set(l.get('contract_id') for l in contract_views)),
            'top_instituciones': dict(instituciones.most_common(10)),
            'top_tipos_procedimiento': dict(tipos.most_common(5))
        }
    
    @staticmethod
    def generate_report(days=7, output_format='json'):
        """Genera reporte de métricas"""
        metrics = PlatformMetrics.get_usage_metrics(days)
        
        if output_format == 'json':
            return json.dumps(metrics, indent=2, ensure_ascii=False)
        elif output_format == 'html':
            return PlatformMetrics._generate_html_report(metrics)
        else:
            return metrics
