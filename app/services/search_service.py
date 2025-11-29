# app/services/search_service.py

"""Servicio de búsqueda de contratos - Optimizado con Full Text Search"""
import re
from sqlalchemy import or_, and_, func, String
from app.utils.query_parser import parse_search_query

class SearchService:
    """Servicio para búsquedas de contratos usando Full Text Search de PostgreSQL"""

    @staticmethod
    def _fts_match(column, search_term):
        """
        Búsqueda usando Full Text Search de PostgreSQL.
        Usa los índices GIN existentes para búsquedas rápidas.
        El diccionario 'spanish' maneja acentos automáticamente.
        """
        return func.to_tsvector('spanish', func.coalesce(column, '')).op('@@')(
            func.plainto_tsquery('spanish', search_term)
        )

    @staticmethod
    def _fts_match_columns(columns, search_term):
        """
        Búsqueda FTS en múltiples columnas concatenadas.
        """
        if len(columns) == 1:
            return SearchService._fts_match(columns[0], search_term)

        # Concatenar columnas con espacios
        concatenated = func.coalesce(columns[0], '')
        for col in columns[1:]:
            concatenated = concatenated.op('||')(' ').op('||')(func.coalesce(col, ''))

        return func.to_tsvector('spanish', concatenated).op('@@')(
            func.plainto_tsquery('spanish', search_term)
        )

    def validate_search_input(self, query_text, search_type):
        """Valida y sanitiza la entrada de búsqueda (ahora con soporte de operadores)"""
        query_text = query_text.strip()

        if len(query_text) > 2000:  # Permitir búsquedas muy largas con múltiples términos
            raise ValueError('Término de búsqueda demasiado largo (máximo 2000 caracteres)')

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
        """
        Construye query simple usando Full Text Search de PostgreSQL.
        Usa índices GIN para búsquedas rápidas en millones de registros.
        """
        # Obtener columnas según tipo de búsqueda
        columns = self._get_search_columns(search_type, Contrato)

        if search_type == 'rfc':
            # RFC usa búsqueda exacta
            query = query.filter(Contrato.rfc == query_text.upper())
        else:
            # FTS busca todas las palabras automáticamente (AND implícito)
            query = query.filter(self._fts_match_columns(columns, query_text))

        return query

    def _build_advanced_query(self, query, parsed, search_type, Contrato):
        """Construye query con operadores avanzados usando Full Text Search"""
        conditions = []

        # Obtener las columnas según el tipo de búsqueda
        columns = self._get_search_columns(search_type, Contrato)

        # 1. Frases exactas (AND entre todas las frases)
        for phrase in parsed['exact_phrases']:
            # Para frases exactas, usar phraseto_tsquery
            conditions.append(self._fts_phrase_match(columns, phrase))

        # 2. Términos de inclusión (AND entre todos)
        for term in parsed['include_terms']:
            conditions.append(self._fts_match_columns(columns, term))

        # 3. Grupos OR
        for or_group in parsed['or_groups']:
            or_conditions = []
            for term in or_group:
                or_conditions.append(self._fts_match_columns(columns, term))
            if or_conditions:
                conditions.append(or_(*or_conditions))

        # 4. Términos de exclusión (NOT)
        for term in parsed['exclude_terms']:
            # Negar la búsqueda FTS
            conditions.append(~self._fts_match_columns(columns, term))

        # Aplicar todas las condiciones con AND
        if conditions:
            query = query.filter(and_(*conditions))

        return query

    @staticmethod
    def _fts_phrase_match(columns, phrase):
        """Búsqueda de frase exacta usando phraseto_tsquery"""
        if len(columns) == 1:
            return func.to_tsvector('spanish', func.coalesce(columns[0], '')).op('@@')(
                func.phraseto_tsquery('spanish', phrase)
            )

        # Concatenar columnas
        concatenated = func.coalesce(columns[0], '')
        for col in columns[1:]:
            concatenated = concatenated.op('||')(' ').op('||')(func.coalesce(col, ''))

        return func.to_tsvector('spanish', concatenated).op('@@')(
            func.phraseto_tsquery('spanish', phrase)
        )

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
                Contrato.rfc,
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
            # anio_fuente puede ser VARCHAR o INTEGER dependiendo de la BD
            # Manejar ambos casos: comparar como string
            query = query.filter(
                Contrato.anio_fuente.cast(String).in_(
                    [str(a) for a in filters['anios']]
                )
            )
    
        
        if filters.get('estatus'):  # Singular
            query = query.filter(
                Contrato.estatus_contrato.in_(filters['estatus'])
            )
        
        return query