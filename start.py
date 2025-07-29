#!/usr/bin/env python3
"""
Script de inicio rápido para el Agente Autónomo de Documentación
"""

import os
import sys
import subprocess
import time
import requests
from pathlib import Path

def check_python_version():
    """Verifica la versión de Python"""
    if sys.version_info < (3, 9):
        print("❌ Error: Se requiere Python 3.9 o superior")
        print(f"Versión actual: {sys.version}")
        return False
    print(f"✅ Python {sys.version.split()[0]} detectado")
    return True

def check_ollama():
    """Verifica si Ollama está instalado y ejecutándose"""
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            models = response.json()
            print("✅ Ollama está ejecutándose")
            if models.get('models'):
                print(f"   Modelos disponibles: {[m['name'] for m in models['models']]}")
            else:
                print("   ⚠️  No hay modelos instalados")
            return True
        else:
            print("❌ Ollama no responde correctamente")
            return False
    except requests.exceptions.RequestException:
        print("❌ Ollama no está ejecutándose")
        print("   Instala Ollama desde: https://ollama.ai")
        print("   Luego ejecuta: ollama pull llama3.2")
        return False

def create_env_file():
    """Crea el archivo .env si no existe"""
    env_file = Path(".env")
    if not env_file.exists():
        print("📝 Creando archivo .env...")
        env_content = """# Base de datos
DATABASE_URL=sqlite:///./app.db

# ChromaDB
CHROMA_PERSIST_DIRECTORY=./chroma_db

# Ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2

# Configuración de la aplicación
MAX_TOKENS=4096
TEMPERATURE=0.7
CHUNK_SIZE=1000
CHUNK_OVERLAP=200

# Configuración de embeddings
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2

# Configuración de web scraping
REQUEST_TIMEOUT=30
MAX_RETRIES=3

# Configuración de la API
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=true
"""
        with open(env_file, 'w') as f:
            f.write(env_content)
        print("✅ Archivo .env creado")
    else:
        print("✅ Archivo .env ya existe")

def install_dependencies():
    """Instala las dependencias"""
    print("📦 Instalando dependencias...")
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], 
                      check=True, capture_output=True, text=True)
        print("✅ Dependencias instaladas")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error instalando dependencias: {e}")
        print(f"   Error: {e.stderr}")
        return False

def init_database():
    """Inicializa la base de datos"""
    print("🗄️  Inicializando base de datos...")
    try:
        subprocess.run([sys.executable, "scripts/init_db.py"], 
                      check=True, capture_output=True, text=True)
        print("✅ Base de datos inicializada")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error inicializando base de datos: {e}")
        print(f"   Error: {e.stderr}")
        return False

def start_server():
    """Inicia el servidor"""
    print("🚀 Iniciando servidor...")
    print("   El servidor estará disponible en: http://localhost:8000")
    print("   Documentación de la API: http://localhost:8000/docs")
    print("   Presiona Ctrl+C para detener el servidor")
    print("-" * 60)
    
    try:
        subprocess.run([sys.executable, "-m", "uvicorn", "app.main:app", 
                       "--host", "0.0.0.0", "--port", "8000", "--reload"])
    except KeyboardInterrupt:
        print("\n👋 Servidor detenido")

def run_tests():
    """Ejecuta los tests"""
    print("🧪 Ejecutando tests...")
    try:
        subprocess.run([sys.executable, "-m", "pytest", "tests/", "-v"], 
                      check=True, capture_output=True, text=True)
        print("✅ Tests pasaron")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Tests fallaron: {e}")
        print(f"   Error: {e.stderr}")
        return False

def main():
    """Función principal"""
    print("🚀 INICIO RÁPIDO - AGENTE AUTÓNOMO DE DOCUMENTACIÓN")
    print("=" * 60)
    
    # Verificar Python
    if not check_python_version():
        sys.exit(1)
    
    # Crear archivo .env
    create_env_file()
    
    # Verificar Ollama
    if not check_ollama():
        print("\n⚠️  Continuando sin Ollama (funcionalidad limitada)")
    
    # Instalar dependencias
    if not install_dependencies():
        sys.exit(1)
    
    # Inicializar base de datos
    if not init_database():
        sys.exit(1)
    
    # Ejecutar tests (opcional)
    run_tests_option = input("\n¿Ejecutar tests? (y/N): ").strip().lower()
    if run_tests_option in ['y', 'yes']:
        run_tests()
    
    print("\n" + "=" * 60)
    print("✅ CONFIGURACIÓN COMPLETADA")
    print("=" * 60)
    
    # Preguntar si iniciar el servidor
    start_option = input("\n¿Iniciar el servidor ahora? (Y/n): ").strip().lower()
    if start_option not in ['n', 'no']:
        start_server()
    else:
        print("\nPara iniciar el servidor manualmente:")
        print("   python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload")
        print("\nPara ejecutar la demostración:")
        print("   python examples/demo.py")

if __name__ == "__main__":
    main()