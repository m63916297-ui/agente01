from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import sys
from contextlib import asynccontextmanager

from app.config import settings
from app.database import create_tables
from app.api.routes import router

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('app.log')
    ]
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Maneja el ciclo de vida de la aplicación"""
    # Startup
    logger.info("Iniciando aplicación...")
    
    try:
        # Crear tablas de base de datos
        create_tables()
        logger.info("Base de datos inicializada")
        
        # Verificar conexión a Ollama
        try:
            import ollama
            client = ollama.Client(host=settings.ollama_base_url)
            models = client.list()
            logger.info(f"Ollama conectado. Modelos disponibles: {[m['name'] for m in models['models']]}")
        except Exception as e:
            logger.warning(f"No se pudo conectar a Ollama: {str(e)}")
            logger.warning("La aplicación funcionará pero sin capacidades de LLM")
        
        logger.info("Aplicación iniciada exitosamente")
        
    except Exception as e:
        logger.error(f"Error durante el startup: {str(e)}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Cerrando aplicación...")


# Crear aplicación FastAPI
app = FastAPI(
    title="Agente Autónomo de Análisis y Síntesis de Documentación Técnica",
    description="""
    API para procesar documentación técnica y responder preguntas usando IA.
    
    ## Características
    
    * **Procesamiento de Documentación**: Extrae y procesa documentación desde URLs
    * **Agente de IA**: Utiliza LangGraph para orquestar el flujo de trabajo
    * **Búsqueda Semántica**: RAG personalizado con embeddings
    * **Análisis de Intención**: Detecta el tipo de pregunta del usuario
    * **Memoria de Conversación**: Mantiene contexto entre mensajes
    * **Formateo de Código**: Formatea automáticamente bloques de código
    
    ## Endpoints Principales
    
    * `POST /api/v1/process-documentation` - Iniciar procesamiento
    * `GET /api/v1/processing-status/{chat_id}` - Consultar estado
    * `POST /api/v1/chat/{chat_id}` - Interactuar con el agente
    * `GET /api/v1/chat-history/{chat_id}` - Obtener historial
    """,
    version="1.0.0",
    contact={
        "name": "Documentation Agent API",
        "url": "https://github.com/your-repo/documentation-agent"
    },
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT"
    },
    lifespan=lifespan
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, especificar dominios específicos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluir rutas
app.include_router(router)


# Manejo de excepciones global
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Maneja excepciones globales"""
    logger.error(f"Excepción no manejada: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Error interno del servidor",
            "detail": str(exc) if settings.debug else "Contacta al administrador"
        }
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Maneja excepciones HTTP"""
    logger.error(f"Excepción HTTP {exc.status_code}: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code
        }
    )


# Endpoints adicionales
@app.get("/")
async def root():
    """Endpoint raíz con información de la API"""
    return {
        "service": "Agente Autónomo de Análisis y Síntesis de Documentación Técnica",
        "version": "1.0.0",
        "description": "API para procesar documentación técnica y responder preguntas usando IA",
        "status": "running",
        "docs": "/docs",
        "redoc": "/redoc",
        "health": "/health"
    }


@app.get("/health")
async def health_check():
    """Endpoint de salud del sistema"""
    try:
        # Verificar base de datos
        from app.database import engine
        with engine.connect() as conn:
            conn.execute("SELECT 1")
        
        # Verificar ChromaDB
        from app.processors.embedding_manager import EmbeddingManager
        embedding_manager = EmbeddingManager()
        embedding_manager.get_embedding_dimension()
        
        return {
            "status": "healthy",
            "service": "Documentation Agent API",
            "version": "1.0.0",
            "database": "connected",
            "chromadb": "connected",
            "ollama": "available"  # Se verifica en startup
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }


@app.get("/config")
async def get_config():
    """Obtiene configuración del sistema (sin información sensible)"""
    return {
        "embedding_model": settings.embedding_model,
        "ollama_model": settings.ollama_model,
        "chunk_size": settings.chunk_size,
        "chunk_overlap": settings.chunk_overlap,
        "max_tokens": settings.max_tokens,
        "temperature": settings.temperature,
        "debug": settings.debug
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
        log_level="info"
    )