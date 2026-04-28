"""
Tests for SMS message retrieval and context building.
Spec: FR-001, Clarification Q5 (10-message window)
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from gurujee.communication.sms_handler import SMSHandler, SMSMessage


class TestSMSMessageRetrieval:
    """Test SMS message retrieval from Termux:API"""

    def test_sms_get_recent_messages_limit_10(self):
        """Test: Retrieve last 10 SMS messages from a contact"""
        handler = SMSHandler()

        # Mock Termux:API response with 15 messages
        mock_messages = [
            {"id": f"msg_{i}", "timestamp": datetime.now() - timedelta(minutes=i),
             "phone": "+1-555-123-4567", "text": f"Message {i}", "direction": "in"}
            for i in range(15)
        ]

        with patch.object(handler, '_query_termux_api', return_value=mock_messages):
            messages = handler.get_recent_messages(contact="+1-555-123-4567", limit=10)

        # Should return only last 10 (limit enforced)
        assert len(messages) == 10
        assert all(msg['phone'] == "+1-555-123-4567" for msg in messages)
        assert messages[0]['id'] == 'msg_0'  # Most recent first
        assert messages[9]['id'] == 'msg_9'  # 10th message

    def test_sms_build_context_format(self):
        """Test: Format SMS conversation history for AI prompt"""
        handler = SMSHandler()

        messages = [
            {"timestamp": "2026-04-28T10:00:00Z", "phone": "+1-555-123-4567", "text": "Hello", "direction": "in"},
            {"timestamp": "2026-04-28T10:01:00Z", "phone": "+1-555-123-4567", "text": "How are you?", "direction": "in"},
        ]

        context = handler.build_context(messages)

        assert "Hello" in context
        assert "How are you?" in context
        assert "+1-555-123-4567" in context
        assert isinstance(context, str)

    def test_sms_context_excludes_24h_old(self):
        """Test: Exclude messages older than 24 hours"""
        handler = SMSHandler()

        now = datetime.now()
        messages = [
            {"timestamp": (now - timedelta(hours=25)).isoformat(), "text": "old message", "direction": "in"},
            {"timestamp": (now - timedelta(hours=12)).isoformat(), "text": "recent message", "direction": "in"},
            {"timestamp": (now - timedelta(hours=1)).isoformat(), "text": "very recent", "direction": "in"},
        ]

        context = handler.build_context(messages, hours_back=24)

        assert "old message" not in context
        assert "recent message" in context
        assert "very recent" in context

    def test_sms_context_respects_limit(self):
        """Test: Respect 10-message limit in context (Q5 clarification)"""
        handler = SMSHandler()

        messages = [
            {"timestamp": "2026-04-28T10:00:00Z", "text": f"Message {i}", "direction": "in"}
            for i in range(15)
        ]

        context = handler.build_context(messages, message_limit=10)

        # Should include only last 10 messages
        for i in range(5, 15):  # Messages 5-14 (most recent 10)
            assert f"Message {i}" in context

        # Should not include messages 0-4
        assert "Message 0" not in context
        assert "Message 4" not in context


class TestSMSHandler:
    """Test SMSHandler class interface"""

    def test_sms_handler_initialization(self):
        """Test: SMSHandler initializes correctly"""
        handler = SMSHandler()
        assert handler is not None
        assert hasattr(handler, 'get_recent_messages')
        assert hasattr(handler, 'build_context')
        assert hasattr(handler, 'send_sms')

    def test_sms_handler_get_recent_messages_returns_list(self):
        """Test: get_recent_messages returns a list"""
        handler = SMSHandler()

        with patch.object(handler, '_query_termux_api', return_value=[]):
            result = handler.get_recent_messages(contact="+1-555-123-4567")

        assert isinstance(result, list)

    def test_sms_handler_build_context_returns_string(self):
        """Test: build_context returns a string"""
        handler = SMSHandler()
        context = handler.build_context([])
        assert isinstance(context, str)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
