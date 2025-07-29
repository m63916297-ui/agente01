#!/usr/bin/env python3
"""
Script de demostración del Agente Autónomo de Documentación
"""

import requests
import time
import json
import sys
import os

# Agregar el directorio raíz al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.utils.helpers import generate_chat_id

# Configuración
API_BASE_URL = "http://localhost:8000"
DEMO_URL = "https://docs.python.org/3/tutorial/"
CHAT_ID = generate_chat_id("demo")
USER_ID = "demo_user"


def print_step(step: str, message: str):
    """Imprime un paso del demo"""
    print(f"\n{'='*60}")
    print(f"PASO {step}: {message}")
    print(f"{'='*60}")


def print_response(response: dict, title: str = "Respuesta"):
    """Imprime una respuesta de la API"""
    print(f"\n{title}:")
    print("-" * 40)
    print(json.dumps(response, indent=2, ensure_ascii=False))


def wait_for_processing():
    """Espera a que termine el procesamiento"""
    print("\nEsperando a que termine el procesamiento...")
    
    while True:
        try:
            response = requests.get(f"{API_BASE_URL}/api/v1/processing-status/{CHAT_ID}")
            if response.status_code == 200:
                status_data = response.json()
                status = status_data['status']
                
                print(f"Estado: {status}")
                
                if status == 'completed':
                    print("✅ Procesamiento completado!")
                    return True
                elif status == 'failed':
                    print("❌ Procesamiento falló!")
                    print(f"Error: {status_data.get('message', 'Error desconocido')}")
                    return False
                
                time.sleep(2)
            else:
                print(f"Error consultando estado: {response.status_code}")
                return False
                
        except requests.exceptions.RequestException as e:
            print(f"Error de conexión: {e}")
            return False


def demo():
    """Ejecuta la demostración completa"""
    print("🚀 DEMOSTRACIÓN DEL AGENTE AUTÓNOMO DE DOCUMENTACIÓN")
    print("=" * 60)
    
    # Paso 1: Procesar documentación
    print_step("1", "PROCESANDO DOCUMENTACIÓN")
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/v1/process-documentation",
            json={
                "url": DEMO_URL,
                "chat_id": CHAT_ID
            }
        )
        
        if response.status_code == 200:
            print_response(response.json(), "Inicio de procesamiento")
            
            # Esperar a que termine el procesamiento
            if not wait_for_processing():
                print("❌ No se pudo completar el procesamiento")
                return
        else:
            print(f"❌ Error iniciando procesamiento: {response.status_code}")
            print(response.text)
            return
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Error de conexión: {e}")
        print("Asegúrate de que el servidor esté ejecutándose en http://localhost:8000")
        return
    
    # Paso 2: Obtener información de la documentación
    print_step("2", "INFORMACIÓN DE LA DOCUMENTACIÓN")
    
    try:
        response = requests.get(f"{API_BASE_URL}/api/v1/documentation-info/{CHAT_ID}")
        if response.status_code == 200:
            print_response(response.json(), "Información de documentación")
        else:
            print(f"Error obteniendo información: {response.status_code}")
    except Exception as e:
        print(f"Error: {e}")
    
    # Paso 3: Preguntas al agente
    print_step("3", "INTERACTUANDO CON EL AGENTE")
    
    questions = [
        "¿Qué es Python?",
        "¿Cómo se define una función en Python?",
        "¿Puedes darme un ejemplo de una clase?",
        "¿Cuál es la diferencia entre una lista y una tupla?",
        "¿Cómo se manejan las excepciones en Python?"
    ]
    
    for i, question in enumerate(questions, 1):
        print(f"\n--- Pregunta {i}: {question} ---")
        
        try:
            response = requests.post(
                f"{API_BASE_URL}/api/v1/chat/{CHAT_ID}",
                json={
                    "message": question,
                    "user_id": USER_ID
                }
            )
            
            if response.status_code == 200:
                chat_response = response.json()
                print(f"Respuesta: {chat_response['response']}")
                print(f"Intención detectada: {chat_response.get('intent', 'N/A')}")
            else:
                print(f"Error en chat: {response.status_code}")
                
        except Exception as e:
            print(f"Error: {e}")
        
        time.sleep(1)  # Pausa entre preguntas
    
    # Paso 4: Obtener historial
    print_step("4", "HISTORIAL DE CONVERSACIÓN")
    
    try:
        response = requests.get(f"{API_BASE_URL}/api/v1/chat-history/{CHAT_ID}")
        if response.status_code == 200:
            history = response.json()
            print(f"Total de mensajes: {history['total_messages']}")
            
            for msg in history['messages']:
                print(f"\nUsuario: {msg['message']}")
                print(f"Asistente: {msg['response'][:100]}...")
                print(f"Intención: {msg.get('intent', 'N/A')}")
        else:
            print(f"Error obteniendo historial: {response.status_code}")
    except Exception as e:
        print(f"Error: {e}")
    
    # Paso 5: Análisis del chat
    print_step("5", "ANÁLISIS DEL CHAT")
    
    try:
        response = requests.get(f"{API_BASE_URL}/api/v1/chat-analytics/{CHAT_ID}")
        if response.status_code == 200:
            analytics = response.json()
            print_response(analytics, "Análisis del chat")
        else:
            print(f"Error obteniendo analytics: {response.status_code}")
    except Exception as e:
        print(f"Error: {e}")
    
    # Paso 6: Información del agente
    print_step("6", "INFORMACIÓN DEL AGENTE")
    
    try:
        response = requests.get(f"{API_BASE_URL}/api/v1/agent-info")
        if response.status_code == 200:
            agent_info = response.json()
            print_response(agent_info, "Información del agente")
        else:
            print(f"Error obteniendo información del agente: {response.status_code}")
    except Exception as e:
        print(f"Error: {e}")
    
    print("\n" + "="*60)
    print("🎉 DEMOSTRACIÓN COMPLETADA")
    print("="*60)
    print(f"Chat ID: {CHAT_ID}")
    print(f"Documentación procesada: {DEMO_URL}")
    print(f"Total de preguntas: {len(questions)}")
    print("\nPuedes continuar interactuando con el agente usando:")
    print(f"curl -X POST {API_BASE_URL}/api/v1/chat/{CHAT_ID} \\")
    print("     -H 'Content-Type: application/json' \\")
    print("     -d '{\"message\": \"Tu pregunta aquí\", \"user_id\": \"tu_usuario\"}'")


if __name__ == "__main__":
    demo()