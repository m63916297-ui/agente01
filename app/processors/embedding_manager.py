import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Any, Optional
import json
import logging
from app.config import settings

logger = logging.getLogger(__name__)


class EmbeddingManager:
    """Gestor de embeddings para ChromaDB"""
    
    def __init__(self):
        self.embedding_model = SentenceTransformer(settings.embedding_model)
        self.client = chromadb.PersistentClient(
            path=settings.chroma_persist_directory,
            settings=Settings(anonymized_telemetry=False)
        )
        self.collections = {}
    
    def get_or_create_collection(self, chat_id: str) -> chromadb.Collection:
        """Obtiene o crea una colección para un chat específico"""
        if chat_id not in self.collections:
            try:
                collection = self.client.get_collection(chat_id)
                logger.info(f"Colección existente cargada: {chat_id}")
            except:
                collection = self.client.create_collection(
                    name=chat_id,
                    metadata={"description": f"Documentación para chat {chat_id}"}
                )
                logger.info(f"Nueva colección creada: {chat_id}")
            
            self.collections[chat_id] = collection
        
        return self.collections[chat_id]
    
    def add_chunks(self, chat_id: str, chunks: List[Dict[str, Any]]) -> List[str]:
        """Agrega chunks a la base de datos vectorial"""
        if not chunks:
            return []
        
        collection = self.get_or_create_collection(chat_id)
        
        # Preparar datos para ChromaDB
        documents = []
        metadatas = []
        ids = []
        
        for i, chunk in enumerate(chunks):
            documents.append(chunk['content'])
            metadatas.append(chunk['metadata'])
            ids.append(f"chunk_{chat_id}_{i}")
        
        # Generar embeddings y agregar a la colección
        try:
            collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            logger.info(f"Agregados {len(chunks)} chunks a la colección {chat_id}")
            return ids
        except Exception as e:
            logger.error(f"Error agregando chunks a ChromaDB: {str(e)}")
            raise
    
    def search_similar(self, chat_id: str, query: str, n_results: int = 5) -> List[Dict[str, Any]]:
        """Busca chunks similares a una consulta"""
        try:
            collection = self.get_or_create_collection(chat_id)
            
            # Realizar búsqueda
            results = collection.query(
                query_texts=[query],
                n_results=n_results,
                include=['documents', 'metadatas', 'distances']
            )
            
            # Formatear resultados
            formatted_results = []
            if results['documents'] and results['documents'][0]:
                for i, doc in enumerate(results['documents'][0]):
                    formatted_results.append({
                        'content': doc,
                        'metadata': results['metadatas'][0][i] if results['metadatas'] and results['metadatas'][0] else {},
                        'distance': results['distances'][0][i] if results['distances'] and results['distances'][0] else 0.0,
                        'relevance_score': 1.0 - (results['distances'][0][i] if results['distances'] and results['distances'][0] else 0.0)
                    })
            
            logger.info(f"Búsqueda completada para {chat_id}: {len(formatted_results)} resultados")
            return formatted_results
            
        except Exception as e:
            logger.error(f"Error en búsqueda vectorial: {str(e)}")
            return []
    
    def search_by_metadata(self, chat_id: str, metadata_filter: Dict[str, Any], n_results: int = 10) -> List[Dict[str, Any]]:
        """Busca chunks por filtros de metadata"""
        try:
            collection = self.get_or_create_collection(chat_id)
            
            # Construir filtro de metadata para ChromaDB
            where_filter = {}
            for key, value in metadata_filter.items():
                where_filter[f"metadata.{key}"] = value
            
            results = collection.query(
                query_texts=[""],  # Query vacía para filtrar solo por metadata
                n_results=n_results,
                where=where_filter,
                include=['documents', 'metadatas']
            )
            
            formatted_results = []
            if results['documents'] and results['documents'][0]:
                for i, doc in enumerate(results['documents'][0]):
                    formatted_results.append({
                        'content': doc,
                        'metadata': results['metadatas'][0][i] if results['metadatas'] and results['metadatas'][0] else {}
                    })
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"Error en búsqueda por metadata: {str(e)}")
            return []
    
    def search_code_blocks(self, chat_id: str, query: str, language: Optional[str] = None) -> List[Dict[str, Any]]:
        """Busca específicamente bloques de código"""
        try:
            collection = self.get_or_create_collection(chat_id)
            
            # Construir filtro para bloques de código
            where_filter = {"metadata.type": "code_block"}
            if language:
                where_filter["metadata.language"] = language
            
            results = collection.query(
                query_texts=[query],
                n_results=5,
                where=where_filter,
                include=['documents', 'metadatas', 'distances']
            )
            
            formatted_results = []
            if results['documents'] and results['documents'][0]:
                for i, doc in enumerate(results['documents'][0]):
                    formatted_results.append({
                        'content': doc,
                        'metadata': results['metadatas'][0][i] if results['metadatas'] and results['metadatas'][0] else {},
                        'distance': results['distances'][0][i] if results['distances'] and results['distances'][0] else 0.0,
                        'relevance_score': 1.0 - (results['distances'][0][i] if results['distances'] and results['distances'][0] else 0.0)
                    })
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"Error en búsqueda de código: {str(e)}")
            return []
    
    def delete_collection(self, chat_id: str) -> bool:
        """Elimina una colección completa"""
        try:
            if chat_id in self.collections:
                del self.collections[chat_id]
            
            self.client.delete_collection(chat_id)
            logger.info(f"Colección eliminada: {chat_id}")
            return True
        except Exception as e:
            logger.error(f"Error eliminando colección {chat_id}: {str(e)}")
            return False
    
    def get_collection_info(self, chat_id: str) -> Dict[str, Any]:
        """Obtiene información sobre una colección"""
        try:
            collection = self.get_or_create_collection(chat_id)
            count = collection.count()
            
            return {
                'chat_id': chat_id,
                'document_count': count,
                'name': collection.name,
                'metadata': collection.metadata
            }
        except Exception as e:
            logger.error(f"Error obteniendo información de colección {chat_id}: {str(e)}")
            return {
                'chat_id': chat_id,
                'document_count': 0,
                'error': str(e)
            }
    
    def update_chunk(self, chat_id: str, chunk_id: str, new_content: str, new_metadata: Dict[str, Any]) -> bool:
        """Actualiza un chunk existente"""
        try:
            collection = self.get_or_create_collection(chat_id)
            
            collection.update(
                ids=[chunk_id],
                documents=[new_content],
                metadatas=[new_metadata]
            )
            
            logger.info(f"Chunk actualizado: {chunk_id}")
            return True
        except Exception as e:
            logger.error(f"Error actualizando chunk {chunk_id}: {str(e)}")
            return False
    
    def get_embedding_dimension(self) -> int:
        """Obtiene la dimensión de los embeddings"""
        return self.embedding_model.get_sentence_embedding_dimension()
    
    def encode_text(self, text: str) -> List[float]:
        """Codifica texto a embeddings"""
        return self.embedding_model.encode(text).tolist()
    
    def encode_batch(self, texts: List[str]) -> List[List[float]]:
        """Codifica un lote de textos a embeddings"""
        return self.embedding_model.encode(texts).tolist()