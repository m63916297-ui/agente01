from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Dict, Any
import asyncio
import logging

from app.database import get_db
from app.models.schemas import (
    ProcessDocumentationRequest, ProcessDocumentationResponse,
    ProcessingStatusResponse, ChatRequest, ChatResponse,
    ChatHistoryResponse, ErrorResponse
)
from app.services.documentation_service import DocumentationService
from app.services.chat_service import ChatService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["Documentation Agent"])

# Instancias de servicios
documentation_service = DocumentationService()
chat_service = ChatService()


@router.post("/process-documentation", response_model=ProcessDocumentationResponse)
async def process_documentation(
    request: ProcessDocumentationRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Inicia el procesamiento asíncrono de documentación"""
    try:
        logger.info(f"Iniciando procesamiento de documentación: {request.url}")
        
        # Crear sesión de chat en la base de datos
        from app.database import ChatSession
        chat_session = ChatSession(
            chat_id=request.chat_id,
            url=str(request.url),
            status="pending"
        )
        db.add(chat_session)
        db.commit()
        
        # Agregar tarea de procesamiento al background
        background_tasks.add_task(
            process_documentation_background,
            str(request.url),
            request.chat_id,
            db
        )
        
        return ProcessDocumentationResponse(
            chat_id=request.chat_id,
            status="processing",
            message="Procesamiento iniciado. Puedes consultar el estado con GET /processing-status/{chat_id}",
            created_at=chat_session.created_at
        )
        
    except Exception as e:
        logger.error(f"Error iniciando procesamiento: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


async def process_documentation_background(url: str, chat_id: str, db: Session):
    """Tarea de background para procesar documentación"""
    try:
        await documentation_service.process_documentation(url, chat_id, db)
        logger.info(f"Procesamiento completado para {chat_id}")
    except Exception as e:
        logger.error(f"Error en procesamiento de background: {str(e)}")


@router.get("/processing-status/{chat_id}", response_model=ProcessingStatusResponse)
def get_processing_status(chat_id: str, db: Session = Depends(get_db)):
    """Obtiene el estado del procesamiento de documentación"""
    try:
        status_info = documentation_service.get_processing_status(chat_id, db)
        
        return ProcessingStatusResponse(
            chat_id=chat_id,
            status=status_info['status'],
            message=status_info['message'],
            created_at=status_info['created_at'],
            updated_at=status_info['updated_at']
        )
        
    except Exception as e:
        logger.error(f"Error obteniendo estado: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat/{chat_id}", response_model=ChatResponse)
def chat_with_agent(
    chat_id: str,
    request: ChatRequest,
    db: Session = Depends(get_db)
):
    """Interactúa con el agente una vez que la documentación ha sido procesada"""
    try:
        logger.info(f"Procesando mensaje de chat: {chat_id}")
        
        # Procesar mensaje con el agente
        response = chat_service.process_chat_message(
            chat_id=chat_id,
            user_message=request.message,
            user_id=request.user_id,
            db=db
        )
        
        return ChatResponse(
            chat_id=chat_id,
            message=request.message,
            response=response['response'],
            intent=response.get('intent'),
            created_at=response.get('timestamp', None)
        )
        
    except Exception as e:
        logger.error(f"Error en chat: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/chat-history/{chat_id}", response_model=ChatHistoryResponse)
def get_chat_history(
    chat_id: str,
    limit: int = None,
    db: Session = Depends(get_db)
):
    """Obtiene el historial de conversación"""
    try:
        history = chat_service.get_chat_history(chat_id, db, limit)
        
        # Convertir a formato de respuesta
        messages = []
        for msg in history['messages']:
            messages.append({
                'id': msg['id'],
                'user_id': msg['user_id'],
                'message': msg['message'],
                'response': msg['response'],
                'intent': msg['intent'],
                'created_at': msg['created_at']
            })
        
        return ChatHistoryResponse(
            chat_id=chat_id,
            messages=messages,
            total_messages=history['total_messages']
        )
        
    except Exception as e:
        logger.error(f"Error obteniendo historial: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/documentation-info/{chat_id}")
def get_documentation_info(chat_id: str, db: Session = Depends(get_db)):
    """Obtiene información sobre la documentación procesada"""
    try:
        info = documentation_service.get_documentation_info(chat_id, db)
        return info
    except Exception as e:
        logger.error(f"Error obteniendo información de documentación: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/chat-analytics/{chat_id}")
def get_chat_analytics(chat_id: str, db: Session = Depends(get_db)):
    """Obtiene análisis del chat"""
    try:
        analytics = chat_service.get_chat_analytics(chat_id, db)
        return analytics
    except Exception as e:
        logger.error(f"Error obteniendo analytics: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agent-info")
def get_agent_info():
    """Obtiene información sobre el agente"""
    try:
        info = chat_service.get_agent_info()
        return info
    except Exception as e:
        logger.error(f"Error obteniendo información del agente: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/chat/{chat_id}")
def delete_chat(chat_id: str, db: Session = Depends(get_db)):
    """Elimina un chat y toda su documentación"""
    try:
        # Eliminar historial de chat
        chat_deleted = chat_service.delete_chat_history(chat_id, db)
        
        # Eliminar documentación
        doc_deleted = documentation_service.delete_documentation(chat_id, db)
        
        return {
            "chat_id": chat_id,
            "chat_deleted": chat_deleted,
            "documentation_deleted": doc_deleted,
            "message": "Chat y documentación eliminados exitosamente"
        }
        
    except Exception as e:
        logger.error(f"Error eliminando chat: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
def health_check():
    """Endpoint de salud del sistema"""
    try:
        return {
            "status": "healthy",
            "service": "Documentation Agent API",
            "version": "1.0.0"
        }
    except Exception as e:
        logger.error(f"Error en health check: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/")
def root():
    """Endpoint raíz con información de la API"""
    return {
        "service": "Agente Autónomo de Análisis y Síntesis de Documentación Técnica",
        "version": "1.0.0",
        "description": "API para procesar documentación técnica y responder preguntas usando IA",
        "endpoints": {
            "POST /process-documentation": "Iniciar procesamiento de documentación",
            "GET /processing-status/{chat_id}": "Consultar estado de procesamiento",
            "POST /chat/{chat_id}": "Interactuar con el agente",
            "GET /chat-history/{chat_id}": "Obtener historial de conversación",
            "GET /documentation-info/{chat_id}": "Información de documentación procesada",
            "GET /chat-analytics/{chat_id}": "Análisis del chat",
            "GET /agent-info": "Información del agente",
            "DELETE /chat/{chat_id}": "Eliminar chat y documentación",
            "GET /health": "Estado de salud del sistema"
        },
        "docs": "/docs"
    }