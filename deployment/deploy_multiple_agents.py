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
Script para desplegar múltiples agentes en Vertex AI Agent Engine.

Este script permite desplegar varios agentes especializados en diferentes aspectos
de la atención médica, siguiendo la estructura ADK estándar.
"""

import argparse
import datetime
import json
import logging
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional

import google.auth
import vertexai
from google.adk.artifacts import GcsArtifactService
from google.cloud import logging as google_cloud_logging
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider, export
from vertexai import agent_engines
from vertexai.preview.reasoning_engines import AdkApp

# Agregar el directorio raíz al path para importar los agentes
sys.path.append(str(Path(__file__).parent.parent))

from app.utils.gcs import create_bucket_if_not_exists
from app.utils.tracing import CloudTraceLoggingSpanExporter
from app.utils.typing import Feedback


class MultiAgentDeployer:
    """Clase para gestionar el despliegue de múltiples agentes."""
    
    def __init__(self, project: str, location: str, staging_bucket_prefix: str = None):
        """
        Inicializa el deployer para múltiples agentes.
        
        Args:
            project: ID del proyecto de Google Cloud
            location: Región de despliegue
            staging_bucket_prefix: Prefijo para buckets de staging
        """
        self.project = project
        self.location = location
        self.staging_bucket_prefix = staging_bucket_prefix or f"{project}-agents"
        
        # Configurar Vertex AI - se configurará por agente para evitar conflictos
        self.base_staging_bucket = f"{self.staging_bucket_prefix}-staging"
        
        # Configurar logging
        self.logger = logging.getLogger(__name__)
        logging.basicConfig(level=logging.INFO)
        
    def _setup_buckets(self) -> None:
        """Crea los buckets necesarios para el despliegue."""
        buckets_to_create = [
            f"{self.staging_bucket_prefix}-staging",
            f"{self.staging_bucket_prefix}-artifacts"
        ]
        
        for bucket_name in buckets_to_create:
            try:
                create_bucket_if_not_exists(
                    bucket_name=bucket_name,
                    project=self.project,
                    location=self.location
                )
                self.logger.info(f"✅ Bucket {bucket_name} ready")
            except Exception as e:
                self.logger.error(f"❌ Error creating bucket {bucket_name}: {e}")
                raise
    
    def _get_agent_config(self, agent_name: str) -> Dict:
        """
        Obtiene la configuración específica para cada agente.
        
        Args:
            agent_name: Nombre del agente
            
        Returns:
            Diccionario con la configuración del agente
        """
        configs = {
            "summarize_agent": {
                "description": "Specialized summarization agent for creating concise summaries, key points extraction, and executive summaries",
                "display_name": "Summarize Agent",
                "extra_packages": ["./app"]
            },
            "chat_agent": {
                "description": "Friendly and knowledgeable conversational agent for general assistance and engaging dialogue", 
                "display_name": "Chat Agent",
                "extra_packages": ["./app"]
            },
            "alert_agent": {
                "description": "Specialized alert management agent for creating, monitoring, and managing system notifications",
                "display_name": "Alert Agent", 
                "extra_packages": ["./app"]
            }
        }
        
        return configs.get(agent_name, {})
    
    def _create_agent_engine_app(self, agent_name: str) -> AdkApp:
        """
        Crea una instancia de AgentEngineApp para un agente específico.
        
        Args:
            agent_name: Nombre del agente
            
        Returns:
            Instancia de AdkApp configurada
        """
        try:
            # Importar dinámicamente el agente desde app/
            agent_module = __import__(f"app.{agent_name}.agent", fromlist=["root_agent"])
            root_agent = agent_module.root_agent
            
            class AgentEngineApp(AdkApp):
                def set_up(self) -> None:
                    """Set up logging and tracing for the agent engine app."""
                    super().set_up()
                    logging_client = google_cloud_logging.Client()
                    self.logger = logging_client.logger(agent_name)
                    provider = TracerProvider()
                    processor = export.BatchSpanProcessor(
                        CloudTraceLoggingSpanExporter(
                            project_id=os.environ.get("GOOGLE_CLOUD_PROJECT")
                        )
                    )
                    provider.add_span_processor(processor)
                    trace.set_tracer_provider(provider)

                def register_feedback(self, feedback: dict) -> None:
                    """Collect and log feedback."""
                    feedback_obj = Feedback.model_validate(feedback)
                    self.logger.log_struct(feedback_obj.model_dump(), severity="INFO")

                def register_operations(self) -> dict:
                    """Registers the operations of the Agent."""
                    operations = super().register_operations()
                    operations[""] = operations[""] + ["register_feedback"]
                    return operations

                def clone(self) -> "AgentEngineApp":
                    """Returns a clone of the ADK application."""
                    template_attributes = self._tmpl_attrs
                    return self.__class__(
                        agent=template_attributes["agent"],
                        enable_tracing=bool(template_attributes.get("enable_tracing", False)),
                        session_service_builder=template_attributes.get("session_service_builder"),
                        artifact_service_builder=template_attributes.get("artifact_service_builder"),
                        env_vars=template_attributes.get("env_vars"),
                    )
            
            return AgentEngineApp(
                agent=root_agent,
                artifact_service_builder=lambda: GcsArtifactService(
                    bucket_name=f"{self.staging_bucket_prefix}-artifacts"
                ),
            )
            
        except ImportError as e:
            self.logger.error(f"❌ Error importing agent {agent_name}: {e}")
            raise
        except Exception as e:
            self.logger.error(f"❌ Error creating AgentEngineApp for {agent_name}: {e}")
            raise
    
    def deploy_agent(
        self, 
        agent_name: str, 
        requirements_file: str = ".requirements.txt",
        env_vars: Optional[Dict[str, str]] = None
    ) -> agent_engines.AgentEngine:
        """
        Despliega un agente específico en Vertex AI Agent Engine.
        
        Args:
            agent_name: Nombre del agente a desplegar
            requirements_file: Archivo de requirements
            env_vars: Variables de entorno adicionales
            
        Returns:
            Instancia del agente desplegado
        """
        self.logger.info(f"🚀 Deploying agent: {agent_name}")
        
        try:
            # Configurar Vertex AI con el bucket base (usaremos prefijos para separar agentes)
            vertexai.init(
                project=self.project, 
                location=self.location, 
                staging_bucket=f"gs://{self.base_staging_bucket}"
            )
            
            # Obtener configuración del agente
            agent_config = self._get_agent_config(agent_name)
            if not agent_config:
                raise ValueError(f"No configuration found for agent: {agent_name}")
            
            # Leer requirements
            if os.path.exists(requirements_file):
                with open(requirements_file) as f:
                    requirements = f.read().strip().split("\n")
            else:
                self.logger.warning(f"Requirements file {requirements_file} not found, using defaults")
                requirements = ["google-cloud-aiplatform[adk,agent_engines]"]
            
            # Crear AgentEngineApp
            agent_engine_app = self._create_agent_engine_app(agent_name)
            
            # Configurar variables de entorno
            final_env_vars = {"NUM_WORKERS": "1"}
            if env_vars:
                final_env_vars.update(env_vars)
            
            # Configuración de despliegue
            deployment_config = {
                "agent_engine": agent_engine_app,
                "display_name": agent_config["display_name"],
                "description": agent_config["description"],
                "extra_packages": agent_config["extra_packages"],
                "requirements": requirements,
                "env_vars": final_env_vars,
            }
            
            # Verificar si el agente ya existe buscando por display_name
            existing_agents = []
            try:
                all_agents = list(agent_engines.list())
                existing_agents = [
                    agent for agent in all_agents 
                    if agent.display_name == agent_config['display_name']
                ]
            except Exception as e:
                self.logger.warning(f"Could not list existing agents: {e}")
            
            if existing_agents:
                self.logger.info(f"📝 Updating existing agent: {agent_config['display_name']}")
                remote_agent = existing_agents[0].update(**deployment_config)
            else:
                self.logger.info(f"🆕 Creating new agent: {agent_config['display_name']}")
                remote_agent = agent_engines.create(**deployment_config)
            
            self.logger.info(f"✅ Successfully deployed {agent_name}")
            self.logger.info(f"   Resource name: {remote_agent.resource_name}")
            
            return remote_agent
            
        except Exception as e:
            self.logger.error(f"❌ Error deploying agent {agent_name}: {e}")
            raise
    
    def deploy_all_agents(
        self, 
        agents: Optional[List[str]] = None,
        requirements_file: str = ".requirements.txt",
        env_vars: Optional[Dict[str, str]] = None
    ) -> Dict[str, agent_engines.AgentEngine]:
        """
        Despliega todos los agentes especificados.
        
        Args:
            agents: Lista de agentes a desplegar (None para todos)
            requirements_file: Archivo de requirements
            env_vars: Variables de entorno adicionales
            
        Returns:
            Diccionario con los agentes desplegados
        """
        if agents is None:
            agents = ["summarize_agent", "chat_agent", "alert_agent"]
        
        self.logger.info(f"🚀 Starting deployment of {len(agents)} agents")
        self.logger.info(f"   Project: {self.project}")
        self.logger.info(f"   Location: {self.location}")
        
        # Configurar buckets
        self._setup_buckets()
        
        deployed_agents = {}
        deployment_metadata = {
            "deployment_timestamp": datetime.datetime.now().isoformat(),
            "project": self.project,
            "location": self.location,
            "agents": {}
        }
        
        for i, agent_name in enumerate(agents):
            try:
                # Pequeño delay entre despliegues para evitar conflictos de archivos
                if i > 0:
                    import time
                    self.logger.info(f"⏳ Waiting 10 seconds before deploying {agent_name}...")
                    time.sleep(10)
                
                remote_agent = self.deploy_agent(agent_name, requirements_file, env_vars)
                deployed_agents[agent_name] = remote_agent
                
                # Guardar metadata
                deployment_metadata["agents"][agent_name] = {
                    "resource_name": remote_agent.resource_name,
                    "display_name": self._get_agent_config(agent_name)["display_name"],
                    "status": "deployed"
                }
                
            except Exception as e:
                self.logger.error(f"❌ Failed to deploy {agent_name}: {e}")
                deployment_metadata["agents"][agent_name] = {
                    "status": "failed",
                    "error": str(e)
                }
                # Continuar con los otros agentes
                continue
        
        # Guardar metadata de despliegue
        metadata_file = f"deployment_metadata_multiple_agents.json"
        with open(metadata_file, "w") as f:
            json.dump(deployment_metadata, f, indent=2)
        
        self.logger.info(f"📋 Deployment metadata saved to {metadata_file}")
        self.logger.info(f"✅ Deployment completed. {len(deployed_agents)}/{len(agents)} agents deployed successfully")
        
        return deployed_agents


def main():
    """Función principal para ejecutar el script."""
    parser = argparse.ArgumentParser(
        description="Deploy multiple agents to Vertex AI Agent Engine"
    )
    
    parser.add_argument(
        "--project",
        default=None,
        help="GCP project ID (defaults to application default credentials)",
    )
    parser.add_argument(
        "--location",
        default="us-central1",
        help="GCP region (defaults to us-central1)",
    )
    parser.add_argument(
        "--agents",
        nargs="+",
        default=None,
        help="List of agents to deploy (defaults to all agents)",
        choices=["summarize_agent", "chat_agent", "alert_agent"]
    )
    parser.add_argument(
        "--requirements-file",
        default=".requirements.txt",
        help="Path to requirements.txt file",
    )
    parser.add_argument(
        "--staging-bucket-prefix",
        default=None,
        help="Prefix for staging buckets (defaults to PROJECT-agents)",
    )
    parser.add_argument(
        "--set-env-vars",
        help="Comma-separated list of environment variables in KEY=VALUE format",
    )
    
    args = parser.parse_args()
    
    # Configurar proyecto
    if not args.project:
        _, args.project = google.auth.default()
    
    # Configurar variables de entorno
    env_vars = {}
    if args.set_env_vars:
        for pair in args.set_env_vars.split(","):
            key, value = pair.split("=", 1)
            env_vars[key] = value
    
    print("""
    ╔═══════════════════════════════════════════════════════════════════╗
    ║                                                                   ║
    ║   🏥 DEPLOYING MULTIPLE MEDICAL AGENTS TO VERTEX AI 🏥            ║
    ║                                                                   ║
    ╚═══════════════════════════════════════════════════════════════════╝
    """)
    
    try:
        # Crear deployer
        deployer = MultiAgentDeployer(
            project=args.project,
            location=args.location,
            staging_bucket_prefix=args.staging_bucket_prefix
        )
        
        # Desplegar agentes
        deployed_agents = deployer.deploy_all_agents(
            agents=args.agents,
            requirements_file=args.requirements_file,
            env_vars=env_vars
        )
        
        print(f"\n🎉 Deployment Summary:")
        for agent_name, agent in deployed_agents.items():
            print(f"   ✅ {agent_name}: {agent.resource_name}")
        
        if len(deployed_agents) == 0:
            print("   ❌ No agents were deployed successfully")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n❌ Deployment failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
