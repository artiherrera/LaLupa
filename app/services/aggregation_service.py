# app/services/aggregation_service.py

"""Servicio de agregación de datos"""
from sqlalchemy import func
from app import db
import logging

logger = logging.getLogger(__name__)

class AggregationService:
    """Servicio para agregaciones y estadísticas"""
    
    def obtener_agregados_optimizado(self, base_query):
        """Obtiene agregados usando consultas SQL optimizadas"""
        try:
            from app.models import Contrato
            
            # Total de contratos y monto total
            subquery = base_query.subquery()
            totales = db.session.query(
                func.count('*').label('total'),
                func.sum(subquery.c.importe).label('monto_total')
            ).select_from(subquery).first()
            
            total_contratos = totales.total or 0
            monto_total = float(totales.monto_total or 0)
            
            # Top 20 proveedores
            proveedores_query = db.session.query(
                subquery.c.proveedor_contratista.label('nombre'),
                subquery.c.rfc.label('rfc'),
                func.count('*').label('num_contratos'),
                func.sum(subquery.c.importe).label('monto_total')
            ).filter(
                subquery.c.proveedor_contratista.isnot(None)
            ).group_by(
                subquery.c.proveedor_contratista,
                subquery.c.rfc
            ).order_by(
                func.sum(subquery.c.importe).desc().nullslast()
            ).limit(20)
            
            proveedores = []
            for p in proveedores_query:
                proveedores.append({
                    'nombre': p.nombre,
                    'rfc': p.rfc if p.rfc and p.rfc != 'XAXX010101000' else 'RFC Genérico',
                    'num_contratos': p.num_contratos,
                    'monto_total': float(p.monto_total or 0)
                })
            
            # Top 20 instituciones
            instituciones_query = db.session.query(
                subquery.c.institucion.label('nombre'),
                subquery.c.siglas_institucion.label('siglas'),
                func.count('*').label('num_contratos'),
                func.sum(subquery.c.importe).label('monto_total')
            ).filter(
                subquery.c.siglas_institucion.isnot(None)
            ).group_by(
                subquery.c.institucion,
                subquery.c.siglas_institucion
            ).order_by(
                func.sum(subquery.c.importe).desc().nullslast()
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
            logger.error(f"Error en agregados: {str(e)}")
            return {
                'total_contratos': 0,
                'monto_total': 0,
                'top_proveedores': [],
                'top_instituciones': []
            }
    
    def get_stats(self):
        """Obtiene estadísticas generales de la base de datos"""
        try:
            from app.models import Contrato
            
            total_contratos = db.session.query(
                func.count(Contrato.codigo_contrato)
            ).scalar()
            
            total_instituciones = db.session.query(
                func.count(func.distinct(Contrato.siglas_institucion))
            ).scalar()
            
            total_empresas = db.session.query(
                func.count(func.distinct(Contrato.rfc))
            ).scalar()
            
            return {
                'total_contratos': total_contratos,
                'total_instituciones': total_instituciones,
                'total_empresas': total_empresas
            }
        except Exception as e:
            logger.error(f"Error obteniendo estadísticas: {str(e)}")
            return {
                'total_contratos': 0,
                'total_instituciones': 0,
                'total_empresas': 0
            }