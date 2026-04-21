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
