# app/services/search_service.py

"""Servicio de búsqueda de contratos"""
import re
import unicodedata
from sqlalchemy import or_, and_, not_, func, String
from app.utils.query_parser import parse_search_query

class SearchService:
    """Servicio para búsquedas de contratos"""

    @staticmethod
    def _remove_accents(text):
        """
        Remueve acentos y diéresis de un texto para búsquedas insensibles a acentos.
        Ejemplo: 'José' -> 'Jose', 'Müller' -> 'Muller'
        """
        if not text:
            return text
        # Normalizar a NFD (descompone caracteres acentuados)
        nfd = unicodedata.normalize('NFD', text)
        # Filtrar solo caracteres que no sean marcas diacríticas
        return ''.join(char for char in nfd if unicodedata.category(char) != 'Mn')

    @staticmethod
    def _unaccent_compare(column, search_term):
        """
        Crea una comparación insensible a acentos usando translate de PostgreSQL.

        translate(string, from, to) reemplaza cada caracter de 'from' con el
        caracter correspondiente en 'to'.

        Ejemplo: translate('José García', 'áéíóúÁÉÍÓÚñÑüÜ', 'aeiouAEIOUnNuU')
                 -> 'Jose Garcia'
        """
        # Normalizar el término de búsqueda removiendo acentos
        normalized_term = SearchService._remove_accents(search_term)

        # Usar translate de PostgreSQL para normalizar la columna
        # translate(column, from_chars, to_chars)
        return func.translate(
            column,
            'áéíóúÁÉÍÓÚàèìòùÀÈÌÒÙâêîôûÂÊÎÔÛãõÃÕñÑüÜ',
            'aeiouAEIOUaeiouAEIOUaeiouAEIOUaoAOnNuU'
        ).ilike(f'%{normalized_term}%')

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
        Construye query simple (sin operadores)
        Si hay múltiples palabras, busca que TODAS estén presentes (AND implícito)
        Búsqueda insensible a acentos y diéresis
        """
        # Dividir el query_text en palabras individuales
        terms = query_text.split()

        if search_type == 'descripcion':
            # Buscar que todas las palabras estén en descripción
            for term in terms:
                query = query.filter(
                    self._unaccent_compare(Contrato.descripcion_contrato, term)
                )
        elif search_type == 'titulo':
            # Buscar que todas las palabras estén en título o expediente
            for term in terms:
                query = query.filter(or_(
                    self._unaccent_compare(Contrato.titulo_contrato, term),
                    self._unaccent_compare(Contrato.titulo_expediente, term)
                ))
        elif search_type == 'empresa':
            # Buscar que todas las palabras estén en el proveedor
            for term in terms:
                query = query.filter(
                    self._unaccent_compare(Contrato.proveedor_contratista, term)
                )
        elif search_type == 'rfc':
            query = query.filter(Contrato.rfc == query_text.upper())
        elif search_type == 'institucion':
            # Buscar que todas las palabras estén en institución o siglas
            for term in terms:
                query = query.filter(or_(
                    self._unaccent_compare(Contrato.institucion, term),
                    self._unaccent_compare(Contrato.siglas_institucion, term)
                ))
        else:  # todo
            # Buscar que todas las palabras estén en cualquier campo
            for term in terms:
                query = query.filter(or_(
                    self._unaccent_compare(Contrato.descripcion_contrato, term),
                    self._unaccent_compare(Contrato.titulo_contrato, term),
                    self._unaccent_compare(Contrato.titulo_expediente, term),
                    self._unaccent_compare(Contrato.proveedor_contratista, term),
                    self._unaccent_compare(Contrato.rfc, term),
                    self._unaccent_compare(Contrato.institucion, term),
                    self._unaccent_compare(Contrato.siglas_institucion, term)
                ))

        return query

    def _build_advanced_query(self, query, parsed, search_type, Contrato):
        """Construye query con operadores avanzados (insensible a acentos)"""
        conditions = []

        # Obtener las columnas según el tipo de búsqueda
        columns = self._get_search_columns(search_type, Contrato)

        # 1. Frases exactas (AND entre todas las frases)
        for phrase in parsed['exact_phrases']:
            phrase_conditions = [self._unaccent_compare(col, phrase) for col in columns]
            conditions.append(or_(*phrase_conditions))

        # 2. Términos de inclusión (AND entre todos)
        for term in parsed['include_terms']:
            term_conditions = [self._unaccent_compare(col, term) for col in columns]
            conditions.append(or_(*term_conditions))

        # 3. Grupos OR
        for or_group in parsed['or_groups']:
            or_conditions = []
            for term in or_group:
                term_conditions = [self._unaccent_compare(col, term) for col in columns]
                or_conditions.extend(term_conditions)
            if or_conditions:
                conditions.append(or_(*or_conditions))

        # 4. Términos de exclusión (NOT)
        for term in parsed['exclude_terms']:
            exclude_conditions = []
            for col in columns:
                # Negar la comparación insensible a acentos
                exclude_conditions.append(~self._unaccent_compare(col, term))
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