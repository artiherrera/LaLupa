-- Crear vista materializada para estadísticas de contratos
-- Esta vista pre-calcula las estadísticas para mejorar el rendimiento

-- Eliminar la vista materializada si existe
DROP MATERIALIZED VIEW IF EXISTS contratos.stats_summary;

-- Crear la vista materializada
CREATE MATERIALIZED VIEW contratos.stats_summary AS
SELECT
    COUNT(*) as total_contratos,
    SUM(importe) as total_importe,
    COUNT(DISTINCT proveedor_contratista) as proveedores_unicos,
    COUNT(DISTINCT siglas_institucion) as instituciones_unicas,
    MAX(fecha_inicio) as ultima_actualizacion,
    MAX(anio_fuente) as ultimo_anio
FROM contratos.contratos;

-- Crear índice único para poder usar REFRESH CONCURRENTLY
CREATE UNIQUE INDEX idx_stats_summary_unique ON contratos.stats_summary ((1));

-- Dar permisos de lectura
GRANT SELECT ON contratos.stats_summary TO PUBLIC;

-- Comentario para documentación
COMMENT ON MATERIALIZED VIEW contratos.stats_summary IS
'Vista materializada que contiene estadísticas pre-calculadas de la base de datos de contratos.
Se actualiza diariamente mediante un cron job o manualmente con: REFRESH MATERIALIZED VIEW CONCURRENTLY contratos.stats_summary;';
