# app/services/search_service.py

"""Servicio de búsqueda de contratos"""
import re
from sqlalchemy import or_, and_, not_
from app.utils.query_parser import parse_search_query

class SearchService:
    """Servicio para búsquedas de contratos"""

    def validate_search_input(self, query_text, search_type):
        """Valida y sanitiza la entrada de búsqueda (ahora con soporte de operadores)"""
        query_text = query_text.strip()

        if len(query_text) > 500:  # Aumentado para soportar queries complejas
            raise ValueError('Término de búsqueda demasiado largo')

        # Mantener operadores: comillas, -, OR, AND, paréntesis
        # Remover solo caracteres realmente peligrosos (SQL injection)
        # Permitir: letras, números, espacios, guiones, comillas, paréntesis, acentos
        query_text = re.sub(r'[^\w\s\-"()áéíóúñÁÉÍÓÚÑ]', '', query_text)

        # Validar tipo de búsqueda
        valid_types = ['descripcion', 'titulo', 'empresa', 'rfc', 'institucion', 'todo']
        if search_type not in valid_types:
            search_type = 'todo'

        # Validación especial para RFC (sin operadores)
        if search_type == 'rfc':
            # Remover operadores para RFC
            clean_query = query_text.replace('"', '').replace('-', '').replace('(', '').replace(')', '')
            rfc_pattern = r'^[A-ZÑ&]{3,4}\d{6}[A-Z0-9]{3}$'
            if not re.match(rfc_pattern, clean_query.upper()):
                raise ValueError('Formato de RFC inválido')
            query_text = clean_query

        return query_text, search_type
    
    def build_search_query(self, query_text, search_type):
        """
        Construye la consulta según el tipo de búsqueda.
        Ahora soporta operadores: "frase exacta", -excluir, OR, AND
        """
        from app.models import Contrato

        # Parsear la query para detectar operadores
        parsed = parse_search_query(query_text)

        query = Contrato.query

        # Construir condiciones según el tipo de búsqueda
        if parsed['has_operators']:
            # Query con operadores avanzados
            query = self._build_advanced_query(query, parsed, search_type, Contrato)
        else:
            # Query simple (backward compatible)
            query = self._build_simple_query(query, query_text, search_type, Contrato)

        return query

    def _build_simple_query(self, query, query_text, search_type, Contrato):
        """Construye query simple (sin operadores) - Backward compatible"""
        if search_type == 'descripcion':
            query = query.filter(
                Contrato.descripcion_contrato.ilike(f'%{query_text}%')
            )
        elif search_type == 'titulo':
            query = query.filter(or_(
                Contrato.titulo_contrato.ilike(f'%{query_text}%'),
                Contrato.titulo_expediente.ilike(f'%{query_text}%')
            ))
        elif search_type == 'empresa':
            query = query.filter(
                Contrato.proveedor_contratista.ilike(f'%{query_text}%')
            )
        elif search_type == 'rfc':
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

    def _build_advanced_query(self, query, parsed, search_type, Contrato):
        """Construye query con operadores avanzados"""
        conditions = []

        # Obtener las columnas según el tipo de búsqueda
        columns = self._get_search_columns(search_type, Contrato)

        # 1. Frases exactas (AND entre todas las frases)
        for phrase in parsed['exact_phrases']:
            phrase_conditions = [col.ilike(f'%{phrase}%') for col in columns]
            conditions.append(or_(*phrase_conditions))

        # 2. Términos de inclusión (AND entre todos)
        for term in parsed['include_terms']:
            term_conditions = [col.ilike(f'%{term}%') for col in columns]
            conditions.append(or_(*term_conditions))

        # 3. Grupos OR
        for or_group in parsed['or_groups']:
            or_conditions = []
            for term in or_group:
                term_conditions = [col.ilike(f'%{term}%') for col in columns]
                or_conditions.extend(term_conditions)
            if or_conditions:
                conditions.append(or_(*or_conditions))

        # 4. Términos de exclusión (NOT)
        for term in parsed['exclude_terms']:
            exclude_conditions = []
            for col in columns:
                # Usar ~ para negación o not_()
                exclude_conditions.append(~col.ilike(f'%{term}%'))
            # Aplicar AND a todas las columnas (debe NO estar en ninguna)
            conditions.append(and_(*exclude_conditions))

        # Aplicar todas las condiciones con AND
        if conditions:
            query = query.filter(and_(*conditions))

        return query

    def _get_search_columns(self, search_type, Contrato):
        """Retorna las columnas a buscar según el tipo"""
        if search_type == 'descripcion':
            return [Contrato.descripcion_contrato]
        elif search_type == 'titulo':
            return [Contrato.titulo_contrato, Contrato.titulo_expediente]
        elif search_type == 'empresa':
            return [Contrato.proveedor_contratista]
        elif search_type == 'rfc':
            return [Contrato.rfc]
        elif search_type == 'institucion':
            return [Contrato.institucion, Contrato.siglas_institucion]
        else:  # todo
            return [
                Contrato.descripcion_contrato,
                Contrato.titulo_contrato,
                Contrato.titulo_expediente,
                Contrato.proveedor_contratista,
                Contrato.institucion,
                Contrato.siglas_institucion
            ]
    
    def apply_filters(self, query, filters):
        """Aplica filtros adicionales a la consulta"""
        from app.models import Contrato
        
        if not filters:
            return query
        
        # Los nombres deben coincidir con lo que envía el frontend
        if filters.get('instituciones'):  # Plural
            query = query.filter(
                Contrato.siglas_institucion.in_(filters['instituciones'])
            )
        
        if filters.get('tipos'):  # Plural
            query = query.filter(
                Contrato.tipo_contratacion.in_(filters['tipos'])
            )
        
        if filters.get('procedimientos'):  # Plural
            query = query.filter(
                Contrato.tipo_procedimiento.in_(filters['procedimientos'])
            )
        if filters.get('anios'):  # Plural
            try:
                # Como anio_fuente es VARCHAR, convertir los años a strings
                anos_str = [str(a) for a in filters['anios']]
                query = query.filter(Contrato.anio_fuente.in_(anos_str))
            except (ValueError, TypeError):
                pass
    
        
        if filters.get('estatus'):  # Singular
            query = query.filter(
                Contrato.estatus_contrato.in_(filters['estatus'])
            )
        
        return query