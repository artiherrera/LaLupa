# admin_app.py - Aplicación Flask para administración y limpieza de datos

import os
import pandas as pd
from flask import Flask, request, jsonify, render_template_string, session, redirect, url_for
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import logging
from datetime import datetime, timedelta
import re
from functools import wraps
import secrets
import time
import uuid

# Cargar variables de entorno
load_dotenv()

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Crear aplicación Flask
app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB max
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', secrets.token_hex(32))
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=2)

# Credenciales de administrador
ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'admin123')

# Configurar base de datos
# Usar ADMIN_DATABASE_URL con permisos de escritura (doadmin), no DATABASE_URL (solo lectura)
DATABASE_URL = os.getenv('ADMIN_DATABASE_URL') or os.getenv('DATABASE_URL')
if not DATABASE_URL:
    raise ValueError("ADMIN_DATABASE_URL o DATABASE_URL no está configurada en las variables de entorno")

engine = create_engine(DATABASE_URL)
logger.info(f"Conectando a la base de datos con usuario: {DATABASE_URL.split('://')[1].split(':')[0]}")
Session = sessionmaker(bind=engine)


def verificar_indices_fts():
    """Verifica y crea los índices GIN para Full Text Search si no existen"""
    indices_sql = """
    -- Índices GIN para Full Text Search (búsquedas rápidas)
    CREATE INDEX IF NOT EXISTS idx_contratos_titulo_gin
        ON contratos.contratos USING gin(to_tsvector('spanish', COALESCE(titulo_contrato, '')));

    CREATE INDEX IF NOT EXISTS idx_contratos_descripcion_gin
        ON contratos.contratos USING gin(to_tsvector('spanish', COALESCE(descripcion_contrato, '')));

    CREATE INDEX IF NOT EXISTS idx_contratos_proveedor_gin
        ON contratos.contratos USING gin(to_tsvector('spanish', COALESCE(proveedor_contratista, '')));

    CREATE INDEX IF NOT EXISTS idx_contratos_institucion_gin
        ON contratos.contratos USING gin(to_tsvector('spanish', COALESCE(institucion, '')));

    -- Índices compuestos para agregaciones (GROUP BY + SUM)
    CREATE INDEX IF NOT EXISTS idx_contratos_proveedor_importe
        ON contratos.contratos(proveedor_contratista, rfc, importe);

    CREATE INDEX IF NOT EXISTS idx_contratos_institucion_importe
        ON contratos.contratos(siglas_institucion, institucion, importe);

    CREATE INDEX IF NOT EXISTS idx_contratos_estatus
        ON contratos.contratos(estatus_contrato);
    """

    try:
        db_session = Session()
        db_session.execute(text(indices_sql))
        db_session.commit()
        db_session.close()
        logger.info("✅ Índices FTS y agregación verificados/creados")
        return True
    except Exception as e:
        logger.warning(f"⚠️ No se pudieron crear índices: {e}")
        return False


# Decorador para requerir autenticación
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


# Templates HTML (mantenemos los mismos)
LOGIN_TEMPLATE = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Login - Panel de Administración</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .login-container {
            background: white;
            padding: 40px;
            border-radius: 10px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            width: 100%;
            max-width: 400px;
        }
        .login-header { text-align: center; margin-bottom: 30px; }
        .login-header h1 { color: #333; margin-bottom: 10px; }
        .login-header p { color: #666; font-size: 0.9em; }
        .form-group { margin-bottom: 20px; }
        .form-group label { display: block; margin-bottom: 8px; color: #333; font-weight: 500; }
        .form-group input {
            width: 100%;
            padding: 12px;
            border: 2px solid #e0e0e0;
            border-radius: 5px;
            font-size: 16px;
            transition: border-color 0.3s;
        }
        .form-group input:focus { outline: none; border-color: #667eea; }
        .btn {
            width: 100%;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 12px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 16px;
            font-weight: 500;
            transition: transform 0.2s;
        }
        .btn:hover { transform: translateY(-2px); box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4); }
        .error {
            background: #fee;
            color: #c33;
            padding: 12px;
            border-radius: 5px;
            margin-bottom: 20px;
            border: 1px solid #fcc;
        }
        .lock-icon {
            width: 60px;
            height: 60px;
            margin: 0 auto 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 30px;
        }
    </style>
</head>
<body>
    <div class="login-container">
        <div class="login-header">
            <div class="lock-icon">🔒</div>
            <h1>Panel de Administración</h1>
            <p>Carga y limpieza de datos de contratos</p>
        </div>
        {% if error %}
        <div class="error">{{ error }}</div>
        {% endif %}
        <form method="POST" action="{{ url_for('login') }}">
            <div class="form-group">
                <label for="username">Usuario</label>
                <input type="text" id="username" name="username" required autofocus>
            </div>
            <div class="form-group">
                <label for="password">Contraseña</label>
                <input type="password" id="password" name="password" required>
            </div>
            <button type="submit" class="btn">Iniciar Sesión</button>
        </form>
    </div>
</body>
</html>
"""

ADMIN_TEMPLATE = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Administración - Carga de Datos</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 900px;
            margin: 0 auto;
            background: white;
            padding: 40px;
            border-radius: 10px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
        }
        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 30px;
            flex-wrap: wrap;
        }
        .header-left h1 { color: #333; margin-bottom: 5px; }
        .header-left .subtitle { color: #666; }
        .header-right { display: flex; gap: 10px; align-items: center; }
        .user-info {
            background: #e8f0fe;
            padding: 8px 15px;
            border-radius: 5px;
            font-size: 14px;
            color: #667eea;
        }
        .logout-btn {
            background: #dc3545;
            color: white;
            padding: 8px 20px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            text-decoration: none;
            font-size: 14px;
        }
        .logout-btn:hover { background: #c82333; }
        .section {
            margin-bottom: 30px;
            padding: 20px;
            background: #f9f9f9;
            border-radius: 8px;
        }
        .section h2 { color: #667eea; margin-bottom: 15px; font-size: 1.2em; }
        .upload-area {
            border: 2px dashed #667eea;
            padding: 30px;
            text-align: center;
            border-radius: 8px;
            background: white;
            cursor: pointer;
            transition: all 0.3s;
        }
        .upload-area:hover { background: #f0f4ff; border-color: #764ba2; }
        input[type="file"] { display: none; }
        .btn {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 12px 30px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 16px;
            transition: transform 0.2s;
            margin: 10px 5px;
        }
        .btn:hover { transform: translateY(-2px); box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4); }
        .btn:disabled { background: #ccc; cursor: not-allowed; transform: none; }
        .btn-danger { background: #dc3545; }
        .btn-danger:hover { background: #c82333; box-shadow: 0 5px 15px rgba(220, 53, 69, 0.4); }
        .progress {
            width: 100%;
            height: 30px;
            background: #e0e0e0;
            border-radius: 15px;
            overflow: hidden;
            margin: 20px 0;
            display: none;
        }
        .progress-bar {
            height: 100%;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            width: 0%;
            transition: width 0.3s;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: bold;
        }
        .log {
            background: #1e1e1e;
            color: #00ff00;
            padding: 15px;
            border-radius: 5px;
            max-height: 400px;
            overflow-y: auto;
            font-family: 'Courier New', monospace;
            font-size: 12px;
            margin-top: 20px;
            display: none;
        }
        .log-line { margin: 2px 0; }
        .log-warning { color: #ffaa00; }
        .log-error { color: #ff4444; }
        .log-success { color: #00ff00; }
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-top: 20px;
        }
        .stat-card {
            background: white;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }
        .stat-value { font-size: 2em; font-weight: bold; color: #667eea; }
        .stat-label { color: #666; margin-top: 5px; }
        .selected-file {
            margin: 10px 0;
            padding: 10px;
            background: #e8f0fe;
            border-radius: 5px;
            display: none;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="header-left">
                <h1>Panel de Administración</h1>
                <p class="subtitle">Carga y limpieza de datos de contratos</p>
            </div>
            <div class="header-right">
                <div class="user-info">👤 {{ username }}</div>
                <a href="{{ url_for('logout') }}" class="logout-btn">Cerrar Sesión</a>
            </div>
        </div>

        <div class="section">
            <h2>📊 Estadísticas de la Base de Datos</h2>
            <div class="stats" id="stats">
                <div class="stat-card">
                    <div class="stat-value" id="totalContratos">-</div>
                    <div class="stat-label">Contratos Totales</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value" id="ultimoAño">-</div>
                    <div class="stat-label">Último Año</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value" id="ultimaActualizacion" style="font-size: 1.2em;">-</div>
                    <div class="stat-label">Última Actualización</div>
                </div>
            </div>
            <button class="btn" onclick="loadStats()">Actualizar Estadísticas</button>
        </div>

        <div class="section">
            <h2>📤 Cargar Archivo CSV</h2>
            <div class="upload-area" onclick="document.getElementById('fileInput').click()">
                <p>🔍 Haz clic o arrastra un archivo CSV aquí</p>
                <p style="font-size: 0.9em; color: #999; margin-top: 10px;">Máximo 500MB | Soporta UTF-8, Latin-1, CP1252</p>
            </div>
            <input type="file" id="fileInput" accept=".csv" onchange="handleFileSelect(event)">
            <div class="selected-file" id="selectedFile"></div>

            <div class="progress" id="progress">
                <div class="progress-bar" id="progressBar">0%</div>
            </div>

            <button class="btn" id="uploadBtn" onclick="uploadFile()" disabled>Cargar y Limpiar Datos</button>
            <button class="btn btn-danger" onclick="clearDuplicates()">Limpiar Duplicados</button>

            <div class="log" id="log"></div>
        </div>
    </div>

    <script>
        let selectedFile = null;

        function addLog(message, type = 'info') {
            const log = document.getElementById('log');
            log.style.display = 'block';
            const timestamp = new Date().toLocaleTimeString();
            const line = document.createElement('div');
            line.className = 'log-line';

            if (type === 'warning') line.classList.add('log-warning');
            else if (type === 'error') line.classList.add('log-error');
            else if (type === 'success') line.classList.add('log-success');

            line.textContent = `[${timestamp}] ${message}`;
            log.appendChild(line);
            log.scrollTop = log.scrollHeight;
        }

        function handleFileSelect(event) {
            selectedFile = event.target.files[0];
            if (selectedFile) {
                document.getElementById('selectedFile').style.display = 'block';
                document.getElementById('selectedFile').textContent = `Archivo seleccionado: ${selectedFile.name} (${(selectedFile.size / 1024 / 1024).toFixed(2)} MB)`;
                document.getElementById('uploadBtn').disabled = false;
                addLog(`Archivo seleccionado: ${selectedFile.name}`, 'info');
            }
        }

        async function loadStats() {
            try {
                const response = await fetch('/api/stats');
                const data = await response.json();
                document.getElementById('totalContratos').textContent = data.total_contratos.toLocaleString();
                document.getElementById('ultimoAño').textContent = data.ultimo_anio || 'N/A';
                document.getElementById('ultimaActualizacion').textContent = data.ultima_actualizacion || 'Sin datos';
                addLog('Estadísticas actualizadas', 'success');
            } catch (error) {
                addLog(`Error al cargar estadísticas: ${error.message}`, 'error');
            }
        }

        async function uploadFile() {
            if (!selectedFile) {
                alert('Por favor selecciona un archivo primero');
                return;
            }

            const formData = new FormData();
            formData.append('file', selectedFile);

            const uploadBtn = document.getElementById('uploadBtn');
            const progress = document.getElementById('progress');
            const progressBar = document.getElementById('progressBar');

            uploadBtn.disabled = true;
            progress.style.display = 'block';
            progressBar.style.width = '10%';
            progressBar.textContent = '10%';

            addLog('Iniciando carga de archivo...', 'info');
            addLog('Detectando encoding y validando estructura...', 'info');

            try {
                progressBar.style.width = '30%';
                progressBar.textContent = '30%';

                const response = await fetch('/api/upload', {
                    method: 'POST',
                    body: formData
                });

                const data = await response.json();

                if (response.ok) {
                    progressBar.style.width = '100%';
                    progressBar.textContent = '100%';

                    addLog('✓ Proceso completado exitosamente', 'success');
                    addLog(`→ Registros procesados: ${data.registros_procesados}`, 'info');
                    addLog(`→ Registros insertados: ${data.registros_insertados}`, 'success');
                    addLog(`→ Omitidos (duplicados): ${data.registros_duplicados}`, 'warning');
                    addLog(`→ Con errores: ${data.registros_con_errores}`, 'error');

                    if (data.advertencias && data.advertencias.length > 0) {
                        addLog('\\nAdvertencias:', 'warning');
                        data.advertencias.forEach(adv => addLog(`  • ${adv}`, 'warning'));
                    }

                    loadStats();
                } else {
                    addLog(`✗ Error: ${data.error}`, 'error');
                    if (data.detalles) {
                        addLog(`Detalles: ${data.detalles}`, 'error');
                    }
                }
            } catch (error) {
                addLog(`✗ Error en la carga: ${error.message}`, 'error');
            } finally {
                uploadBtn.disabled = false;
                setTimeout(() => {
                    progress.style.display = 'none';
                }, 3000);
            }
        }

        async function clearDuplicates() {
            if (!confirm('¿Estás seguro de que quieres eliminar los registros duplicados? Se conservará solo una copia de cada contrato.')) {
                return;
            }

            try {
                addLog('Analizando y eliminando duplicados...', 'warning');
                const response = await fetch('/api/clear', { method: 'POST' });
                const data = await response.json();

                if (response.ok) {
                    addLog(`✓ Duplicados eliminados exitosamente`, 'success');
                    addLog(`  - Registros analizados: ${data.registros_totales || 0}`, 'info');
                    addLog(`  - Duplicados encontrados: ${data.duplicados_encontrados || 0}`, 'info');
                    addLog(`  - Duplicados eliminados: ${data.registros_eliminados || 0}`, 'success');
                    addLog(`  - Registros finales: ${data.registros_finales || 0}`, 'info');
                    loadStats();
                } else {
                    addLog(`✗ Error: ${data.error}`, 'error');
                }
            } catch (error) {
                addLog(`✗ Error al limpiar duplicados: ${error.message}`, 'error');
            }
        }

        // Cargar estadísticas al iniciar
        loadStats();

        // Drag and drop
        const uploadArea = document.querySelector('.upload-area');
        uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadArea.style.background = '#f0f4ff';
        });
        uploadArea.addEventListener('dragleave', () => {
            uploadArea.style.background = 'white';
        });
        uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadArea.style.background = 'white';
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                document.getElementById('fileInput').files = files;
                handleFileSelect({ target: { files } });
            }
        });
    </script>
</body>
</html>
"""


class DataCleaner:
    """Clase mejorada para limpiar y procesar datos de contratos"""

    # Mapeo completo de columnas CSV → BD
    COLUMN_MAPPING = {
        # Campos principales
        'Código del contrato': 'codigo_contrato',
        'C�digo del contrato': 'codigo_contrato',  # Con encoding issues
        'Código del expediente': 'codigo_expediente',
        'C�digo del expediente': 'codigo_expediente',

        # Títulos
        'Título del contrato': 'titulo_contrato',
        'T�tulo del contrato': 'titulo_contrato',
        'Título del expediente': 'titulo_expediente',
        'T�tulo del expediente': 'titulo_expediente',

        # Descripción
        'Descripción del contrato': 'descripcion_contrato',
        'Descripci�n del contrato': 'descripcion_contrato',

        # Tipo
        'Tipo de contratación': 'tipo_contratacion',
        'Tipo de contrataci�n': 'tipo_contratacion',
        'Tipo Procedimiento': 'tipo_procedimiento',

        # Proveedor y RFC
        'Proveedor o contratista': 'proveedor_contratista',
        'rfc': 'rfc',
        'RFC': 'rfc',

        # Institución
        'Institución': 'institucion',
        'Instituci�n': 'institucion',
        'Siglas de la Institución': 'siglas_institucion',
        'Siglas de la Instituci�n': 'siglas_institucion',

        # Importes
        'Importe DRC': 'importe',
        'Monto sin imp./mínimo': 'importe_contrato',
        'Monto sin imp./m�nimo': 'importe_contrato',

        # Moneda
        'Moneda': 'moneda',

        # Fechas
        'Fecha de inicio del contrato': 'fecha_inicio_contrato',
        'Fecha de fin del contrato': 'fecha_fin_contrato',

        # Estatus
        'Estatus Contrato': 'estatus_contrato',

        # Dirección
        'Dirección del anuncio': 'direccion_anuncio',
        'Direcci�n del anuncio': 'direccion_anuncio',

        # Año
        'origen': 'anio_fuente',
    }

    def __init__(self):
        self.advertencias = []
        self.stats = {
            'rfc_intercambiados': 0,
            'rfc_vacios': 0,
            'importes_cero': 0,
            'codigos_generados': 0,
            'fechas_invalidas': 0
        }

    @staticmethod
    def detectar_encoding(file_path):
        """Detecta el encoding correcto del archivo CSV"""
        encodings = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252', 'iso-8859-1']

        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    f.read(1024)  # Leer primeros 1KB
                logger.info(f"Encoding detectado: {encoding}")
                return encoding
            except (UnicodeDecodeError, UnicodeError):
                continue

        logger.warning("No se pudo detectar encoding, usando utf-8 por defecto")
        return 'utf-8'

    def detectar_rfc_proveedor_intercambiados(self, rfc, proveedor):
        """Detecta si RFC y Proveedor están intercambiados y los corrige"""
        if not rfc or not proveedor:
            return rfc, proveedor

        rfc_str = str(rfc).strip()
        prov_str = str(proveedor).strip()

        # Si el "RFC" es muy largo (>20 chars), probablemente es el proveedor
        if len(rfc_str) > 20 and len(prov_str) <= 13:
            logger.warning(f"RFC/Proveedor intercambiados detectado: RFC={rfc_str[:30]}, Prov={prov_str}")
            self.stats['rfc_intercambiados'] += 1
            self.advertencias.append(f"RFC/Proveedor intercambiados corregidos: {prov_str}")
            return prov_str, rfc_str

        return rfc_str, prov_str

    def limpiar_texto(self, texto):
        """Limpia y normaliza texto"""
        if pd.isna(texto):
            return None
        texto = str(texto).strip()
        # Eliminar espacios múltiples
        texto = re.sub(r'\s+', ' ', texto)
        # Limpiar puntuación excesiva
        texto = re.sub(r'\.{3,}', '...', texto)
        return texto if texto else None

    def limpiar_rfc(self, rfc):
        """Limpia y valida RFC (permite NULL)"""
        if pd.isna(rfc) or not rfc:
            self.stats['rfc_vacios'] += 1
            return None

        rfc = str(rfc).strip().upper()
        # Remover caracteres especiales
        rfc = re.sub(r'[^A-Z0-9]', '', rfc)

        # Validar longitud (12-13 caracteres)
        if len(rfc) >= 12 and len(rfc) <= 13:
            return rfc

        # Si no cumple, advertir pero permitir
        if rfc:
            logger.warning(f"RFC con formato no estándar: {rfc}")
            return rfc

        return None

    def limpiar_importe(self, importe_str):
        """Convierte string de importe a número (permite cero)"""
        if pd.isna(importe_str):
            return None
        try:
            # Eliminar comas y espacios
            importe = str(importe_str).replace(',', '').replace(' ', '').strip()
            # Eliminar símbolo de moneda
            importe = re.sub(r'[$€£¥]', '', importe)
            valor = float(importe)

            # Advertir sobre ceros (pero permitir)
            if valor == 0:
                self.stats['importes_cero'] += 1

            # Permitir negativos pero advertir
            if valor < 0:
                logger.warning(f"Importe negativo detectado: {valor}")

            return valor
        except:
            return None

    def limpiar_fecha(self, fecha):
        """Convierte fecha a formato ISO (maneja múltiples formatos)"""
        if pd.isna(fecha):
            return None
        try:
            fecha_str = str(fecha).strip()

            # Formatos a intentar
            formatos = [
                '%d/%m/%Y',           # 01/09/2025
                '%Y-%m-%d',           # 2025-03-21
                '%d-%m-%Y',           # 21-03-2025
                '%Y/%m/%d',           # 2025/03/21
                '%Y-%m-%d %H:%M:%S',  # 2025-03-21 00:00:00
            ]

            for formato in formatos:
                try:
                    dt = datetime.strptime(fecha_str, formato)
                    return dt.date()
                except:
                    continue

            # Intentar con pandas
            return pd.to_datetime(fecha).date()
        except:
            self.stats['fechas_invalidas'] += 1
            return None

    def generar_codigo_contrato(self):
        """Genera un código único para contratos sin código"""
        timestamp = int(time.time())
        unique_id = uuid.uuid4().hex[:8].upper()
        codigo = f"AUTO_{timestamp}_{unique_id}"
        self.stats['codigos_generados'] += 1
        self.advertencias.append(f"Código generado automáticamente: {codigo}")
        return codigo

    def limpiar_dataframe(self, df):
        """Limpia todo el DataFrame"""
        logger.info(f"Iniciando limpieza de {len(df)} registros")
        logger.info(f"Columnas en CSV: {list(df.columns)[:10]}...")  # Mostrar primeras 10

        # Renombrar columnas según el mapeo
        df = df.rename(columns=self.COLUMN_MAPPING)

        logger.info(f"Columnas mapeadas: {[c for c in df.columns if c in self.COLUMN_MAPPING.values()]}")

        # Detectar y corregir RFC/Proveedor intercambiados
        if 'rfc' in df.columns and 'proveedor_contratista' in df.columns:
            df[['rfc', 'proveedor_contratista']] = df.apply(
                lambda row: pd.Series(self.detectar_rfc_proveedor_intercambiados(
                    row.get('rfc'), row.get('proveedor_contratista')
                )),
                axis=1
            )

        # Generar códigos para registros sin código
        if 'codigo_contrato' in df.columns:
            df['codigo_contrato'] = df['codigo_contrato'].apply(
                lambda x: x if pd.notna(x) and str(x).strip() else self.generar_codigo_contrato()
            )

        # Limpiar campos de texto
        text_columns = ['titulo_contrato', 'titulo_expediente', 'descripcion_contrato',
                       'tipo_contratacion', 'tipo_procedimiento', 'proveedor_contratista',
                       'institucion', 'siglas_institucion', 'estatus_contrato',
                       'direccion_anuncio', 'moneda']

        for col in text_columns:
            if col in df.columns:
                df[col] = df[col].apply(self.limpiar_texto)

        # Limpiar RFC
        if 'rfc' in df.columns:
            df['rfc'] = df['rfc'].apply(self.limpiar_rfc)

        # Limpiar importes
        if 'importe' in df.columns:
            df['importe'] = df['importe'].apply(self.limpiar_importe)

        if 'importe_contrato' in df.columns:
            df['importe_contrato'] = df['importe_contrato'].apply(
                lambda x: str(x).replace(',', '').strip() if pd.notna(x) else None
            )

        # Limpiar fechas
        if 'fecha_inicio_contrato' in df.columns:
            df['fecha_inicio_contrato'] = df['fecha_inicio_contrato'].apply(self.limpiar_fecha)

        if 'fecha_fin_contrato' in df.columns:
            df['fecha_fin_contrato'] = df['fecha_fin_contrato'].apply(self.limpiar_fecha)

        # Inferir año si no existe
        if 'anio_fuente' not in df.columns or df['anio_fuente'].isna().all():
            if 'fecha_inicio_contrato' in df.columns:
                df['anio_fuente'] = df['fecha_inicio_contrato'].apply(
                    lambda x: str(x.year) if pd.notna(x) else None
                )

        # Eliminar duplicados por codigo_contrato
        df = df.drop_duplicates(subset=['codigo_contrato'], keep='first')

        logger.info(f"Limpieza completada. {len(df)} registros válidos")
        logger.info(f"Estadísticas: {self.stats}")

        return df


# ============================================
# RUTAS DE AUTENTICACIÓN
# ============================================

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Página de login"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['logged_in'] = True
            session['username'] = username
            session.permanent = True
            logger.info(f"Login exitoso: {username}")
            return redirect(url_for('index'))
        else:
            logger.warning(f"Intento de login fallido: {username}")
            return render_template_string(LOGIN_TEMPLATE, error="Usuario o contraseña incorrectos")

    return render_template_string(LOGIN_TEMPLATE)


@app.route('/logout')
def logout():
    """Cerrar sesión"""
    username = session.get('username', 'unknown')
    session.clear()
    logger.info(f"Logout: {username}")
    return redirect(url_for('login'))


# ============================================
# RUTAS PRINCIPALES
# ============================================

@app.route('/')
@login_required
def index():
    """Página principal"""
    return render_template_string(ADMIN_TEMPLATE, username=session.get('username'))


@app.route('/api/stats', methods=['GET'])
@login_required
def get_stats():
    """Obtiene estadísticas de la base de datos"""
    try:
        db_session = Session()

        result = db_session.execute(text("SELECT COUNT(*) FROM contratos.contratos"))
        total_contratos = result.scalar()

        result = db_session.execute(text("SELECT MAX(anio_fuente) FROM contratos.contratos"))
        ultimo_anio = result.scalar()

        # Obtener fecha de última actualización (contratos más recientes agregados)
        result = db_session.execute(text("""
            SELECT MAX(fecha_inicio_contrato)
            FROM contratos.contratos
            WHERE fecha_inicio_contrato IS NOT NULL
        """))
        ultima_actualizacion = result.scalar()

        db_session.close()

        # Formatear fecha para mostrar
        fecha_formateada = None
        if ultima_actualizacion:
            fecha_formateada = ultima_actualizacion.strftime('%d/%m/%Y')

        return jsonify({
            'total_contratos': total_contratos or 0,
            'ultimo_anio': ultimo_anio,
            'ultima_actualizacion': fecha_formateada or 'Sin datos'
        })

    except Exception as e:
        logger.error(f"Error al obtener estadísticas: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/upload', methods=['POST'])
@login_required
def upload_file():
    """Sube y procesa un archivo CSV con limpieza inteligente"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No se proporcionó ningún archivo'}), 400

        file = request.files['file']

        if file.filename == '':
            return jsonify({'error': 'Nombre de archivo vacío'}), 400

        if not file.filename.endswith('.csv'):
            return jsonify({'error': 'El archivo debe ser CSV'}), 400

        username = session.get('username', 'unknown')
        logger.info(f"Procesando archivo: {file.filename} (usuario: {username})")

        # Guardar temporalmente
        temp_path = f"/tmp/{uuid.uuid4().hex}.csv"
        file.save(temp_path)

        # Detectar encoding
        encoding = DataCleaner.detectar_encoding(temp_path)

        # Leer CSV con encoding correcto
        try:
            df = pd.read_csv(temp_path, encoding=encoding)
        except Exception as e:
            # Intentar con encoding alternativo
            logger.warning(f"Error con {encoding}, intentando latin-1: {e}")
            df = pd.read_csv(temp_path, encoding='latin-1')

        logger.info(f"Archivo leído: {len(df)} filas, {len(df.columns)} columnas")

        # Limpiar datos
        cleaner = DataCleaner()
        df_limpio = cleaner.limpiar_dataframe(df)

        # Insertar en base de datos
        db_session = Session()
        registros_insertados = 0
        registros_duplicados = 0
        registros_con_errores = 0

        # Obtener solo las columnas que existen en el DataFrame limpio
        columnas_disponibles = [col for col in df_limpio.columns if col in DataCleaner.COLUMN_MAPPING.values()]

        logger.info(f"Columnas a insertar: {columnas_disponibles}")

        for _, row in df_limpio.iterrows():
            try:
                # Filtrar solo las columnas disponibles
                datos = {col: row[col] for col in columnas_disponibles if col in row.index and pd.notna(row[col])}

                if not datos.get('codigo_contrato'):
                    logger.error("Registro sin codigo_contrato, saltando")
                    registros_con_errores += 1
                    continue

                # Construir query dinámico
                columnas = ', '.join(datos.keys())
                placeholders = ', '.join([f":{col}" for col in datos.keys()])

                query = text(f"""
                    INSERT INTO contratos.contratos ({columnas})
                    VALUES ({placeholders})
                    ON CONFLICT (codigo_contrato, titulo_contrato, proveedor_contratista) DO NOTHING
                """)

                result = db_session.execute(query, datos)

                # Si rowcount es 0, fue duplicado
                if result.rowcount == 0:
                    registros_duplicados += 1
                else:
                    registros_insertados += 1

                # Commit cada 100 registros
                if (registros_insertados + registros_duplicados) % 100 == 0:
                    db_session.commit()
                    logger.info(f"Procesados {registros_insertados + registros_duplicados} registros")

            except Exception as e:
                logger.error(f"Error al insertar registro: {e}")
                registros_con_errores += 1

        db_session.commit()
        db_session.close()

        # Limpiar archivo temporal
        os.remove(temp_path)

        # Verificar/crear índices FTS para búsquedas rápidas
        verificar_indices_fts()

        # Preparar advertencias
        advertencias_lista = cleaner.advertencias[:10]  # Solo primeras 10
        if cleaner.stats['rfc_intercambiados'] > 0:
            advertencias_lista.append(f"{cleaner.stats['rfc_intercambiados']} RFC/Proveedor intercambiados corregidos")
        if cleaner.stats['rfc_vacios'] > 0:
            advertencias_lista.append(f"{cleaner.stats['rfc_vacios']} registros sin RFC")
        if cleaner.stats['importes_cero'] > 0:
            advertencias_lista.append(f"{cleaner.stats['importes_cero']} contratos con importe $0")
        if cleaner.stats['codigos_generados'] > 0:
            advertencias_lista.append(f"{cleaner.stats['codigos_generados']} códigos generados automáticamente")

        logger.info(f"Carga completada por {username}: {registros_insertados} nuevos, {registros_duplicados} duplicados, {registros_con_errores} errores")

        return jsonify({
            'message': 'Archivo procesado exitosamente',
            'registros_procesados': len(df_limpio),
            'registros_insertados': registros_insertados,
            'registros_duplicados': registros_duplicados,
            'registros_con_errores': registros_con_errores,
            'advertencias': advertencias_lista
        })

    except Exception as e:
        logger.error(f"Error al procesar archivo: {e}", exc_info=True)
        return jsonify({'error': str(e), 'detalles': 'Ver logs del servidor'}), 500


@app.route('/api/clear', methods=['POST'])
@login_required
def clear_duplicates():
    """Elimina registros duplicados conservando solo una copia de cada contrato"""
    try:
        username = session.get('username', 'unknown')
        db_session = Session()

        # Contar registros antes
        result = db_session.execute(text("SELECT COUNT(*) FROM contratos.contratos"))
        registros_totales = result.scalar()

        # Eliminar duplicados usando el índice compuesto (codigo_contrato, titulo_contrato, proveedor_contratista)
        # Conserva el registro con el ctid más pequeño (el más antiguo)
        query_delete = text("""
            DELETE FROM contratos.contratos
            WHERE ctid NOT IN (
                SELECT MIN(ctid)
                FROM contratos.contratos
                GROUP BY codigo_contrato, titulo_contrato, proveedor_contratista
            )
        """)

        result = db_session.execute(query_delete)
        registros_eliminados = result.rowcount

        db_session.commit()

        # Contar registros después
        result = db_session.execute(text("SELECT COUNT(*) FROM contratos.contratos"))
        registros_finales = result.scalar()

        db_session.close()

        duplicados_encontrados = registros_totales - registros_finales

        logger.warning(f"Duplicados eliminados por {username}: {registros_eliminados} de {duplicados_encontrados} duplicados")

        return jsonify({
            'message': 'Duplicados eliminados exitosamente',
            'registros_totales': registros_totales,
            'duplicados_encontrados': duplicados_encontrados,
            'registros_eliminados': registros_eliminados,
            'registros_finales': registros_finales
        })

    except Exception as e:
        logger.error(f"Error al eliminar duplicados: {e}")
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    port = int(os.getenv('ADMIN_PORT', 5001))

    print(f"""
    ==========================================
    Panel de Administración Iniciado
    ==========================================
    URL: http://localhost:{port}

    Credenciales:
    Usuario: {ADMIN_USERNAME}
    Contraseña: *** (configurada en .env)

    Características:
    ✓ Detección automática de encoding
    ✓ Corrección de RFC/Proveedor intercambiados
    ✓ Generación de códigos únicos
    ✓ Inserción solo de registros nuevos
    ✓ Validación inteligente de datos

    IMPORTANTE: Cambia las credenciales en
    producción (.env)
    ==========================================
    """)

    app.run(
        debug=True,
        host='0.0.0.0',
        port=port
    )
