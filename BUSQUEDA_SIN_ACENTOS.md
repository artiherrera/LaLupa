# Búsqueda Insensible a Acentos y Diéresis

## Descripción

El sistema de búsqueda ahora es completamente insensible a acentos, diéresis y otros signos diacríticos. Esto significa que puedes buscar con o sin acentos y obtendrás los mismos resultados.

## Ejemplos

### Búsqueda de nombres
- Buscar `"Jose"` encuentra: **"José"**, **"JOSE"**, **"jose"**
- Buscar `"Muller"` encuentra: **"Müller"**, **"MULLER"**, **"muller"**
- Buscar `"Arlin Medrano"` encuentra: **"ARLIN GABRIELA MEDRANO"**

### Búsqueda de instituciones
- Buscar `"Secretaria Salud"` encuentra: **"Secretaría de Salud"**
- Buscar `"Educacion Publica"` encuentra: **"Educación Pública"**

### Búsqueda de descripciones
- Buscar `"medicamentos pediatricos"` encuentra: **"medicamentos pediátricos"**
- Buscar `"construccion"` encuentra: **"construcción"**, **"reconstrucción"**

## Cómo funciona

### 1. Extensión PostgreSQL (Recomendado)

El sistema intenta usar la extensión `unaccent` de PostgreSQL para máximo rendimiento:

```sql
-- Esto se ejecuta en la base de datos
unaccent('José') = unaccent('Jose')  -- Ambos retornan 'Jose'
```

#### Instalación de la extensión

Para habilitar la extensión `unaccent` en PostgreSQL:

```bash
# Opción 1: Usar el script proporcionado
python3 scripts/enable_unaccent.py

# Opción 2: Ejecutar manualmente en PostgreSQL (requiere privilegios de superusuario)
CREATE EXTENSION IF NOT EXISTS unaccent;
```

**Nota:** Si tu usuario de base de datos no tiene privilegios de superusuario (como en DigitalOcean Managed Databases), necesitarás contactar al administrador o usar el fallback automático.

### 2. Fallback en Python (Automático)

Si la extensión `unaccent` no está disponible, el sistema automáticamente usa normalización Unicode en Python:

```python
# Normalización NFD (Canonical Decomposition)
'José' -> 'Jose'  # Remueve el acento agudo
'Müller' -> 'Muller'  # Remueve la diéresis
```

Este método es ligeramente más lento pero funciona en cualquier configuración.

## Aplicación

La búsqueda insensible a acentos aplica a:

✅ **Todos los tipos de búsqueda:**
- Búsqueda por descripción
- Búsqueda por título
- Búsqueda por empresa/proveedor
- Búsqueda por institución
- Búsqueda tipo "Todo"

✅ **Todos los modos de búsqueda:**
- Búsqueda simple (palabras sueltas)
- Búsqueda avanzada (con operadores OR, -, comillas)

❌ **Excepciones:**
- Búsqueda por RFC: Sigue siendo exacta (sin normalización de acentos)

## Impacto en rendimiento

### Con extensión `unaccent`:
- ✅ Rendimiento óptimo
- ✅ Procesamiento en base de datos
- ✅ Aprovecha índices (si existen)

### Sin extensión (fallback Python):
- ⚠️ Ligeramente más lento
- ⚠️ Normalización en Python antes de enviar a DB
- ✅ Funciona en cualquier configuración

## Archivos modificados

1. **app/services/search_service.py**
   - Agregado método `_remove_accents()` para normalización Unicode
   - Agregado método `_unaccent_compare()` para comparaciones insensibles a acentos
   - Modificado `_build_simple_query()` para usar comparación sin acentos
   - Modificado `_build_advanced_query()` para usar comparación sin acentos

2. **migrations/enable_unaccent_extension.sql**
   - SQL para habilitar la extensión unaccent

3. **scripts/enable_unaccent.py**
   - Script para instalar la extensión automáticamente

## Testing

### Pruebas manuales recomendadas:

1. **Búsqueda con acentos vs sin acentos:**
   - Buscar `"José"` y `"Jose"` → Deben dar los mismos resultados
   - Buscar `"México"` y `"Mexico"` → Deben dar los mismos resultados

2. **Búsqueda de nombres con palabras intermedias:**
   - Buscar `"Arlin Medrano"` → Debe encontrar "ARLIN GABRIELA MEDRANO"

3. **Búsqueda con diéresis:**
   - Buscar `"Muller"` → Debe encontrar cualquier variante (Muller, Müller)

4. **Búsqueda con operadores:**
   - Buscar `"medicamentos -pediatricos"` → Debe excluir "pediátricos" también

## Mantenimiento

- La extensión `unaccent` no requiere mantenimiento regular
- El fallback en Python no tiene dependencias externas
- Ambas soluciones son compatibles con futuras versiones de PostgreSQL y Python
