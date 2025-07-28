import aiohttp
import asyncio
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
import re
from urllib.parse import urljoin, urlparse
import logging
from app.config import settings

logger = logging.getLogger(__name__)


class WebScraper:
    """Clase para extraer contenido de URLs de documentación"""
    
    def __init__(self):
        self.timeout = aiohttp.ClientTimeout(total=settings.request_timeout)
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
    
    async def scrape_url(self, url: str) -> Dict[str, any]:
        """Extrae contenido de una URL"""
        try:
            async with aiohttp.ClientSession(timeout=self.timeout, headers=self.headers) as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        raise Exception(f"HTTP {response.status}: {response.reason}")
                    
                    html_content = await response.text()
                    return await self._parse_html(html_content, url)
                    
        except Exception as e:
            logger.error(f"Error scraping {url}: {str(e)}")
            raise
    
    async def _parse_html(self, html_content: str, base_url: str) -> Dict[str, any]:
        """Parsea el HTML y extrae contenido relevante"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Remover elementos no deseados
        for element in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
            element.decompose()
        
        # Extraer título
        title = soup.find('title')
        title_text = title.get_text().strip() if title else ""
        
        # Extraer contenido principal
        content_sections = []
        
        # Buscar elementos de contenido principal
        main_selectors = [
            'main',
            'article',
            '.content',
            '.main-content',
            '#content',
            '#main',
            '.documentation',
            '.docs-content'
        ]
        
        main_content = None
        for selector in main_selectors:
            main_content = soup.select_one(selector)
            if main_content:
                break
        
        if not main_content:
            # Si no encuentra contenido principal, usar body
            main_content = soup.find('body')
        
        if main_content:
            content_sections = self._extract_sections(main_content, base_url)
        
        # Extraer enlaces para seguimiento
        links = self._extract_links(soup, base_url)
        
        return {
            'title': title_text,
            'url': base_url,
            'sections': content_sections,
            'links': links,
            'raw_html': html_content
        }
    
    def _extract_sections(self, element, base_url: str) -> List[Dict[str, any]]:
        """Extrae secciones del contenido"""
        sections = []
        
        # Buscar encabezados y su contenido
        headers = element.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
        
        for header in headers:
            section = {
                'title': header.get_text().strip(),
                'level': int(header.name[1]),
                'content': [],
                'code_blocks': []
            }
            
            # Obtener contenido hasta el siguiente encabezado del mismo nivel o superior
            current = header.next_sibling
            while current and not (hasattr(current, 'name') and 
                                 current.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6'] and 
                                 int(current.name[1]) <= section['level']):
                
                if hasattr(current, 'name'):
                    if current.name == 'p':
                        text = current.get_text().strip()
                        if text:
                            section['content'].append(text)
                    elif current.name in ['pre', 'code']:
                        code_content = current.get_text().strip()
                        if code_content:
                            section['code_blocks'].append({
                                'content': code_content,
                                'language': self._detect_language(code_content)
                            })
                    elif current.name in ['ul', 'ol']:
                        items = [li.get_text().strip() for li in current.find_all('li')]
                        section['content'].extend(items)
                
                current = current.next_sibling
            
            if section['content'] or section['code_blocks']:
                sections.append(section)
        
        return sections
    
    def _extract_links(self, soup, base_url: str) -> List[str]:
        """Extrae enlaces relevantes"""
        links = []
        for link in soup.find_all('a', href=True):
            href = link['href']
            full_url = urljoin(base_url, href)
            
            # Solo incluir enlaces internos o de documentación
            if self._is_relevant_link(full_url, base_url):
                links.append(full_url)
        
        return list(set(links))  # Remover duplicados
    
    def _is_relevant_link(self, url: str, base_url: str) -> bool:
        """Determina si un enlace es relevante para la documentación"""
        parsed_base = urlparse(base_url)
        parsed_url = urlparse(url)
        
        # Mismo dominio
        if parsed_url.netloc and parsed_url.netloc != parsed_base.netloc:
            return False
        
        # Excluir enlaces no deseados
        exclude_patterns = [
            r'\.(pdf|zip|tar|gz|rar)$',
            r'#',
            r'javascript:',
            r'mailto:',
            r'tel:'
        ]
        
        for pattern in exclude_patterns:
            if re.search(pattern, url, re.IGNORECASE):
                return False
        
        return True
    
    def _detect_language(self, code_content: str) -> str:
        """Detecta el lenguaje de programación del código"""
        # Patrones simples para detectar lenguajes
        patterns = {
            'python': [r'def\s+\w+', r'import\s+\w+', r'from\s+\w+', r'class\s+\w+'],
            'javascript': [r'function\s+\w+', r'const\s+\w+', r'let\s+\w+', r'var\s+\w+'],
            'java': [r'public\s+class', r'private\s+\w+', r'public\s+static'],
            'cpp': [r'#include', r'std::', r'namespace\s+\w+'],
            'c': [r'#include', r'int\s+main', r'printf'],
            'html': [r'<html', r'<div', r'<span', r'<p>'],
            'css': [r'\{', r'\}', r':\s*[^;]+;'],
            'sql': [r'SELECT', r'INSERT', r'UPDATE', r'DELETE', r'CREATE\s+TABLE']
        }
        
        for lang, lang_patterns in patterns.items():
            for pattern in lang_patterns:
                if re.search(pattern, code_content, re.IGNORECASE):
                    return lang
        
        return 'text'  # Por defecto