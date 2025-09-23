# app/api/contracts.py

from flask import Blueprint, request, jsonify
from app.models import Contrato
from app.services.search_service import SearchService
import logging

contracts_bp = Blueprint('contracts', __name__)
logger = logging.getLogger(__name__)

@contracts_bp.route('/contracts/page', methods=['POST'])
def get_contracts_page():
    """Obtiene una página específica de contratos (para scroll infinito)"""
    try:
        data = request.get_json()
        
        query_text = data.get('query', '').strip()
        search_type = data.get('search_type', 'todo')
        filters = data.get('filters', {})
        page = data.get('page', 1)
        per_page = min(data.get('per_page', 50), 100)  # Máximo 100 por página
        
        # Validación básica
        if not query_text:
            return jsonify({'error': 'Query requerido'}), 400
        
        if page < 1:
            page = 1
        
        # Usar el servicio para construir la consulta
        search_service = SearchService()
        query = search_service.build_search_query(query_text, search_type)
        
        # Aplicar filtros
        if filters:
            query = search_service.apply_filters(query, filters)
        
        # Calcular offset
        offset = (page - 1) * per_page
        
        # Obtener contratos paginados ordenados por importe
        contratos = query.order_by(
            Contrato.importe.desc().nullslast()
        ).offset(offset).limit(per_page).all()
        
        # Verificar si hay más páginas
        total_contratos = query.count()
        has_more = (offset + per_page) < total_contratos
        
        return jsonify({
            'contratos': [c.to_dict() for c in contratos],
            'page': page,
            'per_page': per_page,
            'has_more': has_more,
            'total': total_contratos
        })
        
    except Exception as e:
        logger.error(f"Error obteniendo página de contratos: {str(e)}")
        return jsonify({'error': 'Error al obtener contratos'}), 500