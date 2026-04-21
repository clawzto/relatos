# 🚀 Desplegar en Railway

Guía completa para publicar **Relatos IA** en Railway.

## 📋 Requisitos previos

1. **Cuenta en Railway** - https://railway.app
2. **Git instalado** y tu proyecto en un repositorio Git
3. **CLI de Railway** (opcional pero recomendado)
   ```bash
   npm install -g @railway/cli
   # o
   curl -fsSL https://railway.app/install.sh | bash
   ```

## ⚙️ Cambios ya realizados

✅ `Procfile` - Define cómo Railway inicia tu app
✅ `railway.json` - Configuración específica de Railway  
✅ `runtime.txt` - Especifica Python 3.11.8
✅ `requirements.txt` - Incluye `gunicorn` y `psycopg2-binary`
✅ `app.py` - Detecta automáticamente PostgreSQL o SQLite
✅ `.env.example` - Actualizado con todas las variables

---

## 🚀 Pasos para desplegar

### Opción 1: Desde la web (más fácil)

1. **Conecta GitHub a Railway**
   - Ve a https://railway.app
   - Click en "New Project" → "Deploy from GitHub"
   - Autoriza Railway y selecciona tu repositorio

2. **Railroad detectará automáticamente**
   - Lee el `Procfile`
   - Instala `requirements.txt`
   - Inicia con Gunicorn

3. **Configura Variables de Entorno**
   - En el panel de Railway: "Variables"
   - Añade:
     - `SECRET_KEY` = (genera una clave larga y aleatoria)
     - `OPENROUTER_API_KEY` = tu clave de OpenRouter
     - `OLLAMA_URL` = (si usas Ollama remoto)
     - `OPENWEBUI_URL` = (si usas Open WebUI remoto)
   
   **⚠️ IMPORTANTE:** Railway proporciona automáticamente `DATABASE_URL` si añades PostgreSQL

4. **Añade PostgreSQL** (recomendado)
   - En Railway: "+ Add Service" → "Provision PostgreSQL"
   - Railway inyectará automáticamente `DATABASE_URL`

### Opción 2: CLI de Railway (más rápido)

```bash
# 1. Loguearte
railway login

# 2. Conectar proyecto
cd /opt/lampp/htdocs/relatos
railway init

# 3. Selecciona el proyecto creado en Railway

# 4. Añade PostgreSQL
railway add postgresql

# 5. Configura variables (verás que DATABASE_URL ya existe)
railway variables set SECRET_KEY="tu-clave-aqui"
railway variables set OPENROUTER_API_KEY="sk-or-v1-..."
railway variables set OLLAMA_URL="http://..."

# 6. Despliega
railway up

# 7. Ver logs
railway logs
```

---

## 🗄️ Sobre la Base de Datos

| Entorno | BD | Comportamiento |
|---------|----|----|
| **Local** | SQLite | Archivo `relatos.db` en el proyecto |
| **Railway** | PostgreSQL | Automática si la añades; app lo detecta |

**La app es "inteligente":**
```python
if DATABASE_URL:
    # Usa PostgreSQL (Railway)
else:
    # Usa SQLite (local)
```

Si depligas en Railway SIN PostgreSQL:
- ⚠️ **Cada deploy perderá la BD** (filesystem efímero)
- ✅ **Añade PostgreSQL desde el panel de Railway**

---

## 📝 Migrando datos (si ya tienes relatos)

Si tienes datos en local que quieres preservar:

1. **Exporta como JSON**
   ```python
   python
   >>> from app import db, Relato, RelatoHumano, Capitulo
   >>> import json
   >>> relatos = [r.__dict__ for r in Relato.query.all()]
   >>> # Guarda a archivo...
   ```

2. **O usa Railway PostgreSQL desde local**
   - Cambia temporalmente `.env` con el `DATABASE_URL` de Railway
   - Ejecuta tu app local
   - Crea los datos en Railway

---

## 🔗 Variables de Entorno en Railway

**Automáticas (Railway las crea):**
- `DATABASE_URL` - Si añades PostgreSQL
- `PORT` - Puerto dinámico (5000-65535)
- `RAILWAY_ENVIRONMENT_NAME` - nombre del entorno

**Que TÚ debes configurar:**
- `SECRET_KEY` - Para Flask (usa generator: `python -c "import secrets; print(secrets.token_hex(32))"`)
- `OPENROUTER_API_KEY` - Tu API key de OpenRouter
- `OLLAMA_URL` - Si usas Ollama remoto
- `OPENWEBUI_URL` - Si usas Open WebUI remoto
- `OPENWEBUI_API_KEY` - Si Open WebUI requiere autenticación
- `FLASK_DEBUG` - "False" para producción (ya por defecto)

---

## 🧪 Testing antes de desplegar

```bash
# Local: simular entorno de Railway

# 1. Generar SECRET_KEY
python -c "import secrets; print('SECRET_KEY=' + secrets.token_hex(32))" >> .env.local

# 2. Instalar gunicorn localmente
pip install gunicorn

# 3. Ejecutar como lo hace Railway
gunicorn app:app

# 4. Visita http://localhost:8000
```

---

## 🐛 Troubleshooting

| Error | Solución |
|-------|----------|
| `ModuleNotFoundError: gunicorn` | Railway re-ejecutará `pip install -r requirements.txt` al desplegar |
| `Port already in use` | Railway usa variable `$PORT` automáticamente |
| `SQLALCHEMY_DATABASE_URI` no configurada | Asegúrate de que `DATABASE_URL` está en Railway (con PostgreSQL) |
| `Timeout conectando Ollama` | Ollama/Open WebUI locales no funcionan en Railway; usa externos o proxies |
| `Static files 404` | Flask sirve `static/` automáticamente si existe |

---

## ✅ Checklist antes de desplegar

- [ ] Git inicializado y commits realizados
- [ ] `Procfile`, `runtime.txt`, `railway.json` en root
- [ ] `requirements.txt` con `gunicorn`
- [ ] `.env.example` completo (sin valores secretos)
- [ ] `app.py` usa `PORT` de entorno
- [ ] `.gitignore` incluye `.env` y `relatos.db`
- [ ] PostgreSQL añadido en Railway (recomendado)
- [ ] Variables de entorno configuradas en Railway
- [ ] Test local: `gunicorn app:app` funciona

---

## 🔗 Recursos

- **Railway Docs:** https://docs.railway.app
- **Flask + Railway:** https://docs.railway.app/guides/flask
- **OpenRouter:** https://openrouter.ai
- **Ollama:** https://ollama.ai

¡A desplegar! 🎉
