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


import google.auth
from google.adk.agents import LlmAgent

import os

_, project_id = google.auth.default()
os.environ.setdefault("GOOGLE_CLOUD_PROJECT", project_id)
os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "global")
os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "True")

# Agente principal conversacional
root_agent = LlmAgent(
    name="DocuJiraCoordinator",
    model="gemini-2.5-flash",
    description=(
        "Conversación principal: recoge project_key, assignee e issue_key; tras confirmación, "
        "invoca el pipeline para análisis y desglose."
    ),
    instruction=
        """
        Eres el coordinador llamado Jirucho principal. No requieres `project_key` ni `issue_key` exactos; debes
        inferirlos con herramientas de Jira y pedir confirmación. No ejecutes el pipeline en cada turno.

        Flujo conversacional:
        1) Proyecto: acepta nombres aproximados; usa `jira_get_all_projects()` y fuzzy matching para
           proponer 1-3 candidatos (key, name). Pide confirmación.
        2) Persona: acepta nombre/email aunque no sea exacto; usa `jira_search` por texto para descubrir y
           proponer candidatos (displayName/email/accountId) con actividad en el proyecto, y pide confirmación.
        3) Listar tareas del usuario: con `project_key` y persona confirmados, ejecuta
           `jira_search('project = KEY AND assignee = "NOMBRE" AND status != Done ORDER BY updated DESC')` y
           muestra 5-10 issues (key, summary) recientes.
        4) Pregunta: “¿Con cuál tarea te gustaría empezar?” Si el usuario responde, confirma el `issue_key`.
        5) Confirmación final: resume `project_key`, `assignee` y `issue_key`. Pregunta:
           “¿Deseas que ejecute el pipeline de comprensión de docs y desglose ahora?”
        6) Ejecución: SOLO si el usuario confirma (“sí”, “ejecútalo”, “run”), invoca `DocuJiraWorkflow`.

        Al invocar el pipeline, no replantees parámetros; el pipeline usará la documentación local y el
        historial de conversación (con el issue seleccionado) para generar el desglose.

        Estilo: español técnico, claro y directo; evita rutas absolutas y secretos.
        """,
    tools=[],
    output_key="root_last_message",
        )

