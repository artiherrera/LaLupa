# app/services/filter_service.py

"""Servicio de filtros - Optimizado sin subqueries"""
from sqlalchemy import func
from app import db
import logging

logger = logging.getLogger(__name__)

class FilterService:
    """Servicio para manejar filtros"""

    def obtener_filtros_disponibles(self, base_query):
        """
        Obtiene los valores únicos para filtros usando with_entities().
        Esto permite a PostgreSQL optimizar la query completa y usar índices.
        """
        try:
            from app.models import Contrato
            filtros = {}

            # Top 10 instituciones más frecuentes - usando with_entities()
            inst_query = base_query.with_entities(
                Contrato.siglas_institucion,
                func.count(Contrato.codigo_contrato).label('count')
            ).filter(
                Contrato.siglas_institucion.isnot(None)
            ).group_by(
                Contrato.siglas_institucion
            ).order_by(
                func.count(Contrato.codigo_contrato).desc()
            ).limit(10)

            filtros['instituciones'] = {
                i.siglas_institucion: i.count for i in inst_query
            }

            # Top 10 tipos de contratación
            tipos_query = base_query.with_entities(
                Contrato.tipo_contratacion,
                func.count(Contrato.codigo_contrato).label('count')
            ).filter(
                Contrato.tipo_contratacion.isnot(None)
            ).group_by(
                Contrato.tipo_contratacion
            ).order_by(
                func.count(Contrato.codigo_contrato).desc()
            ).limit(10)

            filtros['tipos'] = {
                t.tipo_contratacion: t.count for t in tipos_query
            }

            # Top 10 tipos de procedimiento
            proc_query = base_query.with_entities(
                Contrato.tipo_procedimiento,
                func.count(Contrato.codigo_contrato).label('count')
            ).filter(
                Contrato.tipo_procedimiento.isnot(None)
            ).group_by(
                Contrato.tipo_procedimiento
            ).order_by(
                func.count(Contrato.codigo_contrato).desc()
            ).limit(10)

            filtros['procedimientos'] = {
                p.tipo_procedimiento: p.count for p in proc_query
            }

            # Top 10 años
            anios_query = base_query.with_entities(
                Contrato.anio_fuente,
                func.count(Contrato.codigo_contrato).label('count')
            ).filter(
                Contrato.anio_fuente.isnot(None)
            ).group_by(
                Contrato.anio_fuente
            ).order_by(
                Contrato.anio_fuente.desc()
            ).limit(10)

            filtros['anios'] = {
                str(a.anio_fuente): a.count for a in anios_query
            }

            # Top 5 estatus
            estatus_query = base_query.with_entities(
                Contrato.estatus_contrato,
                func.count(Contrato.codigo_contrato).label('count')
            ).filter(
                Contrato.estatus_contrato.isnot(None)
            ).group_by(
                Contrato.estatus_contrato
            ).order_by(
                func.count(Contrato.codigo_contrato).desc()
            ).limit(5)

            filtros['estatus'] = {
                e.estatus_contrato: e.count for e in estatus_query
            }

            return filtros

        except Exception as e:
            logger.error(f"Error obteniendo filtros: {str(e)}")
            return {}