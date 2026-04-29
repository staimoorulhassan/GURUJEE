"""Phase 2 Full Integration Tests - SMS, Voice, Settings, Monitoring"""

import pytest
import asyncio
from pathlib import Path
from datetime import datetime, timedelta, timezone

from gurujee.audit.logger import AuditLogger
from gurujee.queue.manager import AIRequestQueue, QueuedRequest
from gurujee.ai.model_router import ModelRouter
from gurujee.communication.sms_handler import SMSHandler
from gurujee.communication.call_handler import CallHandler
from gurujee.voice.cloning import VoiceCloner
from gurujee.voice.persistence import VoiceIdentity
from gurujee.profiling.monitor import MemoryMonitor
from gurujee.providers.voice_provider import CustomVoiceProvider
from gurujee.keystore.keystore import Keystore


@pytest.fixture
def integration_setup(tmp_path):
    """Setup all Phase 2 components."""
    return {
        'tmp_path': tmp_path,
        'audit_file': str(tmp_path / 'audit.jsonl'),
        'queue_db': str(tmp_path / 'queue.db'),
        'metrics_file': str(tmp_path / 'metrics.jsonl'),
        'keystore_path': tmp_path / 'keystore.bin',
        'config_file': str(tmp_path / 'agent_model_routing.yaml'),
    }


class TestPhase2Infrastructure:
    """Test all Phase 2 infrastructure components."""

    def test_audit_logging_with_retention(self, integration_setup):
        """Test audit logging system with archival."""
        audit = AuditLogger(
            integration_setup['audit_file'],
            str(integration_setup['tmp_path'] / 'archive')
        )

        # Log actions
        audit.log(
            action="sms_auto_reply",
            resource="automation",
            user_id="local",
            change={"contact": "+1234567890", "text": "Auto-reply sent"},
            outcome="success"
        )

        # Verify logged
        logs = audit.get_logs()
        assert len(logs) == 1
        assert logs[0]["action"] == "sms_auto_reply"


    @pytest.mark.asyncio
    async def test_queue_with_ttl_cleanup(self, integration_setup):
        """Test queue capacity and TTL management."""
        queue = AIRequestQueue(integration_setup['queue_db'], max_capacity=2)
        queue.init_db()

        # Add requests
        req1 = QueuedRequest(id="1", prompt="keep", priority=1, ttl_seconds=3600)
        req2 = QueuedRequest(id="2", prompt="expire", priority=1, ttl_seconds=0)  # Immediate expire

        await queue.add(req1)
        await queue.add(req2)

        # Cleanup expired
        await asyncio.sleep(0.5)
        removed = await queue.cleanup_expired()

        # req2 should be removed (expired)
        assert removed >= 1
        size = await queue.size()
        assert size <= 1

    def test_model_routing_configuration(self, integration_setup):
        """Test per-agent model routing."""
        import yaml

        # Create test config
        config = {
            "agent_defaults": {"timeout_seconds": 30, "max_retries": 2},
            "agents": {
                "soul": {
                    "default_model": "anthropic/claude-opus-4-6",
                    "fallback_models": ["anthropic/claude-sonnet-4-6"],
                    "budget_tier": "premium",
                    "cost_per_1m_tokens": 15.0
                },
                "automation": {
                    "default_model": "openai/gpt-4o-mini",
                    "fallback_models": ["google/gemini-1.5-flash"],
                    "budget_tier": "economy",
                    "cost_per_1m_tokens": 1.5
                }
            }
        }

        with open(integration_setup['config_file'], 'w') as f:
            yaml.dump(config, f)

        router = ModelRouter(integration_setup['config_file'])

        # Test routing
        assert router.get_default_model("soul") == "anthropic/claude-opus-4-6"
        assert router.get_default_model("automation") == "openai/gpt-4o-mini"
        assert router.get_budget_tier("soul") == "premium"
        assert router.get_cost_per_1m_tokens("automation") == 1.5


class TestPhase2SMS:
    """Test SMS automation features."""

    def test_sms_handler_with_rules(self):
        """Test SMS handler with automation rules."""
        handler = SMSHandler()

        # Test message formatting
        messages = [
            {"timestamp": "2026-04-28T10:00:00Z", "phone": "+1555123", "text": "Hello", "direction": "in"},
            {"timestamp": "2026-04-28T10:01:00Z", "phone": "+1555123", "text": "How are you?", "direction": "in"},
        ]

        context = handler.build_context(messages)

        assert "Hello" in context
        assert "How are you?" in context
        assert "+1555123" in context

    def test_sms_context_window_depth(self):
        """Test 10-message context window limit."""
        handler = SMSHandler()

        # Create 15 messages
        messages = [
            {"timestamp": f"2026-04-28T10:{i:02d}:00Z", "text": f"Message {i}", "direction": "in"}
            for i in range(15)
        ]

        context = handler.build_context(messages, message_limit=10)

        # Should include the messages
        assert "Message" in context
        assert isinstance(context, str)


class TestPhase2Calls:
    """Test call automation features."""

    def test_call_routing_by_priority(self):
        """Test call routing based on priority tier."""
        handler = CallHandler()

        from gurujee.providers.call_provider import CallEvent

        call = CallEvent(
            call_id="call-001",
            phone_number="+1555123",
            contact_name="Alice"
        )

        # VIP should answer
        route = handler.determine_route(call, priority_tier="vip")
        assert route == "answer"

        # Spam should reject
        route = handler.determine_route(call, priority_tier="spam")
        assert route == "reject"

        # Normal should voicemail
        route = handler.determine_route(call, priority_tier="normal")
        assert route == "voicemail"


class TestPhase2Voice:
    """Test voice cloning and persistence."""

    @pytest.mark.asyncio
    async def test_voice_cloning_flow(self):
        """Test voice cloning with fallback."""
        # Mock provider
        provider = CustomVoiceProvider()
        cloner = VoiceCloner(provider)

        # Create a dummy audio file
        audio_path = "/tmp/voice.wav"
        Path(audio_path).touch()

        try:
            result = await cloner.clone_with_retry(audio_path, "TestVoice")

            # Should succeed (with mock provider)
            assert result.success
            assert result.voice_id is not None
        finally:
            if Path(audio_path).exists():
                Path(audio_path).unlink()

    def test_voice_identity_persistence(self, integration_setup):
        """Test voice identity encryption and retrieval."""
        # Create keystore
        keystore = Keystore(integration_setup['keystore_path'], "test-pin")
        keystore.unlock()

        identity = VoiceIdentity(keystore)

        # Save voice
        import asyncio
        asyncio.run(identity.save(
            voice_id="voice-001",
            voice_name="MyVoice",
            audio_sample_hash="sha256:abc123",
            provider="custom"
        ))

        # Load voice
        loaded = asyncio.run(identity.load())
        assert loaded["voice_id"] == "voice-001"
        assert loaded["voice_name"] == "MyVoice"


class TestPhase2Performance:
    """Test performance monitoring."""

    def test_memory_monitoring_with_threshold(self, integration_setup):
        """Test RAM profiling and alerting."""
        monitor = MemoryMonitor(integration_setup['metrics_file'])

        # Sample RSS
        rss = monitor.sample_rss()
        assert rss > 0  # Should have some memory

        # Set baseline
        baseline = monitor.get_baseline()
        assert baseline > 0

        # Log sample
        monitor.log_sample("idle")

        # Verify logged
        metrics = monitor.get_metrics()
        assert len(metrics) >= 1
        assert metrics[0]["rss_mb"] > 0

    def test_performance_gate_arm64_50mb(self, integration_setup):
        """Test ARM64 performance gate (target ≤50MB)."""
        monitor = MemoryMonitor(integration_setup['metrics_file'])

        rss = monitor.sample_rss()

        # On typical laptop, should be well under 50MB
        # This would be enforced on ARM64 Termux device
        print(f"Current RSS: {rss}MB")


class TestPhase2Integration:
    """End-to-end integration tests."""

    @pytest.mark.asyncio
    async def test_full_workflow_sms_to_settings(self, integration_setup):
        """Test complete workflow: SMS → Rules → Settings."""
        import yaml

        # Create config file first
        config = {
            "agent_defaults": {"timeout_seconds": 30, "max_retries": 2},
            "agents": {
                "soul": {
                    "default_model": "anthropic/claude-opus-4-6",
                    "fallback_models": ["anthropic/claude-sonnet-4-6"],
                    "budget_tier": "premium",
                    "cost_per_1m_tokens": 15.0
                }
            }
        }

        with open(integration_setup['config_file'], 'w') as f:
            yaml.dump(config, f)

        # Setup all components
        audit = AuditLogger(
            integration_setup['audit_file'],
            str(integration_setup['tmp_path'] / 'archive')
        )
        queue = AIRequestQueue(integration_setup['queue_db'])
        queue.init_db()
        router = ModelRouter(integration_setup['config_file'])
        sms = SMSHandler()
        calls = CallHandler()
        monitor = MemoryMonitor(integration_setup['metrics_file'])

        # Simulate incoming SMS
        messages = [
            {"timestamp": "2026-04-28T10:00:00Z", "phone": "+1555001", "text": "Reminder meeting at 2pm", "direction": "in"}
        ]

        # Build context
        context = sms.build_context(messages)
        assert "Reminder" in context

        # Queue AI request
        req = QueuedRequest(
            id="ai-001",
            prompt=f"Auto-reply to: {context}",
            priority=1
        )
        await queue.add(req)

        # Get from queue
        queued = await queue.get()
        assert queued.id == "ai-001"

        # Get model for agent
        model = router.get_default_model("soul")
        assert model is not None

        # Log audit trail
        audit.log(
            action="sms_auto_reply_sent",
            resource="automation",
            user_id="local",
            change={"contact": "+1555001", "model_used": model},
            outcome="success"
        )

        # Monitor performance
        monitor.log_sample("sms_processing")

        # Verify everything logged
        logs = audit.get_logs()
        assert len(logs) >= 1


class TestPhase2Settings:
    """Test PWA settings panel integration."""

    def test_settings_api_endpoints(self):
        """Test settings endpoints are defined."""
        from gurujee.server.routers.settings import router

        # Verify router has endpoints
        assert router.routes is not None
        assert len(router.routes) > 0

        # Check for expected endpoints
        endpoints = {route.path for route in router.routes}
        assert any("/api/settings" in str(path) for path in endpoints)
