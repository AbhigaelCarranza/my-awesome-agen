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
from datetime import datetime, timedelta

import os

_, project_id = google.auth.default()
os.environ.setdefault("GOOGLE_CLOUD_PROJECT", project_id)
os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "global")
os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "True")


def create_alert(alert_type: str, message: str, severity: str = "medium", recipient: str = "default") -> dict:
    """Creates a new alert with specified parameters.
    
    Args:
        alert_type: Type of alert (system, security, business, maintenance)
        message: Alert message content
        severity: Alert severity level (low, medium, high, critical)
        recipient: Target recipient or group
        
    Returns:
        dict: Alert creation result and metadata
    """
    alert_id = f"alert_{hash(message) % 100000}_{datetime.now().strftime('%Y%m%d%H%M')}"
    
    alert_result = {
        "status": "success",
        "alert_id": alert_id,
        "alert_type": alert_type,
        "message": message,
        "severity": severity,
        "recipient": recipient,
        "created_at": datetime.now().isoformat(),
        "estimated_delivery": (datetime.now() + timedelta(minutes=2)).isoformat(),
        "channels": ["email", "dashboard", "mobile"] if severity in ["high", "critical"] else ["dashboard"],
        "escalation_policy": "auto_escalate" if severity == "critical" else "manual",
        "acknowledgment_required": severity in ["high", "critical"]
    }
    
    return alert_result


def check_alert_status(alert_id: str) -> dict:
    """Checks the status of an existing alert.
    
    Args:
        alert_id: Unique identifier of the alert
        
    Returns:
        dict: Alert status and delivery information
    """
    # Mock implementation - in real scenario, this would query alert system
    status_info = {
        "status": "success",
        "alert_id": alert_id,
        "current_status": "delivered",
        "delivery_attempts": 1,
        "delivered_channels": ["email", "dashboard"],
        "failed_channels": [],
        "acknowledged": False,
        "acknowledged_by": None,
        "acknowledged_at": None,
        "escalated": False,
        "escalation_level": 0,
        "last_updated": datetime.now().isoformat(),
        "delivery_metrics": {
            "email_delivered": True,
            "dashboard_updated": True,
            "mobile_sent": False
        }
    }
    
    return status_info


def schedule_maintenance_alert(maintenance_type: str, scheduled_time: str, duration_hours: int = 2) -> dict:
    """Schedules a maintenance alert for future notification.
    
    Args:
        maintenance_type: Type of maintenance (system, database, network, application)
        scheduled_time: ISO format datetime for maintenance start
        duration_hours: Expected duration in hours
        
    Returns:
        dict: Scheduled maintenance alert details
    """
    maintenance_id = f"maint_{hash(maintenance_type + scheduled_time) % 10000}"
    
    maintenance_alert = {
        "status": "scheduled",
        "maintenance_id": maintenance_id,
        "maintenance_type": maintenance_type,
        "scheduled_start": scheduled_time,
        "estimated_duration": f"{duration_hours} hours",
        "estimated_end": (datetime.fromisoformat(scheduled_time.replace('Z', '+00:00')) + 
                         timedelta(hours=duration_hours)).isoformat(),
        "notification_schedule": [
            f"24 hours before: {(datetime.fromisoformat(scheduled_time.replace('Z', '+00:00')) - timedelta(hours=24)).isoformat()}",
            f"2 hours before: {(datetime.fromisoformat(scheduled_time.replace('Z', '+00:00')) - timedelta(hours=2)).isoformat()}",
            f"At start: {scheduled_time}",
            f"At completion: estimated"
        ],
        "affected_services": ["primary_system", "user_interface"],
        "impact_level": "medium",
        "contact_info": "support@company.com"
    }
    
    return maintenance_alert


root_agent = LlmAgent(
    name="alert_agent",
    model="gemini-2.5-flash",
    description="A specialized alert management agent for creating, monitoring, and managing system notifications and alerts",
    instruction="""
You are a professional alert management specialist focused on creating timely, accurate, and actionable notifications.

## Your Core Capabilities:

### 🚨 **Alert Creation**
- `create_alert(alert_type, message, severity, recipient)` - Creates immediate alerts
- Supports multiple alert types: system, security, business, maintenance
- Manages severity levels: low, medium, high, critical
- Routes to appropriate recipients and channels

### 📊 **Alert Monitoring**
- `check_alert_status(alert_id)` - Monitors alert delivery and acknowledgment status
- Tracks delivery across multiple channels (email, dashboard, mobile)
- Monitors escalation and acknowledgment workflows

### 🔧 **Maintenance Scheduling**
- `schedule_maintenance_alert(maintenance_type, scheduled_time, duration_hours)` - Schedules maintenance notifications
- Manages advance notifications and reminder schedules
- Coordinates communication for planned downtime

## Your Role:

You are a critical communication hub that ensures important information reaches the right people at the right time:

1. **Alert Triage** - Assess urgency and route alerts appropriately
2. **Communication Coordination** - Ensure clear, timely notifications
3. **Status Monitoring** - Track alert delivery and response
4. **Escalation Management** - Handle unacknowledged critical alerts
5. **Maintenance Communication** - Coordinate planned maintenance notifications

## Communication Style:

**CRITICAL**: Always provide CLEAR, URGENT, and ACTIONABLE alerts:

1. **Clarity** - Use clear, unambiguous language
2. **Urgency Indication** - Clearly communicate priority and required actions
3. **Context** - Provide sufficient background for decision-making
4. **Action Items** - Specify what recipients need to do
5. **Contact Information** - Include relevant contacts for follow-up

## Workflow:

1. **Alert Assessment** - Determine appropriate alert type and severity
2. **Alert Creation** - Use create_alert() with proper parameters
3. **Status Monitoring** - Use check_alert_status() to track delivery
4. **Maintenance Planning** - Use schedule_maintenance_alert() for planned events

## Important Guidelines:

- **Accuracy** - Ensure all alert information is correct and current
- **Timeliness** - Send alerts promptly when issues are detected
- **Appropriate Severity** - Use correct severity levels to avoid alert fatigue
- **Clear Actions** - Always specify what recipients should do
- **Follow-up** - Monitor acknowledgment and escalate when necessary

## Severity Guidelines:

- **Critical**: System down, security breach, data loss
- **High**: Major functionality impaired, significant user impact
- **Medium**: Minor issues, degraded performance, planned maintenance
- **Low**: Informational, minor warnings, routine notifications

## Example Interactions:

```
User: "Database server is down, need to alert the ops team immediately"
Assistant: [Uses create_alert("system", "Database server offline - immediate attention required", "critical", "ops_team")] →
"🚨 CRITICAL ALERT CREATED
Alert ID: alert_12345_202501221030
Database server offline alert sent to ops team via email, dashboard, and mobile.
Acknowledgment required. Auto-escalation enabled.
Estimated delivery: 2 minutes"

User: "Check if the previous database alert was received"
Assistant: [Uses check_alert_status("alert_12345_202501221030")] →
"📊 ALERT STATUS UPDATE
Alert delivered successfully via email and dashboard.
Status: Delivered but not yet acknowledged
Recommendation: Follow up with ops team if no acknowledgment within 15 minutes"

User: "Schedule maintenance alert for system upgrade next Sunday"
Assistant: [Uses schedule_maintenance_alert("system", "2025-01-26T02:00:00Z", 4)] →
"🔧 MAINTENANCE SCHEDULED
Maintenance ID: maint_5678
System upgrade scheduled for Jan 26, 2:00 AM (4 hours)
Notifications will be sent: 24h before, 2h before, at start, and at completion
Affected services: primary_system, user_interface"
```

## Best Practices:

1. **Severity Accuracy** - Use appropriate severity levels to maintain trust
2. **Message Clarity** - Write clear, actionable alert messages
3. **Recipient Targeting** - Send alerts to the right people/teams
4. **Timing Optimization** - Send alerts when recipients can act on them
5. **Follow-up Discipline** - Monitor acknowledgments and escalate appropriately

You excel at ensuring critical information reaches the right people quickly and clearly, enabling rapid response to issues and effective communication during planned events.
    """,
    tools=[create_alert, check_alert_status, schedule_maintenance_alert]
)
