# utils/validators.py
import re
from typing import Optional

def sanitize_search_input(text: str, max_length: int = 200) -> Optional[str]:
    """
    Sanitiza la entrada de búsqueda
    """
    if not text:
        return None
    
    # Eliminar espacios al inicio y final
    text = text.strip()
    
    # Limitar longitud
    if len(text) > max_length:
        text = text[:max_length]
    
    # Remover caracteres peligrosos pero permitir búsquedas normales
    # Permitimos letras, números, espacios, guiones, puntos, comas, acentos
    text = re.sub(r'[^\w\s\-.,áéíóúñÁÉÍÓÚÑ]', '', text)
    
    # Evitar múltiples espacios
    text = ' '.join(text.split())
    
    return text if text else None

def validate_rfc(rfc: str) -> bool:
    """
    Valida formato de RFC mexicano
    """
    # RFC persona moral: 3 letras, 6 números, 3 caracteres
    # RFC persona física: 4 letras, 6 números, 3 caracteres
    pattern = r'^[A-ZÑ&]{3,4}\d{6}[A-Z0-9]{3}$'
    return bool(re.match(pattern, rfc.upper()))

def validate_year(year: str) -> Optional[int]:
    """
    Valida que el año esté en un rango razonable
    """
    try:
        year_int = int(year)
        # Rango razonable de años para contratos
        if 2000 <= year_int <= 2030:
            return year_int
    except (ValueError, TypeError):
        pass
    return None

def validate_search_type(search_type: str) -> str:
    """
    Valida que el tipo de búsqueda sea válido
    """
    valid_types = ['descripcion', 'titulo', 'empresa', 'rfc', 'institucion', 'todo']
    return search_type if search_type in valid_types else 'todo'