import uuid
import re
from urllib.parse import urlparse
from typing import Optional
import logging

logger = logging.getLogger(__name__)


def generate_chat_id(prefix: str = "chat") -> str:
    """Genera un ID único para un chat"""
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def validate_url(url: str) -> bool:
    """Valida si una URL es válida"""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False


def sanitize_text(text: str) -> str:
    """Limpia y sanitiza texto"""
    if not text:
        return ""
    
    # Remover caracteres de control excepto saltos de línea
    text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
    
    # Normalizar espacios en blanco
    text = re.sub(r'\s+', ' ', text)
    
    # Limpiar espacios al inicio y final
    text = text.strip()
    
    return text


def extract_domain(url: str) -> Optional[str]:
    """Extrae el dominio de una URL"""
    try:
        parsed = urlparse(url)
        return parsed.netloc
    except Exception:
        return None


def is_technical_documentation(url: str) -> bool:
    """Determina si una URL parece ser documentación técnica"""
    technical_patterns = [
        r'/docs?/',
        r'/documentation',
        r'/api/',
        r'/reference/',
        r'/guide/',
        r'/tutorial/',
        r'/manual/',
        r'/help/',
        r'/developer/',
        r'/technical/'
    ]
    
    url_lower = url.lower()
    return any(re.search(pattern, url_lower) for pattern in technical_patterns)


def truncate_text(text: str, max_length: int = 1000) -> str:
    """Trunca texto a una longitud máxima"""
    if len(text) <= max_length:
        return text
    
    # Truncar en una palabra completa si es posible
    truncated = text[:max_length]
    last_space = truncated.rfind(' ')
    
    if last_space > max_length * 0.8:  # Si el último espacio está cerca del final
        return truncated[:last_space] + "..."
    else:
        return truncated + "..."


def format_code_block(code: str, language: str = "text") -> str:
    """Formatea un bloque de código en Markdown"""
    return f"```{language}\n{code}\n```"


def extract_code_blocks(text: str) -> list:
    """Extrae bloques de código de un texto"""
    pattern = r'```(\w+)?\n(.*?)```'
    matches = re.findall(pattern, text, re.DOTALL)
    
    blocks = []
    for match in matches:
        language = match[0] if match[0] else 'text'
        code = match[1].strip()
        blocks.append({
            'language': language,
            'code': code
        })
    
    return blocks


def count_tokens_estimate(text: str) -> int:
    """Estima el número de tokens en un texto (aproximación simple)"""
    # Aproximación: 1 token ≈ 4 caracteres
    return len(text) // 4


def is_code_question(message: str) -> bool:
    """Determina si un mensaje es una pregunta sobre código"""
    code_keywords = [
        'código', 'code', 'función', 'function', 'clase', 'class',
        'método', 'method', 'sintaxis', 'syntax', 'implementar',
        'implement', 'ejemplo', 'example', 'error', 'bug'
    ]
    
    message_lower = message.lower()
    return any(keyword in message_lower for keyword in code_keywords)


def is_follow_up_question(message: str) -> bool:
    """Determina si un mensaje es una pregunta de seguimiento"""
    follow_up_keywords = [
        'anterior', 'before', 'mencionaste', 'you mentioned',
        'eso', 'that', 'esto', 'this', 'más', 'more',
        'detalles', 'details', 'ejemplo', 'example'
    ]
    
    message_lower = message.lower()
    return any(keyword in message_lower for keyword in follow_up_keywords)


def calculate_similarity_score(text1: str, text2: str) -> float:
    """Calcula un score de similitud simple entre dos textos"""
    # Implementación simple basada en palabras comunes
    words1 = set(text1.lower().split())
    words2 = set(text2.lower().split())
    
    if not words1 or not words2:
        return 0.0
    
    intersection = words1.intersection(words2)
    union = words1.union(words2)
    
    return len(intersection) / len(union) if union else 0.0


def format_timestamp(timestamp) -> str:
    """Formatea un timestamp para mostrar"""
    if not timestamp:
        return "N/A"
    
    try:
        return timestamp.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return str(timestamp)


def get_file_extension_from_url(url: str) -> Optional[str]:
    """Extrae la extensión de archivo de una URL"""
    try:
        path = urlparse(url).path
        return path.split('.')[-1].lower() if '.' in path else None
    except Exception:
        return None


def is_supported_file_type(url: str) -> bool:
    """Determina si el tipo de archivo es soportado"""
    supported_extensions = ['html', 'htm', 'md', 'txt', 'rst']
    extension = get_file_extension_from_url(url)
    return extension in supported_extensions if extension else True  # Por defecto True para URLs sin extensión