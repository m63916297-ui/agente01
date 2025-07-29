# Agente Autónomo de Análisis y Síntesis de Documentación Técnica

## Descripción del Proyecto

Este proyecto implementa un agente de IA autónomo capaz de procesar documentación técnica desde URLs, entenderla y responder preguntas complejas sobre ella. El sistema utiliza LangGraph para orquestar el flujo de trabajo y expone su funcionalidad a través de una API RESTful.

## Arquitectura de la Solución

### Componentes Principales

1. **API RESTful (FastAPI)**: Interfaz principal para interactuar con el agente
2. **LangGraph Workflow**: Orquesta el flujo de procesamiento y respuesta
3. **Base de Datos Vectorial (ChromaDB)**: Almacena embeddings de la documentación
4. **Base de Datos SQLite**: Persiste conversaciones y estados de procesamiento
5. **Web Scraping**: Extrae contenido de URLs de documentación
6. **RAG Pipeline**: Recuperación y generación aumentada de respuestas

### Diagrama de Arquitectura

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Cliente       │    │   FastAPI       │    │   LangGraph     │
│   (Frontend)    │◄──►│   (API Layer)   │◄──►│   (Workflow)    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │                       │
                                ▼                       ▼
                       ┌─────────────────┐    ┌─────────────────┐
                       │   SQLite DB     │    │   ChromaDB      │
                       │   (Chat History)│    │   (Embeddings)  │
                       └─────────────────┘    └─────────────────┘
```

### Flujo de LangGraph

```
Input Node → Intent Analysis → Conditional Router
     ↓              ↓              ↓
Memory Node ← Response Gen ← RAG Node
     ↓              ↓              ↓
Code Format ← Output Node ← Context Builder
```

## Decisiones Técnicas

### Framework Backend: FastAPI
- **Rendimiento**: Alto rendimiento con async/await
- **Documentación automática**: OpenAPI/Swagger integrado
- **Validación**: Pydantic para validación de datos
- **Facilidad de desarrollo**: Sintaxis moderna y intuitiva

### Base de Datos: SQLite + ChromaDB
- **SQLite**: Para persistencia de conversaciones y estados
- **ChromaDB**: Base de datos vectorial para embeddings
- **Simplicidad**: No requiere configuración de servidor externo

### Modelos de IA
- **Embeddings**: sentence-transformers/all-MiniLM-L6-v2
- **LLM**: Ollama (llama3.2) para generación de respuestas
- **Análisis de intención**: Clasificador personalizado

## Instalación y Configuración

### Prerrequisitos

- Python 3.9+
- Ollama (para el modelo LLM)
- Git

### Instalación

1. **Clonar el repositorio**:
```bash
git clone <repository-url>
cd test-AI
```

2. **Crear entorno virtual**:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# o
venv\Scripts\activate     # Windows
```

3. **Instalar dependencias**:
```bash
pip install -r requirements.txt
```

4. **Configurar variables de entorno**:
```bash
cp .env.example .env
# Editar .env con tus configuraciones
```

5. **Inicializar base de datos**:
```bash
python scripts/init_db.py
```

6. **Ejecutar el servidor**:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Variables de Entorno

```env
# Base de datos
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
```

## Uso de la API

### 1. Procesar Documentación

```bash
curl -X POST "http://localhost:8000/api/v1/process-documentation" \
     -H "Content-Type: application/json" \
     -d '{
       "url": "https://docs.python.org/3/tutorial/",
       "chat_id": "chat_123"
     }'
```

### 2. Verificar Estado de Procesamiento

```bash
curl -X GET "http://localhost:8000/api/v1/processing-status/chat_123"
```

### 3. Hacer Preguntas

```bash
curl -X POST "http://localhost:8000/api/v1/chat/chat_123" \
     -H "Content-Type: application/json" \
     -d '{
       "message": "¿Cómo funciona la herencia en Python?",
       "user_id": "user_456"
     }'
```

### 4. Obtener Historial

```bash
curl -X GET "http://localhost:8000/api/v1/chat-history/chat_123"
```

## Estructura del Proyecto

```
test-AI/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI app
│   ├── config.py              # Configuraciones
│   ├── database.py            # Conexión a BD
│   ├── models/                # Modelos Pydantic
│   ├── api/                   # Endpoints de la API
│   ├── services/              # Lógica de negocio
│   ├── agents/                # Agentes LangGraph
│   ├── processors/            # Procesamiento de documentos
│   └── utils/                 # Utilidades
├── scripts/
│   └── init_db.py            # Inicialización de BD
├── tests/                    # Tests unitarios
├── requirements.txt          # Dependencias
├── .env.example             # Variables de entorno
└── README.md               # Este archivo
```

## Características Implementadas

### ✅ Funcionalidades Completadas

1. **API RESTful completa** con todos los endpoints requeridos
2. **LangGraph workflow** con nodos especializados
3. **Web scraping** inteligente con limpieza de HTML
4. **Segmentación semántica** de documentos
5. **Sistema RAG** personalizado con embeddings
6. **Análisis de intención** del usuario
7. **Memoria de conversación** persistente
8. **Formateo de código** automático
9. **Procesamiento asíncrono** de documentos
10. **Base de datos vectorial** para búsquedas semánticas

### 🔧 Componentes Técnicos

- **FastAPI**: Framework web moderno y rápido
- **LangGraph**: Orquestación de flujos de IA
- **ChromaDB**: Base de datos vectorial
- **SQLite**: Persistencia de datos
- **BeautifulSoup**: Web scraping
- **Sentence Transformers**: Generación de embeddings
- **Ollama**: Modelo de lenguaje local
- **Pydantic**: Validación de datos
- **AsyncIO**: Programación asíncrona

## Ejemplos de Uso

### Procesamiento de Documentación de Python

```python
import requests

# 1. Iniciar procesamiento
response = requests.post("http://localhost:8000/api/v1/process-documentation", json={
    "url": "https://docs.python.org/3/tutorial/",
    "chat_id": "python_docs_001"
})

# 2. Verificar estado
status = requests.get("http://localhost:8000/api/v1/processing-status/python_docs_001")

# 3. Hacer preguntas
question = requests.post("http://localhost:8000/api/v1/chat/python_docs_001", json={
    "message": "¿Cómo se define una función en Python?",
    "user_id": "user_123"
})
```

### Preguntas de Seguimiento

El agente mantiene contexto de la conversación, permitiendo preguntas como:
- "¿Puedes darme un ejemplo de lo anterior?"
- "¿Y cómo se aplica esto en clases?"
- "¿Cuál es la diferencia con otros lenguajes?"

## Contribución

1. Fork el proyecto
2. Crea una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

## Licencia

Este proyecto está bajo la Licencia MIT. Ver el archivo `LICENSE` para más detalles.