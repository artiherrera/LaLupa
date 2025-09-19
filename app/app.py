# app.py
# Aplicación principal de LaLupa

from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import or_, func, desc, text
import os
from dotenv import load_dotenv
from decimal import Decimal
import re

# Cargar variables de entorno
load_dotenv()

# Crear aplicación Flask
app = Flask(__name__)

# Configuración
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-key-lalupa')
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_size': 10,
    'pool_recycle': 3600,
    'pool_pre_ping': True
}

# Inicializar base de datos
db = SQLAlchemy(app)

# ===========================
# MODELO DE BASE DE DATOS
# ===========================

class Contrato(db.Model):
    __tablename__ = 'contratos'
    __table_args__ = {'schema': 'contratos'}
    
    # Campos principales (usando los nombres reales de la BD)
    codigo_contrato = db.Column(db.String, primary_key=True)
    codigo_expediente = db.Column(db.String, primary_key=True)
    clave_uc = db.Column(db.String)
    
    # Información del contrato
    descripcion_contrato = db.Column(db.Text)
    titulo_contrato = db.Column(db.Text)
    titulo_expediente = db.Column(db.Text)
    tipo_contratacion = db.Column(db.String)
    tipo_procedimiento = db.Column(db.String)
    
    # Información del proveedor
    proveedor_contratista = db.Column(db.String)
    rfc = db.Column(db.String)
    anio_fundacion_empresa = db.Column(db.Integer)
    
    # Información de la institución
    institucion = db.Column(db.String)
    siglas_institucion = db.Column(db.String)
    nombre_uc = db.Column(db.String)
    
    # Montos
    importe = db.Column(db.Numeric)
    importe_contrato = db.Column(db.String)
    moneda = db.Column(db.String)
    
    # Fechas
    fecha_inicio_contrato = db.Column(db.DateTime)
    fecha_fin_contrato = db.Column(db.DateTime)
    fecha_publicacion = db.Column(db.DateTime)
    fecha_firma_contrato = db.Column(db.DateTime)
    
    # Estado y otros
    estatus_contrato = db.Column(db.String)
    direccion_anuncio = db.Column(db.String)
    anio_fuente = db.Column(db.Integer)
    estratificacion = db.Column(db.String)
    forma_participacion = db.Column(db.String)
    
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
    """API de búsqueda principal con validación de seguridad"""
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
        
        # Construir la consulta según el tipo
        query = build_search_query(query_text, search_type)
        
        # Aplicar filtros si existen
        if filters:
            query = apply_filters(query, filters)
        
        # Limitar resultados para mejorar performance
        contratos = query.limit(1000).all()
        
        if not contratos:
            return jsonify({
                'query': query_text,
                'search_type': search_type,
                'total': 0,
                'monto_total': 0,
                'empresas': [],
                'instituciones': [],
                'contratos': [],
                'filtros_disponibles': {}
            })
        
        # Procesar y agrupar resultados
        resultado = procesar_resultados(contratos, query_text, search_type)
        
        return jsonify(resultado)
        
    except Exception as e:
        app.logger.error(f"Error en búsqueda: {str(e)}")
        return jsonify({'error': 'Error al procesar la búsqueda'}), 500

@app.route('/api/empresa/<rfc>')
def get_empresa(rfc):
    """Obtiene todos los contratos de una empresa"""
    try:
        contratos = Contrato.query.filter_by(rfc=rfc).all()
        
        if not contratos:
            return jsonify({'error': 'No se encontraron contratos para este RFC'}), 404
        
        # Ordenar por importe
        contratos_ordenados = sorted(
            contratos,
            key=lambda x: x.get_importe_numerico(),
            reverse=True
        )
        
        monto_total = sum(c.get_importe_numerico() for c in contratos)
        
        # Agrupar por institución
        instituciones_dict = {}
        for c in contratos:
            if c.siglas_institucion:
                if c.siglas_institucion not in instituciones_dict:
                    instituciones_dict[c.siglas_institucion] = {
                        'nombre': c.institucion,
                        'monto': 0,
                        'cantidad': 0
                    }
                instituciones_dict[c.siglas_institucion]['monto'] += c.get_importe_numerico()
                instituciones_dict[c.siglas_institucion]['cantidad'] += 1
        
        return jsonify({
            'empresa': contratos[0].proveedor_contratista,
            'rfc': rfc,
            'total_contratos': len(contratos),
            'monto_total': monto_total,
            'instituciones_clientes': instituciones_dict,
            'contratos': [c.to_dict() for c in contratos_ordenados[:100]]
        })
        
    except Exception as e:
        app.logger.error(f"Error obteniendo empresa {rfc}: {str(e)}")
        return jsonify({'error': 'Error al obtener datos de la empresa'}), 500

@app.route('/api/institucion/<siglas>')
def get_institucion(siglas):
    """Obtiene todos los contratos de una institución"""
    try:
        contratos = Contrato.query.filter_by(siglas_institucion=siglas).all()
        
        if not contratos:
            return jsonify({'error': 'No se encontraron contratos para esta institución'}), 404
        
        # Ordenar por importe
        contratos_ordenados = sorted(
            contratos,
            key=lambda x: x.get_importe_numerico(),
            reverse=True
        )
        
        monto_total = sum(c.get_importe_numerico() for c in contratos)
        
        # Agrupar por empresa
        empresas_dict = {}
        for c in contratos:
            if c.rfc and c.rfc != 'XAXX010101000':  # Excluir RFC genérico
                if c.rfc not in empresas_dict:
                    empresas_dict[c.rfc] = {
                        'nombre': c.proveedor_contratista,
                        'monto': 0,
                        'cantidad': 0
                    }
                empresas_dict[c.rfc]['monto'] += c.get_importe_numerico()
                empresas_dict[c.rfc]['cantidad'] += 1
        
        return jsonify({
            'institucion': contratos[0].institucion,
            'siglas': siglas,
            'total_contratos': len(contratos),
            'monto_total': monto_total,
            'proveedores': empresas_dict,
            'contratos': [c.to_dict() for c in contratos_ordenados[:100]]
        })
        
    except Exception as e:
        app.logger.error(f"Error obteniendo institución {siglas}: {str(e)}")
        return jsonify({'error': 'Error al obtener datos de la institución'}), 500

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
# FUNCIONES AUXILIARES
# ===========================

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

# FIX TEMPORAL para app.py - Mejorar la agrupación por proveedor
# Reemplazar en la función procesar_resultados

def procesar_resultados(contratos, query_text, search_type):
    """Procesa y agrupa los resultados de búsqueda"""
    # Diccionarios para agrupar
    proveedores_dict = {}
    instituciones_dict = {}
    
    # Primero, crear un mapeo de nombres a RFC real
    rfc_mapping = {}
    for contrato in contratos:
        if contrato.proveedor_contratista and contrato.rfc and contrato.rfc != 'XAXX010101000':
            rfc_mapping[contrato.proveedor_contratista] = contrato.rfc
    
    # Procesar cada contrato
    for contrato in contratos:
        importe = contrato.get_importe_numerico()
        
        # Determinar la clave para agrupar proveedores
        if contrato.proveedor_contratista:
            # Si conocemos el RFC real de este proveedor, usarlo
            if contrato.proveedor_contratista in rfc_mapping:
                proveedor_key = rfc_mapping[contrato.proveedor_contratista]
                rfc_display = rfc_mapping[contrato.proveedor_contratista]
            # Si tiene un RFC no genérico, usarlo
            elif contrato.rfc and contrato.rfc != 'XAXX010101000':
                proveedor_key = contrato.rfc
                rfc_display = contrato.rfc
            # Si solo tiene RFC genérico, usar el nombre
            else:
                proveedor_key = f"nombre_{contrato.proveedor_contratista}"
                rfc_display = 'RFC Genérico'
            
            if proveedor_key not in proveedores_dict:
                proveedores_dict[proveedor_key] = {
                    'nombre': contrato.proveedor_contratista,
                    'rfc': rfc_display,
                    'monto_total': 0,
                    'num_contratos': 0
                }
            proveedores_dict[proveedor_key]['monto_total'] += importe
            proveedores_dict[proveedor_key]['num_contratos'] += 1
        
        # Agrupar por institución (sin cambios)
        if contrato.siglas_institucion:
            if contrato.siglas_institucion not in instituciones_dict:
                instituciones_dict[contrato.siglas_institucion] = {
                    'nombre': contrato.institucion,
                    'siglas': contrato.siglas_institucion,
                    'monto_total': 0,
                    'num_contratos': 0
                }
            instituciones_dict[contrato.siglas_institucion]['monto_total'] += importe
            instituciones_dict[contrato.siglas_institucion]['num_contratos'] += 1
    
    # Convertir a listas y ordenar por monto
    proveedores = sorted(
        proveedores_dict.values(),
        key=lambda x: x['monto_total'],
        reverse=True
    )[:20]
    
    instituciones = sorted(
        instituciones_dict.values(),
        key=lambda x: x['monto_total'],
        reverse=True
    )[:20]
    
    # Ordenar contratos por monto
    contratos_ordenados = sorted(
        contratos,
        key=lambda x: x.get_importe_numerico(),
        reverse=True
    )[:100]
    
    # Calcular totales correctamente
    monto_total = sum(c.get_importe_numerico() for c in contratos)
    
    # Extraer filtros disponibles
    filtros_disponibles = extraer_filtros(contratos)
    
    return {
        'query': query_text,
        'search_type': search_type,
        'total': len(contratos),
        'monto_total': monto_total,
        'proveedores': proveedores,
        'instituciones': instituciones,
        'contratos': [c.to_dict() for c in contratos_ordenados],
        'filtros_disponibles': filtros_disponibles,
        'tiene_mas': len(contratos) > 100
    }

def extraer_filtros(contratos):
    """Extrae los valores únicos para los filtros desde los resultados"""
    filtros = {
        'instituciones': {},
        'tipos': {},
        'procedimientos': {},
        'anios': {},
        'estatus': {}
    }
    
    for contrato in contratos:
        # Instituciones
        if contrato.siglas_institucion:
            key = contrato.siglas_institucion
            filtros['instituciones'][key] = filtros['instituciones'].get(key, 0) + 1
        
        # Tipos de contratación
        if contrato.tipo_contratacion:
            filtros['tipos'][contrato.tipo_contratacion] = filtros['tipos'].get(contrato.tipo_contratacion, 0) + 1
        
        # Tipos de procedimiento
        if contrato.tipo_procedimiento:
            filtros['procedimientos'][contrato.tipo_procedimiento] = filtros['procedimientos'].get(contrato.tipo_procedimiento, 0) + 1
        
        # Años
        if contrato.anio_fuente:
            filtros['anios'][str(contrato.anio_fuente)] = filtros['anios'].get(str(contrato.anio_fuente), 0) + 1
        
        # Estados
        if contrato.estatus_contrato:
            filtros['estatus'][contrato.estatus_contrato] = filtros['estatus'].get(contrato.estatus_contrato, 0) + 1
    
    # Ordenar cada categoría por cantidad y limitar a top 10
    for categoria in filtros:
        filtros[categoria] = dict(sorted(
            filtros[categoria].items(),
            key=lambda x: x[1],
            reverse=True
        )[:10])
    
    return filtros

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
            
        except Exception as e:
            print(f"❌ Error de conexión a la BD: {e}")
            exit(1)
    
    # Ejecutar aplicación
    app.run(debug=True, host='0.0.0.0', port=5000)