# wsgi.py - Punto de entrada para Gunicorn
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

from app import create_app

# Crear aplicacion en modo produccion
app = create_app(os.environ.get('FLASK_ENV', 'production'))

if __name__ == '__main__':
    app.run()
