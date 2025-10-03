# app/routes.py
from flask import Blueprint, render_template, request, jsonify
from app import db
from sqlalchemy import func, text

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    """Página principal"""
    return render_template('index.html')

@main_bp.route('/api/filters', methods=['GET'])
def get_filters():
    """
    Obtener opciones disponibles para filtros
    """
    try:
        from app.models.contrato import Contrato
        
        # Obtener instituciones únicas con conteo
        instituciones = db.session.query(
            Contrato.siglas_institucion,
            Contrato.institucion,
            func.count(Contrato.codigo_contrato).label('total')
        ).filter(
            Contrato.siglas_institucion != None
        ).group_by(
            Contrato.siglas_institucion,
            Contrato.institucion
        ).having(
            func.count(Contrato.codigo_contrato) > 10
        ).order_by(
            text('total DESC')
        ).limit(100).all()
        
        # Años disponibles
        anios = db.session.query(
            Contrato.anio_fuente
        ).distinct().filter(
            Contrato.anio_fuente != None
        ).order_by(
            Contrato.anio_fuente.desc()
        ).all()
        
        # Tipos de contratación
        tipos_contratacion = db.session.query(
            Contrato.tipo_contratacion
        ).distinct().filter(
            Contrato.tipo_contratacion != None
        ).all()
        
        # Tipos de procedimiento
        tipos_procedimiento = db.session.query(
            Contrato.tipo_procedimiento
        ).distinct().filter(
            Contrato.tipo_procedimiento != None
        ).all()
        
        return jsonify({
            'instituciones': [
                {
                    'siglas': inst[0],
                    'nombre': inst[1] or inst[0],
                    'total': inst[2]
                }
                for inst in instituciones
            ],
            'anios': [a[0] for a in anios if a[0]],
            'tipos_contratacion': [t[0] for t in tipos_contratacion if t[0]],
            'tipos_procedimiento': [t[0] for t in tipos_procedimiento if t[0]]
        })
        
    except Exception as e:
        print(f"Error obteniendo filtros: {str(e)}")
        return jsonify({'error': 'Error al obtener filtros'}), 500

@main_bp.route('/api/stats', methods=['GET'])
def api_stats():
    """
    Estadísticas generales de la plataforma
    """
    try:
        from app.models.contrato import Contrato
        
        stats = {
            'total_contratos': db.session.query(func.count(Contrato.codigo_contrato)).scalar() or 0,
            'total_importe': float(db.session.query(func.sum(Contrato.importe)).scalar() or 0),
            'proveedores_unicos': db.session.query(func.count(func.distinct(Contrato.proveedor_contratista))).scalar() or 0,
            'instituciones_unicas': db.session.query(func.count(func.distinct(Contrato.siglas_institucion))).scalar() or 0
        }
        
        return jsonify(stats)
        
    except Exception as e:
        print(f"Error en stats: {str(e)}")
        return jsonify({'error': 'Error al obtener estadísticas'}), 500

@main_bp.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({'status': 'healthy'}), 200