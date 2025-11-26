#!/usr/bin/env python3
"""
Script para refrescar la vista materializada de estadísticas.
Este script debe ejecutarse diariamente mediante un cron job.

Ejemplo de crontab:
0 2 * * * cd /path/to/lalupa && python3 scripts/refresh_stats_view.py >> logs/refresh_stats.log 2>&1

Esto ejecutará el refresh todos los días a las 2:00 AM.
"""

import os
import sys
from pathlib import Path
from datetime import datetime

# Agregar el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text

def refresh_materialized_view():
    """Refrescar la vista materializada de estadísticas"""

    # Obtener la configuración de base de datos desde variable de entorno
    database_url = os.environ.get('DATABASE_URL') or 'postgresql://lalupa:Kx9mP!7Nq3Lw5Rv_@db-postgresql-nyc1-16758-do-user-15464590-0.k.db.ondigitalocean.com:25060/defaultdb?sslmode=require'

    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    print(f"\n{'=' * 80}")
    print(f"REFRESCANDO VISTA MATERIALIZADA - {timestamp}")
    print(f"{'=' * 80}\n")

    # Crear engine
    engine = create_engine(database_url)

    try:
        start_time = datetime.now()

        with engine.connect() as conn:
            print("Ejecutando REFRESH MATERIALIZED VIEW CONCURRENTLY...")

            # Usar CONCURRENTLY para no bloquear lecturas durante el refresh
            conn.execute(text("REFRESH MATERIALIZED VIEW CONCURRENTLY contratos.stats_summary"))
            conn.commit()

            elapsed = (datetime.now() - start_time).total_seconds()

            # Verificar los datos actualizados
            result = conn.execute(text("SELECT * FROM contratos.stats_summary"))
            row = result.fetchone()

            if row:
                print(f"\n{'=' * 80}")
                print(f"VISTA MATERIALIZADA REFRESCADA EXITOSAMENTE")
                print(f"{'=' * 80}\n")
                print(f"Tiempo de ejecución: {elapsed:.2f} segundos")
                print(f"\nEstadísticas actualizadas:")
                print(f"  Total contratos: {row[0]:,}")
                print(f"  Total importe: ${row[1]:,.2f}")
                print(f"  Proveedores únicos: {row[2]:,}")
                print(f"  Instituciones únicas: {row[3]:,}")
                print(f"  Última actualización: {row[4]}")
                print(f"  Último año: {row[5]}")
                print(f"\n{'=' * 80}\n")
                return True
            else:
                print(f"\n✗ ERROR: La vista se refrescó pero no tiene datos")
                return False

    except Exception as e:
        print(f"\n✗ ERROR al refrescar la vista materializada: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = refresh_materialized_view()
    sys.exit(0 if success else 1)
