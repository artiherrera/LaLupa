-- Habilitar la extensión unaccent para búsquedas insensibles a acentos
-- Esta extensión permite comparar texto ignorando acentos y diéresis
-- Ejemplo: 'José' = 'Jose', 'Müller' = 'Muller'

-- Intentar crear la extensión (requiere permisos de superusuario)
CREATE EXTENSION IF NOT EXISTS unaccent;

-- Verificar que la extensión está instalada
SELECT * FROM pg_extension WHERE extname = 'unaccent';
