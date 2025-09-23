# app/services/filter_service.py

"""Servicio de filtros"""
from sqlalchemy import func
from app import db
import logging

logger = logging.getLogger(__name__)

class FilterService:
    """Servicio para manejar filtros"""
    
    def obtener_filtros_disponibles(self, base_query):
        """Obtiene los valores únicos para filtros usando consultas optimizadas"""
        try:
            from app.models import Contrato
            filtros = {}
            
            # Crear alias para la subquery
            subquery = base_query.subquery()
            
            # Top 10 instituciones más frecuentes
            inst_query = db.session.query(
                subquery.c.siglas_institucion,
                func.count('*').label('count')
            ).group_by(
                subquery.c.siglas_institucion
            ).filter(
                subquery.c.siglas_institucion.isnot(None)
            ).order_by(
                func.count('*').desc()
            ).limit(10)
            
            filtros['instituciones'] = {
                i.siglas_institucion: i.count for i in inst_query
            }
            
            # Top 10 tipos de contratación
            tipos_query = db.session.query(
                subquery.c.tipo_contratacion,
                func.count('*').label('count')
            ).group_by(
                subquery.c.tipo_contratacion
            ).filter(
                subquery.c.tipo_contratacion.isnot(None)
            ).order_by(
                func.count('*').desc()
            ).limit(10)
            
            filtros['tipos'] = {
                t.tipo_contratacion: t.count for t in tipos_query
            }
            
            # Top 10 tipos de procedimiento
            proc_query = db.session.query(
                subquery.c.tipo_procedimiento,
                func.count('*').label('count')
            ).group_by(
                subquery.c.tipo_procedimiento
            ).filter(
                subquery.c.tipo_procedimiento.isnot(None)
            ).order_by(
                func.count('*').desc()
            ).limit(10)
            
            filtros['procedimientos'] = {
                p.tipo_procedimiento: p.count for p in proc_query
            }
            
            # Top 10 años
            anios_query = db.session.query(
                subquery.c.anio_fuente,
                func.count('*').label('count')
            ).group_by(
                subquery.c.anio_fuente
            ).filter(
                subquery.c.anio_fuente.isnot(None)
            ).order_by(
                subquery.c.anio_fuente.desc()
            ).limit(10)
            
            filtros['anios'] = {
                str(a.anio_fuente): a.count for a in anios_query
            }
            
            # Top 5 estatus
            estatus_query = db.session.query(
                subquery.c.estatus_contrato,
                func.count('*').label('count')
            ).group_by(
                subquery.c.estatus_contrato
            ).filter(
                subquery.c.estatus_contrato.isnot(None)
            ).order_by(
                func.count('*').desc()
            ).limit(5)
            
            filtros['estatus'] = {
                e.estatus_contrato: e.count for e in estatus_query
            }
            
            return filtros
            
        except Exception as e:
            logger.error(f"Error obteniendo filtros: {str(e)}")
            return {}