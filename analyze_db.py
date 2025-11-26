#!/usr/bin/env python3
# analyze_db.py - Análisis de estructura y datos

DATABASE_URL = 'postgresql://lalupa:Kx9mP!7Nq3Lw5Rv_@db-postgresql-nyc1-16758-do-user-15464590-0.k.db.ondigitalocean.com:25060/defaultdb?sslmode=require'

from sqlalchemy import create_engine, text
import pandas as pd

engine = create_engine(DATABASE_URL)

print('=' * 80)
print('ANÁLISIS COMPLETO DE LA BASE DE DATOS')
print('=' * 80)

with engine.connect() as conn:
    # 1. Total de registros
    result = conn.execute(text('SELECT COUNT(*) FROM contratos.contratos'))
    total = result.scalar()
    print(f'\nTotal de registros: {total:,}')

    # 2. Muestra de datos
    print('\n' + '=' * 80)
    print('MUESTRA DE DATOS (3 registros)')
    print('=' * 80)

    result = conn.execute(text('''
        SELECT
            codigo_contrato,
            titulo_contrato,
            proveedor_contratista,
            rfc,
            importe,
            anio_fuente,
            fecha_inicio_contrato,
            tipo_contratacion,
            tipo_procedimiento
        FROM contratos.contratos
        WHERE codigo_contrato IS NOT NULL
        LIMIT 3
    '''))

    for idx, row in enumerate(result, 1):
        print(f'\n--- Registro {idx} ---')
        print(f'Código: {row[0]}')
        titulo = row[1][:70] + '...' if row[1] and len(row[1]) > 70 else row[1]
        print(f'Título: {titulo}')
        proveedor = row[2][:50] + '...' if row[2] and len(row[2]) > 50 else row[2]
        print(f'Proveedor: {proveedor}')
        print(f'RFC: {row[3]}')
        if row[4]:
            print(f'Importe: ${row[4]:,.2f}')
        else:
            print(f'Importe: N/A')
        print(f'Año: {row[5]}')
        print(f'Fecha inicio: {row[6]}')
        print(f'Tipo contratación: {row[7]}')
        print(f'Tipo procedimiento: {row[8]}')

    # 3. Análisis de calidad
    print('\n' + '=' * 80)
    print('CALIDAD DE DATOS')
    print('=' * 80)

    result = conn.execute(text('''
        SELECT
            COUNT(*) as total,
            COUNT(codigo_contrato) as con_codigo,
            COUNT(titulo_contrato) as con_titulo,
            COUNT(proveedor_contratista) as con_proveedor,
            COUNT(rfc) as con_rfc,
            COUNT(importe) as con_importe,
            COUNT(fecha_inicio_contrato) as con_fecha,
            COUNT(anio_fuente) as con_anio
        FROM contratos.contratos
    '''))

    row = result.fetchone()
    total = row[0]

    print(f'\nTotal registros: {total:,}')
    print(f'\nCampos poblados:')
    print(f'  Código contrato: {row[1]:,} ({row[1]/total*100:.1f}%)')
    print(f'  Título: {row[2]:,} ({row[2]/total*100:.1f}%)')
    print(f'  Proveedor: {row[3]:,} ({row[3]/total*100:.1f}%)')
    print(f'  RFC: {row[4]:,} ({row[4]/total*100:.1f}%)')
    print(f'  Importe: {row[5]:,} ({row[5]/total*100:.1f}%)')
    print(f'  Fecha inicio: {row[6]:,} ({row[6]/total*100:.1f}%)')
    print(f'  Año fuente: {row[7]:,} ({row[7]/total*100:.1f}%)')

    # 4. Duplicados
    print('\n' + '=' * 80)
    print('ANÁLISIS DE DUPLICADOS')
    print('=' * 80)

    result = conn.execute(text('''
        SELECT codigo_contrato, COUNT(*) as cnt
        FROM contratos.contratos
        WHERE codigo_contrato IS NOT NULL
        GROUP BY codigo_contrato
        HAVING COUNT(*) > 1
        ORDER BY cnt DESC
        LIMIT 5
    '''))

    duplicados = list(result)
    if duplicados:
        print(f'\nSe encontraron {len(duplicados)} códigos duplicados')
        print('\nTop 5 códigos más duplicados:')
        for row in duplicados:
            print(f'  {row[0]}: {row[1]} veces')
    else:
        print('\nNo se encontraron duplicados')

    # 5. Rangos de importes
    print('\n' + '=' * 80)
    print('ANÁLISIS DE IMPORTES')
    print('=' * 80)

    result = conn.execute(text('''
        SELECT
            MIN(importe) as min_imp,
            MAX(importe) as max_imp,
            AVG(importe) as avg_imp,
            COUNT(*) FILTER (WHERE importe <= 0) as negativos_o_cero
        FROM contratos.contratos
        WHERE importe IS NOT NULL
    '''))

    row = result.fetchone()
    if row[0] is not None:
        print(f'\nMínimo: ${row[0]:,.2f}')
        print(f'Máximo: ${row[1]:,.2f}')
        print(f'Promedio: ${row[2]:,.2f}')
        print(f'Negativos o cero: {row[3]:,}')

    # 6. Muestra de RFC
    print('\n' + '=' * 80)
    print('MUESTRA DE RFC (para validar formato)')
    print('=' * 80)

    result = conn.execute(text('''
        SELECT DISTINCT rfc
        FROM contratos.contratos
        WHERE rfc IS NOT NULL
        LIMIT 10
    '''))

    print('\nEjemplos de RFC en la BD:')
    for row in result:
        print(f'  {row[0]}')

    # 7. Años disponibles
    print('\n' + '=' * 80)
    print('AÑOS DISPONIBLES')
    print('=' * 80)

    result = conn.execute(text('''
        SELECT anio_fuente, COUNT(*) as cantidad
        FROM contratos.contratos
        WHERE anio_fuente IS NOT NULL
        GROUP BY anio_fuente
        ORDER BY anio_fuente DESC
    '''))

    print('\nRegistros por año:')
    for row in result:
        print(f'  {row[0]}: {row[1]:,}')

print('\n' + '=' * 80)
print('ANÁLISIS COMPLETADO')
print('=' * 80)
