#!/usr/bin/env python3
"""
Script para crear y configurar la vista materializada de estadísticas.
Ejecutar con: python3 scripts/setup_materialized_view.py
"""

import os
import sys
from pathlib import Path

# Agregar el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text

def create_materialized_view():
    """Crear la vista materializada de estadísticas"""

    # Obtener la configuración de base de datos desde variable de entorno
    database_url = os.environ.get('DATABASE_URL') or 'postgresql://lalupa:Kx9mP!7Nq3Lw5Rv_@db-postgresql-nyc1-16758-do-user-15464590-0.k.db.ondigitalocean.com:25060/defaultdb?sslmode=require'

    print("=" * 80)
    print("CREANDO VISTA MATERIALIZADA DE ESTADÍSTICAS")
    print("=" * 80)

    # Crear engine
    engine = create_engine(database_url)

    # Leer el SQL desde el archivo de migración
    sql_file = Path(__file__).parent.parent / 'migrations' / 'create_stats_materialized_view.sql'

    with open(sql_file, 'r') as f:
        sql_content = f.read()

    try:
        with engine.connect() as conn:
            # Ejecutar el SQL para crear la vista materializada
            print("\n1. Eliminando vista materializada existente (si existe)...")
            conn.execute(text("DROP MATERIALIZED VIEW IF EXISTS contratos.stats_summary CASCADE"))
            conn.commit()

            print("2. Creando vista materializada...")
            conn.execute(text("""
                CREATE MATERIALIZED VIEW contratos.stats_summary AS
                SELECT
                    COUNT(*) as total_contratos,
                    SUM(importe) as total_importe,
                    COUNT(DISTINCT proveedor_contratista) as proveedores_unicos,
                    COUNT(DISTINCT siglas_institucion) as instituciones_unicas,
                    MAX(fecha_inicio) as ultima_actualizacion,
                    MAX(anio_fuente) as ultimo_anio
                FROM contratos.contratos
            """))
            conn.commit()

            print("3. Creando índice único...")
            conn.execute(text("CREATE UNIQUE INDEX idx_stats_summary_unique ON contratos.stats_summary ((1))"))
            conn.commit()

            print("4. Configurando permisos...")
            conn.execute(text("GRANT SELECT ON contratos.stats_summary TO PUBLIC"))
            conn.commit()

            print("5. Agregando comentario de documentación...")
            conn.execute(text("""
                COMMENT ON MATERIALIZED VIEW contratos.stats_summary IS
                'Vista materializada que contiene estadísticas pre-calculadas de la base de datos de contratos.
                Se actualiza diariamente mediante un cron job o manualmente con: REFRESH MATERIALIZED VIEW CONCURRENTLY contratos.stats_summary;'
            """))
            conn.commit()

            # Verificar que se creó correctamente
            print("\n6. Verificando datos...")
            result = conn.execute(text("SELECT * FROM contratos.stats_summary"))
            row = result.fetchone()

            if row:
                print("\n" + "=" * 80)
                print("VISTA MATERIALIZADA CREADA EXITOSAMENTE")
                print("=" * 80)
                print(f"\nEstadísticas:")
                print(f"  Total contratos: {row[0]:,}")
                print(f"  Total importe: ${row[1]:,.2f}")
                print(f"  Proveedores únicos: {row[2]:,}")
                print(f"  Instituciones únicas: {row[3]:,}")
                print(f"  Última actualización: {row[4]}")
                print(f"  Último año: {row[5]}")

                print("\n" + "=" * 80)
                print("PRÓXIMOS PASOS")
                print("=" * 80)
                print("\n1. Configurar refresh automático diario:")
                print("   - Usar pg_cron (si está instalado en PostgreSQL)")
                print("   - O usar un cron job del sistema:")
                print("     Agregar a crontab: 0 2 * * * python3 /path/to/refresh_stats_view.py")
                print("\n2. Modificar el endpoint /api/stats para usar la vista materializada")
                print("\n3. Para refrescar manualmente:")
                print("   REFRESH MATERIALIZED VIEW CONCURRENTLY contratos.stats_summary;")

                return True
            else:
                print("\n✗ ERROR: La vista se creó pero no tiene datos")
                return False

    except Exception as e:
        print(f"\n✗ ERROR al crear la vista materializada: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = create_materialized_view()
    sys.exit(0 if success else 1)
