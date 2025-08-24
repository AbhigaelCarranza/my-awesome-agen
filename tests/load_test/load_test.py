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

import json
import logging
import os
import time

from locust import HttpUser, between, task

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Initialize Vertex AI and load agent config
# Load multiple agents metadata
with open("deployment_metadata_multiple_agents.json") as f:
    metadata = json.load(f)

# Get the agent to test (default to chat_agent, or from environment variable)
agent_to_test = os.environ.get("LOAD_TEST_AGENT", "chat_agent")
logger.info(f"Testing agent: {agent_to_test}")

# Get the specific agent's resource name
if agent_to_test not in metadata["agents"]:
    available_agents = list(metadata["agents"].keys())
    logger.error(f"Agent '{agent_to_test}' not found. Available agents: {available_agents}")
    raise ValueError(f"Agent '{agent_to_test}' not found in deployment metadata")

agent_info = metadata["agents"][agent_to_test]
remote_agent_engine_id = agent_info["resource_name"]

parts = remote_agent_engine_id.split("/")
project_id = parts[1]
location = parts[3]
engine_id = parts[5]

# Convert remote agent engine ID to streaming URL.
base_url = f"https://{location}-aiplatform.googleapis.com"
url_path = f"/v1beta1/projects/{project_id}/locations/{location}/reasoningEngines/{engine_id}:streamQuery"

logger.info("Using remote agent engine ID: %s", remote_agent_engine_id)
logger.info("Using base URL: %s", base_url)
logger.info("Using URL path: %s", url_path)


class ChatStreamUser(HttpUser):
    """Simulates a user interacting with the chat stream API."""

    wait_time = between(1, 3)  # Wait 1-3 seconds between tasks
    host = base_url  # Set the base host URL for Locust

    @task
    def chat_stream(self) -> None:
        """Simulates a chat stream interaction."""
        headers = {"Content-Type": "application/json"}
        headers["Authorization"] = f"Bearer {os.environ['_AUTH_TOKEN']}"

        # Customize message based on the agent being tested
        messages = {
            "chat_agent": "Hello! Can you help me understand artificial intelligence?",
            "summarize_agent": "Please summarize this quarterly business report with key points",
            "alert_agent": "Create a critical alert for system downtime"
        }
        
        test_message = messages.get(agent_to_test, "Hello, how can you help me?")
        
        data = {
            "input": {
                "message": test_message,
                "user_id": "test",
            }
        }

        start_time = time.time()
        with self.client.post(
            url_path,
            headers=headers,
            json=data,
            catch_response=True,
            name="/stream_messages first message",
            stream=True,
            params={"alt": "sse"},
        ) as response:
            if response.status_code == 200:
                events = []
                for line in response.iter_lines():
                    if line:
                        line_str = line.decode("utf-8")
                        events.append(line_str)

                        if "429 Too Many Requests" in line_str:
                            self.environment.events.request.fire(
                                request_type="POST",
                                name=f"{url_path} rate_limited 429s",
                                response_time=0,
                                response_length=len(line),
                                response=response,
                                context={},
                            )
                end_time = time.time()
                total_time = end_time - start_time
                self.environment.events.request.fire(
                    request_type="POST",
                    name="/stream_messages end",
                    response_time=total_time * 1000,  # Convert to milliseconds
                    response_length=len(events),
                    response=response,
                    context={},
                )
            else:
                response.failure(f"Unexpected status code: {response.status_code}")
