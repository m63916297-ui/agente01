import pytest
import sys
import os

# Agregar el directorio raíz al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.utils.helpers import (
    generate_chat_id, validate_url, sanitize_text, extract_domain,
    is_technical_documentation, truncate_text, format_code_block,
    extract_code_blocks, is_code_question, is_follow_up_question
)


class TestHelpers:
    """Tests para las funciones de utilidad"""
    
    def test_generate_chat_id(self):
        """Test para generar ID de chat"""
        chat_id = generate_chat_id()
        assert chat_id.startswith("chat_")
        assert len(chat_id) == 12  # "chat_" + 8 caracteres hex
        
        custom_id = generate_chat_id("test")
        assert custom_id.startswith("test_")
    
    def test_validate_url(self):
        """Test para validar URLs"""
        # URLs válidas
        assert validate_url("https://docs.python.org/3/tutorial/")
        assert validate_url("http://example.com")
        assert validate_url("https://api.github.com/v3")
        
        # URLs inválidas
        assert not validate_url("not-a-url")
        assert not validate_url("")
        assert not validate_url("ftp://invalid")
    
    def test_sanitize_text(self):
        """Test para sanitizar texto"""
        # Texto normal
        assert sanitize_text("Hello World") == "Hello World"
        
        # Texto con espacios extra
        assert sanitize_text("  Hello   World  ") == "Hello World"
        
        # Texto con caracteres de control
        text_with_control = "Hello\x00World\x08Test"
        assert sanitize_text(text_with_control) == "HelloWorldTest"
        
        # Texto vacío
        assert sanitize_text("") == ""
        assert sanitize_text(None) == ""
    
    def test_extract_domain(self):
        """Test para extraer dominio"""
        assert extract_domain("https://docs.python.org/3/tutorial/") == "docs.python.org"
        assert extract_domain("http://example.com") == "example.com"
        assert extract_domain("https://api.github.com/v3") == "api.github.com"
        assert extract_domain("invalid-url") is None
    
    def test_is_technical_documentation(self):
        """Test para detectar documentación técnica"""
        # URLs de documentación técnica
        assert is_technical_documentation("https://docs.python.org/3/tutorial/")
        assert is_technical_documentation("https://example.com/api/docs")
        assert is_technical_documentation("https://example.com/developer/guide")
        assert is_technical_documentation("https://example.com/technical/manual")
        
        # URLs que no son documentación técnica
        assert not is_technical_documentation("https://example.com/blog")
        assert not is_technical_documentation("https://example.com/about")
    
    def test_truncate_text(self):
        """Test para truncar texto"""
        long_text = "This is a very long text that should be truncated"
        
        # Truncar a 20 caracteres
        truncated = truncate_text(long_text, 20)
        assert len(truncated) <= 23  # 20 + "..."
        assert truncated.endswith("...")
        
        # Texto corto no debe truncarse
        short_text = "Short text"
        assert truncate_text(short_text, 20) == short_text
    
    def test_format_code_block(self):
        """Test para formatear bloques de código"""
        code = "print('Hello World')"
        
        # Con lenguaje especificado
        formatted = format_code_block(code, "python")
        assert formatted == "```python\nprint('Hello World')\n```"
        
        # Sin lenguaje
        formatted = format_code_block(code)
        assert formatted == "```text\nprint('Hello World')\n```"
    
    def test_extract_code_blocks(self):
        """Test para extraer bloques de código"""
        text = """
        Here is some text.
        
        ```python
        def hello():
            print("Hello World")
        ```
        
        More text.
        
        ```javascript
        function hello() {
            console.log("Hello World");
        }
        ```
        """
        
        blocks = extract_code_blocks(text)
        assert len(blocks) == 2
        assert blocks[0]['language'] == 'python'
        assert 'def hello():' in blocks[0]['code']
        assert blocks[1]['language'] == 'javascript'
        assert 'function hello()' in blocks[1]['code']
    
    def test_is_code_question(self):
        """Test para detectar preguntas sobre código"""
        # Preguntas sobre código
        assert is_code_question("¿Cómo se define una función en Python?")
        assert is_code_question("Show me the code for this")
        assert is_code_question("What's the syntax for classes?")
        assert is_code_question("Hay algún error en este código?")
        
        # Preguntas generales
        assert not is_code_question("¿Qué es Python?")
        assert not is_code_question("How does it work?")
    
    def test_is_follow_up_question(self):
        """Test para detectar preguntas de seguimiento"""
        # Preguntas de seguimiento
        assert is_follow_up_question("¿Puedes darme más detalles sobre eso?")
        assert is_follow_up_question("Can you explain that further?")
        assert is_follow_up_question("¿Mencionaste algo sobre clases?")
        assert is_follow_up_question("Give me an example of this")
        
        # Preguntas iniciales
        assert not is_follow_up_question("¿Qué es Python?")
        assert not is_follow_up_question("How do I start?")


if __name__ == "__main__":
    pytest.main([__file__])