"""
Action Layer
Handles executable actions triggered by user intent.
Simulates enterprise integrations (ticket creation, calendar, notifications).
"""

from typing import Dict, Any, Optional, List
from loguru import logger
from datetime import datetime, timezone
import uuid

from app.core.llm_client import LLMClient


class ActionDetector:
    """
    Detects user intent for actionable requests.
    Uses LLM to classify whether a query requires an action vs. information retrieval.
    """

    def __init__(self):
        self.llm = LLMClient()
        self.action_keywords = {
            "create_ticket": ["create ticket", "open ticket", "support ticket", "bug report", "file a ticket"],
            "schedule_meeting": ["schedule meeting", "book meeting", "set up a call", "arrange meeting"],
            "send_notification": ["notify", "send notification", "alert team", "send message to"],
            "generate_report": ["generate report", "create report", "export data", "summary report"],
            "create_task": ["create task", "add task", "todo", "action item"],
        }

    async def detect_action(self, query: str) -> Optional[Dict[str, Any]]:
        """Detect if the query requires an action using rule-based matching only."""
        query_lower = query.lower()

        # Rule-based detection only (saves LLM tokens)
        for action_type, keywords in self.action_keywords.items():
            if any(kw in query_lower for kw in keywords):
                return {"action_type": action_type, "confidence": 0.8}

        return None

    async def _detect_action_llm(self, query: str) -> Optional[Dict[str, Any]]:
        """LLM-based action detection (unused - kept for reference)."""
        try:
            messages = [{
                "role": "user",
                "content": f"""Classify this user request. Is it asking for an ACTION (something to be done/created) 
or INFORMATION (a question to be answered)?

Request: "{query}"

Respond with JSON: {{"is_action": true/false, "action_type": "type_if_action", "confidence": 0.0-1.0}}
Action types: create_ticket, schedule_meeting, send_notification, generate_report, create_task, none""",
            }]

            result = await self.llm.generate_structured(
                messages=messages,
                schema={"is_action": "boolean", "action_type": "string", "confidence": "number"},
            )

            if result.get("is_action") and result.get("confidence", 0) > 0.6:
                return {
                    "action_type": result["action_type"],
                    "confidence": result["confidence"],
                }
        except Exception as e:
            logger.warning(f"Action detection LLM call failed: {e}")

        return None


class ActionExecutor:
    """
    Executes detected actions by simulating enterprise API calls.
    In production, these would connect to real systems (Jira, Slack, Calendar, etc.)
    """

    def __init__(self):
        self.llm = LLMClient()

    async def execute(self, action_type: str, query: str, context: Dict = None) -> Dict[str, Any]:
        """Execute an action based on type."""
        executors = {
            "create_ticket": self._create_ticket,
            "schedule_meeting": self._schedule_meeting,
            "send_notification": self._send_notification,
            "generate_report": self._generate_report,
            "create_task": self._create_task,
        }

        executor = executors.get(action_type)
        if not executor:
            return {"status": "error", "message": f"Unknown action type: {action_type}"}

        # Extract parameters from query using LLM
        params = await self._extract_params(action_type, query)

        # Execute action
        result = await executor(params, context)
        return result

    async def _extract_params(self, action_type: str, query: str) -> Dict[str, Any]:
        """Extract action parameters from natural language query."""
        param_schemas = {
            "create_ticket": {"title": "string", "description": "string", "priority": "low|medium|high", "assignee": "string"},
            "schedule_meeting": {"title": "string", "participants": ["string"], "duration_minutes": "number", "date": "string"},
            "send_notification": {"recipients": ["string"], "message": "string", "channel": "slack|email"},
            "generate_report": {"report_type": "string", "date_range": "string", "format": "pdf|csv"},
            "create_task": {"title": "string", "description": "string", "due_date": "string", "assignee": "string"},
        }

        schema = param_schemas.get(action_type, {})

        messages = [{
            "role": "user",
            "content": f"Extract parameters from this request for a '{action_type}' action:\n\"{query}\"\n\nSchema: {schema}\n\nFill in reasonable defaults for missing fields.",
        }]

        try:
            params = await self.llm.generate_structured(
                messages=messages,
                schema=schema,
            )
            return params if params else {"title": query}
        except Exception:
            return {"title": query}

    async def _create_ticket(self, params: Dict, context: Dict = None) -> Dict[str, Any]:
        """Simulate creating a support ticket."""
        ticket_id = f"TKT-{uuid.uuid4().hex[:6].upper()}"
        return {
            "status": "success",
            "action": "create_ticket",
            "result": {
                "ticket_id": ticket_id,
                "title": params.get("title", "New Ticket"),
                "description": params.get("description", ""),
                "priority": params.get("priority", "medium"),
                "assignee": params.get("assignee", "unassigned"),
                "status": "open",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "url": f"https://tickets.example.com/{ticket_id}",
            },
            "message": f"✅ Ticket {ticket_id} created successfully!",
        }

    async def _schedule_meeting(self, params: Dict, context: Dict = None) -> Dict[str, Any]:
        """Simulate scheduling a meeting."""
        meeting_id = f"MTG-{uuid.uuid4().hex[:6].upper()}"
        return {
            "status": "success",
            "action": "schedule_meeting",
            "result": {
                "meeting_id": meeting_id,
                "title": params.get("title", "Meeting"),
                "participants": params.get("participants", []),
                "duration_minutes": params.get("duration_minutes", 30),
                "date": params.get("date", "TBD"),
                "meeting_link": f"https://meet.example.com/{meeting_id}",
            },
            "message": f"✅ Meeting {meeting_id} scheduled successfully!",
        }

    async def _send_notification(self, params: Dict, context: Dict = None) -> Dict[str, Any]:
        """Simulate sending a notification."""
        return {
            "status": "success",
            "action": "send_notification",
            "result": {
                "recipients": params.get("recipients", ["team"]),
                "message": params.get("message", ""),
                "channel": params.get("channel", "slack"),
                "sent_at": datetime.now(timezone.utc).isoformat(),
            },
            "message": "✅ Notification sent successfully!",
        }

    async def _generate_report(self, params: Dict, context: Dict = None) -> Dict[str, Any]:
        """Simulate generating a report."""
        report_id = f"RPT-{uuid.uuid4().hex[:6].upper()}"
        return {
            "status": "success",
            "action": "generate_report",
            "result": {
                "report_id": report_id,
                "type": params.get("report_type", "general"),
                "format": params.get("format", "pdf"),
                "download_url": f"https://reports.example.com/{report_id}",
                "generated_at": datetime.now(timezone.utc).isoformat(),
            },
            "message": f"✅ Report {report_id} generated successfully!",
        }

    async def _create_task(self, params: Dict, context: Dict = None) -> Dict[str, Any]:
        """Simulate creating a task."""
        task_id = f"TSK-{uuid.uuid4().hex[:6].upper()}"
        return {
            "status": "success",
            "action": "create_task",
            "result": {
                "task_id": task_id,
                "title": params.get("title", "New Task"),
                "description": params.get("description", ""),
                "assignee": params.get("assignee", "unassigned"),
                "due_date": params.get("due_date", "TBD"),
                "status": "todo",
            },
            "message": f"✅ Task {task_id} created successfully!",
        }
