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
Script inteligente para desplegar solo los agentes que han sido modificados.

Este script analiza los cambios en Git para determinar qué agentes necesitan
ser redespliegados, optimizando el proceso de CI/CD.
"""

import argparse
import logging
import subprocess
import sys
from pathlib import Path
from typing import List, Set

# Importar el deployer existente
from deployment.deploy_multiple_agents import MultiAgentDeployer


class IntelligentAgentDeployer:
    """Deployer inteligente que detecta cambios y despliega solo agentes modificados."""
    
    def __init__(self, project: str, location: str, staging_bucket_prefix: str = None):
        """
        Inicializa el deployer inteligente.
        
        Args:
            project: ID del proyecto de Google Cloud
            location: Región de despliegue
            staging_bucket_prefix: Prefijo para buckets de staging
        """
        self.project = project
        self.location = location
        self.deployer = MultiAgentDeployer(project, location, staging_bucket_prefix)
        self.logger = logging.getLogger(__name__)
        logging.basicConfig(level=logging.INFO)
        
        # Mapeo de directorios a agentes
        self.agent_directories = {
            "app/summarize_agent/": "summarize_agent",
            "app/chat_agent/": "chat_agent", 
            "app/alert_agent/": "alert_agent"
        }
        
        # Archivos que afectan a todos los agentes (solo cambios críticos)
        self.global_files = {
            "app/utils/",
            "deployment/deploy_multiple_agents.py",
            "deployment/deploy_changed_agents.py"
        }
    
    def get_changed_files(self, base_ref: str = "HEAD~1") -> List[str]:
        """
        Obtiene la lista de archivos modificados desde la referencia base.
        
        Args:
            base_ref: Referencia base para comparar (por defecto último commit)
            
        Returns:
            Lista de archivos modificados
        """
        try:
            # Obtener archivos modificados desde el commit base
            result = subprocess.run(
                ["git", "diff", "--name-only", base_ref, "HEAD"],
                capture_output=True,
                text=True,
                check=True
            )
            
            changed_files = result.stdout.strip().split('\n') if result.stdout.strip() else []
            self.logger.info(f"📁 Changed files detected: {len(changed_files)}")
            for file in changed_files:
                self.logger.info(f"   - {file}")
            
            return changed_files
            
        except subprocess.CalledProcessError as e:
            self.logger.warning(f"Could not get git diff: {e}")
            # Si no podemos obtener el diff, asumimos que todos los agentes necesitan actualización
            return ["app/"]
        except FileNotFoundError:
            self.logger.warning("Git not found, deploying all agents")
            return ["app/"]
    
    def analyze_affected_agents(self, changed_files: List[str]) -> Set[str]:
        """
        Analiza qué agentes están afectados por los archivos modificados.
        
        Args:
            changed_files: Lista de archivos modificados
            
        Returns:
            Set de nombres de agentes que necesitan ser redespliegados
        """
        affected_agents = set()
        
        # Verificar si hay cambios globales que afectan a todos los agentes
        global_changes = any(
            any(changed_file.startswith(global_pattern) for global_pattern in self.global_files)
            for changed_file in changed_files
        )
        
        if global_changes:
            self.logger.info("🌍 Global changes detected, all agents will be deployed")
            return set(self.agent_directories.values())
        
        # Verificar cambios específicos por agente
        for changed_file in changed_files:
            for agent_dir, agent_name in self.agent_directories.items():
                if changed_file.startswith(agent_dir):
                    affected_agents.add(agent_name)
                    self.logger.info(f"🎯 Agent {agent_name} affected by changes in {changed_file}")
        
        return affected_agents
    
    def deploy_changed_agents(
        self, 
        base_ref: str = "HEAD~1",
        requirements_file: str = ".requirements.txt",
        env_vars: dict = None,
        force_all: bool = False
    ) -> dict:
        """
        Despliega solo los agentes que han sido modificados.
        
        Args:
            base_ref: Referencia base para comparar cambios
            requirements_file: Archivo de requirements
            env_vars: Variables de entorno adicionales
            force_all: Forzar despliegue de todos los agentes
            
        Returns:
            Diccionario con los agentes desplegados
        """
        if force_all:
            self.logger.info("🚀 Force deployment of all agents requested")
            affected_agents = set(self.agent_directories.values())
        else:
            # Detectar archivos modificados
            changed_files = self.get_changed_files(base_ref)
            
            if not changed_files or (len(changed_files) == 1 and changed_files[0] == ''):
                self.logger.info("📭 No changes detected, skipping deployment")
                return {}
            
            # Analizar agentes afectados
            affected_agents = self.analyze_affected_agents(changed_files)
        
        if not affected_agents:
            self.logger.info("📭 No agents affected by changes, skipping deployment")
            return {}
        
        self.logger.info(f"🎯 Deploying {len(affected_agents)} affected agents: {', '.join(affected_agents)}")
        
        # Desplegar solo los agentes afectados usando el mismo método que funciona
        deployed_agents = {}
        
        for agent_name in affected_agents:
            try:
                remote_agent = self.deployer.deploy_agent(agent_name, requirements_file, env_vars)
                deployed_agents[agent_name] = remote_agent
                self.logger.info(f"✅ Successfully deployed {agent_name}")
            except Exception as e:
                self.logger.error(f"❌ Failed to deploy {agent_name}: {e}")
                continue
        
        return deployed_agents


def main():
    """Función principal para ejecutar el script."""
    parser = argparse.ArgumentParser(
        description="Deploy only changed agents to Vertex AI Agent Engine"
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
        "--base-ref",
        default="HEAD~1",
        help="Git reference to compare against (defaults to HEAD~1)",
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
    parser.add_argument(
        "--force-all",
        action="store_true",
        help="Force deployment of all agents regardless of changes",
    )
    
    args = parser.parse_args()
    
    # Configurar proyecto
    if not args.project:
        import google.auth
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
    ║   🧠 INTELLIGENT AGENT DEPLOYMENT TO VERTEX AI 🧠                 ║
    ║                                                                   ║
    ╚═══════════════════════════════════════════════════════════════════╝
    """)
    
    try:
        # Crear deployer inteligente
        deployer = IntelligentAgentDeployer(
            project=args.project,
            location=args.location,
            staging_bucket_prefix=args.staging_bucket_prefix
        )
        
        # Desplegar agentes modificados
        deployed_agents = deployer.deploy_changed_agents(
            base_ref=args.base_ref,
            requirements_file=args.requirements_file,
            env_vars=env_vars,
            force_all=args.force_all
        )
        
        print(f"\n🎉 Intelligent Deployment Summary:")
        if deployed_agents:
            for agent_name, agent in deployed_agents.items():
                print(f"   ✅ {agent_name}: {agent.resource_name}")
        else:
            print("   📭 No agents needed deployment")
            
    except Exception as e:
        print(f"\n❌ Intelligent deployment failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
