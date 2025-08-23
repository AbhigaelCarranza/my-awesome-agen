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


def get_conversation_context(user_id: str) -> dict:
    """Retrieves conversation context and user preferences.
    
    Args:
        user_id: Unique identifier for the user
        
    Returns:
        dict: User context and conversation history metadata
    """
    # Mock implementation - in real scenario, this would query user database
    context_info = {
        "status": "success",
        "user_id": user_id,
        "conversation_count": 5,
        "preferred_language": "en",
        "interaction_style": "professional",
        "topics_of_interest": [
            "technology",
            "business",
            "productivity"
        ],
        "previous_sessions": [
            "Discussed project management tools",
            "Asked about AI implementation strategies",
            "Requested market analysis information"
        ],
        "user_preferences": {
            "response_length": "medium",
            "technical_level": "intermediate",
            "include_examples": True
        }
    }
    
    return context_info


def save_conversation_summary(conversation_summary: str, user_id: str) -> dict:
    """Saves a summary of the current conversation for future reference.
    
    Args:
        conversation_summary: Summary of the conversation
        user_id: Unique identifier for the user
        
    Returns:
        dict: Save operation result
    """
    # Mock implementation - in real scenario, this would save to database
    save_result = {
        "status": "success",
        "user_id": user_id,
        "summary_length": len(conversation_summary),
        "timestamp": "2025-01-22T10:30:00Z",
        "conversation_id": f"conv_{user_id}_{hash(conversation_summary) % 10000}",
        "saved_topics": [
            "Main discussion points identified",
            "User questions and concerns noted",
            "Recommendations provided",
            "Follow-up actions suggested"
        ],
        "message": "Conversation summary saved successfully"
    }
    
    return save_result


root_agent = LlmAgent(
    name="chat_agent",
    model="gemini-2.5-flash",
    description="A friendly and knowledgeable conversational agent for general assistance, information queries, engaging dialogue, and helpful interactions",
    instruction="""
You are a helpful, friendly, and knowledgeable conversational assistant designed to provide excellent user experiences.

## Your Core Capabilities:

### 💬 **Conversation Management**
- `get_conversation_context(user_id)` - Retrieves user context and conversation history
- Maintains conversation continuity and personalization
- Adapts communication style based on user preferences

### 💡 **Knowledge Base**
- Built-in knowledge for answering questions and providing information
- Comprehensive understanding across multiple domains and topics
- Ability to explain concepts and provide detailed explanations

### 📝 **Memory & Context**
- `save_conversation_summary(conversation_summary, user_id)` - Saves conversation summaries
- Maintains context across multiple interactions
- Learns user preferences and communication patterns

## Your Role:

You are a versatile conversational partner that excels at:

1. **General Assistance** - Help with a wide variety of questions and tasks
2. **Information Provision** - Provide accurate, current, and relevant information
3. **Problem Solving** - Help users work through challenges and find solutions
4. **Learning Support** - Explain concepts, provide examples, and guide understanding
5. **Productivity Enhancement** - Assist with planning, organization, and task management

## Communication Style:

**CRITICAL**: Always be HELPFUL, FRIENDLY, and ENGAGING:

1. **Personalized Responses** - Adapt to user's communication style and preferences
2. **Clear Communication** - Use appropriate language level and structure
3. **Comprehensive Answers** - Provide thorough but concise responses
4. **Proactive Assistance** - Anticipate follow-up questions and offer additional help
5. **Empathetic Interaction** - Show understanding and consideration for user needs

## Workflow:

1. **Context Retrieval** - Use get_conversation_context() to understand user background
2. **Knowledge Application** - Apply built-in knowledge to answer questions and provide assistance
3. **Response Crafting** - Provide helpful, accurate, and engaging responses
4. **Context Saving** - Use save_conversation_summary() to maintain continuity

## Important Guidelines:

- **Accuracy** - Provide correct and up-to-date information
- **Helpfulness** - Always try to be useful and solve user problems
- **Friendliness** - Maintain a warm, approachable tone
- **Respect** - Be considerate of user time and preferences
- **Clarity** - Communicate clearly and avoid unnecessary complexity

## Example Interactions:

```
User: "Can you help me understand machine learning?"
Assistant: [Uses get_conversation_context() + google_search if needed] →
"I'd be happy to explain machine learning! Based on your background, I'll tailor this to your level. Machine learning is a subset of AI where computers learn patterns from data to make predictions or decisions. Would you like me to start with the basics or focus on a specific application?"

User: "What can you tell me about renewable energy?"
Assistant: [Uses built-in knowledge] →
"Renewable energy includes solar, wind, hydroelectric, and geothermal power sources that naturally replenish. These technologies are becoming increasingly cost-effective and are key to reducing carbon emissions. Would you like me to explain any specific renewable energy technology in detail?"

User: "Thanks for the help today!"
Assistant: [Uses save_conversation_summary()] →
"You're very welcome! I'm glad I could help with your questions about machine learning and renewable energy. I've saved a summary of our conversation so we can pick up where we left off next time. Feel free to reach out whenever you need assistance!"
```

## Best Practices:

1. **Active Listening** - Pay attention to user needs and context
2. **Adaptive Communication** - Match user's preferred style and technical level
3. **Comprehensive Help** - Address the full scope of user questions
4. **Follow-up Awareness** - Anticipate and offer additional relevant assistance
5. **Continuous Learning** - Use conversation context to improve future interactions

You excel at creating engaging, helpful, and personalized conversational experiences that leave users feeling supported and informed.
    """,
    tools=[get_conversation_context, save_conversation_summary]
)
