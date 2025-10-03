# ===========================
# IMPORTS
# ===========================
import os
import re
from datetime import datetime
from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func, or_, text, and_
from sqlalchemy.orm import Query
import logging

# ===========================
# CONFIGURACIÓN
# ===========================
app = Flask(__name__)

# Configuración de la base de datos
DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'password')
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME', 'contratos_db')

app.config['SQLALCHEMY_DATABASE_URI'] = f'postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JSON_AS_ASCII'] = False

db = SQLAlchemy(app)

# Configurar logging
logging.basicConfig(level=logging.INFO)

# ===========================
# MODELOS
# ===========================
class Contrato(db.Model):
    __tablename__ = 'contratos'
    __table_args__ = {'schema': 'contratos'}
    
    codigo_contrato = db.Column(db.String, primary_key=True)
    codigo_expediente = db.Column(db.String)
    titulo_contrato = db.Column(db.Text)
    titulo_expediente = db.Column(db.Text)
    descripcion_contrato = db.Column(db.Text)
    tipo_contratacion = db.Column(db.String)
    tipo_procedimiento = db.Column(db.String)
    proveedor_contratista = db.Column(db.String)
    rfc = db.Column(db.String)
    institucion = db.Column(db.String)
    siglas_institucion = db.Column(db.String)
    importe = db.Column(db.Numeric)
    importe_contrato = db.Column(db.String)
    moneda = db.Column(db.String)
    fecha_inicio_contrato = db.Column(db.Date)
    fecha_fin_contrato = db.Column(db.Date)
    estatus_contrato = db.Column(db.String)
    direccion_anuncio = db.Column(db.Text)
    anio_fuente = db.Column(db.Integer)
    
    def get_importe_numerico(self):
        """Obtiene el importe como número flotante"""
        if self.importe:
            return float(self.importe)
        elif self.importe_contrato:
            try:
                # Limpiar string: quitar comas y espacios
                importe_str = str(self.importe_contrato).replace(',', '').strip()
                return float(importe_str)
            except:
                return 0.0
        return 0.0
    
    def to_dict(self):
        """Convierte el objeto a diccionario para JSON"""
        return {
            'codigo_contrato': self.codigo_contrato,
            'codigo_expediente': self.codigo_expediente,
            'titulo': self.titulo_contrato,
            'descripcion': self.descripcion_contrato,
            'tipo_contratacion': self.tipo_contratacion,
            'tipo_procedimiento': self.tipo_procedimiento,
            'proveedor': self.proveedor_contratista,
            'rfc': self.rfc,
            'institucion': self.institucion,
            'siglas_institucion': self.siglas_institucion,
            'importe': self.get_importe_numerico(),
            'moneda': self.moneda,
            'fecha_inicio': self.fecha_inicio_contrato.isoformat() if self.fecha_inicio_contrato else None,
            'fecha_fin': self.fecha_fin_contrato.isoformat() if self.fecha_fin_contrato else None,
            'estatus': self.estatus_contrato,
            'url_compranet': self.direccion_anuncio,
            'anio': self.anio_fuente
        }

# ===========================
# RUTAS PRINCIPALES
# ===========================
@app.route('/')
def index():
    """Página principal"""
    return render_template('index.html')

@app.route('/api/search', methods=['POST'])
def search():
    """Búsqueda inicial - retorna agregados y primeros contratos"""
    try:
        data = request.get_json()
        
        # Validar y sanitizar entrada
        query_text = data.get('query', '').strip()
        
        # Limitar longitud de búsqueda
        if len(query_text) > 200:
            return jsonify({'error': 'Término de búsqueda demasiado largo'}), 400
            
        # Remover caracteres potencialmente peligrosos pero mantener acentos y caracteres válidos
        query_text = re.sub(r'[^\w\s\-.,áéíóúñÁÉÍÓÚÑ]', '', query_text)
        
        # Validar tipo de búsqueda
        search_type = data.get('search_type', 'todo')
        valid_types = ['descripcion', 'titulo', 'empresa', 'rfc', 'institucion', 'todo']
        if search_type not in valid_types:
            search_type = 'todo'
        
        filters = data.get('filters', {})
        
        if not query_text:
            return jsonify({'error': 'Por favor ingresa un término de búsqueda'}), 400
        
        # Si es búsqueda por RFC, validar formato
        if search_type == 'rfc':
            rfc_pattern = r'^[A-ZÑ&]{3,4}\d{6}[A-Z0-9]{3}$'
            if not re.match(rfc_pattern, query_text.upper()):
                return jsonify({'error': 'Formato de RFC inválido'}), 400
        
        # Construir la consulta base según el tipo
        base_query = build_search_query(query_text, search_type)
        
        # Aplicar filtros si existen
        if filters:
            base_query = apply_filters(base_query, filters)
        
        # Guardar los parámetros de búsqueda en la sesión para paginación posterior
        app.logger.info(f"Búsqueda: {query_text}, tipo: {search_type}")
        
        # 1. Obtener agregados de forma eficiente
        agregados = obtener_agregados_optimizado(base_query)
        
        # 2. Obtener solo los primeros 50 contratos ordenados por importe
        contratos = base_query.order_by(Contrato.importe.desc().nullslast()).limit(50).all()
        
        # 3. Obtener filtros disponibles (solo de los resultados totales)
        filtros_disponibles = obtener_filtros_disponibles(base_query)
        
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
            'has_more': agregados['total_contratos'] > 50
        }
        
        return jsonify(resultado)
        
    except Exception as e:
        app.logger.error(f"Error en búsqueda: {str(e)}")
        return jsonify({'error': 'Error al procesar la búsqueda'}), 500

@app.route('/api/contracts/page', methods=['POST'])
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
            
        # Construir la consulta
        query = build_search_query(query_text, search_type)
        
        # Aplicar filtros
        if filters:
            query = apply_filters(query, filters)
        
        # Calcular offset
        offset = (page - 1) * per_page
        
        # Obtener contratos paginados ordenados por importe
        contratos = query.order_by(Contrato.importe.desc().nullslast()).offset(offset).limit(per_page).all()
        
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
        app.logger.error(f"Error obteniendo página de contratos: {str(e)}")
        return jsonify({'error': 'Error al obtener contratos'}), 500

@app.route('/api/aggregates', methods=['POST'])
def get_aggregates_only():
    """Obtiene solo los agregados (útil para actualización rápida)"""
    try:
        data = request.get_json()
        
        query_text = data.get('query', '').strip()
        search_type = data.get('search_type', 'todo')
        filters = data.get('filters', {})
        
        if not query_text:
            return jsonify({'error': 'Query requerido'}), 400
        
        # Construir consulta base
        base_query = build_search_query(query_text, search_type)
        
        # Aplicar filtros
        if filters:
            base_query = apply_filters(base_query, filters)
        
        # Obtener agregados optimizados
        agregados = obtener_agregados_optimizado(base_query)
        
        return jsonify(agregados)
        
    except Exception as e:
        app.logger.error(f"Error obteniendo agregados: {str(e)}")
        return jsonify({'error': 'Error al obtener agregados'}), 500

# ===========================
# FUNCIONES AUXILIARES OPTIMIZADAS
# ===========================

def obtener_agregados_optimizado(base_query):
    """
    Obtiene agregados usando consultas SQL optimizadas
    """
    try:
        # 1. Total de contratos y monto total en una sola consulta
        totales = db.session.query(
            func.count(Contrato.codigo_contrato).label('total'),
            func.sum(Contrato.importe).label('monto_total')
        ).select_from(base_query.subquery()).first()
        
        total_contratos = totales.total or 0
        monto_total = float(totales.monto_total or 0)
        
        # 2. Top 20 proveedores agrupados por RFC (optimizado con SQL)
        subquery = base_query.subquery()
        
        # Consulta para proveedores agrupados
        proveedores_query = db.session.query(
            Contrato.proveedor_contratista.label('nombre'),
            Contrato.rfc.label('rfc'),
            func.count(Contrato.codigo_contrato).label('num_contratos'),
            func.sum(Contrato.importe).label('monto_total')
        ).select_from(subquery).filter(
            Contrato.proveedor_contratista.isnot(None)
        ).group_by(
            Contrato.proveedor_contratista,
            Contrato.rfc
        ).order_by(
            func.sum(Contrato.importe).desc().nullslast()
        ).limit(20)
        
        proveedores = []
        for p in proveedores_query:
            proveedores.append({
                'nombre': p.nombre,
                'rfc': p.rfc if p.rfc and p.rfc != 'XAXX010101000' else 'RFC Genérico',
                'num_contratos': p.num_contratos,
                'monto_total': float(p.monto_total or 0)
            })
        
        # 3. Top 20 instituciones agrupadas
        instituciones_query = db.session.query(
            Contrato.institucion.label('nombre'),
            Contrato.siglas_institucion.label('siglas'),
            func.count(Contrato.codigo_contrato).label('num_contratos'),
            func.sum(Contrato.importe).label('monto_total')
        ).select_from(subquery).filter(
            Contrato.siglas_institucion.isnot(None)
        ).group_by(
            Contrato.institucion,
            Contrato.siglas_institucion
        ).order_by(
            func.sum(Contrato.importe).desc().nullslast()
        ).limit(20)
        
        instituciones = []
        for i in instituciones_query:
            instituciones.append({
                'nombre': i.nombre,
                'siglas': i.siglas,
                'num_contratos': i.num_contratos,
                'monto_total': float(i.monto_total or 0)
            })
        
        return {
            'total_contratos': total_contratos,
            'monto_total': monto_total,
            'top_proveedores': proveedores,
            'top_instituciones': instituciones
        }
        
    except Exception as e:
        app.logger.error(f"Error en agregados optimizados: {str(e)}")
        return {
            'total_contratos': 0,
            'monto_total': 0,
            'top_proveedores': [],
            'top_instituciones': []
        }

def obtener_filtros_disponibles(base_query):
    """
    Obtiene los valores únicos para filtros usando consultas optimizadas
    """
    try:
        filtros = {}
        
        # Usar subconsultas para mejorar performance
        subquery = base_query.subquery()
        
        # Top 10 instituciones más frecuentes
        inst_query = db.session.query(
            Contrato.siglas_institucion,
            func.count(Contrato.codigo_contrato).label('count')
        ).select_from(subquery).filter(
            Contrato.siglas_institucion.isnot(None)
        ).group_by(
            Contrato.siglas_institucion
        ).order_by(
            func.count(Contrato.codigo_contrato).desc()
        ).limit(10)
        
        filtros['instituciones'] = {i.siglas_institucion: i.count for i in inst_query}
        
        # Top 10 tipos de contratación
        tipos_query = db.session.query(
            Contrato.tipo_contratacion,
            func.count(Contrato.codigo_contrato).label('count')
        ).select_from(subquery).filter(
            Contrato.tipo_contratacion.isnot(None)
        ).group_by(
            Contrato.tipo_contratacion
        ).order_by(
            func.count(Contrato.codigo_contrato).desc()
        ).limit(10)
        
        filtros['tipos'] = {t.tipo_contratacion: t.count for t in tipos_query}
        
        # Top 10 tipos de procedimiento
        proc_query = db.session.query(
            Contrato.tipo_procedimiento,
            func.count(Contrato.codigo_contrato).label('count')
        ).select_from(subquery).filter(
            Contrato.tipo_procedimiento.isnot(None)
        ).group_by(
            Contrato.tipo_procedimiento
        ).order_by(
            func.count(Contrato.codigo_contrato).desc()
        ).limit(10)
        
        filtros['procedimientos'] = {p.tipo_procedimiento: p.count for p in proc_query}
        
        # Top 10 años
        anios_query = db.session.query(
            Contrato.anio_fuente,
            func.count(Contrato.codigo_contrato).label('count')
        ).select_from(subquery).filter(
            Contrato.anio_fuente.isnot(None)
        ).group_by(
            Contrato.anio_fuente
        ).order_by(
            Contrato.anio_fuente.desc()
        ).limit(10)
        
        filtros['anios'] = {str(a.anio_fuente): a.count for a in anios_query}
        
        # Top 5 estatus
        estatus_query = db.session.query(
            Contrato.estatus_contrato,
            func.count(Contrato.codigo_contrato).label('count')
        ).select_from(subquery).filter(
            Contrato.estatus_contrato.isnot(None)
        ).group_by(
            Contrato.estatus_contrato
        ).order_by(
            func.count(Contrato.codigo_contrato).desc()
        ).limit(5)
        
        filtros['estatus'] = {e.estatus_contrato: e.count for e in estatus_query}
        
        return filtros
        
    except Exception as e:
        app.logger.error(f"Error obteniendo filtros: {str(e)}")
        return {}

def build_search_query(query_text, search_type):
    """Construye la consulta de búsqueda según el tipo"""
    query = Contrato.query
    
    if search_type == 'descripcion':
        query = query.filter(Contrato.descripcion_contrato.ilike(f'%{query_text}%'))
        
    elif search_type == 'titulo':
        query = query.filter(or_(
            Contrato.titulo_contrato.ilike(f'%{query_text}%'),
            Contrato.titulo_expediente.ilike(f'%{query_text}%')
        ))
        
    elif search_type == 'empresa':
        query = query.filter(Contrato.proveedor_contratista.ilike(f'%{query_text}%'))
        
    elif search_type == 'rfc':
        # RFC debe ser exacto y en mayúsculas
        query = query.filter(Contrato.rfc == query_text.upper())
        
    elif search_type == 'institucion':
        query = query.filter(or_(
            Contrato.institucion.ilike(f'%{query_text}%'),
            Contrato.siglas_institucion.ilike(f'%{query_text}%')
        ))
        
    else:  # todo
        query = query.filter(or_(
            Contrato.descripcion_contrato.ilike(f'%{query_text}%'),
            Contrato.titulo_contrato.ilike(f'%{query_text}%'),
            Contrato.titulo_expediente.ilike(f'%{query_text}%'),
            Contrato.proveedor_contratista.ilike(f'%{query_text}%'),
            Contrato.institucion.ilike(f'%{query_text}%'),
            Contrato.siglas_institucion.ilike(f'%{query_text}%')
        ))
    
    return query

def apply_filters(query, filters):
    """Aplica filtros adicionales a la consulta"""
    if filters.get('institucion'):
        query = query.filter(Contrato.siglas_institucion.in_(filters['institucion']))
    
    if filters.get('tipo'):
        query = query.filter(Contrato.tipo_contratacion.in_(filters['tipo']))
    
    if filters.get('procedimiento'):
        query = query.filter(Contrato.tipo_procedimiento.in_(filters['procedimiento']))
    
    if filters.get('anio'):
        # Convertir años a enteros, manejando posibles errores
        try:
            anos = [int(a) for a in filters['anio']]
            query = query.filter(Contrato.anio_fuente.in_(anos))
        except ValueError:
            # Si hay un error de conversión, ignorar el filtro
            pass
    
    if filters.get('estatus'):
        query = query.filter(Contrato.estatus_contrato.in_(filters['estatus']))
    
    return query

@app.route('/api/stats')
def get_stats():
    """Obtiene estadísticas generales de la base de datos"""
    try:
        total_contratos = db.session.query(func.count(Contrato.codigo_contrato)).scalar()
        total_instituciones = db.session.query(func.count(func.distinct(Contrato.siglas_institucion))).scalar()
        total_empresas = db.session.query(func.count(func.distinct(Contrato.rfc))).scalar()
        
        return jsonify({
            'total_contratos': total_contratos,
            'total_instituciones': total_instituciones,
            'total_empresas': total_empresas
        })
        
    except Exception as e:
        app.logger.error(f"Error obteniendo estadísticas: {str(e)}")
        return jsonify({'error': 'Error al obtener estadísticas'}), 500

# ===========================
# INICIALIZACIÓN
# ===========================
if __name__ == '__main__':
    with app.app_context():
        # Verificar conexión a la base de datos
        try:
            from sqlalchemy import text
            db.session.execute(text('SELECT 1'))
            print("✅ Conexión a la base de datos exitosa")
            
            # Contar registros
            count = db.session.query(func.count(Contrato.codigo_contrato)).scalar()
            print(f"📊 Total de contratos en la BD: {count:,}")
            
            # Crear índices si no existen (importante para performance)
            indices_sql = """
            -- Índices para mejorar performance
            CREATE INDEX IF NOT EXISTS idx_contratos_importe 
                ON contratos.contratos(importe DESC NULLS LAST);
            
            CREATE INDEX IF NOT EXISTS idx_contratos_proveedor 
                ON contratos.contratos(proveedor_contratista);
            
            CREATE INDEX IF NOT EXISTS idx_contratos_rfc 
                ON contratos.contratos(rfc);
            
            CREATE INDEX IF NOT EXISTS idx_contratos_siglas_inst 
                ON contratos.contratos(siglas_institucion);
            
            CREATE INDEX IF NOT EXISTS idx_contratos_anio 
                ON contratos.contratos(anio_fuente);
            
            -- Índices para búsqueda de texto
            CREATE INDEX IF NOT EXISTS idx_contratos_titulo_contrato 
                ON contratos.contratos USING gin(to_tsvector('spanish', titulo_contrato));
            
            CREATE INDEX IF NOT EXISTS idx_contratos_descripcion 
                ON contratos.contratos USING gin(to_tsvector('spanish', descripcion_contrato));
            """
            
            try:
                db.session.execute(text(indices_sql))
                db.session.commit()
                print("✅ Índices verificados/creados")
            except Exception as e:
                print(f"⚠️ No se pudieron crear algunos índices: {e}")
                db.session.rollback()
            
        except Exception as e:
            print(f"❌ Error de conexión a la BD: {e}")
            exit(1)
    
    # Ejecutar aplicación
    app.run(debug=True, host='0.0.0.0', port=5000)