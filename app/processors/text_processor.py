import re
from typing import List, Dict, Any
from app.config import settings
import logging

logger = logging.getLogger(__name__)


class TextProcessor:
    """Clase para procesar y segmentar texto de documentación"""
    
    def __init__(self):
        self.chunk_size = settings.chunk_size
        self.chunk_overlap = settings.chunk_overlap
    
    def process_document(self, document_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Procesa un documento completo y retorna chunks"""
        chunks = []
        
        # Procesar título
        if document_data.get('title'):
            title_chunk = {
                'content': f"Título: {document_data['title']}",
                'metadata': {
                    'type': 'title',
                    'url': document_data['url'],
                    'section': 'header'
                },
                'source': document_data['url']
            }
            chunks.append(title_chunk)
        
        # Procesar secciones
        for section in document_data.get('sections', []):
            section_chunks = self._process_section(section, document_data['url'])
            chunks.extend(section_chunks)
        
        return chunks
    
    def _process_section(self, section: Dict[str, Any], base_url: str) -> List[Dict[str, Any]]:
        """Procesa una sección individual"""
        chunks = []
        
        # Crear chunk del título de la sección
        if section.get('title'):
            title_chunk = {
                'content': f"Sección: {section['title']}",
                'metadata': {
                    'type': 'section_title',
                    'level': section.get('level', 1),
                    'url': base_url,
                    'section': section['title']
                },
                'source': base_url
            }
            chunks.append(title_chunk)
        
        # Procesar contenido de texto
        if section.get('content'):
            text_chunks = self._chunk_text(
                '\n'.join(section['content']),
                metadata={
                    'type': 'text_content',
                    'section': section.get('title', ''),
                    'url': base_url
                },
                source=base_url
            )
            chunks.extend(text_chunks)
        
        # Procesar bloques de código
        for code_block in section.get('code_blocks', []):
            code_chunk = {
                'content': f"Código ({code_block.get('language', 'text')}):\n{code_block['content']}",
                'metadata': {
                    'type': 'code_block',
                    'language': code_block.get('language', 'text'),
                    'section': section.get('title', ''),
                    'url': base_url
                },
                'source': base_url
            }
            chunks.append(code_chunk)
        
        return chunks
    
    def _chunk_text(self, text: str, metadata: Dict[str, Any], source: str) -> List[Dict[str, Any]]:
        """Segmenta texto en chunks semánticos"""
        # Limpiar texto
        cleaned_text = self._clean_text(text)
        
        if len(cleaned_text) <= self.chunk_size:
            return [{
                'content': cleaned_text,
                'metadata': metadata,
                'source': source
            }]
        
        # Segmentación semántica
        chunks = []
        
        # Dividir por párrafos primero
        paragraphs = re.split(r'\n\s*\n', cleaned_text)
        
        current_chunk = ""
        current_metadata = metadata.copy()
        
        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if not paragraph:
                continue
            
            # Si el párrafo es muy largo, dividirlo
            if len(paragraph) > self.chunk_size:
                if current_chunk:
                    chunks.append({
                        'content': current_chunk.strip(),
                        'metadata': current_metadata,
                        'source': source
                    })
                    current_chunk = ""
                
                # Dividir párrafo largo
                sub_chunks = self._split_long_paragraph(paragraph)
                for sub_chunk in sub_chunks:
                    chunks.append({
                        'content': sub_chunk,
                        'metadata': current_metadata,
                        'source': source
                    })
            else:
                # Verificar si agregar este párrafo excedería el límite
                if len(current_chunk) + len(paragraph) + 1 > self.chunk_size:
                    if current_chunk:
                        chunks.append({
                            'content': current_chunk.strip(),
                            'metadata': current_metadata,
                            'source': source
                        })
                        current_chunk = paragraph
                    else:
                        current_chunk = paragraph
                else:
                    if current_chunk:
                        current_chunk += "\n" + paragraph
                    else:
                        current_chunk = paragraph
        
        # Agregar el último chunk si existe
        if current_chunk:
            chunks.append({
                'content': current_chunk.strip(),
                'metadata': current_metadata,
                'source': source
            })
        
        return chunks
    
    def _split_long_paragraph(self, paragraph: str) -> List[str]:
        """Divide un párrafo largo en chunks más pequeños"""
        chunks = []
        
        # Intentar dividir por oraciones
        sentences = re.split(r'[.!?]+', paragraph)
        
        current_chunk = ""
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            if len(current_chunk) + len(sentence) + 1 > self.chunk_size:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                    current_chunk = sentence
                else:
                    # Si una sola oración es muy larga, dividir por palabras
                    if len(sentence) > self.chunk_size:
                        word_chunks = self._split_by_words(sentence)
                        chunks.extend(word_chunks)
                    else:
                        chunks.append(sentence)
            else:
                if current_chunk:
                    current_chunk += ". " + sentence
                else:
                    current_chunk = sentence
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks
    
    def _split_by_words(self, text: str) -> List[str]:
        """Divide texto por palabras cuando es necesario"""
        words = text.split()
        chunks = []
        current_chunk = ""
        
        for word in words:
            if len(current_chunk) + len(word) + 1 > self.chunk_size:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                    current_chunk = word
                else:
                    # Si una sola palabra es muy larga, truncar
                    chunks.append(word[:self.chunk_size])
            else:
                if current_chunk:
                    current_chunk += " " + word
                else:
                    current_chunk = word
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks
    
    def _clean_text(self, text: str) -> str:
        """Limpia el texto de caracteres no deseados"""
        # Remover caracteres de control excepto saltos de línea
        text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
        
        # Normalizar espacios en blanco
        text = re.sub(r'\s+', ' ', text)
        
        # Remover líneas vacías múltiples
        text = re.sub(r'\n\s*\n\s*\n', '\n\n', text)
        
        # Limpiar espacios al inicio y final
        text = text.strip()
        
        return text
    
    def merge_overlapping_chunks(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Merges chunks with overlap for better context"""
        if not chunks:
            return chunks
        
        merged_chunks = []
        current_chunk = chunks[0].copy()
        
        for next_chunk in chunks[1:]:
            # Verificar si hay overlap significativo
            if self._has_significant_overlap(current_chunk['content'], next_chunk['content']):
                # Merge chunks
                overlap_text = self._find_overlap(current_chunk['content'], next_chunk['content'])
                merged_content = current_chunk['content'] + next_chunk['content'][len(overlap_text):]
                
                current_chunk['content'] = merged_content
                # Merge metadata
                current_chunk['metadata'].update(next_chunk['metadata'])
            else:
                # No hay overlap significativo, agregar chunk actual y continuar
                merged_chunks.append(current_chunk)
                current_chunk = next_chunk.copy()
        
        # Agregar el último chunk
        merged_chunks.append(current_chunk)
        
        return merged_chunks
    
    def _has_significant_overlap(self, text1: str, text2: str) -> bool:
        """Verifica si hay overlap significativo entre dos textos"""
        # Buscar overlap de al menos 50 caracteres
        min_overlap = 50
        
        for i in range(len(text1) - min_overlap + 1):
            overlap = text1[i:]
            if text2.startswith(overlap) and len(overlap) >= min_overlap:
                return True
        
        return False
    
    def _find_overlap(self, text1: str, text2: str) -> str:
        """Encuentra el texto de overlap entre dos strings"""
        for i in range(len(text1)):
            overlap = text1[i:]
            if text2.startswith(overlap):
                return overlap
        return ""