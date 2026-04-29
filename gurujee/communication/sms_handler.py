"""SMS handler: retrieval, context building, rules, sending."""

import logging
import asyncio
import yaml
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone, timedelta
from gurujee.providers.sms_provider import SMSProvider, SMSMessage, CustomSMSProvider

logger = logging.getLogger(__name__)


class SMSHandler:
    """Handle SMS retrieval, context building, automation rules."""

    def __init__(self, provider: Optional[SMSProvider] = None, rules_file: Optional[str] = None):
        self.provider = provider or CustomSMSProvider()
        self.rules_file = rules_file
        self.rules = self._load_rules()

    def _load_rules(self) -> List[Dict[str, Any]]:
        """Load SMS automation rules from YAML."""
        if not self.rules_file or not Path(self.rules_file).exists():
            return []

        try:
            with open(self.rules_file, "r") as f:
                config = yaml.safe_load(f) or {}
            return config.get("rules", [])
        except Exception as e:
            logger.error(f"Failed to load SMS rules: {e}")
            return []

    def _query_termux_api(self) -> List[Dict[str, Any]]:
        """Query Termux:API for SMS messages (sync wrapper)."""
        # Stub for compatibility with tests
        return []

    def get_recent_messages(self, contact: Optional[str] = None, phone_number: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent SMS messages (sync interface for compatibility)."""
        # Support both 'contact' and 'phone_number' parameters
        phone = phone_number or contact

        # Use mock Termux:API data by default
        messages = self._query_termux_api()

        # Filter by contact if specified
        if phone:
            messages = [m for m in messages if m.get('phone') == phone]

        # Enforce limit
        return messages[:limit]

    def build_context(self, messages: List[Dict[str, Any]], hours_back: int = 24, message_limit: int = 10) -> str:
        """Build multi-turn SMS context for AI prompt (from message list)."""
        # Filter messages by time window
        now = datetime.now()
        cutoff = now - timedelta(hours=hours_back)

        filtered = []
        for msg in messages:
            try:
                if isinstance(msg.get('timestamp'), str):
                    msg_time = datetime.fromisoformat(msg['timestamp'].replace('Z', '+00:00'))
                else:
                    msg_time = msg.get('timestamp', now)

                if msg_time >= cutoff:
                    filtered.append(msg)
            except:
                filtered.append(msg)

        # Apply message limit (most recent N)
        filtered = filtered[-message_limit:]

        # Build context string with contact phone if available
        context = "SMS conversation"
        if filtered and filtered[0].get('phone'):
            context += f" with {filtered[0].get('phone')}"
        context += ":\n\n"

        for msg in filtered:
            direction = "→" if msg.get('direction') == 'out' else "←"
            context += f"{direction} {msg.get('text', '')}\n"

        return context

    async def get_recent_messages_async(self, phone_number: Optional[str] = None, limit: int = 10) -> List[SMSMessage]:
        """Get recent SMS messages (async version using provider)."""
        return await self.provider.get_recent_messages(phone_number, limit)

    async def build_context_async(self, phone_number: str, depth: int = 10) -> str:
        """Build multi-turn SMS context for AI prompt (async version)."""
        messages = await self.provider.get_conversation_thread(phone_number, depth)

        context = f"SMS conversation with {phone_number}:\n\n"
        for msg in messages:
            direction = "→" if msg.direction == "out" else "←"
            context += f"{direction} {msg.text}\n"

        return context

    def _matches_rule(self, message: SMSMessage, rule: Dict[str, Any]) -> bool:
        """Check if message matches rule conditions."""
        conditions = rule.get("conditions", [])

        for condition in conditions:
            if "contact" in condition:
                if condition["contact"] != message.phone_number:
                    return False

            if "contact_regex" in condition:
                import re
                if not re.match(condition["contact_regex"], message.phone_number or ""):
                    return False

            if "keyword_any" in condition:
                keywords = condition["keyword_any"]
                if not any(kw.lower() in message.text.lower() for kw in keywords):
                    return False

            if "time_range" in condition:
                # Parse HH:MM-HH:MM
                time_range = condition["time_range"]
                start_str, end_str = time_range.split("-")
                start_h, start_m = map(int, start_str.split(":"))
                end_h, end_m = map(int, end_str.split(":"))

                now = datetime.now()
                current_time = now.hour * 60 + now.minute
                start_time = start_h * 60 + start_m
                end_time = end_h * 60 + end_m

                if not (start_time <= current_time <= end_time):
                    return False

        return True

    def should_auto_reply(self, message: SMSMessage) -> bool:
        """Check if message should be auto-replied based on rules."""
        matching_rules = self.collect_all_matching_rules(message)

        # Check if any rule enables auto_reply
        for rule in matching_rules:
            actions = rule.get("actions", {})
            if actions.get("auto_reply"):
                return True

        return False

    def collect_all_matching_rules(self, message: SMSMessage) -> List[Dict[str, Any]]:
        """Get all rules matching this message."""
        matching = []
        for rule in self.rules:
            if rule.get("enabled", True) and self._matches_rule(message, rule):
                matching.append(rule)
        return matching

    async def send_sms(self, phone_number: str, text: str) -> bool:
        """Send SMS message."""
        result = await self.provider.send_sms(phone_number, text)
        return result.success

    def format_sms_preview(self, phone_number: str, text: str, delay_seconds: int = 0) -> Dict[str, str]:
        """Format SMS preview for user confirmation."""
        return {
            "phone": phone_number,
            "message": text,
            "delay_seconds": str(delay_seconds),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    async def send_sms_with_preview(self, phone_number: str, text: str, delay_seconds: int = 0) -> bool:
        """Send SMS with optional delay."""
        if delay_seconds > 0:
            await asyncio.sleep(delay_seconds)

        return await self.send_sms(phone_number, text)
