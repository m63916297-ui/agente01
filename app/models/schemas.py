from pydantic import BaseModel, HttpUrl
from typing import List, Optional
from datetime import datetime


class ProcessDocumentationRequest(BaseModel):
    """Request para procesar documentación"""
    url: HttpUrl
    chat_id: str


class ProcessDocumentationResponse(BaseModel):
    """Response para procesar documentación"""
    chat_id: str
    status: str
    message: str
    created_at: datetime


class ProcessingStatusResponse(BaseModel):
    """Response para estado de procesamiento"""
    chat_id: str
    status: str
    progress: Optional[float] = None
    message: str
    created_at: datetime
    updated_at: datetime


class ChatRequest(BaseModel):
    """Request para chat"""
    message: str
    user_id: str


class ChatResponse(BaseModel):
    """Response para chat"""
    chat_id: str
    message: str
    response: str
    intent: Optional[str] = None
    created_at: datetime


class ChatMessageResponse(BaseModel):
    """Modelo para mensaje individual en historial"""
    id: int
    user_id: str
    message: str
    response: str
    intent: Optional[str] = None
    created_at: datetime


class ChatHistoryResponse(BaseModel):
    """Response para historial de chat"""
    chat_id: str
    messages: List[ChatMessageResponse]
    total_messages: int


class ErrorResponse(BaseModel):
    """Response para errores"""
    error: str
    detail: Optional[str] = None
    timestamp: datetime = datetime.utcnow()