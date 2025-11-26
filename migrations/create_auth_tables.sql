-- Script para crear tablas de autenticacion en DigitalOcean
-- Ejecutar en la consola de DigitalOcean (Database > Query)

-- 1. Crear tabla de usuarios
CREATE TABLE IF NOT EXISTS contratos.usuarios (
    id SERIAL PRIMARY KEY,
    email VARCHAR(120) UNIQUE NOT NULL,
    password_hash VARCHAR(256) NOT NULL,
    nombre VARCHAR(100) NOT NULL,
    rol VARCHAR(20) DEFAULT 'usuario',
    activo BOOLEAN DEFAULT TRUE,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ultimo_acceso TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_usuarios_email ON contratos.usuarios(email);

-- 2. Crear tabla de sesiones activas
CREATE TABLE IF NOT EXISTS contratos.sesiones_activas (
    id SERIAL PRIMARY KEY,
    usuario_id INTEGER NOT NULL REFERENCES contratos.usuarios(id) ON DELETE CASCADE,
    token_sesion VARCHAR(256) UNIQUE NOT NULL,
    ip VARCHAR(45),
    user_agent VARCHAR(500),
    fecha_inicio TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ultima_actividad TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_sesiones_usuario ON contratos.sesiones_activas(usuario_id);
CREATE INDEX IF NOT EXISTS idx_sesiones_token ON contratos.sesiones_activas(token_sesion);

-- 3. Crear tabla de historial de busquedas
CREATE TABLE IF NOT EXISTS contratos.historial_busquedas (
    id SERIAL PRIMARY KEY,
    usuario_id INTEGER NOT NULL REFERENCES contratos.usuarios(id) ON DELETE CASCADE,
    query TEXT NOT NULL,
    tipo_busqueda VARCHAR(50),
    filtros JSONB,
    resultados_count INTEGER,
    monto_total NUMERIC,
    tiempo_busqueda FLOAT,
    fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_historial_usuario ON contratos.historial_busquedas(usuario_id);
CREATE INDEX IF NOT EXISTS idx_historial_fecha ON contratos.historial_busquedas(fecha);

-- 4. Crear tabla de log de accesos
CREATE TABLE IF NOT EXISTS contratos.log_accesos (
    id SERIAL PRIMARY KEY,
    usuario_id INTEGER NOT NULL REFERENCES contratos.usuarios(id) ON DELETE CASCADE,
    ip VARCHAR(45),
    user_agent VARCHAR(500),
    fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    tipo VARCHAR(30),
    exitoso BOOLEAN DEFAULT TRUE,
    detalles TEXT
);

CREATE INDEX IF NOT EXISTS idx_log_usuario ON contratos.log_accesos(usuario_id);
CREATE INDEX IF NOT EXISTS idx_log_fecha ON contratos.log_accesos(fecha);

-- 5. Crear usuario administrador
INSERT INTO contratos.usuarios (email, password_hash, nombre, rol, activo)
VALUES (
    'arti.herrera@mail.com',
    'scrypt:32768:8:1$kUrOYWErLtvHdktN$41301107416bb8048106f8acc0d9daa3291ddfa2a5ab387fd8db0be32a84f7224fffb88dc2178eed720a15c3e3e585510b32a359d5ece4d37e271953c309f4e1',
    'Arturo Herrera',
    'admin',
    TRUE
) ON CONFLICT (email) DO NOTHING;
