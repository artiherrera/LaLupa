# app/auth/routes.py
from flask import render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, login_required, current_user
from app.auth import auth_bp
from app.models import Usuario, SesionActiva, LogAcceso, HistorialBusqueda
from app import db
from datetime import datetime
import secrets


def get_client_ip():
    """Obtiene la IP real del cliente"""
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    return request.remote_addr


def get_user_agent():
    """Obtiene el user agent del navegador"""
    return request.headers.get('User-Agent', '')[:500]


def registrar_log(usuario_id, tipo, exitoso=True, detalles=None):
    """Registra un evento de acceso"""
    log = LogAcceso(
        usuario_id=usuario_id,
        ip=get_client_ip(),
        user_agent=get_user_agent(),
        tipo=tipo,
        exitoso=exitoso,
        detalles=detalles
    )
    db.session.add(log)
    db.session.commit()


def crear_sesion(usuario):
    """Crea una nueva sesion y expulsa las anteriores (sesion unica)"""
    # Primero, expulsar todas las sesiones anteriores
    sesiones_anteriores = SesionActiva.query.filter_by(usuario_id=usuario.id).all()
    for sesion in sesiones_anteriores:
        # Registrar que fue expulsado
        registrar_log(
            usuario_id=usuario.id,
            tipo='expulsado',
            exitoso=True,
            detalles=f'Expulsado por nuevo login desde {get_client_ip()}'
        )
        db.session.delete(sesion)

    # Crear nueva sesion
    token = secrets.token_urlsafe(32)
    nueva_sesion = SesionActiva(
        usuario_id=usuario.id,
        token_sesion=token,
        ip=get_client_ip(),
        user_agent=get_user_agent()
    )
    db.session.add(nueva_sesion)
    db.session.commit()

    # Guardar token en la sesion de Flask
    session['token_sesion'] = token

    return token


def validar_sesion():
    """Valida que la sesion actual sea valida"""
    if not current_user.is_authenticated:
        return False

    token = session.get('token_sesion')
    if not token:
        return False

    sesion = SesionActiva.query.filter_by(
        usuario_id=current_user.id,
        token_sesion=token
    ).first()

    if not sesion:
        # La sesion fue invalidada (expulsado)
        logout_user()
        session.pop('token_sesion', None)
        return False

    # Actualizar ultima actividad
    sesion.actualizar_actividad()
    db.session.commit()

    return True


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Pagina de inicio de sesion"""
    # Si ya esta logueado, redirigir a inicio
    if current_user.is_authenticated:
        if validar_sesion():
            return redirect(url_for('main.index'))
        else:
            # Sesion invalida, hacer logout
            logout_user()

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        if not email or not password:
            flash('Por favor ingresa email y contrasena', 'error')
            return render_template('auth/login.html')

        usuario = Usuario.query.filter_by(email=email).first()

        if usuario is None or not usuario.check_password(password):
            # Registrar intento fallido
            if usuario:
                registrar_log(usuario.id, 'login_fallido', exitoso=False)
            flash('Email o contrasena incorrectos', 'error')
            return render_template('auth/login.html')

        if not usuario.activo:
            flash('Tu cuenta esta desactivada. Contacta al administrador.', 'error')
            return render_template('auth/login.html')

        # Login exitoso
        login_user(usuario, remember=True)

        # Crear sesion unica (expulsa las anteriores)
        crear_sesion(usuario)

        # Actualizar ultimo acceso
        usuario.ultimo_acceso = datetime.utcnow()
        db.session.commit()

        # Registrar login exitoso
        registrar_log(usuario.id, 'login', exitoso=True)

        flash(f'Bienvenido, {usuario.nombre}!', 'success')

        # Redirigir a la pagina solicitada o al inicio
        next_page = request.args.get('next')
        if next_page:
            return redirect(next_page)
        return redirect(url_for('main.index'))

    return render_template('auth/login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    """Cerrar sesion"""
    # Eliminar sesion activa
    token = session.get('token_sesion')
    if token:
        sesion = SesionActiva.query.filter_by(token_sesion=token).first()
        if sesion:
            db.session.delete(sesion)
            db.session.commit()

    # Registrar logout
    registrar_log(current_user.id, 'logout', exitoso=True)

    logout_user()
    session.pop('token_sesion', None)

    flash('Has cerrado sesion correctamente', 'success')
    return redirect(url_for('auth.login'))


@auth_bp.route('/mi-cuenta')
@login_required
def mi_cuenta():
    """Panel de usuario con historial de busquedas"""
    if not validar_sesion():
        flash('Tu sesion ha expirado o fue cerrada desde otro dispositivo', 'warning')
        return redirect(url_for('auth.login'))

    # Obtener historial de busquedas
    historial = HistorialBusqueda.query.filter_by(
        usuario_id=current_user.id
    ).order_by(HistorialBusqueda.fecha.desc()).limit(50).all()

    # Obtener log de accesos recientes
    accesos = LogAcceso.query.filter_by(
        usuario_id=current_user.id
    ).order_by(LogAcceso.fecha.desc()).limit(20).all()

    # Obtener sesion activa actual
    token = session.get('token_sesion')
    sesion_actual = SesionActiva.query.filter_by(token_sesion=token).first() if token else None

    return render_template(
        'auth/mi_cuenta.html',
        historial=historial,
        accesos=accesos,
        sesion_actual=sesion_actual
    )


@auth_bp.route('/cambiar-password', methods=['POST'])
@login_required
def cambiar_password():
    """Cambiar contraseña del usuario actual"""
    if not validar_sesion():
        flash('Tu sesion ha expirado', 'warning')
        return redirect(url_for('auth.login'))

    password_actual = request.form.get('password_actual', '')
    password_nueva = request.form.get('password_nueva', '')
    password_confirmar = request.form.get('password_confirmar', '')

    if not password_actual or not password_nueva or not password_confirmar:
        flash('Todos los campos son requeridos', 'error')
        return redirect(url_for('auth.mi_cuenta'))

    if not current_user.check_password(password_actual):
        flash('La contraseña actual es incorrecta', 'error')
        return redirect(url_for('auth.mi_cuenta'))

    if password_nueva != password_confirmar:
        flash('Las contraseñas nuevas no coinciden', 'error')
        return redirect(url_for('auth.mi_cuenta'))

    if len(password_nueva) < 6:
        flash('La contraseña debe tener al menos 6 caracteres', 'error')
        return redirect(url_for('auth.mi_cuenta'))

    current_user.set_password(password_nueva)
    db.session.commit()

    registrar_log(current_user.id, 'cambio_password', exitoso=True)
    flash('Contraseña actualizada correctamente', 'success')
    return redirect(url_for('auth.mi_cuenta'))


@auth_bp.route('/admin/usuarios')
@login_required
def admin_usuarios():
    """Panel de administracion de usuarios (solo admin)"""
    if not validar_sesion():
        flash('Tu sesion ha expirado', 'warning')
        return redirect(url_for('auth.login'))

    if not current_user.es_admin():
        flash('No tienes permisos para acceder a esta pagina', 'error')
        return redirect(url_for('main.index'))

    usuarios = Usuario.query.order_by(Usuario.fecha_creacion.desc()).all()

    return render_template('auth/admin_usuarios.html', usuarios=usuarios)


@auth_bp.route('/admin/usuarios/crear', methods=['GET', 'POST'])
@login_required
def crear_usuario():
    """Crear nuevo usuario (solo admin)"""
    if not validar_sesion():
        return redirect(url_for('auth.login'))

    if not current_user.es_admin():
        flash('No tienes permisos', 'error')
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        nombre = request.form.get('nombre', '').strip()
        password = request.form.get('password', '')
        rol = request.form.get('rol', 'usuario')

        if not email or not nombre or not password:
            flash('Todos los campos son requeridos', 'error')
            return render_template('auth/crear_usuario.html')

        if Usuario.query.filter_by(email=email).first():
            flash('Ya existe un usuario con ese email', 'error')
            return render_template('auth/crear_usuario.html')

        nuevo_usuario = Usuario(
            email=email,
            nombre=nombre,
            rol=rol
        )
        nuevo_usuario.set_password(password)

        db.session.add(nuevo_usuario)
        db.session.commit()

        flash(f'Usuario {email} creado exitosamente', 'success')
        return redirect(url_for('auth.admin_usuarios'))

    return render_template('auth/crear_usuario.html')


@auth_bp.route('/admin/usuarios/<int:id>/toggle')
@login_required
def toggle_usuario(id):
    """Activar/desactivar usuario (solo admin)"""
    if not validar_sesion():
        return redirect(url_for('auth.login'))

    if not current_user.es_admin():
        flash('No tienes permisos', 'error')
        return redirect(url_for('main.index'))

    usuario = Usuario.query.get_or_404(id)

    # No permitir desactivarse a si mismo
    if usuario.id == current_user.id:
        flash('No puedes desactivarte a ti mismo', 'error')
        return redirect(url_for('auth.admin_usuarios'))

    usuario.activo = not usuario.activo
    db.session.commit()

    estado = 'activado' if usuario.activo else 'desactivado'
    flash(f'Usuario {usuario.email} {estado}', 'success')

    return redirect(url_for('auth.admin_usuarios'))


@auth_bp.route('/admin/usuarios/<int:id>/historial')
@login_required
def ver_historial_usuario(id):
    """Ver historial de busquedas de un usuario (solo admin)"""
    if not validar_sesion():
        return redirect(url_for('auth.login'))

    if not current_user.es_admin():
        flash('No tienes permisos', 'error')
        return redirect(url_for('main.index'))

    usuario = Usuario.query.get_or_404(id)

    # Obtener historial de busquedas del usuario
    historial = HistorialBusqueda.query.filter_by(
        usuario_id=usuario.id
    ).order_by(HistorialBusqueda.fecha.desc()).limit(100).all()

    # Obtener log de accesos
    accesos = LogAcceso.query.filter_by(
        usuario_id=usuario.id
    ).order_by(LogAcceso.fecha.desc()).limit(50).all()

    return render_template(
        'auth/historial_usuario.html',
        usuario=usuario,
        historial=historial,
        accesos=accesos
    )


@auth_bp.route('/admin/historial-general')
@login_required
def historial_general():
    """Ver historial de busquedas de todos los usuarios (solo admin)"""
    if not validar_sesion():
        return redirect(url_for('auth.login'))

    if not current_user.es_admin():
        flash('No tienes permisos', 'error')
        return redirect(url_for('main.index'))

    # Obtener historial de todos los usuarios con join
    from sqlalchemy import desc
    historial = db.session.query(
        HistorialBusqueda, Usuario
    ).join(
        Usuario, HistorialBusqueda.usuario_id == Usuario.id
    ).order_by(
        desc(HistorialBusqueda.fecha)
    ).limit(200).all()

    return render_template(
        'auth/historial_general.html',
        historial=historial
    )


# Middleware para validar sesion en cada request
@auth_bp.before_app_request
def verificar_sesion_activa():
    """Verifica que la sesion sea valida en cada request"""
    if current_user.is_authenticated:
        # Rutas que no requieren validacion de sesion
        if request.endpoint and request.endpoint.startswith('static'):
            return

        token = session.get('token_sesion')
        if token:
            sesion = SesionActiva.query.filter_by(
                usuario_id=current_user.id,
                token_sesion=token
            ).first()

            if not sesion:
                # Sesion invalida - fue expulsado
                logout_user()
                session.pop('token_sesion', None)
                if request.endpoint != 'auth.login':
                    flash('Tu sesion fue cerrada porque iniciaste sesion en otro dispositivo', 'warning')
                    return redirect(url_for('auth.login'))
            else:
                # Actualizar ultima actividad
                sesion.actualizar_actividad()
                db.session.commit()
