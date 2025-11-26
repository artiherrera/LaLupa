#!/usr/bin/env python3
"""
Script para habilitar la extensión unaccent de PostgreSQL.
Esta extensión permite búsquedas insensibles a acentos y diéresis.
"""

import sys
import os

# Agregar el directorio padre al path para importar app
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db

def enable_unaccent():
    """Habilita la extensión unaccent en PostgreSQL"""
    app = create_app()

    with app.app_context():
        try:
            # Intentar crear la extensión
            print("Intentando habilitar la extensión unaccent...")
            db.session.execute(db.text("CREATE EXTENSION IF NOT EXISTS unaccent;"))
            db.session.commit()

            # Verificar que está instalada
            result = db.session.execute(db.text(
                "SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'unaccent');"
            ))
            exists = result.scalar()

            if exists:
                print("✅ Extensión unaccent habilitada exitosamente")
                print("   Las búsquedas ahora serán insensibles a acentos y diéresis")
                return True
            else:
                print("❌ La extensión no pudo ser instalada")
                return False

        except Exception as e:
            db.session.rollback()
            print(f"❌ Error al habilitar unaccent: {str(e)}")
            print("\nNOTA: Si obtienes un error de permisos, la extensión unaccent")
            print("      requiere privilegios de superusuario en PostgreSQL.")
            print("\nOpciones:")
            print("  1. Contacta al administrador de la base de datos para que ejecute:")
            print("     CREATE EXTENSION unaccent;")
            print("  2. El sistema usará un fallback que normaliza los textos en Python")
            print("     (funcionará pero puede ser un poco más lento)")
            return False

if __name__ == '__main__':
    success = enable_unaccent()
    sys.exit(0 if success else 1)
