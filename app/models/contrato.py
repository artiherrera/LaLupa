# app/models/contrato.py

from app import db
from datetime import datetime

class Contrato(db.Model):
    """Modelo de Contrato"""
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
    
    def __repr__(self):
        return f'<Contrato {self.codigo_contrato}>'