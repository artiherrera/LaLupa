# app/api/search.py (versión con manejo de errores mejorado)

from flask import Blueprint, request, jsonify
from flask_login import current_user
from app.models import Contrato, HistorialBusqueda
from app.services.search_service import SearchService
from app.services.aggregation_service import AggregationService
from app.services.filter_service import FilterService
from app import db
from sqlalchemy import func, case, and_
import logging
import time

search_bp = Blueprint('search', __name__)
logger = logging.getLogger(__name__)


def guardar_historial_busqueda(query_text, search_type, filters, total, monto_total, tiempo):
    """Guarda la busqueda en el historial del usuario si esta autenticado"""
    try:
        if current_user.is_authenticated:
            historial = HistorialBusqueda(
                usuario_id=current_user.id,
                termino_busqueda=query_text,
                tipo_busqueda=search_type,
                filtros=filters if filters else None,
                resultados_count=total,
                monto_total=monto_total,
                tiempo_busqueda=tiempo
            )
            db.session.add(historial)
            db.session.commit()
    except Exception as e:
        logger.error(f"Error guardando historial de busqueda: {str(e)}")
        try:
            db.session.rollback()
        except:
            pass

@search_bp.route('/search', methods=['POST'])
def search():
    """Búsqueda con paginación - retorna agregados COMPLETOS y contratos paginados con ordenamiento"""
    try:
        start_time = time.time()
        data = request.get_json()

        # Validar entrada
        search_service = SearchService()
        query_text, search_type = search_service.validate_search_input(
            data.get('query', ''),
            data.get('search_type', 'todo')
        )

        # Obtener campos de búsqueda (nuevo multi-select)
        search_fields = data.get('search_fields', None)

        filters = data.get('filters', {})

        # Limpiar sesión antes de cualquier query
        try:
            db.session.expire_all()
        except:
            pass

        # Obtener parámetros de paginación y ordenamiento
        page = data.get('page', 1)
        per_page = data.get('per_page', 50)
        sort_order = data.get('sort', 'monto_desc')

        if not query_text:
            return jsonify({'error': 'Por favor ingresa un término de búsqueda'}), 400

        # Construir la consulta base (con soporte para multi-select)
        base_query = search_service.build_search_query(query_text, search_type, search_fields)

        # Aplicar filtros
        if filters:
            base_query = search_service.apply_filters(base_query, filters)

        logger.info(f"Búsqueda: {query_text}, campos: {search_fields or search_type}, filtros: {filters}, página: {page}, orden: {sort_order}")

        # 1. Obtener agregados COMPLETOS de TODOS los resultados
        # IMPORTANTE: with_entities() modifica la query, así que necesitamos reconstruirla después
        aggregation_service = AggregationService()
        try:
            agregados = aggregation_service.obtener_agregados_optimizado(base_query)
            logger.debug(f"Agregados obtenidos: total={agregados['total_contratos']}")
        except Exception as agg_error:
            logger.error(f"Error en agregados: {str(agg_error)}")
            try:
                db.session.rollback()
            except:
                pass
            # Si falla agregados, retornar valores por defecto
            agregados = {
                'total_contratos': 0,
                'monto_total': 0,
                'top_proveedores': [],
                'top_instituciones': [],
                'contratos_por_anio': []
            }

        # Limpiar estado de la sesión antes de ejecutar nuevas queries
        try:
            db.session.expire_all()
        except:
            pass

        # IMPORTANTE: Reconstruir la query base porque with_entities() la modificó
        base_query = search_service.build_search_query(query_text, search_type, search_fields)
        if filters:
            base_query = search_service.apply_filters(base_query, filters)


        # 2. Aplicar ordenamiento según el parámetro
        if sort_order == 'monto_desc':
            base_query = base_query.order_by(Contrato.importe.desc().nullslast())
        elif sort_order == 'monto_asc':
            base_query = base_query.order_by(Contrato.importe.asc().nullsfirst())
        elif sort_order == 'fecha_desc':
            base_query = base_query.order_by(Contrato.fecha_inicio_contrato.desc().nullslast())
        elif sort_order == 'fecha_asc':
            base_query = base_query.order_by(Contrato.fecha_inicio_contrato.asc().nullsfirst())
        # 'relevancia' no tiene ordenamiento específico (orden natural de la query)

        # 3. Aplicar paginación
        offset = (page - 1) * per_page
        try:
            # Verificar conteo antes de paginar
            contratos_count = base_query.count()

            # IMPORTANTE: Comparar con el total de agregación para detectar discrepancias
            if contratos_count != agregados['total_contratos']:
                logger.warning(
                    f"DISCREPANCIA DETECTADA: Agregación reporta {agregados['total_contratos']} "
                    f"pero query reconstruida tiene {contratos_count} contratos. "
                    f"Query: {query_text}, search_type: {search_type}, search_fields: {search_fields}"
                )

            contratos = base_query.offset(offset).limit(per_page).all()
            logger.info(f"Contratos retornados (página {page}): {len(contratos)} de {contratos_count} total")

            # Detectar discrepancia entre count y fetch
            if len(contratos) != min(per_page, contratos_count - offset):
                expected = min(per_page, contratos_count - offset)
                logger.warning(
                    f"DISCREPANCIA EN FETCH: count={contratos_count}, offset={offset}, "
                    f"esperados={expected}, obtenidos={len(contratos)}"
                )
                # Obtener IDs para debugging
                try:
                    ids_query = search_service.build_search_query(query_text, search_type, search_fields)
                    if filters:
                        ids_query = search_service.apply_filters(ids_query, filters)
                    all_ids = [c.codigo_contrato for c in ids_query.with_entities(Contrato.codigo_contrato).all()]
                    fetched_ids = [c.codigo_contrato for c in contratos]
                    missing_ids = set(all_ids) - set(fetched_ids)
                    # Detectar duplicados
                    unique_ids = len(set(all_ids))
                    if unique_ids != len(all_ids):
                        from collections import Counter
                        id_counts = Counter(all_ids)
                        duplicates = {k: v for k, v in id_counts.items() if v > 1}
                        logger.warning(f"DUPLICADOS DETECTADOS: {len(all_ids)} IDs pero solo {unique_ids} únicos. Duplicados: {duplicates}")
                    logger.warning(f"IDs en query: {len(all_ids)}, IDs únicos: {unique_ids}, IDs obtenidos: {len(fetched_ids)}, Faltantes: {missing_ids}")
                except Exception as debug_error:
                    logger.error(f"Error en debug de IDs: {str(debug_error)}")
        except Exception as query_error:
            logger.error(f"Error en query de contratos: {str(query_error)}")
            try:
                db.session.rollback()
            except:
                pass
            try:
                db.session.remove()
            except:
                pass
            raise  # Re-lanzar para que sea capturado por el except principal

        # 4. Obtener filtros disponibles
        # Reconstruir query base sin ordenamiento ni paginación para los filtros
        filter_query = search_service.build_search_query(query_text, search_type, search_fields)
        if filters:
            filter_query = search_service.apply_filters(filter_query, filters)

        filter_service = FilterService()
        try:
            filtros_disponibles = filter_service.obtener_filtros_disponibles(filter_query)
        except Exception as filter_error:
            logger.error(f"Error obteniendo filtros: {str(filter_error)}")
            try:
                db.session.rollback()
            except:
                pass
            filtros_disponibles = {}

        elapsed_time = time.time() - start_time
        logger.info(f"Búsqueda completada en {elapsed_time:.2f} segundos")

        resultado = {
            'query': query_text,
            'search_type': search_type,
            'total': agregados['total_contratos'],
            'monto_total': agregados['monto_total'],
            'proveedores': agregados['top_proveedores'],
            'instituciones': agregados['top_instituciones'],
            'contratos_por_anio': agregados.get('contratos_por_anio', []),
            'contratos': [c.to_dict() for c in contratos],
            'filtros_disponibles': filtros_disponibles,
            'page': page,
            'has_more': (page * per_page) < agregados['total_contratos'],
            'tiempo_busqueda': f"{elapsed_time:.2f}s"
        }

        # Guardar en historial si el usuario esta autenticado (solo pagina 1)
        if page == 1:
            guardar_historial_busqueda(
                query_text=query_text,
                search_type=search_type,
                filters=filters,
                total=agregados['total_contratos'],
                monto_total=agregados['monto_total'],
                tiempo=elapsed_time
            )

        return jsonify(resultado)

    except ValueError as ve:
        logger.error(f"Error de validación: {str(ve)}")
        db.session.rollback()
        return jsonify({'error': str(ve)}), 400
    except Exception as e:
        logger.error(f"Error en búsqueda: {str(e)}", exc_info=True)
        db.session.rollback()
        return jsonify({'error': 'Error al procesar la búsqueda'}), 500
    finally:
        # Asegurarse de que la sesión esté limpia
        try:
            db.session.remove()
        except:
            pass

@search_bp.route('/aggregates', methods=['POST'])
def get_aggregates_only():
    """Obtiene solo los agregados de TODOS los resultados"""
    try:
        data = request.get_json()

        search_service = SearchService()
        query_text, search_type = search_service.validate_search_input(
            data.get('query', ''),
            data.get('search_type', 'todo')
        )

        filters = data.get('filters', {})

        if not query_text:
            return jsonify({'error': 'Query requerido'}), 400

        base_query = search_service.build_search_query(query_text, search_type)

        if filters:
            base_query = search_service.apply_filters(base_query, filters)

        # Obtener agregados completos
        aggregation_service = AggregationService()
        agregados = aggregation_service.obtener_agregados_optimizado(base_query)

        return jsonify(agregados)

    except Exception as e:
        logger.error(f"Error obteniendo agregados: {str(e)}", exc_info=True)
        db.session.rollback()
        return jsonify({'error': 'Error al obtener agregados'}), 500
    finally:
        try:
            db.session.remove()
        except:
            pass

@search_bp.route('/all-providers', methods=['POST'])
def get_all_providers():
    """Obtiene TODOS los proveedores de los resultados de búsqueda (sin límite)"""
    try:
        data = request.get_json()

        search_service = SearchService()
        query_text, search_type = search_service.validate_search_input(
            data.get('query', ''),
            data.get('search_type', 'todo')
        )

        filters = data.get('filters', {})

        if not query_text:
            return jsonify({'error': 'Query requerido'}), 400

        base_query = search_service.build_search_query(query_text, search_type)

        if filters:
            base_query = search_service.apply_filters(base_query, filters)

        # Obtener TODOS los proveedores (sin límite) - usando with_entities()
        # IMPORTANTE: Agrupar por RFC cuando es válido para consolidar variaciones de nombre
        from app.models import Contrato

        rfc_group_key = case(
            (and_(
                Contrato.rfc.isnot(None),
                Contrato.rfc != 'XAXX010101000',
                Contrato.rfc != ''
            ), Contrato.rfc),
            else_=Contrato.proveedor_contratista
        )

        proveedores_query = base_query.with_entities(
            func.max(Contrato.proveedor_contratista).label('nombre'),
            func.max(Contrato.rfc).label('rfc'),
            func.count(Contrato.codigo_contrato).label('num_contratos'),
            func.sum(Contrato.importe).label('monto_total')
        ).filter(
            Contrato.proveedor_contratista.isnot(None)
        ).group_by(
            rfc_group_key  # Agrupa por RFC si es válido, sino por nombre
        ).order_by(
            func.sum(Contrato.importe).desc().nullslast()
        ).all()  # SIN LÍMITE

        proveedores = []
        for p in proveedores_query:
            proveedores.append({
                'nombre': p.nombre,
                'rfc': p.rfc if p.rfc and p.rfc != 'XAXX010101000' else 'RFC Genérico',
                'num_contratos': p.num_contratos,
                'monto_total': float(p.monto_total or 0)
            })

        return jsonify({'top_proveedores': proveedores})

    except Exception as e:
        logger.error(f"Error obteniendo todos los proveedores: {str(e)}", exc_info=True)
        db.session.rollback()
        return jsonify({'error': 'Error al obtener proveedores'}), 500
    finally:
        try:
            db.session.remove()
        except:
            pass

@search_bp.route('/all-institutions', methods=['POST'])
def get_all_institutions():
    """Obtiene TODAS las instituciones de los resultados de búsqueda (sin límite)"""
    try:
        data = request.get_json()

        search_service = SearchService()
        query_text, search_type = search_service.validate_search_input(
            data.get('query', ''),
            data.get('search_type', 'todo')
        )

        filters = data.get('filters', {})

        if not query_text:
            return jsonify({'error': 'Query requerido'}), 400

        base_query = search_service.build_search_query(query_text, search_type)

        if filters:
            base_query = search_service.apply_filters(base_query, filters)

        # Obtener TODAS las instituciones (sin límite) - usando with_entities()
        # IMPORTANTE: Agrupar SOLO por siglas para evitar duplicados
        from app.models import Contrato

        instituciones_query = base_query.with_entities(
            func.max(Contrato.institucion).label('nombre'),  # MAX obtiene el nombre más completo
            Contrato.siglas_institucion.label('siglas'),
            func.count(Contrato.codigo_contrato).label('num_contratos'),
            func.sum(Contrato.importe).label('monto_total')
        ).filter(
            Contrato.siglas_institucion.isnot(None)
        ).group_by(
            Contrato.siglas_institucion  # Solo agrupar por siglas
        ).order_by(
            func.sum(Contrato.importe).desc().nullslast()
        ).all()  # SIN LÍMITE

        instituciones = []
        for i in instituciones_query:
            instituciones.append({
                'nombre': i.nombre,
                'siglas': i.siglas,
                'num_contratos': i.num_contratos,
                'monto_total': float(i.monto_total or 0)
            })

        return jsonify({'top_instituciones': instituciones})

    except Exception as e:
        logger.error(f"Error obteniendo todas las instituciones: {str(e)}", exc_info=True)
        db.session.rollback()
        return jsonify({'error': 'Error al obtener instituciones'}), 500
    finally:
        try:
            db.session.remove()
        except:
            pass

@search_bp.route('/all-contracts', methods=['POST'])
def get_all_contracts():
    """Obtiene TODOS los contratos de los resultados de búsqueda (sin paginación, solo primeros 1000)"""
    try:
        data = request.get_json()

        search_service = SearchService()
        query_text, search_type = search_service.validate_search_input(
            data.get('query', ''),
            data.get('search_type', 'todo')
        )

        filters = data.get('filters', {})
        sort_order = data.get('sort', 'monto_desc')

        if not query_text:
            return jsonify({'error': 'Query requerido'}), 400

        base_query = search_service.build_search_query(query_text, search_type)

        if filters:
            base_query = search_service.apply_filters(base_query, filters)

        # Aplicar ordenamiento
        if sort_order == 'monto_desc':
            base_query = base_query.order_by(Contrato.importe.desc().nullslast())
        elif sort_order == 'monto_asc':
            base_query = base_query.order_by(Contrato.importe.asc().nullsfirst())
        elif sort_order == 'fecha_desc':
            base_query = base_query.order_by(Contrato.fecha_inicio.desc().nullslast())
        elif sort_order == 'fecha_asc':
            base_query = base_query.order_by(Contrato.fecha_inicio.asc().nullsfirst())

        # Limitar a 1000 contratos para evitar problemas de memoria
        contratos = base_query.limit(1000).all()

        return jsonify({
            'contratos': [c.to_dict() for c in contratos],
            'total_returned': len(contratos),
            'limited': len(contratos) == 1000
        })

    except Exception as e:
        logger.error(f"Error obteniendo todos los contratos: {str(e)}", exc_info=True)
        db.session.rollback()
        return jsonify({'error': 'Error al obtener contratos'}), 500
    finally:
        try:
            db.session.remove()
        except:
            pass