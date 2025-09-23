# app/api/search.py (versión con manejo de errores mejorado)

from flask import Blueprint, request, jsonify
from app.models import Contrato
from app.services.search_service import SearchService
from app.services.aggregation_service import AggregationService
from app.services.filter_service import FilterService
from app import db
from sqlalchemy import func
import logging
import time

search_bp = Blueprint('search', __name__)
logger = logging.getLogger(__name__)

@search_bp.route('/search', methods=['POST'])
def search():
    """Búsqueda inicial - retorna agregados COMPLETOS y primeros 50 contratos"""
    try:
        start_time = time.time()
        data = request.get_json()
        
        # Validar entrada
        search_service = SearchService()
        query_text, search_type = search_service.validate_search_input(
            data.get('query', ''),
            data.get('search_type', 'todo')
        )
        
        filters = data.get('filters', {})
        
        if not query_text:
            return jsonify({'error': 'Por favor ingresa un término de búsqueda'}), 400
        
        # Construir la consulta base
        base_query = search_service.build_search_query(query_text, search_type)
        
        # Aplicar filtros
        if filters:
            base_query = search_service.apply_filters(base_query, filters)
        
        logger.info(f"Búsqueda: {query_text}, tipo: {search_type}, filtros: {filters}")
        
        # 1. Obtener agregados COMPLETOS de TODOS los resultados
        aggregation_service = AggregationService()
        agregados = aggregation_service.obtener_agregados_optimizado(base_query)
        
        # 2. Obtener solo los primeros 50 contratos para mostrar
        contratos = base_query.order_by(
            Contrato.importe.desc().nullslast()
        ).limit(50).all()
        
        # 3. Obtener filtros disponibles
        filter_service = FilterService() 
        filtros_disponibles = filter_service.obtener_filtros_disponibles(base_query)
        
        elapsed_time = time.time() - start_time
        logger.info(f"Búsqueda completada en {elapsed_time:.2f} segundos")
        
        resultado = {
            'query': query_text,
            'search_type': search_type,
            'total': agregados['total_contratos'],
            'monto_total': agregados['monto_total'],
            'proveedores': agregados['top_proveedores'],
            'instituciones': agregados['top_instituciones'],
            'contratos': [c.to_dict() for c in contratos],
            'filtros_disponibles': filtros_disponibles,
            'page': 1,
            'has_more': agregados['total_contratos'] > 50,
            'tiempo_busqueda': f"{elapsed_time:.2f}s"
        }
        
        return jsonify(resultado)
        
    except ValueError as ve:
        db.session.rollback()  # Rollback en caso de error
        return jsonify({'error': str(ve)}), 400
    except Exception as e:
        db.session.rollback()  # Rollback en caso de error
        logger.error(f"Error en búsqueda: {str(e)}")
        return jsonify({'error': 'Error al procesar la búsqueda'}), 500
    finally:
        db.session.close()  # Siempre cerrar la sesión

@search_bp.route('/aggregates', methods=['POST'])
def get_aggregates_only():
    """Obtiene solo los agregados de TODOS los resultados"""
    try:
        data = request.get_json()
        
        search_service = SearchService()
        query_text, search_type = search_service.validate_search_input(
            data.get('query', ''),
            data.get('search_type', 'todo')
        )
        
        filters = data.get('filters', {})
        
        if not query_text:
            return jsonify({'error': 'Query requerido'}), 400
        
        base_query = search_service.build_search_query(query_text, search_type)
        
        if filters:
            base_query = search_service.apply_filters(base_query, filters)
        
        # Obtener agregados completos
        aggregation_service = AggregationService()
        agregados = aggregation_service.obtener_agregados_optimizado(base_query)
        
        return jsonify(agregados)
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error obteniendo agregados: {str(e)}")
        return jsonify({'error': 'Error al obtener agregados'}), 500
    finally:
        db.session.close()