# app/models/usuario.py
from app import db
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin

class Usuario(UserMixin, db.Model):
    """Modelo de Usuario"""
    __tablename__ = 'usuarios'
    __table_args__ = {'schema': 'contratos'}

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    nombre = db.Column(db.String(100), nullable=False)
    rol = db.Column(db.String(20), default='usuario')  # 'admin' o 'usuario'
    activo = db.Column(db.Boolean, default=True)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    ultimo_acceso = db.Column(db.DateTime)

    # Relaciones
    sesiones = db.relationship('SesionActiva', backref='usuario', lazy='dynamic', cascade='all, delete-orphan')
    historial_busquedas = db.relationship('HistorialBusqueda', backref='usuario', lazy='dynamic', cascade='all, delete-orphan')
    log_accesos = db.relationship('LogAcceso', backref='usuario', lazy='dynamic', cascade='all, delete-orphan')

    def set_password(self, password):
        """Hashea y guarda la contraseña"""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Verifica la contraseña"""
        return check_password_hash(self.password_hash, password)

    def es_admin(self):
        """Verifica si es administrador"""
        return self.rol == 'admin'

    def to_dict(self):
        """Convierte a diccionario"""
        return {
            'id': self.id,
            'email': self.email,
            'nombre': self.nombre,
            'rol': self.rol,
            'activo': self.activo,
            'fecha_creacion': self.fecha_creacion.isoformat() if self.fecha_creacion else None,
            'ultimo_acceso': self.ultimo_acceso.isoformat() if self.ultimo_acceso else None
        }

    def __repr__(self):
        return f'<Usuario {self.email}>'


class SesionActiva(db.Model):
    """Modelo para sesiones activas (para implementar sesion unica)"""
    __tablename__ = 'sesiones_activas'
    __table_args__ = {'schema': 'contratos'}

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('contratos.usuarios.id'), nullable=False, index=True)
    token_sesion = db.Column(db.String(256), unique=True, nullable=False, index=True)
    ip = db.Column(db.String(45))  # IPv6 puede tener hasta 45 caracteres
    user_agent = db.Column(db.String(500))
    fecha_inicio = db.Column(db.DateTime, default=datetime.utcnow)
    ultima_actividad = db.Column(db.DateTime, default=datetime.utcnow)

    def actualizar_actividad(self):
        """Actualiza el timestamp de ultima actividad"""
        self.ultima_actividad = datetime.utcnow()

    def to_dict(self):
        return {
            'id': self.id,
            'ip': self.ip,
            'user_agent': self.user_agent[:100] if self.user_agent else None,
            'fecha_inicio': self.fecha_inicio.isoformat() if self.fecha_inicio else None,
            'ultima_actividad': self.ultima_actividad.isoformat() if self.ultima_actividad else None
        }

    def __repr__(self):
        return f'<SesionActiva {self.usuario_id}>'


class HistorialBusqueda(db.Model):
    """Modelo para guardar historial de busquedas por usuario"""
    __tablename__ = 'historial_busquedas'
    __table_args__ = {'schema': 'contratos'}

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('contratos.usuarios.id'), nullable=False, index=True)
    query = db.Column(db.Text, nullable=False)
    tipo_busqueda = db.Column(db.String(50))
    filtros = db.Column(db.JSON)  # Guardar filtros como JSON
    resultados_count = db.Column(db.Integer)
    monto_total = db.Column(db.Numeric)
    tiempo_busqueda = db.Column(db.Float)  # En segundos
    fecha = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    def to_dict(self):
        return {
            'id': self.id,
            'query': self.query,
            'tipo_busqueda': self.tipo_busqueda,
            'filtros': self.filtros,
            'resultados_count': self.resultados_count,
            'monto_total': float(self.monto_total) if self.monto_total else 0,
            'tiempo_busqueda': self.tiempo_busqueda,
            'fecha': self.fecha.isoformat() if self.fecha else None
        }

    def __repr__(self):
        return f'<HistorialBusqueda {self.query[:30]}>'


class LogAcceso(db.Model):
    """Modelo para registrar accesos (login/logout)"""
    __tablename__ = 'log_accesos'
    __table_args__ = {'schema': 'contratos'}

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('contratos.usuarios.id'), nullable=False, index=True)
    ip = db.Column(db.String(45))
    user_agent = db.Column(db.String(500))
    fecha = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    tipo = db.Column(db.String(30))  # 'login', 'logout', 'sesion_expirada', 'expulsado', 'login_fallido'
    exitoso = db.Column(db.Boolean, default=True)
    detalles = db.Column(db.Text)  # Info adicional (ej: "Expulsado por nuevo login")

    def to_dict(self):
        return {
            'id': self.id,
            'ip': self.ip,
            'user_agent': self.user_agent[:100] if self.user_agent else None,
            'fecha': self.fecha.isoformat() if self.fecha else None,
            'tipo': self.tipo,
            'exitoso': self.exitoso,
            'detalles': self.detalles
        }

    def __repr__(self):
        return f'<LogAcceso {self.tipo} {self.fecha}>'
