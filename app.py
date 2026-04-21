"""
RELATOS IA - Flask App con Autenticación
Flask + SQLite/PostgreSQL + SQLAlchemy + Flask-Login + OpenRouter/Ollama/OpenWebUI
Abril 2026 - Santa Cruz de Tenerife

CARACTERÍSTICAS:
- Relatos IA (generados): GRATUITOS, acceso público
- Relatos Humanos: PRIVADOS, requieren autenticación
- Autenticación: Login/Registro
- Control de acceso: Solo usuarios autenticados pueden leer relatos humanos
- Lectura online: No se permite copiar/descargar
"""

import os
import requests
from datetime import datetime
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
from flask_login import LoginManager, current_user

login_manager = LoginManager()
login_manager.init_app(app)  # add_context_processor=True por defecto
login_manager.login_view = 'login'
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'relatos-ia-2026-super-secreta')

# Base de datos: PostgreSQL en Railway, SQLite localmente
DATABASE_URL = os.getenv('DATABASE_URL')
if DATABASE_URL:
    if DATABASE_URL.startswith('postgres://'):
        DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///relatos.db'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['PERMANENT_SESSION_LIFETIME'] = 30 * 24 * 60 * 60  # 30 días

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Debes iniciar sesión para acceder a esta página.'

# ──────────────────────────────────────────────
# MODELOS — Usuarios
# ──────────────────────────────────────────────

class Usuario(UserMixin, db.Model):
    """Modelo de usuario con autenticación."""
    id           = db.Column(db.Integer, primary_key=True)
    email        = db.Column(db.String(120), unique=True, nullable=False, index=True)
    nombre       = db.Column(db.String(120), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    suscrito     = db.Column(db.Boolean, default=False)  # Acceso a relatos humanos
    creado_en    = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relaciones
    relatos_humanos = db.relationship('RelatoHumano', backref='autor', lazy=True,
                                      foreign_keys='RelatoHumano.autor_id',
                                      cascade='all, delete-orphan')
    compras      = db.relationship('Acceso', backref='usuario', lazy=True,
                                   cascade='all, delete-orphan')

    def set_password(self, password):
        """Hashear y guardar contraseña."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Verificar contraseña."""
        return check_password_hash(self.password_hash, password)

    def puede_acceder_relato(self, relato_id):
        """Verificar si el usuario puede acceder a un relato humano."""
        if not self.suscrito:
            return False
        acceso = Acceso.query.filter_by(usuario_id=self.id, relato_id=relato_id).first()
        return acceso is not None

    def __repr__(self):
        return f'<Usuario {self.email}: {self.nombre}>'


@login_manager.user_loader
def load_user(user_id):
    return Usuario.query.get(int(user_id))


# ──────────────────────────────────────────────
# MODELOS — Relatos IA (GRATUITOS)
# ──────────────────────────────────────────────

class Relato(db.Model):
    """Relatos generados por IA - GRATUITOS."""
    id         = db.Column(db.Integer, primary_key=True)
    titulo     = db.Column(db.String(200), nullable=False)
    prompt     = db.Column(db.Text, nullable=False)
    contenido  = db.Column(db.Text, nullable=False)
    proveedor  = db.Column(db.String(50), default='openrouter')
    modelo     = db.Column(db.String(100), default='')
    creado_en  = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Relato {self.id}: {self.titulo[:40]}>'


# ──────────────────────────────────────────────
# MODELOS — Relatos Humanos (PRIVADOS)
# ──────────────────────────────────────────────

class RelatoHumano(db.Model):
    """Relatos de autores humanos - PRIVADOS."""
    id        = db.Column(db.Integer, primary_key=True)
    titulo    = db.Column(db.String(200), nullable=False)
    descripcion = db.Column(db.Text, default='')
    precio    = db.Column(db.Float, default=0.0)  # Precio de acceso
    autor_id  = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    creado_en = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relaciones
    capitulos = db.relationship('Capitulo', backref='relato', lazy=True,
                                order_by='Capitulo.orden', cascade='all, delete-orphan')
    accesos   = db.relationship('Acceso', backref='relato_humano', lazy=True,
                                cascade='all, delete-orphan')

    def __repr__(self):
        return f'<RelatoHumano {self.id}: {self.titulo[:40]}>'


class Capitulo(db.Model):
    """Capítulos de relatos humanos."""
    id         = db.Column(db.Integer, primary_key=True)
    relato_id  = db.Column(db.Integer, db.ForeignKey('relato_humano.id'), nullable=False)
    orden      = db.Column(db.Integer, default=1)
    titulo     = db.Column(db.String(200), nullable=False)
    contenido  = db.Column(db.Text, nullable=False)
    creado_en  = db.Column(db.DateTime, default=datetime.utcnow)


# ──────────────────────────────────────────────
# MODELOS — Control de Acceso
# ──────────────────────────────────────────────

class Acceso(db.Model):
    """Registro de acceso de usuarios a relatos humanos."""
    id         = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    relato_id  = db.Column(db.Integer, db.ForeignKey('relato_humano.id'), nullable=False)
    fecha_compra = db.Column(db.DateTime, default=datetime.utcnow)
    veces_leido = db.Column(db.Integer, default=0)
    ultima_lectura = db.Column(db.DateTime)

    __table_args__ = (db.UniqueConstraint('usuario_id', 'relato_id', name='uq_usuario_relato'),)

    def __repr__(self):
        return f'<Acceso {self.usuario_id}→{self.relato_id}>'


# ──────────────────────────────────────────────
# CONFIGURACIÓN — Proveedores de IA
# ──────────────────────────────────────────────

OPENROUTER_KEY = os.getenv('OPENROUTER_API_KEY', '')
OLLAMA_URL     = os.getenv('OLLAMA_URL', 'http://localhost:11434')
OPENWEBUI_URL  = os.getenv('OPENWEBUI_URL', 'http://localhost:3000')
OPENWEBUI_KEY  = os.getenv('OPENWEBUI_API_KEY', '')


def generar_openrouter(prompt: str, modelo: str = 'meta-llama/llama-3.1-8b-instruct') -> tuple:
    if not OPENROUTER_KEY:
        return None, 'OPENROUTER_API_KEY no configurada en .env'
    try:
        r = requests.post(
            'https://openrouter.ai/api/v1/chat/completions',
            headers={
                'Authorization': f'Bearer {OPENROUTER_KEY}',
                'Content-Type': 'application/json',
                'HTTP-Referer': 'https://relatos-ia.local',
                'X-Title': 'Relatos IA',
            },
            json={
                'model': modelo,
                'messages': [
                    {'role': 'system', 'content': 'Eres un escritor creativo en español. Escribe relatos originales, evocadores y bien estructurados.'},
                    {'role': 'user', 'content': f'Escribe un relato corto sobre: {prompt}'},
                ],
                'max_tokens': 1200,
            },
            timeout=60,
        )
        r.raise_for_status()
        return r.json()['choices'][0]['message']['content'], None
    except requests.exceptions.Timeout:
        return None, 'Tiempo de espera agotado (OpenRouter)'
    except requests.exceptions.RequestException as e:
        return None, f'Error de conexión (OpenRouter): {e}'
    except (KeyError, IndexError) as e:
        return None, f'Respuesta inesperada de OpenRouter: {e}'


def generar_ollama(prompt: str, modelo: str = 'llama3') -> tuple:
    try:
        r = requests.post(
            f'{OLLAMA_URL}/api/chat',
            json={
                'model': modelo,
                'messages': [
                    {'role': 'system', 'content': 'Eres un escritor creativo en español.'},
                    {'role': 'user', 'content': f'Escribe un relato corto sobre: {prompt}'},
                ],
                'stream': False,
            },
            timeout=120,
        )
        r.raise_for_status()
        return r.json()['message']['content'], None
    except requests.exceptions.ConnectionError:
        return None, f'No se puede conectar con Ollama en {OLLAMA_URL}. ¿Está corriendo?'
    except requests.exceptions.Timeout:
        return None, 'Tiempo de espera agotado (Ollama).'
    except Exception as e:
        return None, f'Error Ollama: {e}'


def generar_openwebui(prompt: str, modelo: str = 'llama3') -> tuple:
    headers = {'Content-Type': 'application/json'}
    if OPENWEBUI_KEY:
        headers['Authorization'] = f'Bearer {OPENWEBUI_KEY}'
    try:
        r = requests.post(
            f'{OPENWEBUI_URL}/api/chat/completions',
            headers=headers,
            json={
                'model': modelo,
                'messages': [
                    {'role': 'system', 'content': 'Eres un escritor creativo en español.'},
                    {'role': 'user', 'content': f'Escribe un relato corto sobre: {prompt}'},
                ],
            },
            timeout=120,
        )
        r.raise_for_status()
        return r.json()['choices'][0]['message']['content'], None
    except requests.exceptions.ConnectionError:
        return None, f'No se puede conectar con Open WebUI en {OPENWEBUI_URL}'
    except Exception as e:
        return None, f'Error Open WebUI: {e}'


PROVEEDORES = {
    'openrouter': generar_openrouter,
    'ollama':     generar_ollama,
    'openwebui':  generar_openwebui,
}

MODELOS_POR_PROVEEDOR = {
    'openrouter': [
        'meta-llama/llama-3.1-8b-instruct',
        'meta-llama/llama-3.3-70b-instruct',
        'mistralai/mistral-7b-instruct',
        'google/gemma-2-9b-it:free',
        'anthropic/claude-3-haiku',
    ],
    'ollama': ['llama3', 'mistral', 'phi3', 'gemma2', 'qwen2'],
    'openwebui': ['llama3', 'mistral', 'phi3'],
}


# ──────────────────────────────────────────────
# DECORADORES — Control de Acceso
# ──────────────────────────────────────────────

def requiere_acceso_relato(f):
    """Decorador: Verificar que el usuario tiene acceso al relato humano."""
    @wraps(f)
    def decorated_function(relato_id, *args, **kwargs):
        relato = RelatoHumano.query.get_or_404(relato_id)
        
        # Admin (autor) siempre puede
        if current_user.is_authenticated and current_user.id == relato.autor_id:
            return f(relato_id, *args, **kwargs)
        
        # Usuarios autenticados con acceso
        if current_user.is_authenticated and current_user.puede_acceder_relato(relato_id):
            # Registrar lectura
            acceso = Acceso.query.filter_by(usuario_id=current_user.id, relato_id=relato_id).first()
            if acceso:
                acceso.veces_leido += 1
                acceso.ultima_lectura = datetime.utcnow()
                db.session.commit()
            return f(relato_id, *args, **kwargs)
        
        # No tiene acceso
        flash('No tienes acceso a este relato. Suscríbete para leer relatos de autores.', 'warning')
        return redirect(url_for('landing'))
    
    return decorated_function


# ──────────────────────────────────────────────
# RUTAS — Autenticación
# ──────────────────────────────────────────────

@app.route('/landing')
def landing():
    """Página de bienvenida para invitados (home)."""
    relatos_ia = Relato.query.order_by(Relato.creado_en.desc()).limit(3).all()
    return render_template('landing.html', relatos_ia=relatos_ia)


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Iniciar sesión."""
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '').strip()
        
        if not email or not password:
            flash('Email y contraseña son obligatorios.', 'error')
            return redirect(url_for('login'))
        
        usuario = Usuario.query.filter_by(email=email).first()
        
        if not usuario or not usuario.check_password(password):
            flash('Email o contraseña incorrectos.', 'error')
            return redirect(url_for('login'))
        
        login_user(usuario, remember=True)
        flash(f'¡Bienvenido, {usuario.nombre}!', 'success')
        
        next_page = request.args.get('next')
        if not next_page or not url_has_allowed_host_and_scheme(next_page, request.host):
            next_page = url_for('index')
        return redirect(next_page)
    
    return render_template('login.html')


@app.route('/registro', methods=['GET', 'POST'])
def registro():
    """Registrar nuevo usuario."""
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        nombre = request.form.get('nombre', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '').strip()
        password2 = request.form.get('password2', '').strip()
        
        # Validaciones
        if not nombre or not email or not password:
            flash('Todos los campos son obligatorios.', 'error')
            return redirect(url_for('registro'))
        
        if password != password2:
            flash('Las contraseñas no coinciden.', 'error')
            return redirect(url_for('registro'))
        
        if len(password) < 6:
            flash('La contraseña debe tener al menos 6 caracteres.', 'error')
            return redirect(url_for('registro'))
        
        if Usuario.query.filter_by(email=email).first():
            flash('Este email ya está registrado.', 'error')
            return redirect(url_for('registro'))
        
        # Crear usuario
        usuario = Usuario(nombre=nombre, email=email)
        usuario.set_password(password)
        db.session.add(usuario)
        db.session.commit()
        
        login_user(usuario, remember=True)
        flash(f'¡Cuenta creada! Bienvenido, {nombre}.', 'success')
        return redirect(url_for('index'))
    
    return render_template('registro.html')


@app.route('/logout')
@login_required
def logout():
    """Cerrar sesión."""
    logout_user()
    flash('Has cerrado sesión.', 'info')
    return redirect(url_for('landing'))


# ──────────────────────────────────────────────
# RUTAS — Relatos IA (GRATUITOS)
# ──────────────────────────────────────────────

@app.route('/')
def index():
    """Home: relatos IA gratuitos."""
    if not current_user.is_authenticated:
        return redirect(url_for('landing'))
    
    relatos = Relato.query.order_by(Relato.creado_en.desc()).all()
    return render_template('index.html', relatos=relatos)


@app.route('/generar', methods=['GET', 'POST'])
def generar():
    """Generar nuevo relato con IA."""
    if request.method == 'POST':
        titulo    = request.form.get('titulo', '').strip()
        prompt    = request.form.get('prompt', '').strip()
        proveedor = request.form.get('proveedor', 'openrouter')
        modelo    = request.form.get('modelo', '').strip()

        if not titulo or not prompt:
            flash('El título y el prompt son obligatorios.', 'error')
            return redirect(url_for('generar'))

        fn_generar = PROVEEDORES.get(proveedor, generar_openrouter)
        contenido, error = fn_generar(prompt, modelo) if modelo else fn_generar(prompt)

        if error:
            flash(f'Error al generar: {error}', 'error')
            return redirect(url_for('generar'))

        relato = Relato(
            titulo=titulo,
            prompt=prompt,
            contenido=contenido,
            proveedor=proveedor,
            modelo=modelo,
        )
        db.session.add(relato)
        db.session.commit()
        flash('¡Relato generado con éxito!', 'success')
        return redirect(url_for('ver_relato', relato_id=relato.id))

    return render_template(
        'generar.html',
        modelos_por_proveedor=MODELOS_POR_PROVEEDOR,
    )


@app.route('/relato/<int:relato_id>')
def ver_relato(relato_id):
    """Ver relato IA."""
    relato = Relato.query.get_or_404(relato_id)
    return render_template('relato.html', relato=relato)


@app.route('/relato/<int:relato_id>/eliminar', methods=['POST'])
def eliminar_relato(relato_id):
    """Eliminar relato IA."""
    relato = Relato.query.get_or_404(relato_id)
    db.session.delete(relato)
    db.session.commit()
    flash('Relato eliminado.', 'info')
    return redirect(url_for('index'))


# ──────────────────────────────────────────────
# RUTAS — Relatos Humanos (PRIVADOS)
# ──────────────────────────────────────────────

@app.route('/humanos')
@login_required
def humanos_index():
    """Listado de relatos humanos disponibles."""
    # Admin ve todos, usuarios normales solo sus suscripciones
    if current_user.suscrito:
        # Relatos a los que tiene acceso
        accesos = db.session.query(Acceso.relato_id).filter_by(usuario_id=current_user.id).all()
        relatos_ids = [a[0] for a in accesos]
        relatos = RelatoHumano.query.filter(RelatoHumano.id.in_(relatos_ids)).order_by(RelatoHumano.creado_en.desc()).all()
    else:
        relatos = []
    
    return render_template('humanos/index.html', relatos=relatos)


@app.route('/humanos/nuevo', methods=['GET', 'POST'])
@login_required
def humanos_nuevo():
    """Crear nuevo relato humano (solo autores)."""
    if request.method == 'POST':
        titulo      = request.form.get('titulo', '').strip()
        descripcion = request.form.get('descripcion', '').strip()
        precio      = request.form.get('precio', '0.0').strip()
        
        if not titulo:
            flash('El título es obligatorio.', 'error')
            return redirect(url_for('humanos_nuevo'))
        
        try:
            precio = float(precio)
        except:
            precio = 0.0
        
        relato = RelatoHumano(
            titulo=titulo,
            descripcion=descripcion,
            precio=precio,
            autor_id=current_user.id
        )
        db.session.add(relato)
        db.session.commit()
        flash('Relato creado. Ahora añade el primer capítulo.', 'success')
        return redirect(url_for('humanos_ver', relato_id=relato.id))
    
    return render_template('humanos/nuevo.html')


@app.route('/humanos/<int:relato_id>')
@login_required
@requiere_acceso_relato
def humanos_ver(relato_id):
    """Ver relato humano (protegido)."""
    relato = RelatoHumano.query.get_or_404(relato_id)
    return render_template('humanos/ver.html', relato=relato)


@app.route('/humanos/<int:relato_id>/capitulo/nuevo', methods=['GET', 'POST'])
@login_required
def capitulo_nuevo(relato_id):
    """Añadir capítulo (solo autor)."""
    relato = RelatoHumano.query.get_or_404(relato_id)
    
    if relato.autor_id != current_user.id:
        flash('No tienes permiso para editar este relato.', 'error')
        return redirect(url_for('humanos_index'))
    
    if request.method == 'POST':
        titulo    = request.form.get('titulo', '').strip()
        contenido = request.form.get('contenido', '').strip()
        
        if not titulo or not contenido:
            flash('El título y el contenido son obligatorios.', 'error')
            return redirect(url_for('capitulo_nuevo', relato_id=relato_id))
        
        orden = len(relato.capitulos) + 1
        cap = Capitulo(relato_id=relato_id, titulo=titulo, contenido=contenido, orden=orden)
        db.session.add(cap)
        db.session.commit()
        flash(f'Capítulo {orden} añadido.', 'success')
        return redirect(url_for('humanos_ver', relato_id=relato_id))
    
    return render_template('humanos/capitulo_nuevo.html', relato=relato)


@app.route('/humanos/<int:relato_id>/capitulo/<int:cap_id>/editar', methods=['GET', 'POST'])
@login_required
def capitulo_editar(relato_id, cap_id):
    """Editar capítulo (solo autor)."""
    relato = RelatoHumano.query.get_or_404(relato_id)
    cap    = Capitulo.query.get_or_404(cap_id)
    
    if relato.autor_id != current_user.id:
        flash('No tienes permiso para editar este relato.', 'error')
        return redirect(url_for('humanos_index'))
    
    if request.method == 'POST':
        cap.titulo    = request.form.get('titulo', '').strip()
        cap.contenido = request.form.get('contenido', '').strip()
        db.session.commit()
        flash('Capítulo actualizado.', 'success')
        return redirect(url_for('humanos_ver', relato_id=relato_id))
    
    return render_template('humanos/capitulo_nuevo.html', relato=relato, cap=cap)


@app.route('/humanos/<int:relato_id>/capitulo/<int:cap_id>/eliminar', methods=['POST'])
@login_required
def capitulo_eliminar(relato_id, cap_id):
    """Eliminar capítulo (solo autor)."""
    relato = RelatoHumano.query.get_or_404(relato_id)
    
    if relato.autor_id != current_user.id:
        flash('No tienes permiso para editar este relato.', 'error')
        return redirect(url_for('humanos_index'))
    
    cap = Capitulo.query.get_or_404(cap_id)
    db.session.delete(cap)
    db.session.commit()
    
    # Reordenar
    for i, c in enumerate(relato.capitulos, 1):
        c.orden = i
    db.session.commit()
    
    flash('Capítulo eliminado.', 'info')
    return redirect(url_for('humanos_ver', relato_id=relato_id))


@app.route('/humanos/<int:relato_id>/eliminar', methods=['POST'])
@login_required
def humanos_eliminar(relato_id):
    """Eliminar relato (solo autor)."""
    relato = RelatoHumano.query.get_or_404(relato_id)
    
    if relato.autor_id != current_user.id:
        flash('No tienes permiso para eliminar este relato.', 'error')
        return redirect(url_for('humanos_index'))
    
    db.session.delete(relato)
    db.session.commit()
    flash('Relato eliminado.', 'info')
    return redirect(url_for('humanos_index'))


# ──────────────────────────────────────────────
# RUTAS — Admin (Temporal - para testing)
# ──────────────────────────────────────────────

@app.route('/admin/usuarios')
def admin_usuarios():
    """Admin: Listar usuarios y gestionar suscripciones."""
    if not current_user.is_authenticated or current_user.email != 'admin@relatos.local':
        flash('Acceso denegado.', 'error')
        return redirect(url_for('index'))
    
    usuarios = Usuario.query.all()
    return render_template('admin/usuarios.html', usuarios=usuarios)


# ──────────────────────────────────────────────
# UTILIDADES
# ──────────────────────────────────────────────

def url_has_allowed_host_and_scheme(url):
    """Validar que la URL es segura para redirect."""
    return url.startswith('/') or url.startswith('http')


# ──────────────────────────────────────────────
# INIT — Base de Datos
# ──────────────────────────────────────────────

with app.app_context():
    db.create_all()
    
    # Crear usuario admin si no existe
    if not Usuario.query.filter_by(email='admin@relatos.local').first():
        admin = Usuario(
            nombre='Admin',
            email='admin@relatos.local',
            suscrito=True
        )
        admin.set_password('admin123456')
        db.session.add(admin)
        db.session.commit()


if __name__ == '__main__':
    debug = os.getenv('FLASK_DEBUG', 'False') == 'True'
    port = int(os.getenv('PORT', 5000))
    app.run(debug=debug, host='0.0.0.0', port=port)
"""
RELATOS IA - Flask App Completa
Flask + SQLite + SQLAlchemy + OpenRouter / Ollama / Open WebUI
Abril 2026 - Santa Cruz de Tenerife
"""

import os
import requests
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'relatos-ia-2026-super-secreta')

# Base de datos: PostgreSQL en Railway, SQLite localmente
DATABASE_URL = os.getenv('DATABASE_URL')
if DATABASE_URL:
    # Railway o similar — PostgreSQL
    if DATABASE_URL.startswith('postgres://'):
        app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///relatos.db').replace('postgres://', 'postgresql://')
else:
    # Local development — SQLite
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///relatos.db'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ──────────────────────────────────────────────
# Modelo
# ──────────────────────────────────────────────

class Relato(db.Model):
    id         = db.Column(db.Integer, primary_key=True)
    titulo     = db.Column(db.String(200), nullable=False)
    prompt     = db.Column(db.Text, nullable=False)
    contenido  = db.Column(db.Text, nullable=False)
    proveedor  = db.Column(db.String(50), default='openrouter')
    modelo     = db.Column(db.String(100), default='')
    creado_en  = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Relato {self.id}: {self.titulo[:40]}>'

# ──────────────────────────────────────────────
# Proveedores de IA
# ──────────────────────────────────────────────

OPENROUTER_KEY = os.getenv('OPENROUTER_API_KEY', '')
OLLAMA_URL     = os.getenv('OLLAMA_URL', 'http://localhost:11434')
OPENWEBUI_URL  = os.getenv('OPENWEBUI_URL', 'http://localhost:3000')
OPENWEBUI_KEY  = os.getenv('OPENWEBUI_API_KEY', '')


def generar_openrouter(prompt: str, modelo: str = 'meta-llama/llama-3.1-8b-instruct') -> str:
    if not OPENROUTER_KEY:
        return None, 'OPENROUTER_API_KEY no configurada en .env'
    try:
        r = requests.post(
            'https://openrouter.ai/api/v1/chat/completions',
            headers={
                'Authorization': f'Bearer {OPENROUTER_KEY}',
                'Content-Type': 'application/json',
                'HTTP-Referer': 'https://relatos-ia.local',
                'X-Title': 'Relatos IA',
            },
            json={
                'model': modelo,
                'messages': [
                    {'role': 'system', 'content': 'Eres un escritor creativo en español. Escribe relatos originales, evocadores y bien estructurados.'},
                    {'role': 'user', 'content': f'Escribe un relato corto sobre: {prompt}'},
                ],
                'max_tokens': 1200,
            },
            timeout=60,
        )
        r.raise_for_status()
        return r.json()['choices'][0]['message']['content'], None
    except requests.exceptions.Timeout:
        return None, 'Tiempo de espera agotado (OpenRouter)'
    except requests.exceptions.RequestException as e:
        return None, f'Error de conexión (OpenRouter): {e}'
    except (KeyError, IndexError) as e:
        return None, f'Respuesta inesperada de OpenRouter: {e}'


def generar_ollama(prompt: str, modelo: str = 'llama3') -> str:
    try:
        r = requests.post(
            f'{OLLAMA_URL}/api/chat',
            json={
                'model': modelo,
                'messages': [
                    {'role': 'system', 'content': 'Eres un escritor creativo en español.'},
                    {'role': 'user', 'content': f'Escribe un relato corto sobre: {prompt}'},
                ],
                'stream': False,
            },
            timeout=120,
        )
        r.raise_for_status()
        return r.json()['message']['content'], None
    except requests.exceptions.ConnectionError:
        return None, f'No se puede conectar con Ollama en {OLLAMA_URL}. ¿Está corriendo?'
    except requests.exceptions.Timeout:
        return None, 'Tiempo de espera agotado (Ollama). Los modelos locales pueden ser lentos.'
    except Exception as e:
        return None, f'Error Ollama: {e}'


def generar_openwebui(prompt: str, modelo: str = 'llama3') -> str:
    headers = {'Content-Type': 'application/json'}
    if OPENWEBUI_KEY:
        headers['Authorization'] = f'Bearer {OPENWEBUI_KEY}'
    try:
        r = requests.post(
            f'{OPENWEBUI_URL}/api/chat/completions',
            headers=headers,
            json={
                'model': modelo,
                'messages': [
                    {'role': 'system', 'content': 'Eres un escritor creativo en español.'},
                    {'role': 'user', 'content': f'Escribe un relato corto sobre: {prompt}'},
                ],
            },
            timeout=120,
        )
        r.raise_for_status()
        return r.json()['choices'][0]['message']['content'], None
    except requests.exceptions.ConnectionError:
        return None, f'No se puede conectar con Open WebUI en {OPENWEBUI_URL}'
    except Exception as e:
        return None, f'Error Open WebUI: {e}'


PROVEEDORES = {
    'openrouter': generar_openrouter,
    'ollama':     generar_ollama,
    'openwebui':  generar_openwebui,
}

MODELOS_POR_PROVEEDOR = {
    'openrouter': [
        'meta-llama/llama-3.1-8b-instruct',
        'meta-llama/llama-3.3-70b-instruct',
        'mistralai/mistral-7b-instruct',
        'google/gemma-2-9b-it:free',
        'anthropic/claude-3-haiku',
    ],
    'ollama': ['llama3', 'mistral', 'phi3', 'gemma2', 'qwen2'],
    'openwebui': ['llama3', 'mistral', 'phi3'],
}

# ──────────────────────────────────────────────
# Rutas
# ──────────────────────────────────────────────

@app.route('/')
def index():
    relatos = Relato.query.order_by(Relato.creado_en.desc()).all()
    return render_template('index.html', relatos=relatos)


@app.route('/generar', methods=['GET', 'POST'])
def generar():
    if request.method == 'POST':
        titulo    = request.form.get('titulo', '').strip()
        prompt    = request.form.get('prompt', '').strip()
        proveedor = request.form.get('proveedor', 'openrouter')
        modelo    = request.form.get('modelo', '').strip()

        if not titulo or not prompt:
            flash('El título y el prompt son obligatorios.', 'error')
            return redirect(url_for('generar'))

        fn_generar = PROVEEDORES.get(proveedor, generar_openrouter)
        contenido, error = fn_generar(prompt, modelo) if modelo else fn_generar(prompt)

        if error:
            flash(f'Error al generar: {error}', 'error')
            return redirect(url_for('generar'))

        relato = Relato(
            titulo=titulo,
            prompt=prompt,
            contenido=contenido,
            proveedor=proveedor,
            modelo=modelo,
        )
        db.session.add(relato)
        db.session.commit()
        flash('¡Relato generado con éxito!', 'success')
        return redirect(url_for('ver_relato', relato_id=relato.id))

    return render_template(
        'generar.html',
        modelos_por_proveedor=MODELOS_POR_PROVEEDOR,
    )


@app.route('/relato/<int:relato_id>')
def ver_relato(relato_id):
    relato = Relato.query.get_or_404(relato_id)
    return render_template('relato.html', relato=relato)


@app.route('/relato/<int:relato_id>/eliminar', methods=['POST'])
def eliminar_relato(relato_id):
    relato = Relato.query.get_or_404(relato_id)
    db.session.delete(relato)
    db.session.commit()
    flash('Relato eliminado.', 'info')
    return redirect(url_for('index'))


# ──────────────────────────────────────────────
# Init DB y arranque
# ──────────────────────────────────────────────
# Modelos — Relatos Humanos
# ──────────────────────────────────────────────

class RelatoHumano(db.Model):
    id        = db.Column(db.Integer, primary_key=True)
    titulo    = db.Column(db.String(200), nullable=False)
    descripcion = db.Column(db.Text, default='')
    creado_en = db.Column(db.DateTime, default=datetime.utcnow)
    capitulos = db.relationship('Capitulo', backref='relato', lazy=True,
                                order_by='Capitulo.orden', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<RelatoHumano {self.id}: {self.titulo[:40]}>'


class Capitulo(db.Model):
    id         = db.Column(db.Integer, primary_key=True)
    relato_id  = db.Column(db.Integer, db.ForeignKey('relato_humano.id'), nullable=False)
    orden      = db.Column(db.Integer, default=1)
    titulo     = db.Column(db.String(200), nullable=False)
    contenido  = db.Column(db.Text, nullable=False)
    creado_en  = db.Column(db.DateTime, default=datetime.utcnow)


# ──────────────────────────────────────────────
# Rutas — Relatos Humanos
# ──────────────────────────────────────────────

@app.route('/humanos')
def humanos_index():
    relatos = RelatoHumano.query.order_by(RelatoHumano.creado_en.desc()).all()
    return render_template('humanos/index.html', relatos=relatos)


@app.route('/humanos/nuevo', methods=['GET', 'POST'])
def humanos_nuevo():
    if request.method == 'POST':
        titulo      = request.form.get('titulo', '').strip()
        descripcion = request.form.get('descripcion', '').strip()
        if not titulo:
            flash('El título es obligatorio.', 'error')
            return redirect(url_for('humanos_nuevo'))
        relato = RelatoHumano(titulo=titulo, descripcion=descripcion)
        db.session.add(relato)
        db.session.commit()
        flash('Relato creado. Ahora añade el primer capítulo.', 'success')
        return redirect(url_for('humanos_ver', relato_id=relato.id))
    return render_template('humanos/nuevo.html')


@app.route('/humanos/<int:relato_id>')
def humanos_ver(relato_id):
    relato = RelatoHumano.query.get_or_404(relato_id)
    return render_template('humanos/ver.html', relato=relato)


@app.route('/humanos/<int:relato_id>/capitulo/nuevo', methods=['GET', 'POST'])
def capitulo_nuevo(relato_id):
    relato = RelatoHumano.query.get_or_404(relato_id)
    if request.method == 'POST':
        titulo    = request.form.get('titulo', '').strip()
        contenido = request.form.get('contenido', '').strip()
        if not titulo or not contenido:
            flash('El título y el contenido son obligatorios.', 'error')
            return redirect(url_for('capitulo_nuevo', relato_id=relato_id))
        orden = len(relato.capitulos) + 1
        cap = Capitulo(relato_id=relato_id, titulo=titulo, contenido=contenido, orden=orden)
        db.session.add(cap)
        db.session.commit()
        flash(f'Capítulo {orden} añadido.', 'success')
        return redirect(url_for('humanos_ver', relato_id=relato_id))
    return render_template('humanos/capitulo_nuevo.html', relato=relato)


@app.route('/humanos/<int:relato_id>/capitulo/<int:cap_id>/editar', methods=['GET', 'POST'])
def capitulo_editar(relato_id, cap_id):
    relato = RelatoHumano.query.get_or_404(relato_id)
    cap    = Capitulo.query.get_or_404(cap_id)
    if request.method == 'POST':
        cap.titulo    = request.form.get('titulo', '').strip()
        cap.contenido = request.form.get('contenido', '').strip()
        db.session.commit()
        flash('Capítulo actualizado.', 'success')
        return redirect(url_for('humanos_ver', relato_id=relato_id))
    return render_template('humanos/capitulo_nuevo.html', relato=relato, cap=cap)


@app.route('/humanos/<int:relato_id>/capitulo/<int:cap_id>/eliminar', methods=['POST'])
def capitulo_eliminar(relato_id, cap_id):
    cap = Capitulo.query.get_or_404(cap_id)
    db.session.delete(cap)
    db.session.commit()
    # Reordenar
    relato = RelatoHumano.query.get_or_404(relato_id)
    for i, c in enumerate(relato.capitulos, 1):
        c.orden = i
    db.session.commit()
    flash('Capítulo eliminado.', 'info')
    return redirect(url_for('humanos_ver', relato_id=relato_id))


@app.route('/humanos/<int:relato_id>/eliminar', methods=['POST'])
def humanos_eliminar(relato_id):
    relato = RelatoHumano.query.get_or_404(relato_id)
    db.session.delete(relato)
    db.session.commit()
    flash('Relato eliminado.', 'info')
    return redirect(url_for('humanos_index'))


# ──────────────────────────────────────────────
# Modelos — Relatos Humanos
# ──────────────────────────────────────────────


with app.app_context():
    db.create_all()

if __name__ == '__main__':
    debug = os.getenv('FLASK_DEBUG', 'False') == 'True'
    port = int(os.getenv('PORT', 5000))
    app.run(debug=debug, host='0.0.0.0', port=port)
