"""Per-agent model routing configuration with fallback chains."""

import logging
import yaml
from pathlib import Path
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)


class ModelRouter:
    """Routes requests to appropriate models based on agent and budget tier."""

    def __init__(self, config_path: str):
        self.config_path = Path(config_path)
        self._config = self._load_config()
        self._setup_defaults()

    def _load_config(self) -> Dict[str, Any]:
        """Load YAML config file."""
        if not self.config_path.exists():
            logger.warning(f"Model routing config not found: {self.config_path}")
            return {"agent_defaults": {}, "agents": {}}

        try:
            with open(self.config_path, "r") as f:
                config = yaml.safe_load(f) or {}
            return config
        except Exception as e:
            logger.error(f"Failed to load model routing config: {e}")
            return {"agent_defaults": {}, "agents": {}}

    def _setup_defaults(self) -> None:
        """Extract global defaults."""
        defaults = self._config.get("agent_defaults", {})
        self.default_timeout = defaults.get("timeout_seconds", 30)
        self.default_retries = defaults.get("max_retries", 2)

    def get_default_model(self, agent_name: str) -> Optional[str]:
        """Get default model for agent."""
        agent = self._config.get("agents", {}).get(agent_name, {})
        return agent.get("default_model")

    def get_fallback_models(self, agent_name: str) -> List[str]:
        """Get fallback model chain for agent."""
        agent = self._config.get("agents", {}).get(agent_name, {})
        return agent.get("fallback_models", [])

    def get_budget_tier(self, agent_name: str) -> Optional[str]:
        """Get budget tier (premium, standard, economy)."""
        agent = self._config.get("agents", {}).get(agent_name, {})
        return agent.get("budget_tier")

    def get_cost_per_1m_tokens(self, agent_name: str) -> Optional[float]:
        """Get cost in USD per 1M tokens."""
        agent = self._config.get("agents", {}).get(agent_name, {})
        return agent.get("cost_per_1m_tokens")

    def get_all_agents(self) -> List[str]:
        """Get all configured agents."""
        return list(self._config.get("agents", {}).keys())

    def get_routing_policy(self, agent_name: str) -> Optional[Dict[str, Any]]:
        """Get complete routing policy for agent."""
        agent = self._config.get("agents", {}).get(agent_name)
        if not agent:
            return None

        return {
            "agent_name": agent_name,
            "default_model": agent.get("default_model"),
            "fallback_models": agent.get("fallback_models", []),
            "budget_tier": agent.get("budget_tier"),
            "cost_per_1m_tokens": agent.get("cost_per_1m_tokens"),
            "timeout_seconds": self.default_timeout,
            "max_retries": self.default_retries
        }

    def reload(self) -> None:
        """Reload config from file."""
        self._config = self._load_config()
        self._setup_defaults()
        logger.info("Model routing config reloaded")
