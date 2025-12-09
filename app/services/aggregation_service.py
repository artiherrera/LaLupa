# app/services/aggregation_service.py

"""Servicio de agregación de datos - Optimizado sin subqueries"""
from sqlalchemy import func, case, and_
from app import db
import logging

logger = logging.getLogger(__name__)

class AggregationService:
    """Servicio para agregaciones y estadísticas"""

    def obtener_agregados_optimizado(self, base_query):
        """
        Obtiene agregados usando with_entities() en lugar de subquery().
        Esto permite a PostgreSQL optimizar la query completa y usar índices.
        """
        try:
            from app.models import Contrato

            # Total de contratos y monto total - usando with_entities()
            # Esto es MUCHO más eficiente que subquery() porque PostgreSQL
            # puede optimizar la query completa de una vez
            totales = base_query.with_entities(
                func.count(Contrato.codigo_contrato).label('total'),
                func.sum(Contrato.importe).label('monto_total')
            ).first()

            total_contratos = totales.total or 0
            monto_total = float(totales.monto_total or 0)
            logger.debug(f"[Agregación] Total contratos base: {total_contratos}")

            # Top 20 proveedores - query directa con GROUP BY
            # Agrupar por RFC cuando es válido para evitar duplicados por variaciones de nombre
            # Ej: "ASTRAZENECA SA DE CV" y "ASTRAZENECA" con mismo RFC se combinan
            rfc_group_key = case(
                (and_(
                    Contrato.rfc.isnot(None),
                    Contrato.rfc != 'XAXX010101000',
                    Contrato.rfc != ''
                ), Contrato.rfc),
                else_=Contrato.proveedor_contratista
            )

            proveedores_query = base_query.with_entities(
                func.max(Contrato.proveedor_contratista).label('nombre'),  # MAX obtiene el nombre más completo
                func.max(Contrato.rfc).label('rfc'),
                func.count(Contrato.codigo_contrato).label('num_contratos'),
                func.sum(Contrato.importe).label('monto_total')
            ).filter(
                Contrato.proveedor_contratista.isnot(None)
            ).group_by(
                rfc_group_key  # Agrupa por RFC si es válido, sino por nombre
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

            # Top 20 instituciones - query directa con GROUP BY
            instituciones_query = base_query.with_entities(
                Contrato.institucion.label('nombre'),
                Contrato.siglas_institucion.label('siglas'),
                func.count(Contrato.codigo_contrato).label('num_contratos'),
                func.sum(Contrato.importe).label('monto_total')
            ).filter(
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

            # Contratos por año - para gráfica temporal
            contratos_por_anio_query = base_query.with_entities(
                func.extract('year', Contrato.fecha_inicio_contrato).label('anio'),
                func.count(Contrato.codigo_contrato).label('num_contratos'),
                func.sum(Contrato.importe).label('monto_total')
            ).filter(
                Contrato.fecha_inicio_contrato.isnot(None)
            ).group_by(
                func.extract('year', Contrato.fecha_inicio_contrato)
            ).order_by(
                func.extract('year', Contrato.fecha_inicio_contrato)
            )

            contratos_por_anio = []
            for c in contratos_por_anio_query:
                if c.anio:
                    contratos_por_anio.append({
                        'anio': int(c.anio),
                        'num_contratos': c.num_contratos,
                        'monto_total': float(c.monto_total or 0)
                    })

            return {
                'total_contratos': total_contratos,
                'monto_total': monto_total,
                'top_proveedores': proveedores,
                'top_instituciones': instituciones,
                'contratos_por_anio': contratos_por_anio
            }

        except Exception as e:
            logger.error(f"Error en agregados: {str(e)}")
            try:
                db.session.rollback()
            except:
                pass
            return {
                'total_contratos': 0,
                'monto_total': 0,
                'top_proveedores': [],
                'top_instituciones': [],
                'contratos_por_anio': []
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