# app/routes.py
from flask import Blueprint, render_template, request, jsonify
from app import db
from sqlalchemy import func, text
from datetime import datetime, timedelta
import threading

main_bp = Blueprint('main', __name__)

# Caché en memoria para estadísticas
_stats_cache = {
    'data': None,
    'last_updated': None,
    'lock': threading.Lock()
}

# Tiempo de vida del caché (1 hora = 3600 segundos)
CACHE_TTL_SECONDS = 3600

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

def _calculate_stats():
    """
    Función privada para calcular estadísticas de la base de datos
    """
    from app.models.contrato import Contrato

    # Obtener última actualización (fecha más reciente de inicio de contrato)
    ultima_actualizacion = db.session.query(
        func.max(Contrato.fecha_inicio_contrato)
    ).scalar()

    # Formatear fecha para mostrar
    fecha_formateada = None
    if ultima_actualizacion:
        fecha_formateada = ultima_actualizacion.strftime('%d/%m/%Y')

    # Obtener año más reciente (solo valores numéricos)
    # anio_fuente es VARCHAR, filtrar usando regex para solo años de 4 dígitos
    from sqlalchemy import text
    ultimo_anio = db.session.query(
        func.max(
            func.cast(Contrato.anio_fuente, db.Integer)
        )
    ).filter(
        Contrato.anio_fuente.op('~')(r'^\d{4}$')
    ).scalar()

    stats = {
        'total_contratos': db.session.query(func.count(Contrato.codigo_contrato)).scalar() or 0,
        'total_importe': float(db.session.query(func.sum(Contrato.importe)).scalar() or 0),
        'proveedores_unicos': db.session.query(func.count(func.distinct(Contrato.proveedor_contratista))).scalar() or 0,
        'instituciones_unicas': db.session.query(func.count(func.distinct(Contrato.siglas_institucion))).scalar() or 0,
        'ultima_actualizacion': fecha_formateada or 'Sin datos',
        'ultimo_anio': ultimo_anio
    }

    return stats


@main_bp.route('/api/stats', methods=['GET'])
def api_stats():
    """
    Estadísticas generales de la plataforma (con caché de 1 hora)
    """
    try:
        now = datetime.now()

        # Verificar si el caché es válido
        with _stats_cache['lock']:
            if (_stats_cache['data'] is not None and
                _stats_cache['last_updated'] is not None and
                (now - _stats_cache['last_updated']).total_seconds() < CACHE_TTL_SECONDS):
                # Retornar datos del caché
                return jsonify(_stats_cache['data'])

            # Caché expirado o vacío - calcular nuevas estadísticas
            print(f"[STATS] Calculando estadísticas (caché expirado o vacío)...")
            stats = _calculate_stats()

            # Actualizar caché
            _stats_cache['data'] = stats
            _stats_cache['last_updated'] = now
            print(f"[STATS] Caché actualizado a las {now.strftime('%Y-%m-%d %H:%M:%S')}")

        return jsonify(stats)

    except Exception as e:
        print(f"Error en stats: {str(e)}")
        return jsonify({'error': 'Error al obtener estadísticas'}), 500

@main_bp.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({'status': 'healthy'}), 200