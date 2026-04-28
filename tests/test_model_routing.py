"""Tests for model routing configuration."""

import pytest
import yaml
from pathlib import Path
from gurujee.ai.model_router import ModelRouter


@pytest.fixture
def config_file(tmp_path):
    """Create test model routing config."""
    config = {
        "agent_defaults": {
            "timeout_seconds": 30,
            "max_retries": 2
        },
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

    config_path = tmp_path / "agent_model_routing.yaml"
    with open(config_path, "w") as f:
        yaml.dump(config, f)

    return str(config_path)


def test_model_router_loads_config(config_file):
    """Test loading model routing config."""
    router = ModelRouter(config_file)

    # Verify loaded
    assert router.default_timeout == 30
    assert router.default_retries == 2


def test_model_router_default_model(config_file):
    """Test getting default model for agent."""
    router = ModelRouter(config_file)

    model = router.get_default_model("soul")
    assert model == "anthropic/claude-opus-4-6"

    model = router.get_default_model("automation")
    assert model == "openai/gpt-4o-mini"


def test_model_router_fallback_chain(config_file):
    """Test getting fallback models."""
    router = ModelRouter(config_file)

    fallbacks = router.get_fallback_models("soul")
    assert fallbacks == ["anthropic/claude-sonnet-4-6"]

    fallbacks = router.get_fallback_models("automation")
    assert fallbacks == ["google/gemini-1.5-flash"]


def test_model_router_budget_tier(config_file):
    """Test getting budget tier."""
    router = ModelRouter(config_file)

    tier = router.get_budget_tier("soul")
    assert tier == "premium"

    tier = router.get_budget_tier("automation")
    assert tier == "economy"


def test_model_router_cost(config_file):
    """Test getting model cost."""
    router = ModelRouter(config_file)

    cost = router.get_cost_per_1m_tokens("soul")
    assert cost == 15.0

    cost = router.get_cost_per_1m_tokens("automation")
    assert cost == 1.5


def test_model_router_get_all_agents(config_file):
    """Test getting all agent names."""
    router = ModelRouter(config_file)

    agents = router.get_all_agents()
    assert "soul" in agents
    assert "automation" in agents


def test_model_router_missing_agent(config_file):
    """Test handling missing agent."""
    router = ModelRouter(config_file)

    model = router.get_default_model("nonexistent")
    assert model is None


def test_model_router_get_routing_policy(config_file):
    """Test getting complete routing policy."""
    router = ModelRouter(config_file)

    policy = router.get_routing_policy("soul")
    assert policy["default_model"] == "anthropic/claude-opus-4-6"
    assert policy["budget_tier"] == "premium"
    assert "fallback_models" in policy
