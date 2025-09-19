# test_connection.py
# Prueba de conexión usando SOLO el archivo .env

import os
from dotenv import load_dotenv
import psycopg2
from urllib.parse import urlparse

# Cargar variables desde .env
load_dotenv()

print("🔍 PRUEBA DE CONEXIÓN DESDE .env")
print("=" * 60)

# Obtener DATABASE_URL del .env
DATABASE_URL = os.getenv('DATABASE_URL')

if not DATABASE_URL:
    print("❌ Error: No se encontró DATABASE_URL en el archivo .env")
    print("Verifica que el archivo .env existe y contiene DATABASE_URL")
    exit(1)

print("✅ DATABASE_URL encontrada en .env")
print(f"📝 URL: {DATABASE_URL[:50]}...")  # Mostrar solo el inicio por seguridad
print()

# Parsear la DATABASE_URL
result = urlparse(DATABASE_URL)

print("📋 Configuración parseada:")
print(f"   Host: {result.hostname}")
print(f"   Puerto: {result.port}")
print(f"   Base de datos: {result.path[1:]}")
print(f"   Usuario: {result.username}")
print(f"   SSL: sslmode=require")
print()

print("🔌 Intentando conectar...")
print("-" * 60)

try:
    # Conectar usando psycopg2 directamente
    conn = psycopg2.connect(DATABASE_URL)
    
    print("✅ ¡CONEXIÓN EXITOSA!")
    print()
    
    cur = conn.cursor()
    
    # Prueba 1: Contar registros
    cur.execute("SELECT COUNT(*) FROM contratos.contratos")
    count = cur.fetchone()[0]
    print(f"📊 Total de contratos en la BD: {count:,}")
    
    # Prueba 2: Obtener muestra de datos
    print("\n📝 Muestra de datos (primeros 3 contratos):")
    print("-" * 60)
    
    cur.execute("""
        SELECT 
            codigo_contrato,
            proveedor_contratista,
            institucion,
            importe,
            titulo_contrato
        FROM contratos.contratos 
        LIMIT 3
    """)
    
    for i, row in enumerate(cur.fetchall(), 1):
        print(f"\nContrato {i}:")
        print(f"  Código: {row[0]}")
        print(f"  Proveedor: {row[1] if row[1] else 'N/A'}")
        print(f"  Institución: {row[2][:50] if row[2] else 'N/A'}...")
        print(f"  Importe: ${float(row[3]):,.2f}" if row[3] else "  Importe: N/A")
        print(f"  Título: {row[4][:60] if row[4] else 'N/A'}...")
    
    # Prueba 3: Búsqueda simple
    print("\n🔍 Prueba de búsqueda (contratos con 'medicamento'):")
    print("-" * 60)
    
    cur.execute("""
        SELECT COUNT(*) 
        FROM contratos.contratos 
        WHERE descripcion_contrato ILIKE '%medicamento%'
    """)
    
    medicamentos_count = cur.fetchone()[0]
    print(f"Contratos relacionados con medicamentos: {medicamentos_count:,}")
    
    # Prueba 4: Verificar columnas
    print("\n📋 Columnas disponibles en la tabla:")
    print("-" * 60)
    
    cur.execute("""
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_schema = 'contratos' 
        AND table_name = 'contratos'
        LIMIT 10
    """)
    
    for col in cur.fetchall():
        print(f"  • {col[0]:<30} ({col[1]})")
    
    print("\n" + "=" * 60)
    print("✨ ¡TODO FUNCIONANDO CORRECTAMENTE!")
    print("=" * 60)
    print("\n🚀 Ya puedes ejecutar la aplicación:")
    print("   python app_simple.py")
    print("\n📌 Luego abre en tu navegador:")
    print("   http://localhost:5000")
    
    cur.close()
    conn.close()
    
except psycopg2.OperationalError as e:
    print(f"❌ Error de conexión: {e}")
    print()
    print("🔧 Posibles soluciones:")
    print("1. Verifica que el archivo .env tenga la DATABASE_URL correcta")
    print("2. Si el error es 'permission denied for schema contratos',")
    print("   ejecuta estos comandos SQL como administrador:")
    print()
    print("   GRANT USAGE ON SCHEMA contratos TO lalupa;")
    print("   GRANT SELECT ON ALL TABLES IN SCHEMA contratos TO lalupa;")
    print()
    print("3. Si el error es de autenticación, verifica la contraseña")
    
except Exception as e:
    print(f"❌ Error: {e}")
    print()
    print("Verifica tu archivo .env y la conexión a internet")