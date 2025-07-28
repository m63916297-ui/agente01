from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    # Base de datos
    database_url: str = "sqlite:///./app.db"
    
    # ChromaDB
    chroma_persist_directory: str = "./chroma_db"
    
    # Ollama
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"
    
    # Configuración de la aplicación
    max_tokens: int = 4096
    temperature: float = 0.7
    chunk_size: int = 1000
    chunk_overlap: int = 200
    
    # Configuración de embeddings
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    
    # Configuración de web scraping
    request_timeout: int = 30
    max_retries: int = 3
    
    # Configuración de la API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    debug: bool = True
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Instancia global de configuración
settings = Settings()