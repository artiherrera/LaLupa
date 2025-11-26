#!/usr/bin/env python
# inspect_database.py - Script para inspeccionar la estructura y datos de la BD

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text, inspect
import pandas as pd

# Cargar variables de entorno
load_dotenv()

# Conectar a la base de datos
DATABASE_URL = os.getenv('DATABASE_URL')
engine = create_engine(DATABASE_URL)

print("=" * 80)
print("INSPECCIÓN DE BASE DE DATOS - CONTRATOS")
print("=" * 80)

# 1. Información de la tabla
print("\n1. ESTRUCTURA DE LA TABLA")
print("-" * 80)

inspector = inspect(engine)
columns = inspector.get_columns('contratos', schema='contratos')

print(f"{'Columna':<30} {'Tipo':<20} {'Nullable':<10}")
print("-" * 80)
for col in columns:
    nullable = "Sí" if col['nullable'] else "No"
    print(f"{col['name']:<30} {str(col['type']):<20} {nullable:<10}")

# 2. Contar registros totales
print("\n2. ESTADÍSTICAS GENERALES")
print("-" * 80)

with engine.connect() as conn:
    result = conn.execute(text("SELECT COUNT(*) FROM contratos.contratos"))
    total = result.scalar()
    print(f"Total de registros: {total:,}")

    # Registros por año
    result = conn.execute(text("""
        SELECT anio_fuente, COUNT(*) as cantidad
        FROM contratos.contratos
        WHERE anio_fuente IS NOT NULL
        GROUP BY anio_fuente
        ORDER BY anio_fuente DESC
        LIMIT 10
    """))
    print("\nRegistros por año (últimos 10):")
    for row in result:
        print(f"  {row[0]}: {row[1]:,} contratos")

# 3. Muestra de datos
print("\n3. MUESTRA DE DATOS (5 registros)")
print("-" * 80)

query = """
    SELECT
        codigo_contrato,
        titulo_contrato,
        proveedor_contratista,
        rfc,
        importe,
        fecha_inicio_contrato,
        anio_fuente
    FROM contratos.contratos
    LIMIT 5
"""

df = pd.read_sql(query, engine)
pd.set_option('display.max_columns', None)
pd.set_option('display.width', None)
pd.set_option('display.max_colwidth', 50)
print(df.to_string())

# 4. Análisis de calidad de datos
print("\n4. ANÁLISIS DE CALIDAD DE DATOS")
print("-" * 80)

with engine.connect() as conn:
    # Valores nulos por columna
    print("\nValores NULL por columna:")
    result = conn.execute(text("""
        SELECT
            COUNT(*) FILTER (WHERE codigo_contrato IS NULL) as null_codigo,
            COUNT(*) FILTER (WHERE titulo_contrato IS NULL) as null_titulo,
            COUNT(*) FILTER (WHERE proveedor_contratista IS NULL) as null_proveedor,
            COUNT(*) FILTER (WHERE rfc IS NULL) as null_rfc,
            COUNT(*) FILTER (WHERE importe IS NULL) as null_importe,
            COUNT(*) FILTER (WHERE fecha_inicio_contrato IS NULL) as null_fecha_inicio,
            COUNT(*) FILTER (WHERE anio_fuente IS NULL) as null_anio
        FROM contratos.contratos
    """))
    row = result.fetchone()
    print(f"  codigo_contrato: {row[0]:,}")
    print(f"  titulo_contrato: {row[1]:,}")
    print(f"  proveedor_contratista: {row[2]:,}")
    print(f"  rfc: {row[3]:,}")
    print(f"  importe: {row[4]:,}")
    print(f"  fecha_inicio_contrato: {row[5]:,}")
    print(f"  anio_fuente: {row[6]:,}")

    # Duplicados
    result = conn.execute(text("""
        SELECT COUNT(*)
        FROM (
            SELECT codigo_contrato, COUNT(*)
            FROM contratos.contratos
            GROUP BY codigo_contrato
            HAVING COUNT(*) > 1
        ) duplicados
    """))
    duplicados = result.scalar()
    print(f"\nCódigos de contrato duplicados: {duplicados:,}")

    # Rangos de importes
    result = conn.execute(text("""
        SELECT
            MIN(importe) as min_importe,
            MAX(importe) as max_importe,
            AVG(importe) as avg_importe,
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY importe) as median_importe
        FROM contratos.contratos
        WHERE importe IS NOT NULL
    """))
    row = result.fetchone()
    print(f"\nImportes:")
    print(f"  Mínimo: ${row[0]:,.2f}" if row[0] else "  Mínimo: N/A")
    print(f"  Máximo: ${row[1]:,.2f}" if row[1] else "  Máximo: N/A")
    print(f"  Promedio: ${row[2]:,.2f}" if row[2] else "  Promedio: N/A")
    print(f"  Mediana: ${row[3]:,.2f}" if row[3] else "  Mediana: N/A")

# 5. Muestra de RFC para validar formato
print("\n5. MUESTRA DE RFC (10 registros)")
print("-" * 80)

with engine.connect() as conn:
    result = conn.execute(text("""
        SELECT DISTINCT rfc, proveedor_contratista
        FROM contratos.contratos
        WHERE rfc IS NOT NULL
        LIMIT 10
    """))
    print(f"{'RFC':<15} {'Proveedor':<50}")
    print("-" * 80)
    for row in result:
        proveedor = (row[1][:47] + '...') if row[1] and len(row[1]) > 50 else (row[1] or '')
        print(f"{row[0]:<15} {proveedor:<50}")

# 6. Tipos de contratación
print("\n6. TIPOS DE CONTRATACIÓN")
print("-" * 80)

with engine.connect() as conn:
    result = conn.execute(text("""
        SELECT tipo_contratacion, COUNT(*) as cantidad
        FROM contratos.contratos
        WHERE tipo_contratacion IS NOT NULL
        GROUP BY tipo_contratacion
        ORDER BY cantidad DESC
        LIMIT 10
    """))
    print(f"{'Tipo':<40} {'Cantidad':<15}")
    print("-" * 80)
    for row in result:
        tipo = (row[0][:37] + '...') if row[0] and len(row[0]) > 40 else (row[0] or '')
        print(f"{tipo:<40} {row[1]:,}")

# 7. Verificar caracteres especiales o problemas de encoding
print("\n7. VERIFICACIÓN DE ENCODING Y CARACTERES")
print("-" * 80)

with engine.connect() as conn:
    result = conn.execute(text("""
        SELECT titulo_contrato, descripcion_contrato
        FROM contratos.contratos
        WHERE titulo_contrato IS NOT NULL
        LIMIT 3
    """))
    print("Muestra de títulos (para verificar encoding):")
    for idx, row in enumerate(result, 1):
        titulo = (row[0][:70] + '...') if row[0] and len(row[0]) > 70 else (row[0] or '')
        print(f"\n{idx}. {titulo}")

print("\n" + "=" * 80)
print("INSPECCIÓN COMPLETADA")
print("=" * 80)
