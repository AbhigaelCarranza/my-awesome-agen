# Install dependencies using uv package manager
install:
	@command -v uv >/dev/null 2>&1 || { echo "uv is not installed. Installing uv..."; curl -LsSf https://astral.sh/uv/0.6.12/install.sh | sh; source $HOME/.local/bin/env; }
	uv sync --dev --extra jupyter

# Launch local dev playground
playground:
	@echo "==============================================================================="
	@echo "| 🚀 Starting your agent playground...                                        |"
	@echo "|                                                                             |"
	@echo "| 💡 Try asking: What's the weather in San Francisco?                         |"
	@echo "|                                                                             |"
	@echo "| 🔍 IMPORTANT: Select the 'app' folder to interact with your agent.          |"
	@echo "==============================================================================="
	uv run adk web --port 8501

# Deploy single agent (legacy)
backend:
	# Export dependencies to requirements file using uv export.
	uv export --no-hashes --no-header --no-dev --no-emit-project --no-annotate > .requirements.txt 2>/dev/null || \
	uv export --no-hashes --no-header --no-dev --no-emit-project > .requirements.txt && uv run app/agent_engine_app.py

# Deploy multiple agents to Vertex AI Agent Engine
deploy-multiple:
	@echo "==============================================================================="
	@echo "| 🚀 Deploying multiple business agents to Vertex AI Agent Engine...         |"
	@echo "==============================================================================="
	# Export dependencies to requirements file using uv export.
	uv export --no-hashes --no-header --no-dev --no-emit-project --no-annotate > .requirements.txt 2>/dev/null || \
	uv export --no-hashes --no-header --no-dev --no-emit-project > .requirements.txt
	uv run python deployment/deploy_multiple_agents.py

# Deploy specific agents
deploy-agents:
	@echo "==============================================================================="
	@echo "| 🚀 Deploying specific agents to Vertex AI Agent Engine...                  |"
	@echo "| Usage: make deploy-agents AGENTS='summarize_agent chat_agent'              |"
	@echo "==============================================================================="
	uv export --no-hashes --no-header --no-dev --no-emit-project --no-annotate > .requirements.txt 2>/dev/null || \
	uv export --no-hashes --no-header --no-dev --no-emit-project > .requirements.txt
	uv run python deployment/deploy_multiple_agents.py --agents $(AGENTS)

# Test multiple agents locally
test-agents:
	@echo "==============================================================================="
	@echo "| 🧪 Testing multiple agents locally...                                      |"
	@echo "==============================================================================="
	uv run python test_multiple_agents.py

# Deploy only changed agents (intelligent deployment)
deploy-changed:
	@echo "==============================================================================="
	@echo "| 🧠 Deploying only changed agents to Vertex AI Agent Engine...              |"
	@echo "==============================================================================="
	@echo "| ⚠️  Note: This uses git diff to detect changes. If you want to force       |"
	@echo "| deployment of all agents, use 'make deploy-multiple' instead.              |"
	@echo "| Usage: make deploy-changed BASE_REF=origin/main (to compare against main)   |"
	@echo "==============================================================================="
	# Export dependencies to requirements file using uv export.
	uv export --no-hashes --no-header --no-dev --no-emit-project --no-annotate > .requirements.txt 2>/dev/null || \
	uv export --no-hashes --no-header --no-dev --no-emit-project > .requirements.txt
	uv run python deployment/deploy_changed_agents.py --base-ref $(or $(BASE_REF),HEAD~1)

# Force deploy all agents
deploy-force:
	@echo "==============================================================================="
	@echo "| 🚀 Force deploying all agents to Vertex AI Agent Engine...                 |"
	@echo "==============================================================================="
	# Export dependencies to requirements file using uv export.
	uv export --no-hashes --no-header --no-dev --no-emit-project --no-annotate > .requirements.txt 2>/dev/null || \
	uv export --no-hashes --no-header --no-dev --no-emit-project > .requirements.txt
	uv run python deployment/deploy_changed_agents.py --force-all

# Set up development environment resources using Terraform
setup-dev-env:
	PROJECT_ID=$$(gcloud config get-value project) && \
	(cd deployment/terraform/dev && terraform init && terraform apply --var-file vars/env.tfvars --var dev_project_id=$$PROJECT_ID --auto-approve)

# Run unit and integration tests
test:
	uv run pytest tests/unit && uv run pytest tests/integration

# Run code quality checks (codespell, ruff, mypy)
lint:
	uv run codespell
	uv run ruff check . --diff
	uv run ruff format . --check --diff
	uv run mypy .