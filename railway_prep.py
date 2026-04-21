#!/usr/bin/env python3
"""
Utilidades para preparar Relatos IA para Railway
"""
import secrets
import sys
import os
from pathlib import Path


def generar_secret_key():
    """Genera una SECRET_KEY segura para Flask."""
    key = secrets.token_hex(32)
    print(f"🔐 SECRET_KEY generada:\n{key}\n")
    print("👉 Cópiala y pégala en Railway → Variables")
    return key


def verificar_archivos():
    """Verifica que existan los archivos necesarios para Railway."""
    archivos_necesarios = [
        'Procfile',
        'runtime.txt',
        'railway.json',
        'requirements.txt',
        '.env.example',
        'app.py',
    ]
    
    root = Path(__file__).parent
    print("📋 Verificando archivos necesarios...\n")
    
    todos_ok = True
    for archivo in archivos_necesarios:
        ruta = root / archivo
        existe = ruta.exists()
        status = "✅" if existe else "❌"
        print(f"{status} {archivo}")
        if not existe:
            todos_ok = False
    
    if todos_ok:
        print("\n✅ ¡Todos los archivos están presentes!")
    else:
        print("\n❌ Faltan archivos. Ejecuta:")
        print("   git status")
    
    return todos_ok


def verificar_requirements():
    """Verifica que requirements.txt tenga las dependencias clave."""
    reqs_necesarios = ['flask', 'flask-sqlalchemy', 'gunicorn', 'psycopg2-binary']
    root = Path(__file__).parent
    req_file = root / 'requirements.txt'
    
    if not req_file.exists():
        print("❌ requirements.txt no encontrado")
        return False
    
    contenido = req_file.read_text()
    print("📦 Verificando dependencias en requirements.txt...\n")
    
    todos_ok = True
    for req in reqs_necesarios:
        existe = req.lower() in contenido.lower()
        status = "✅" if existe else "❌"
        print(f"{status} {req}")
        if not existe:
            todos_ok = False
    
    if not todos_ok:
        print("\n❌ Faltan dependencias. Ejecuta:")
        print("   pip install gunicorn psycopg2-binary")
        print("   pip freeze > requirements.txt")
    
    return todos_ok


def crear_env_local():
    """Crea un .env.local para testing local con variables de ejemplo."""
    root = Path(__file__).parent
    env_local = root / '.env.local'
    
    if env_local.exists():
        print("ℹ️  .env.local ya existe, no se sobrescribe")
        return
    
    secret_key = secrets.token_hex(32)
    
    contenido = f"""# Variables de entorno para testing LOCAL
SECRET_KEY={secret_key}
FLASK_DEBUG=True
OPENROUTER_API_KEY=sk-or-v1-xxx
OLLAMA_URL=http://localhost:11434
OPENWEBUI_URL=http://localhost:3000
"""
    
    env_local.write_text(contenido)
    print(f"✅ {env_local} creado con variables de ejemplo")


def mostrar_pasos():
    """Muestra los pasos para desplegar en Railway."""
    pasos = """
╔════════════════════════════════════════════════════════════════════╗
║  🚀 Pasos para desplegar en Railway                                ║
╚════════════════════════════════════════════════════════════════════╝

1️⃣  PUSH a GitHub (si aún no lo hiciste)
    $ git add -A
    $ git commit -m "Preparar para Railway"
    $ git push origin main

2️⃣  VE A RAILWAY
    https://railway.app
    Click: "New Project" → "Deploy from GitHub"

3️⃣  SELECCIONA TU REPOSITORIO
    Autoriza Railway y selecciona "relatos"

4️⃣  CONFIGURA VARIABLES DE ENTORNO
    En el panel de Railway: Variables
    
    • SECRET_KEY = [copia de aquí abajo]
    • OPENROUTER_API_KEY = sk-or-v1-tu-clave
    • OLLAMA_URL = http://... (si es remoto)
    • OPENWEBUI_URL = http://... (si es remoto)

5️⃣  AÑADE PostgreSQL (IMPORTANTE)
    En Railway: "+ Add Service" → "PostgreSQL"
    
    ℹ️  Automáticamente inyectará DATABASE_URL
    ℹ️  Si no lo haces, los datos se pierden en cada deploy

6️⃣  DEPLOY
    Railway detectará automáticamente tu Procfile
    Tu app estará en: https://tu-proyecto.railway.app

════════════════════════════════════════════════════════════════════════

🔐 Usa esta SECRET_KEY para Railway:
"""
    
    secret = secrets.token_hex(32)
    
    print(pasos)
    print(secret)
    print("\n📚 Documentación completa: RAILWAY.md")


def main():
    if len(sys.argv) > 1:
        comando = sys.argv[1].lower()
        
        if comando == 'secret':
            generar_secret_key()
        elif comando == 'check':
            print()
            verificar_archivos()
            print()
            verificar_requirements()
            print()
        elif comando == 'env':
            crear_env_local()
        elif comando == 'help':
            print("""
Utilidades para Railway:

    python railway_prep.py secret      → Generar SECRET_KEY
    python railway_prep.py check       → Verificar archivos
    python railway_prep.py env         → Crear .env.local
    python railway_prep.py steps       → Mostrar pasos
    python railway_prep.py help        → Esta ayuda
""")
        elif comando == 'steps':
            print()
            mostrar_pasos()
        else:
            print(f"Comando desconocido: {comando}")
            print("Usa: python railway_prep.py help")
    else:
        print()
        mostrar_pasos()
        print("\n" + "="*70)
        print()
        verificar_archivos()
        print()
        verificar_requirements()
        print()


if __name__ == '__main__':
    main()
