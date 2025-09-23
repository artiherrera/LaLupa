# app/services/search_service.py

"""Servicio de búsqueda de contratos"""
import re
from sqlalchemy import or_

class SearchService:
    """Servicio para búsquedas de contratos"""
    
    def validate_search_input(self, query_text, search_type):
        """Valida y sanitiza la entrada de búsqueda"""
        query_text = query_text.strip()
        
        if len(query_text) > 200:
            raise ValueError('Término de búsqueda demasiado largo')
        
        # Remover caracteres peligrosos pero mantener acentos
        query_text = re.sub(r'[^\w\s\-.,áéíóúñÁÉÍÓÚÑ]', '', query_text)
        
        # Validar tipo de búsqueda
        valid_types = ['descripcion', 'titulo', 'empresa', 'rfc', 'institucion', 'todo']
        if search_type not in valid_types:
            search_type = 'todo'
        
        # Validación especial para RFC
        if search_type == 'rfc':
            rfc_pattern = r'^[A-ZÑ&]{3,4}\d{6}[A-Z0-9]{3}$'
            if not re.match(rfc_pattern, query_text.upper()):
                raise ValueError('Formato de RFC inválido')
        
        return query_text, search_type
    
    def build_search_query(self, query_text, search_type):
        """Construye la consulta según el tipo de búsqueda"""
        # Importar aquí para evitar import circular
        from app.models import Contrato
        
        query = Contrato.query
        
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