# run.py (en la raíz del proyecto, NO dentro de app/)

import os
from dotenv import load_dotenv

# Cargar variables de entorno ANTES de importar la app
load_dotenv()

from app import create_app, db
from app.models import Contrato
from sqlalchemy import text, func

# Obtener configuración del entorno
config_name = os.environ.get('FLASK_ENV', 'development')
app = create_app(config_name)

def create_indexes():
    """Crea los índices necesarios para optimizar las búsquedas"""
    indices_sql = """
    -- Índices para mejorar performance
    CREATE INDEX IF NOT EXISTS idx_contratos_importe 
        ON contratos.contratos(importe DESC NULLS LAST);
    
    CREATE INDEX IF NOT EXISTS idx_contratos_proveedor 
        ON contratos.contratos(proveedor_contratista);
    
    CREATE INDEX IF NOT EXISTS idx_contratos_rfc 
        ON contratos.contratos(rfc);
    
    CREATE INDEX IF NOT EXISTS idx_contratos_siglas_inst 
        ON contratos.contratos(siglas_institucion);
    
    CREATE INDEX IF NOT EXISTS idx_contratos_anio 
        ON contratos.contratos(anio_fuente);
    
    CREATE INDEX IF NOT EXISTS idx_contratos_tipo_contratacion
        ON contratos.contratos(tipo_contratacion);
    
    CREATE INDEX IF NOT EXISTS idx_contratos_tipo_procedimiento
        ON contratos.contratos(tipo_procedimiento);
    
    -- Índices para búsqueda de texto
    CREATE INDEX IF NOT EXISTS idx_contratos_titulo_gin
        ON contratos.contratos USING gin(to_tsvector('spanish', titulo_contrato));
    
    CREATE INDEX IF NOT EXISTS idx_contratos_descripcion_gin
        ON contratos.contratos USING gin(to_tsvector('spanish', descripcion_contrato));
    """
    
    try:
        db.session.execute(text(indices_sql))
        db.session.commit()
        print("✅ Índices verificados/creados")
        return True
    except Exception as e:
        print(f"⚠️ No se pudieron crear algunos índices: {e}")
        db.session.rollback()
        return False

if __name__ == '__main__':
    with app.app_context():
        # Verificar conexión a la base de datos
        try:
            db.session.execute(text('SELECT 1'))
            print("✅ Conexión a la base de datos exitosa")
            
            # Contar registros
            count = db.session.query(func.count(Contrato.codigo_contrato)).scalar()
            print(f"📊 Total de contratos en la BD: {count:,}")
            
            # Crear índices si no existen
            create_indexes()
            
        except Exception as e:
            print(f"❌ Error de conexión a la BD: {e}")
            exit(1)
    
    # Ejecutar aplicación
    port = int(os.environ.get('PORT', 5000))
    debug = config_name == 'development'
    
    app.run(
        debug=debug,
        host='0.0.0.0',
        port=port
    )