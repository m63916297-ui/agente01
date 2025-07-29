#!/usr/bin/env python3
"""
Script para inicializar la base de datos del Agente de Documentación
"""

import sys
import os
import logging

# Agregar el directorio raíz al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import create_tables, engine, SessionLocal
from app.config import settings

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def init_database():
    """Inicializa la base de datos"""
    try:
        logger.info("Inicializando base de datos...")
        
        # Crear tablas
        create_tables()
        logger.info("Tablas creadas exitosamente")
        
        # Verificar conexión
        with engine.connect() as conn:
            result = conn.execute("SELECT 1")
            logger.info("Conexión a base de datos verificada")
        
        logger.info("Base de datos inicializada correctamente")
        return True
        
    except Exception as e:
        logger.error(f"Error inicializando base de datos: {str(e)}")
        return False


def create_sample_data():
    """Crea datos de ejemplo (opcional)"""
    try:
        logger.info("Creando datos de ejemplo...")
        
        db = SessionLocal()
        
        # Aquí podrías agregar datos de ejemplo si es necesario
        # Por ejemplo, crear algunas sesiones de chat de prueba
        
        db.close()
        logger.info("Datos de ejemplo creados")
        
    except Exception as e:
        logger.error(f"Error creando datos de ejemplo: {str(e)}")


def main():
    """Función principal"""
    print("=" * 60)
    print("Inicialización de Base de Datos - Agente de Documentación")
    print("=" * 60)
    
    # Mostrar configuración
    print(f"Base de datos: {settings.database_url}")
    print(f"ChromaDB: {settings.chroma_persist_directory}")
    print(f"Ollama: {settings.ollama_base_url}")
    print()
    
    # Inicializar base de datos
    if init_database():
        print("✅ Base de datos inicializada correctamente")
        
        # Preguntar si crear datos de ejemplo
        response = input("\n¿Deseas crear datos de ejemplo? (y/N): ").strip().lower()
        if response in ['y', 'yes']:
            create_sample_data()
    else:
        print("❌ Error inicializando base de datos")
        sys.exit(1)
    
    print("\n" + "=" * 60)
    print("Inicialización completada")
    print("=" * 60)


if __name__ == "__main__":
    main()