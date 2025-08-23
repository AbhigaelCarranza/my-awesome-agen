#!/usr/bin/env python3
# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Script para probar múltiples agentes localmente antes del despliegue.

Este script permite validar que todos los agentes funcionan correctamente
antes de desplegarlos en Vertex AI Agent Engine.
"""

import asyncio
import sys
from pathlib import Path

# Agregar el directorio raíz al path para importar los agentes
sys.path.append(str(Path(__file__).parent))

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types as genai_types


async def test_agent(agent_name: str, test_query: str) -> str:
    """
    Prueba un agente específico con una consulta de prueba.
    
    Args:
        agent_name: Nombre del agente a probar
        test_query: Consulta de prueba
        
    Returns:
        Respuesta del agente
    """
    try:
        # Importar dinámicamente el agente desde app/
        agent_module = __import__(f"app.{agent_name}.agent", fromlist=["root_agent"])
        root_agent = agent_module.root_agent
        
        # Crear session service y runner
        session_service = InMemorySessionService()
        await session_service.create_session(
            app_name=agent_name, 
            user_id="test_user", 
            session_id="test_session"
        )
        
        runner = Runner(
            agent=root_agent, 
            app_name=agent_name, 
            session_service=session_service
        )
        
        # Ejecutar la consulta
        response_parts = []
        async for event in runner.run_async(
            user_id="test_user",
            session_id="test_session",
            new_message=genai_types.Content(
                role="user", 
                parts=[genai_types.Part.from_text(text=test_query)]
            ),
        ):
            if event.is_final_response() and event.content and event.content.parts:
                response_parts.append(event.content.parts[0].text)
        
        return "\n".join(response_parts) if response_parts else "No response received"
        
    except Exception as e:
        return f"Error testing {agent_name}: {str(e)}"


async def test_all_agents():
    """Prueba todos los agentes con consultas específicas."""
    
    test_cases = {
        "summarize_agent": "Summarize this quarterly business report with key points",
        "chat_agent": "Hello! Can you help me understand artificial intelligence?",
        "alert_agent": "Create a critical alert for system downtime"
    }
    
    print("""
    ╔═══════════════════════════════════════════════════════════════════╗
    ║                                                                   ║
    ║   🧪 TESTING MULTIPLE BUSINESS AGENTS LOCALLY 🧪                  ║
    ║                                                                   ║
    ╚═══════════════════════════════════════════════════════════════════╝
    """)
    
    for agent_name, test_query in test_cases.items():
        print(f"\n🤖 Testing {agent_name}...")
        print(f"   Query: {test_query}")
        print("   " + "="*60)
        
        response = await test_agent(agent_name, test_query)
        
        # Truncar respuesta si es muy larga
        if len(response) > 500:
            response = response[:500] + "... (truncated)"
        
        print(f"   Response: {response}")
        print("   " + "="*60)
        
        # Determinar si la prueba fue exitosa
        if "Error testing" in response:
            print("   ❌ FAILED")
        else:
            print("   ✅ PASSED")


async def main():
    """Función principal."""
    try:
        await test_all_agents()
        print(f"\n🎉 All agent tests completed!")
        
    except Exception as e:
        print(f"\n❌ Testing failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
