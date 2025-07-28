from langgraph.graph import StateGraph, END
from typing import Dict, Any, List
import logging
from .nodes import (
    State, InputNode, IntentAnalysisNode, ConditionalRouter,
    RAGNode, ResponseGenerationNode, CodeFormattingNode, 
    MemoryNode, ContextBuilderNode, ClarificationNode
)

logger = logging.getLogger(__name__)


class DocumentationAgent:
    """Agente principal de documentación usando LangGraph"""
    
    def __init__(self):
        self.graph = self._build_graph()
        self.app = self.graph.compile()
    
    def _build_graph(self) -> StateGraph:
        """Construye el grafo de LangGraph"""
        # Crear el grafo
        workflow = StateGraph(State)
        
        # Crear instancias de nodos
        input_node = InputNode()
        intent_analysis = IntentAnalysisNode()
        conditional_router = ConditionalRouter()
        rag_node = RAGNode()
        context_builder = ContextBuilderNode()
        response_generation = ResponseGenerationNode()
        code_formatting = CodeFormattingNode()
        memory_node = MemoryNode()
        clarification_node = ClarificationNode()
        
        # Agregar nodos al grafo
        workflow.add_node("input", input_node.run)
        workflow.add_node("intent_analysis", intent_analysis.run)
        workflow.add_node("conditional_router", conditional_router.run)
        workflow.add_node("rag", rag_node.run)
        workflow.add_node("context_builder", context_builder.run)
        workflow.add_node("response_generation", response_generation.run)
        workflow.add_node("code_formatting", code_formatting.run)
        workflow.add_node("memory", memory_node.run)
        workflow.add_node("clarification", clarification_node.run)
        
        # Definir el flujo principal
        workflow.set_entry_point("input")
        
        # Conectar nodos
        workflow.add_edge("input", "intent_analysis")
        workflow.add_edge("intent_analysis", "conditional_router")
        
        # Rutas condicionales desde el router
        workflow.add_conditional_edges(
            "conditional_router",
            conditional_router.run,
            {
                "rag": "rag",
                "context_builder": "context_builder",
                "clarification": "clarification"
            }
        )
        
        # Conectar nodos de procesamiento
        workflow.add_edge("rag", "response_generation")
        workflow.add_edge("context_builder", "rag")
        workflow.add_edge("response_generation", "code_formatting")
        workflow.add_edge("code_formatting", "memory")
        workflow.add_edge("memory", END)
        
        # Ruta de aclaración
        workflow.add_edge("clarification", END)
        
        return workflow
    
    def process_message(self, chat_id: str, user_message: str, user_id: str, chat_history: List[Dict] = None) -> Dict[str, Any]:
        """Procesa un mensaje del usuario y retorna la respuesta"""
        try:
            logger.info(f"Procesando mensaje para chat {chat_id}")
            
            # Crear estado inicial
            initial_state = State(
                chat_id=chat_id,
                user_message=user_message,
                user_id=user_id,
                chat_history=chat_history or []
            )
            
            # Ejecutar el grafo
            result = self.app.invoke(initial_state)
            
            # Extraer respuesta del resultado
            response = result.formatted_response or result.response
            
            # Si necesita aclaración, usar la pregunta de aclaración
            if result.needs_clarification and result.clarification_question:
                response = result.clarification_question
            
            return {
                'chat_id': chat_id,
                'response': response,
                'intent': result.intent,
                'confidence': result.confidence,
                'needs_clarification': result.needs_clarification,
                'retrieved_context_count': len(result.retrieved_context),
                'context_sources': [ctx.get('source', '') for ctx in result.retrieved_context]
            }
            
        except Exception as e:
            logger.error(f"Error procesando mensaje: {str(e)}")
            return {
                'chat_id': chat_id,
                'response': "Lo siento, tuve un problema procesando tu pregunta. ¿Podrías intentar reformularla?",
                'intent': 'error',
                'confidence': 0.0,
                'needs_clarification': False,
                'error': str(e)
            }
    
    def get_workflow_info(self) -> Dict[str, Any]:
        """Retorna información sobre el workflow"""
        return {
            'nodes': [
                'input',
                'intent_analysis', 
                'conditional_router',
                'rag',
                'context_builder',
                'response_generation',
                'code_formatting',
                'memory',
                'clarification'
            ],
            'edges': [
                'input → intent_analysis',
                'intent_analysis → conditional_router',
                'conditional_router → rag (code_question)',
                'conditional_router → context_builder (follow_up)',
                'conditional_router → clarification (clarification)',
                'context_builder → rag',
                'rag → response_generation',
                'response_generation → code_formatting',
                'code_formatting → memory',
                'memory → END',
                'clarification → END'
            ],
            'description': 'Workflow de LangGraph para análisis y síntesis de documentación técnica'
        }