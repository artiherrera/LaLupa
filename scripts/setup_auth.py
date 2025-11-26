#!/usr/bin/env python3
"""
Script para configurar el sistema de autenticacion.
Crea el schema 'auth', las tablas necesarias y el usuario admin inicial.

Uso: python scripts/setup_auth.py
"""

import os
import sys

# Agregar el directorio raiz al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models import Usuario, SesionActiva, HistorialBusqueda, LogAcceso
from sqlalchemy import text


def setup_auth():
    """Configura el sistema de autenticacion"""
    app = create_app()

    with app.app_context():
        print("=" * 50)
        print("CONFIGURACION DEL SISTEMA DE AUTENTICACION")
        print("=" * 50)

        # 1. Crear las tablas (usamos schema 'public')
        print("\n[1/3] Creando tablas de autenticacion...")
        try:
            # Crear tablas especificas del schema auth
            Usuario.__table__.create(db.engine, checkfirst=True)
            print("     - Tabla 'usuarios' creada/verificada")

            SesionActiva.__table__.create(db.engine, checkfirst=True)
            print("     - Tabla 'sesiones_activas' creada/verificada")

            HistorialBusqueda.__table__.create(db.engine, checkfirst=True)
            print("     - Tabla 'historial_busquedas' creada/verificada")

            LogAcceso.__table__.create(db.engine, checkfirst=True)
            print("     - Tabla 'log_accesos' creada/verificada")

        except Exception as e:
            print(f"     Error creando tablas: {e}")
            db.session.rollback()
            return False

        # 2. Crear usuario admin
        print("\n[2/3] Verificando usuario admin...")
        admin_email = "arti.herrera@mail.com"
        admin_password = "1899Hayek$"

        existing_admin = Usuario.query.filter_by(email=admin_email).first()

        if existing_admin:
            print(f"     Usuario admin ya existe: {admin_email}")
        else:
            try:
                admin = Usuario(
                    email=admin_email,
                    nombre="Arturo Herrera",
                    rol="admin",
                    activo=True
                )
                admin.set_password(admin_password)
                db.session.add(admin)
                db.session.commit()
                print(f"     Usuario admin creado: {admin_email}")
            except Exception as e:
                print(f"     Error creando admin: {e}")
                db.session.rollback()
                return False

        # 3. Verificar configuracion
        print("\n[3/3] Verificando configuracion...")
        try:
            usuarios_count = Usuario.query.count()
            print(f"     Total de usuarios: {usuarios_count}")

            admin = Usuario.query.filter_by(email=admin_email).first()
            if admin and admin.check_password(admin_password):
                print("     Credenciales de admin verificadas correctamente")
            else:
                print("     ADVERTENCIA: No se pudieron verificar las credenciales")

        except Exception as e:
            print(f"     Error en verificacion: {e}")
            return False

        print("\n" + "=" * 50)
        print("CONFIGURACION COMPLETADA EXITOSAMENTE")
        print("=" * 50)
        print(f"\nCredenciales del administrador:")
        print(f"  Email: {admin_email}")
        print(f"  Password: {admin_password}")
        print(f"\nAccede a: http://localhost:5000/login")
        print("=" * 50)

        return True


if __name__ == "__main__":
    success = setup_auth()
    sys.exit(0 if success else 1)
