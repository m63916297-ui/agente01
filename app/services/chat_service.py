from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from app.database import ChatMessage, ChatSession
from app.agents.workflow import DocumentationAgent
import logging
from datetime import datetime
import json

logger = logging.getLogger(__name__)


class ChatService:
    """Servicio para manejar el chat con el agente de documentación"""
    
    def __init__(self):
        self.agent = DocumentationAgent()
    
    def process_chat_message(self, chat_id: str, user_message: str, user_id: str, db: Session) -> Dict[str, Any]:
        """Procesa un mensaje de chat y retorna la respuesta"""
        try:
            logger.info(f"Procesando mensaje de chat: {chat_id}")
            
            # Verificar que la documentación esté procesada
            chat_session = db.query(ChatSession).filter(ChatSession.chat_id == chat_id).first()
            if not chat_session or chat_session.status != 'completed':
                return {
                    'chat_id': chat_id,
                    'response': "La documentación aún no ha sido procesada. Por favor, espera a que termine el procesamiento.",
                    'intent': 'error',
                    'confidence': 0.0,
                    'needs_clarification': False,
                    'error': 'Documentation not processed'
                }
            
            # Obtener historial de chat
            chat_history = self._get_chat_history(chat_id, db)
            
            # Procesar mensaje con el agente
            agent_response = self.agent.process_message(
                chat_id=chat_id,
                user_message=user_message,
                user_id=user_id,
                chat_history=chat_history
            )
            
            # Guardar mensaje en la base de datos
            self._save_chat_message(
                db=db,
                chat_id=chat_id,
                user_id=user_id,
                message=user_message,
                response=agent_response['response'],
                intent=agent_response.get('intent')
            )
            
            logger.info(f"Mensaje procesado exitosamente para {chat_id}")
            return agent_response
            
        except Exception as e:
            logger.error(f"Error procesando mensaje de chat: {str(e)}")
            return {
                'chat_id': chat_id,
                'response': "Lo siento, tuve un problema procesando tu mensaje. ¿Podrías intentar de nuevo?",
                'intent': 'error',
                'confidence': 0.0,
                'needs_clarification': False,
                'error': str(e)
            }
    
    def _get_chat_history(self, chat_id: str, db: Session) -> List[Dict[str, Any]]:
        """Obtiene el historial de chat desde la base de datos"""
        try:
            messages = db.query(ChatMessage).filter(
                ChatMessage.chat_id == chat_id
            ).order_by(ChatMessage.created_at.asc()).all()
            
            history = []
            for msg in messages:
                history.append({
                    'message': msg.message,
                    'response': msg.response,
                    'intent': msg.intent,
                    'timestamp': msg.created_at.isoformat() if msg.created_at else None
                })
            
            return history
            
        except Exception as e:
            logger.error(f"Error obteniendo historial de chat: {str(e)}")
            return []
    
    def _save_chat_message(self, db: Session, chat_id: str, user_id: str, message: str, response: str, intent: Optional[str] = None):
        """Guarda un mensaje de chat en la base de datos"""
        try:
            chat_message = ChatMessage(
                chat_id=chat_id,
                user_id=user_id,
                message=message,
                response=response,
                intent=intent
            )
            
            db.add(chat_message)
            db.commit()
            
            logger.info(f"Mensaje guardado en BD para {chat_id}")
            
        except Exception as e:
            logger.error(f"Error guardando mensaje en BD: {str(e)}")
            db.rollback()
            raise
    
    def get_chat_history(self, chat_id: str, db: Session, limit: Optional[int] = None) -> Dict[str, Any]:
        """Obtiene el historial completo de un chat"""
        try:
            query = db.query(ChatMessage).filter(ChatMessage.chat_id == chat_id).order_by(ChatMessage.created_at.desc())
            
            if limit:
                query = query.limit(limit)
            
            messages = query.all()
            
            # Convertir a formato de respuesta
            message_list = []
            for msg in reversed(messages):  # Ordenar por fecha ascendente
                message_list.append({
                    'id': msg.id,
                    'user_id': msg.user_id,
                    'message': msg.message,
                    'response': msg.response,
                    'intent': msg.intent,
                    'created_at': msg.created_at
                })
            
            return {
                'chat_id': chat_id,
                'messages': message_list,
                'total_messages': len(message_list)
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo historial de chat: {str(e)}")
            return {
                'chat_id': chat_id,
                'messages': [],
                'total_messages': 0,
                'error': str(e)
            }
    
    def get_chat_analytics(self, chat_id: str, db: Session) -> Dict[str, Any]:
        """Obtiene análisis del chat"""
        try:
            messages = db.query(ChatMessage).filter(ChatMessage.chat_id == chat_id).all()
            
            if not messages:
                return {
                    'chat_id': chat_id,
                    'total_messages': 0,
                    'intent_distribution': {},
                    'average_confidence': 0.0,
                    'most_common_topics': []
                }
            
            # Análisis de intenciones
            intent_counts = {}
            for msg in messages:
                intent = msg.intent or 'unknown'
                intent_counts[intent] = intent_counts.get(intent, 0) + 1
            
            # Calcular distribución de intenciones
            total_messages = len(messages)
            intent_distribution = {
                intent: {
                    'count': count,
                    'percentage': (count / total_messages) * 100
                }
                for intent, count in intent_counts.items()
            }
            
            # Análisis de temas (basado en palabras clave)
            topics = self._analyze_topics([msg.message for msg in messages])
            
            return {
                'chat_id': chat_id,
                'total_messages': total_messages,
                'intent_distribution': intent_distribution,
                'most_common_topics': topics,
                'first_message': messages[0].created_at if messages else None,
                'last_message': messages[-1].created_at if messages else None
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo analytics del chat: {str(e)}")
            return {
                'chat_id': chat_id,
                'error': str(e)
            }
    
    def _analyze_topics(self, messages: List[str]) -> List[Dict[str, Any]]:
        """Analiza temas comunes en los mensajes"""
        try:
            # Palabras clave para diferentes temas
            topic_keywords = {
                'código': ['código', 'code', 'función', 'function', 'clase', 'class', 'método', 'method'],
                'sintaxis': ['sintaxis', 'syntax', 'error', 'bug', 'compilar', 'compile'],
                'conceptos': ['concepto', 'concept', 'definición', 'definition', 'explicar', 'explain'],
                'ejemplos': ['ejemplo', 'example', 'caso', 'case', 'uso', 'use'],
                'configuración': ['configurar', 'configure', 'instalar', 'install', 'setup'],
                'API': ['api', 'endpoint', 'request', 'response', 'http', 'rest']
            }
            
            topic_counts = {topic: 0 for topic in topic_keywords.keys()}
            
            for message in messages:
                message_lower = message.lower()
                for topic, keywords in topic_keywords.items():
                    if any(keyword in message_lower for keyword in keywords):
                        topic_counts[topic] += 1
            
            # Ordenar por frecuencia
            sorted_topics = sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)
            
            return [
                {'topic': topic, 'count': count}
                for topic, count in sorted_topics if count > 0
            ]
            
        except Exception as e:
            logger.error(f"Error analizando temas: {str(e)}")
            return []
    
    def delete_chat_history(self, chat_id: str, db: Session) -> bool:
        """Elimina el historial de chat"""
        try:
            deleted_count = db.query(ChatMessage).filter(ChatMessage.chat_id == chat_id).delete()
            db.commit()
            
            logger.info(f"Eliminados {deleted_count} mensajes del chat {chat_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error eliminando historial de chat: {str(e)}")
            db.rollback()
            return False
    
    def get_agent_info(self) -> Dict[str, Any]:
        """Obtiene información sobre el agente"""
        try:
            workflow_info = self.agent.get_workflow_info()
            
            return {
                'agent_type': 'DocumentationAgent',
                'workflow': workflow_info,
                'capabilities': [
                    'Análisis de intención del usuario',
                    'Búsqueda semántica en documentación',
                    'Generación de respuestas contextuales',
                    'Formateo automático de código',
                    'Memoria de conversación',
                    'Solicitud de aclaraciones'
                ],
                'supported_intents': [
                    'code_question',
                    'follow_up', 
                    'general_question',
                    'clarification'
                ]
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo información del agente: {str(e)}")
            return {
                'error': str(e)
            }