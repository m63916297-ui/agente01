import asyncio
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from app.database import ChatSession, DocumentChunk
from app.processors.web_scraper import WebScraper
from app.processors.text_processor import TextProcessor
from app.processors.embedding_manager import EmbeddingManager
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class DocumentationService:
    """Servicio para procesar documentación técnica"""
    
    def __init__(self):
        self.web_scraper = WebScraper()
        self.text_processor = TextProcessor()
        self.embedding_manager = EmbeddingManager()
    
    async def process_documentation(self, url: str, chat_id: str, db: Session) -> Dict[str, Any]:
        """Procesa documentación desde una URL"""
        try:
            logger.info(f"Iniciando procesamiento de documentación: {url}")
            
            # Actualizar estado a processing
            self._update_processing_status(db, chat_id, "processing", "Procesando documentación...")
            
            # 1. Web scraping
            logger.info("Paso 1: Web scraping")
            document_data = await self.web_scraper.scrape_url(url)
            
            # 2. Procesamiento de texto
            logger.info("Paso 2: Procesamiento de texto")
            chunks = self.text_processor.process_document(document_data)
            
            # 3. Generar embeddings y almacenar
            logger.info("Paso 3: Generando embeddings")
            chunk_ids = self.embedding_manager.add_chunks(chat_id, chunks)
            
            # 4. Guardar chunks en base de datos
            logger.info("Paso 4: Guardando en base de datos")
            self._save_chunks_to_db(db, chat_id, chunks, chunk_ids)
            
            # 5. Actualizar estado a completed
            self._update_processing_status(db, chat_id, "completed", "Documentación procesada exitosamente")
            
            logger.info(f"Procesamiento completado: {len(chunks)} chunks procesados")
            
            return {
                'chat_id': chat_id,
                'status': 'completed',
                'url': url,
                'chunks_processed': len(chunks),
                'sections_found': len(document_data.get('sections', [])),
                'title': document_data.get('title', ''),
                'processed_at': datetime.utcnow()
            }
            
        except Exception as e:
            logger.error(f"Error procesando documentación: {str(e)}")
            self._update_processing_status(db, chat_id, "failed", f"Error: {str(e)}")
            raise
    
    def _update_processing_status(self, db: Session, chat_id: str, status: str, message: str):
        """Actualiza el estado de procesamiento en la base de datos"""
        try:
            chat_session = db.query(ChatSession).filter(ChatSession.chat_id == chat_id).first()
            
            if chat_session:
                chat_session.status = status
                chat_session.updated_at = datetime.utcnow()
                if status == "failed":
                    chat_session.error_message = message
            else:
                # Crear nueva sesión si no existe
                chat_session = ChatSession(
                    chat_id=chat_id,
                    url="",  # Se actualizará después
                    status=status
                )
                db.add(chat_session)
            
            db.commit()
            logger.info(f"Estado actualizado para {chat_id}: {status}")
            
        except Exception as e:
            logger.error(f"Error actualizando estado: {str(e)}")
            db.rollback()
    
    def _save_chunks_to_db(self, db: Session, chat_id: str, chunks: List[Dict], chunk_ids: List[str]):
        """Guarda chunks en la base de datos"""
        try:
            for i, chunk in enumerate(chunks):
                db_chunk = DocumentChunk(
                    chat_id=chat_id,
                    content=chunk['content'],
                    metadata=str(chunk.get('metadata', {})),  # Convertir a string
                    embedding_id=chunk_ids[i] if i < len(chunk_ids) else None
                )
                db.add(db_chunk)
            
            db.commit()
            logger.info(f"Guardados {len(chunks)} chunks en BD para {chat_id}")
            
        except Exception as e:
            logger.error(f"Error guardando chunks en BD: {str(e)}")
            db.rollback()
            raise
    
    def get_processing_status(self, chat_id: str, db: Session) -> Dict[str, Any]:
        """Obtiene el estado de procesamiento"""
        try:
            chat_session = db.query(ChatSession).filter(ChatSession.chat_id == chat_id).first()
            
            if not chat_session:
                return {
                    'chat_id': chat_id,
                    'status': 'not_found',
                    'message': 'Sesión no encontrada',
                    'created_at': None,
                    'updated_at': None
                }
            
            return {
                'chat_id': chat_id,
                'status': chat_session.status,
                'message': chat_session.error_message if chat_session.status == 'failed' else 'Procesamiento normal',
                'created_at': chat_session.created_at,
                'updated_at': chat_session.updated_at,
                'url': chat_session.url
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo estado: {str(e)}")
            return {
                'chat_id': chat_id,
                'status': 'error',
                'message': f'Error: {str(e)}',
                'created_at': None,
                'updated_at': None
            }
    
    def get_documentation_info(self, chat_id: str, db: Session) -> Dict[str, Any]:
        """Obtiene información sobre la documentación procesada"""
        try:
            # Obtener información de ChromaDB
            collection_info = self.embedding_manager.get_collection_info(chat_id)
            
            # Obtener chunks de la base de datos
            chunks = db.query(DocumentChunk).filter(DocumentChunk.chat_id == chat_id).all()
            
            # Obtener sesión de chat
            chat_session = db.query(ChatSession).filter(ChatSession.chat_id == chat_id).first()
            
            return {
                'chat_id': chat_id,
                'url': chat_session.url if chat_session else None,
                'status': chat_session.status if chat_session else 'unknown',
                'total_chunks': len(chunks),
                'vector_collection_info': collection_info,
                'processed_at': chat_session.created_at if chat_session else None,
                'last_updated': chat_session.updated_at if chat_session else None
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo información de documentación: {str(e)}")
            return {
                'chat_id': chat_id,
                'error': str(e)
            }
    
    def delete_documentation(self, chat_id: str, db: Session) -> bool:
        """Elimina toda la documentación de un chat"""
        try:
            # Eliminar de ChromaDB
            self.embedding_manager.delete_collection(chat_id)
            
            # Eliminar chunks de la base de datos
            db.query(DocumentChunk).filter(DocumentChunk.chat_id == chat_id).delete()
            
            # Eliminar sesión de chat
            db.query(ChatSession).filter(ChatSession.chat_id == chat_id).delete()
            
            db.commit()
            logger.info(f"Documentación eliminada para {chat_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error eliminando documentación: {str(e)}")
            db.rollback()
            return False
    
    async def process_multiple_urls(self, urls: List[str], chat_id: str, db: Session) -> Dict[str, Any]:
        """Procesa múltiples URLs de documentación"""
        try:
            logger.info(f"Procesando múltiples URLs para {chat_id}: {len(urls)} URLs")
            
            results = []
            total_chunks = 0
            
            for i, url in enumerate(urls):
                try:
                    # Crear chat_id único para cada URL
                    url_chat_id = f"{chat_id}_url_{i}"
                    
                    # Procesar URL individual
                    result = await self.process_documentation(url, url_chat_id, db)
                    results.append(result)
                    total_chunks += result['chunks_processed']
                    
                except Exception as e:
                    logger.error(f"Error procesando URL {url}: {str(e)}")
                    results.append({
                        'url': url,
                        'status': 'failed',
                        'error': str(e)
                    })
            
            return {
                'chat_id': chat_id,
                'total_urls': len(urls),
                'successful_urls': len([r for r in results if r.get('status') == 'completed']),
                'failed_urls': len([r for r in results if r.get('status') == 'failed']),
                'total_chunks': total_chunks,
                'results': results
            }
            
        except Exception as e:
            logger.error(f"Error procesando múltiples URLs: {str(e)}")
            raise