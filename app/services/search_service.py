# app/services/search_service.py

"""Servicio de búsqueda de contratos - Optimizado con Full Text Search"""
import re
import unicodedata
from sqlalchemy import or_, and_, func, String
from app.utils.query_parser import parse_search_query


def normalize_accents(text):
    """
    Normaliza acentos para búsqueda insensible a acentos.
    Convierte: García -> Garcia, López -> Lopez, etc.
    """
    if not text:
        return text
    # NFD descompone caracteres acentuados (á -> a + ́)
    # Luego filtramos los caracteres de combinación (acentos)
    normalized = unicodedata.normalize('NFD', text)
    # Filtrar caracteres de combinación (categoría 'Mn' = Mark, Nonspacing)
    without_accents = ''.join(c for c in normalized if unicodedata.category(c) != 'Mn')
    return without_accents


def normalize_for_search(text):
    """
    Normaliza texto para búsqueda: quita acentos Y caracteres especiales.
    Convierte: "GARCIA. CHAVEZ" -> "GARCIA CHAVEZ"
    """
    if not text:
        return text
    # Primero quitar acentos
    text = normalize_accents(text)
    # Quitar caracteres especiales (puntos, comas, guiones, etc.)
    # Mantener solo letras, números y espacios
    text = re.sub(r'[^\w\s]', ' ', text)
    # Normalizar espacios múltiples a uno solo
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


class SearchService:
    """Servicio para búsquedas de contratos usando Full Text Search de PostgreSQL"""

    @staticmethod
    def _fts_match(column, search_term):
        """
        Búsqueda usando Full Text Search de PostgreSQL.
        Usa los índices GIN existentes para búsquedas rápidas.
        Normaliza acentos para búsqueda insensible.
        """
        # Normalizar el término de búsqueda (quitar acentos)
        normalized_term = normalize_accents(search_term)
        return func.to_tsvector('spanish', func.coalesce(column, '')).op('@@')(
            func.plainto_tsquery('spanish', normalized_term)
        )

    @staticmethod
    def _fts_match_columns(columns, search_term):
        """
        Búsqueda FTS en múltiples columnas usando OR.
        Cada columna usa su propio índice GIN para máxima velocidad.
        """
        if len(columns) == 1:
            return SearchService._fts_match(columns[0], search_term)

        # Usar OR entre columnas - cada una puede usar su índice GIN
        or_conditions = []
        for col in columns:
            or_conditions.append(SearchService._fts_match(col, search_term))

        return or_(*or_conditions)

    @staticmethod
    def _exact_phrase_match(column, phrase):
        """
        Búsqueda de frase EXACTA usando estrategia híbrida:
        1. FTS para filtrar rápidamente (usa índices GIN)
        2. ILIKE normalizado para precisión

        Insensible a mayúsculas/minúsculas, acentos y caracteres especiales.
        """
        # Normalizar la frase de búsqueda
        normalized_phrase = normalize_for_search(phrase)

        # Estrategia híbrida: FTS + ILIKE
        # 1. FTS rápido (usa índice GIN) - filtra candidatos
        fts_condition = func.to_tsvector('spanish', func.coalesce(column, '')).op('@@')(
            func.plainto_tsquery('spanish', normalized_phrase)
        )

        # 2. ILIKE con normalización - precisión en la frase exacta
        accent_from = 'áéíóúÁÉÍÓÚàèìòùÀÈÌÒÙäëïöüÄËÏÖÜâêîôûÂÊÎÔÛñÑ'
        accent_to = 'aeiouAEIOUaeiouAEIOUaeiouAEIOUaeiouAEIOUnN'

        normalized_column = func.translate(func.coalesce(column, ''), accent_from, accent_to)
        normalized_column = func.regexp_replace(normalized_column, '[^a-zA-Z0-9 ]', ' ', 'g')
        normalized_column = func.regexp_replace(normalized_column, ' +', ' ', 'g')

        ilike_condition = normalized_column.ilike(f'%{normalized_phrase}%')

        # Combinar: FTS AND ILIKE (FTS filtra rápido, ILIKE asegura frase exacta)
        return and_(fts_condition, ilike_condition)

    @staticmethod
    def _exact_phrase_match_columns(columns, phrase):
        """
        Búsqueda de frase exacta en múltiples columnas (OR entre columnas).
        """
        if len(columns) == 1:
            return SearchService._exact_phrase_match(columns[0], phrase)

        # Buscar en cualquiera de las columnas
        or_conditions = []
        for col in columns:
            or_conditions.append(SearchService._exact_phrase_match(col, phrase))

        return or_(*or_conditions)

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
    
    def build_search_query(self, query_text, search_type, search_fields=None):
        """
        Construye la consulta según el tipo de búsqueda.
        Ahora soporta operadores: "frase exacta", -excluir, OR, AND

        Args:
            query_text: Texto de búsqueda
            search_type: Tipo de búsqueda (backward compatible)
            search_fields: Lista de campos a buscar (nuevo multi-select)
        """
        from app.models import Contrato

        # Parsear la query para detectar operadores
        parsed = parse_search_query(query_text)

        query = Contrato.query

        # Construir condiciones según el tipo de búsqueda
        if parsed['has_operators']:
            # Query con operadores avanzados
            query = self._build_advanced_query(query, parsed, search_type, Contrato, search_fields)
        else:
            # Query simple (backward compatible)
            query = self._build_simple_query(query, query_text, search_type, Contrato, search_fields)

        return query

    def _build_simple_query(self, query, query_text, search_type, Contrato, search_fields=None):
        """
        Construye query simple usando Full Text Search de PostgreSQL.
        Usa índices GIN para búsquedas rápidas en millones de registros.
        """
        # Obtener columnas según tipo de búsqueda
        columns = self._get_search_columns(search_type, Contrato, search_fields)

        # RFC usa búsqueda exacta
        if search_type == 'rfc' or (search_fields and search_fields == ['rfc']):
            query = query.filter(Contrato.rfc == query_text.upper())
        else:
            # FTS busca todas las palabras automáticamente (AND implícito)
            query = query.filter(self._fts_match_columns(columns, query_text))

        return query

    def _build_advanced_query(self, query, parsed, search_type, Contrato, search_fields=None):
        """
        Construye query con operadores avanzados.
        - Frases exactas ("..."): ILIKE con unaccent para búsqueda exacta
        - Términos normales: FTS para búsqueda rápida
        - OR: Combina condiciones con OR
        - Exclusión (-): NOT en la condición
        """
        conditions = []

        # Obtener las columnas según el tipo de búsqueda
        columns = self._get_search_columns(search_type, Contrato, search_fields)

        # 1. Frases exactas (AND entre todas las frases)
        # Usa ILIKE con unaccent() para búsqueda exacta insensible a acentos
        for phrase in parsed['exact_phrases']:
            conditions.append(self._exact_phrase_match_columns(columns, phrase))

        # 2. Términos de inclusión (AND entre todos)
        # Usa FTS para búsqueda rápida
        for term in parsed['include_terms']:
            conditions.append(self._fts_match_columns(columns, term))

        # 3. Grupos OR - pueden contener frases exactas o términos normales
        for or_group in parsed['or_groups']:
            or_conditions = []
            for term in or_group:
                # Detectar si es una frase exacta (viene con comillas en el original)
                # El parser ya removió las comillas, pero podemos detectar espacios
                if ' ' in term:
                    # Frase con espacios = búsqueda exacta con ILIKE
                    or_conditions.append(self._exact_phrase_match_columns(columns, term))
                else:
                    # Término simple = FTS
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

    def _get_search_columns(self, search_type, Contrato, search_fields=None):
        """
        Retorna las columnas a buscar.

        Args:
            search_type: Tipo de búsqueda (backward compatible)
            Contrato: Modelo de contrato
            search_fields: Lista de campos a buscar (nuevo multi-select)
        """
        # Mapeo de campos a columnas
        field_mapping = {
            'descripcion': [Contrato.descripcion_contrato],
            'titulo': [Contrato.titulo_contrato, Contrato.titulo_expediente],
            'empresa': [Contrato.proveedor_contratista],
            'rfc': [Contrato.rfc],
            'institucion': [Contrato.institucion, Contrato.siglas_institucion]
        }

        # Si se proporcionan search_fields (nuevo multi-select)
        if search_fields and isinstance(search_fields, list):
            columns = []
            for field in search_fields:
                if field in field_mapping:
                    columns.extend(field_mapping[field])
            if columns:
                return columns

        # Backward compatible: usar search_type
        if search_type == 'descripcion':
            return field_mapping['descripcion']
        elif search_type == 'titulo':
            return field_mapping['titulo']
        elif search_type == 'empresa':
            return field_mapping['empresa']
        elif search_type == 'rfc':
            return field_mapping['rfc']
        elif search_type == 'institucion':
            return field_mapping['institucion']
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