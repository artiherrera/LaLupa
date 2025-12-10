"""
Parser de queries tipo Google para búsquedas avanzadas.

Operadores soportados:
- "frase exacta": Busca la frase completa
- -excluir: Excluye términos
- AND: Ambos términos deben estar presentes (implícito por defecto)
- OR: Cualquiera de los términos
- ( ): Agrupar operaciones

Ejemplos:
- medicamentos "COVID-19" -vacunas
- (medicamentos OR equipos) AND IMSS
- "Secretaría de Salud" -2020
"""

import re
from typing import List, Dict, Any


class QueryParser:
    """Parser para queries de búsqueda con operadores tipo Google"""

    def __init__(self, query: str):
        self.original_query = query
        self.exact_phrases = []
        self.include_terms = []
        self.exclude_terms = []
        self.or_groups = []

    def parse(self) -> Dict[str, Any]:
        """
        Parsea la query y extrae todos los operadores.

        Returns:
            Dict con:
                - exact_phrases: List[str] - Frases exactas entre comillas
                - include_terms: List[str] - Términos que deben incluirse
                - exclude_terms: List[str] - Términos a excluir (con -)
                - or_groups: List[List[str]] - Grupos de términos con OR
                - simple_query: str - Query simplificada sin operadores
        """
        query = self.original_query.strip()

        if not query:
            return self._empty_result()

        # 1. Extraer frases exactas (entre comillas)
        query = self._extract_exact_phrases(query)

        # 2. Extraer términos a excluir (con -)
        query = self._extract_exclude_terms(query)

        # 3. Extraer grupos OR
        query = self._extract_or_groups(query)

        # 4. Lo que queda son términos de inclusión
        self._extract_include_terms(query)

        # 5. Generar query simplificada
        simple_query = self._build_simple_query()

        return {
            'exact_phrases': self.exact_phrases,
            'include_terms': self.include_terms,
            'exclude_terms': self.exclude_terms,
            'or_groups': self.or_groups,
            'simple_query': simple_query,
            'has_operators': self._has_operators()
        }

    def _extract_exact_phrases(self, query: str) -> str:
        """Extrae frases entre comillas"""
        # Regex para encontrar texto entre comillas dobles
        pattern = r'"([^"]+)"'
        matches = re.findall(pattern, query)

        for match in matches:
            self.exact_phrases.append(match.strip())

        # Remover las frases del query
        query = re.sub(pattern, '', query)
        return query

    def _extract_exclude_terms(self, query: str) -> str:
        """Extrae términos que empiezan con -"""
        # Regex para encontrar -palabra o " - palabra" (con espacio opcional antes)
        # Captura el término después del guión
        pattern = r'(?:^|\s)-\s*(\w+)'
        matches = re.findall(pattern, query)

        for match in matches:
            self.exclude_terms.append(match.strip())

        # Remover los términos excluidos del query (incluyendo espacio antes si existe)
        query = re.sub(r'(?:^|\s)-\s*\w+', ' ', query)
        return query

    def _extract_or_groups(self, query: str) -> str:
        """Extrae grupos con operador OR"""
        # Dividir por OR (case insensitive)
        parts = re.split(r'\s+OR\s+', query, flags=re.IGNORECASE)

        if len(parts) > 1:
            # Hay operador OR
            or_group = []
            for part in parts:
                # Limpiar y agregar al grupo
                term = part.strip()
                if term:
                    or_group.append(term)

            if or_group:
                self.or_groups.append(or_group)

            # Retornar vacío porque ya procesamos todo
            return ''

        return query

    def _extract_include_terms(self, query: str):
        """Extrae términos normales (sin operadores)"""
        # Remover AND explícito (es implícito)
        query = re.sub(r'\s+AND\s+', ' ', query, flags=re.IGNORECASE)

        # Dividir por espacios y limpiar
        terms = query.split()

        for term in terms:
            term = term.strip()
            if term and term not in ['AND', 'OR', 'and', 'or']:
                self.include_terms.append(term)

    def _build_simple_query(self) -> str:
        """Construye una query simplificada para búsqueda básica"""
        parts = []

        # Agregar frases exactas
        parts.extend(self.exact_phrases)

        # Agregar términos de inclusión
        parts.extend(self.include_terms)

        # Agregar primer elemento de grupos OR
        for or_group in self.or_groups:
            if or_group:
                parts.append(or_group[0])

        return ' '.join(parts)

    def _has_operators(self) -> bool:
        """Verifica si la query tiene operadores avanzados"""
        return bool(
            self.exact_phrases or
            self.exclude_terms or
            self.or_groups
        )

    def _empty_result(self) -> Dict[str, Any]:
        """Retorna resultado vacío"""
        return {
            'exact_phrases': [],
            'include_terms': [],
            'exclude_terms': [],
            'or_groups': [],
            'simple_query': '',
            'has_operators': False
        }

    def to_sql_conditions(self, column_name: str) -> List[str]:
        """
        Convierte el parsing a condiciones SQL para usar con SQLAlchemy.

        Args:
            column_name: Nombre de la columna a buscar

        Returns:
            Lista de condiciones SQL como strings
        """
        conditions = []

        # Frases exactas (ILIKE con frase completa)
        for phrase in self.exact_phrases:
            conditions.append(f"{column_name} ILIKE '%{phrase}%'")

        # Términos de inclusión (ILIKE)
        for term in self.include_terms:
            conditions.append(f"{column_name} ILIKE '%{term}%'")

        # Grupos OR
        for or_group in self.or_groups:
            or_conditions = [f"{column_name} ILIKE '%{term}%'" for term in or_group]
            if or_conditions:
                conditions.append(f"({' OR '.join(or_conditions)})")

        # Términos de exclusión (NOT ILIKE)
        for term in self.exclude_terms:
            conditions.append(f"{column_name} NOT ILIKE '%{term}%'")

        return conditions


def parse_search_query(query: str) -> Dict[str, Any]:
    """
    Función helper para parsear queries.

    Args:
        query: Query de búsqueda con operadores

    Returns:
        Dict con los componentes parseados
    """
    parser = QueryParser(query)
    return parser.parse()


# Ejemplos de uso
if __name__ == '__main__':
    # Test cases
    test_queries = [
        'medicamentos COVID',
        '"medicamentos COVID-19"',
        'medicamentos -vacunas',
        'medicamentos OR equipos',
        '(medicamentos OR equipos) -vacunas',
        '"Secretaría de Salud" IMSS -2020',
    ]

    for query in test_queries:
        print(f"\nQuery: {query}")
        result = parse_search_query(query)
        print(f"  Exact phrases: {result['exact_phrases']}")
        print(f"  Include: {result['include_terms']}")
        print(f"  Exclude: {result['exclude_terms']}")
        print(f"  OR groups: {result['or_groups']}")
        print(f"  Simple: {result['simple_query']}")
