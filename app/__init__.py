# app/__init__.py

import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

# Inicializar extensiones (sin app todavía)
db = SQLAlchemy()
migrate = Migrate()

def create_app(config_name=None):
    """Factory pattern para crear la aplicación Flask"""
    
    if config_name is None:
        import os
        config_name = os.environ.get('FLASK_ENV', 'development')
    
    # Importar config aquí para evitar import circular
    from config import config
    
    app = Flask(__name__)
    
    # Cargar configuración
    app.config.from_object(config[config_name])
    
    # Inicializar extensiones con la app
    db.init_app(app)
    migrate.init_app(app, db)
    
    # Configurar logging
    if not app.debug and not app.testing:
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s %(levelname)s: %(message)s'
        )
    
    # Registrar blueprints
    from app.api import search_bp, contracts_bp, stats_bp
    app.register_blueprint(search_bp, url_prefix='/api')
    app.register_blueprint(contracts_bp, url_prefix='/api')
    app.register_blueprint(stats_bp, url_prefix='/api')
    
    # Registrar rutas principales
    from app import routes
    app.register_blueprint(routes.main_bp)
    
    # Contexto de la aplicación para el shell
    @app.shell_context_processor
    def make_shell_context():
        from app.models import Contrato
        return {'db': db, 'Contrato': Contrato}
    
    return app