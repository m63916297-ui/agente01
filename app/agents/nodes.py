from typing import Dict, Any, List, Optional
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage
from langchain_community.llms import Ollama
from app.config import settings
from app.processors.embedding_manager import EmbeddingManager
import re
import json
import logging

logger = logging.getLogger(__name__)


class State:
    """Estado del grafo de LangGraph"""
    def __init__(self, chat_id: str, user_message: str, user_id: str, chat_history: List[Dict] = None):
        self.chat_id = chat_id
        self.user_message = user_message
        self.user_id = user_id
        self.chat_history = chat_history or []
        self.intent = None
        self.retrieved_context = []
        self.response = None
        self.formatted_response = None
        self.confidence = 0.0
        self.needs_clarification = False
        self.clarification_question = None


def create_llm():
    """Crea instancia del modelo de lenguaje"""
    return Ollama(
        base_url=settings.ollama_base_url,
        model=settings.ollama_model,
        temperature=settings.temperature
    )


class InputNode:
    """Nodo de entrada que recibe la pregunta del usuario"""
    
    def __init__(self):
        self.name = "input_node"
    
    def run(self, state: State) -> State:
        """Procesa el input inicial"""
        logger.info(f"Input node: Procesando mensaje para chat {state.chat_id}")
        
        # Validar que el mensaje no esté vacío
        if not state.user_message.strip():
            state.user_message = "Por favor, proporciona una pregunta sobre la documentación."
        
        return state


class IntentAnalysisNode:
    """Nodo que analiza la intención del usuario"""
    
    def __init__(self):
        self.name = "intent_analysis_node"
        self.llm = create_llm()
    
    def run(self, state: State) -> State:
        """Analiza la intención del mensaje del usuario"""
        logger.info(f"Intent analysis: Analizando intención para chat {state.chat_id}")
        
        # Patrones para detectar intenciones
        intent_patterns = {
            'code_question': [
                r'\b(código|code|función|function|clase|class|método|method)\b',
                r'\b(implementar|implement|ejemplo|example)\b',
                r'\b(sintaxis|syntax|error|bug)\b'
            ],
            'follow_up': [
                r'\b(anterior|before|mencionaste|you mentioned)\b',
                r'\b(eso|that|esto|this)\b',
                r'\b(más|more|detalles|details)\b'
            ],
            'general_question': [
                r'\b(qué|what|cómo|how|cuándo|when|dónde|where)\b',
                r'\b(explicar|explain|definir|define)\b',
                r'\b(concepto|concept|idea|notion)\b'
            ],
            'clarification': [
                r'\b(no entiendo|don\'t understand|confuso|confused)\b',
                r'\b(puedes explicar|can you explain|más simple|simpler)\b'
            ]
        }
        
        # Detectar intención por patrones
        detected_intent = self._detect_intent_by_patterns(state.user_message, intent_patterns)
        
        # Usar LLM para confirmar/refinar la intención
        refined_intent = self._refine_intent_with_llm(state.user_message, detected_intent, state.chat_history)
        
        state.intent = refined_intent
        logger.info(f"Intent detected: {refined_intent}")
        
        return state
    
    def _detect_intent_by_patterns(self, message: str, patterns: Dict[str, List[str]]) -> str:
        """Detecta intención usando patrones regex"""
        message_lower = message.lower()
        
        scores = {
            'code_question': 0,
            'follow_up': 0,
            'general_question': 0,
            'clarification': 0
        }
        
        for intent, pattern_list in patterns.items():
            for pattern in pattern_list:
                if re.search(pattern, message_lower, re.IGNORECASE):
                    scores[intent] += 1
        
        # Retornar la intención con mayor puntuación
        if max(scores.values()) > 0:
            return max(scores, key=scores.get)
        
        return 'general_question'  # Por defecto
    
    def _refine_intent_with_llm(self, message: str, detected_intent: str, chat_history: List[Dict]) -> str:
        """Refina la intención usando el LLM"""
        try:
            # Construir prompt para el LLM
            context = ""
            if chat_history:
                recent_messages = chat_history[-3:]  # Últimos 3 mensajes
                context = "Contexto de la conversación anterior:\n"
                for msg in recent_messages:
                    context += f"Usuario: {msg['message']}\n"
                    context += f"Asistente: {msg['response']}\n"
            
            prompt = f"""
            Analiza la siguiente pregunta del usuario y determina su intención principal.
            
            {context}
            
            Pregunta del usuario: "{message}"
            Intención detectada por patrones: {detected_intent}
            
            Opciones de intención:
            - code_question: Pregunta sobre código, sintaxis, implementación
            - follow_up: Pregunta de seguimiento que requiere contexto anterior
            - general_question: Pregunta general sobre conceptos o documentación
            - clarification: Solicita aclaración o explicación más simple
            
            Responde solo con una de las opciones anteriores.
            """
            
            response = self.llm.invoke(prompt)
            refined_intent = response.strip().lower()
            
            # Validar que la respuesta sea una intención válida
            valid_intents = ['code_question', 'follow_up', 'general_question', 'clarification']
            if refined_intent in valid_intents:
                return refined_intent
            
            return detected_intent
            
        except Exception as e:
            logger.error(f"Error refinando intención con LLM: {str(e)}")
            return detected_intent


class ConditionalRouter:
    """Nodo de enrutamiento condicional"""
    
    def __init__(self):
        self.name = "conditional_router"
    
    def run(self, state: State) -> str:
        """Determina el siguiente nodo basado en la intención"""
        logger.info(f"Conditional router: Enrutando a {state.intent}")
        
        if state.intent == 'clarification':
            return 'clarification_node'
        elif state.intent == 'code_question':
            return 'rag_node'
        elif state.intent == 'follow_up':
            return 'context_builder_node'
        else:  # general_question
            return 'rag_node'


class RAGNode:
    """Nodo de Recuperación y Aumento de Generación"""
    
    def __init__(self):
        self.name = "rag_node"
        self.embedding_manager = EmbeddingManager()
        self.llm = create_llm()
    
    def run(self, state: State) -> State:
        """Realiza búsqueda semántica y recupera contexto relevante"""
        logger.info(f"RAG node: Buscando contexto para chat {state.chat_id}")
        
        try:
            # Búsqueda semántica general
            general_results = self.embedding_manager.search_similar(
                state.chat_id, 
                state.user_message, 
                n_results=3
            )
            
            # Si es pregunta de código, buscar también bloques de código
            code_results = []
            if state.intent == 'code_question':
                code_results = self.embedding_manager.search_code_blocks(
                    state.chat_id,
                    state.user_message
                )
            
            # Combinar y ordenar resultados por relevancia
            all_results = general_results + code_results
            all_results.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
            
            # Tomar los mejores resultados
            top_results = all_results[:5]
            
            state.retrieved_context = top_results
            
            # Calcular confianza basada en scores de relevancia
            if top_results:
                avg_score = sum(r.get('relevance_score', 0) for r in top_results) / len(top_results)
                state.confidence = avg_score
            else:
                state.confidence = 0.0
            
            logger.info(f"RAG completado: {len(top_results)} resultados, confianza: {state.confidence:.2f}")
            
        except Exception as e:
            logger.error(f"Error en RAG node: {str(e)}")
            state.retrieved_context = []
            state.confidence = 0.0
        
        return state


class ContextBuilderNode:
    """Nodo para construir contexto de conversación anterior"""
    
    def __init__(self):
        self.name = "context_builder_node"
    
    def run(self, state: State) -> State:
        """Construye contexto basado en el historial de conversación"""
        logger.info(f"Context builder: Construyendo contexto para chat {state.chat_id}")
        
        if not state.chat_history:
            # Si no hay historial, tratar como pregunta general
            state.intent = 'general_question'
            return state
        
        # Agregar contexto del historial al mensaje
        recent_context = self._build_context_from_history(state.chat_history)
        enhanced_message = f"Contexto anterior: {recent_context}\n\nPregunta actual: {state.user_message}"
        
        state.user_message = enhanced_message
        state.intent = 'general_question'  # Cambiar a pregunta general con contexto
        
        return state
    
    def _build_context_from_history(self, chat_history: List[Dict]) -> str:
        """Construye contexto a partir del historial"""
        if not chat_history:
            return ""
        
        # Tomar los últimos 2 intercambios
        recent_exchanges = chat_history[-4:]  # Últimos 4 mensajes (2 intercambios)
        
        context_parts = []
        for msg in recent_exchanges:
            if msg.get('response'):  # Solo respuestas del asistente
                # Extraer información clave de la respuesta
                key_info = self._extract_key_info(msg['response'])
                if key_info:
                    context_parts.append(key_info)
        
        return " ".join(context_parts)
    
    def _extract_key_info(self, response: str) -> str:
        """Extrae información clave de una respuesta"""
        # Buscar conceptos clave, definiciones, etc.
        lines = response.split('\n')
        key_lines = []
        
        for line in lines:
            line = line.strip()
            if line and len(line) < 200:  # Líneas no muy largas
                # Buscar patrones de información clave
                if any(keyword in line.lower() for keyword in ['es', 'son', 'define', 'significa', 'permite', 'utiliza']):
                    key_lines.append(line)
        
        return " ".join(key_lines[:2])  # Máximo 2 líneas clave


class ResponseGenerationNode:
    """Nodo de generación de respuesta"""
    
    def __init__(self):
        self.name = "response_generation_node"
        self.llm = create_llm()
    
    def run(self, state: State) -> State:
        """Genera respuesta basada en el contexto recuperado"""
        logger.info(f"Response generation: Generando respuesta para chat {state.chat_id}")
        
        try:
            # Construir prompt con contexto
            prompt = self._build_response_prompt(state)
            
            # Generar respuesta
            response = self.llm.invoke(prompt)
            
            state.response = response.strip()
            
            # Si la confianza es baja, marcar para aclaración
            if state.confidence < 0.3:
                state.needs_clarification = True
                state.clarification_question = "¿Podrías ser más específico sobre lo que necesitas saber?"
            
            logger.info(f"Respuesta generada: {len(state.response)} caracteres")
            
        except Exception as e:
            logger.error(f"Error generando respuesta: {str(e)}")
            state.response = "Lo siento, tuve un problema generando la respuesta. ¿Podrías intentar reformular tu pregunta?"
        
        return state
    
    def _build_response_prompt(self, state: State) -> str:
        """Construye el prompt para generar la respuesta"""
        # Construir contexto
        context_parts = []
        for result in state.retrieved_context:
            content = result['content']
            metadata = result.get('metadata', {})
            
            # Agregar información de metadata si es relevante
            if metadata.get('type') == 'code_block':
                context_parts.append(f"Bloque de código ({metadata.get('language', 'text')}):\n{content}")
            elif metadata.get('section'):
                context_parts.append(f"Sección '{metadata['section']}':\n{content}")
            else:
                context_parts.append(content)
        
        context_text = "\n\n".join(context_parts)
        
        # Construir prompt
        prompt = f"""
        Eres un asistente experto en documentación técnica. Responde la pregunta del usuario basándote en la información proporcionada.
        
        Información de la documentación:
        {context_text}
        
        Pregunta del usuario: {state.user_message}
        
        Instrucciones:
        1. Responde de manera clara y concisa
        2. Si la información no está disponible en el contexto, indícalo claramente
        3. Si es necesario, proporciona ejemplos de código
        4. Mantén un tono profesional pero accesible
        5. Si la pregunta requiere más contexto, sugiere qué información adicional sería útil
        
        Respuesta:
        """
        
        return prompt


class CodeFormattingNode:
    """Nodo de formateo de código"""
    
    def __init__(self):
        self.name = "code_formatting_node"
    
    def run(self, state: State) -> State:
        """Formatea la respuesta si contiene código"""
        logger.info(f"Code formatting: Formateando respuesta para chat {state.chat_id}")
        
        if not state.response:
            return state
        
        # Detectar y formatear bloques de código
        formatted_response = self._format_code_blocks(state.response)
        
        # Detectar y formatear comandos
        formatted_response = self._format_commands(formatted_response)
        
        # Detectar y formatear variables y funciones
        formatted_response = self._format_technical_terms(formatted_response)
        
        state.formatted_response = formatted_response
        
        return state
    
    def _format_code_blocks(self, text: str) -> str:
        """Formatea bloques de código en Markdown"""
        # Patrón para detectar bloques de código
        code_pattern = r'```(\w+)?\n(.*?)```'
        
        def replace_code(match):
            language = match.group(1) or 'text'
            code = match.group(2)
            return f"```{language}\n{code}\n```"
        
        return re.sub(code_pattern, replace_code, text, flags=re.DOTALL)
    
    def _format_commands(self, text: str) -> str:
        """Formatea comandos en línea"""
        # Patrón para comandos
        command_pattern = r'`([^`]+)`'
        
        def replace_command(match):
            command = match.group(1)
            # Si ya está formateado, no hacer nada
            if command.startswith('`') and command.endswith('`'):
                return match.group(0)
            return f"`{command}`"
        
        return re.sub(command_pattern, replace_command, text)
    
    def _format_technical_terms(self, text: str) -> str:
        """Formatea términos técnicos"""
        # Patrones para términos técnicos
        patterns = [
            (r'\b(function|class|method|variable|parameter)\b', r'**\1**'),
            (r'\b(API|URL|HTTP|JSON|XML|SQL)\b', r'**\1**'),
            (r'\b(import|export|return|if|else|for|while)\b', r'`\1`')
        ]
        
        for pattern, replacement in patterns:
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
        
        return text


class MemoryNode:
    """Nodo de memoria para mantener estado de la conversación"""
    
    def __init__(self):
        self.name = "memory_node"
    
    def run(self, state: State) -> State:
        """Actualiza la memoria de la conversación"""
        logger.info(f"Memory node: Actualizando memoria para chat {state.chat_id}")
        
        # Aquí se actualizaría la base de datos con el nuevo mensaje
        # Por ahora solo actualizamos el estado
        
        # Agregar el intercambio actual al historial
        new_exchange = {
            'user_message': state.user_message,
            'response': state.formatted_response or state.response,
            'intent': state.intent,
            'confidence': state.confidence,
            'timestamp': 'now'  # En implementación real sería datetime
        }
        
        state.chat_history.append(new_exchange)
        
        return state


class ClarificationNode:
    """Nodo para solicitar aclaración al usuario"""
    
    def __init__(self):
        self.name = "clarification_node"
        self.llm = create_llm()
    
    def run(self, state: State) -> State:
        """Genera una pregunta de aclaración"""
        logger.info(f"Clarification node: Generando aclaración para chat {state.chat_id}")
        
        try:
            prompt = f"""
            El usuario hizo la siguiente pregunta: "{state.user_message}"
            
            Genera una pregunta de aclaración que ayude al usuario a ser más específico sobre lo que necesita saber.
            La pregunta debe ser corta, clara y útil.
            
            Pregunta de aclaración:
            """
            
            clarification = self.llm.invoke(prompt)
            state.clarification_question = clarification.strip()
            state.needs_clarification = True
            
        except Exception as e:
            logger.error(f"Error generando aclaración: {str(e)}")
            state.clarification_question = "¿Podrías ser más específico sobre lo que necesitas saber?"
            state.needs_clarification = True
        
        return state