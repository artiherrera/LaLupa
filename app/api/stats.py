# app/api/stats.py

from flask import Blueprint, jsonify
from app.services.aggregation_service import AggregationService
import logging

stats_bp = Blueprint('stats', __name__)
logger = logging.getLogger(__name__)

@stats_bp.route('/stats', methods=['GET'])
def get_stats():
    """Obtiene estadísticas generales de la base de datos"""
    try:
        aggregation_service = AggregationService()
        stats = aggregation_service.get_stats()
        return jsonify(stats)
        
    except Exception as e:
        logger.error(f"Error obteniendo estadísticas: {str(e)}")
        return jsonify({'error': 'Error al obtener estadísticas'}), 500