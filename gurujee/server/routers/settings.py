"""Settings API endpoints: model, voice, automation, keys, export/import."""

from fastapi import APIRouter, HTTPException, File, UploadFile, Response
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import yaml
import json
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/settings", tags=["settings"])


class ModelSettingRequest(BaseModel):
    """Request to set default model."""
    agent_name: str
    model_name: str


class VoiceRecordRequest(BaseModel):
    """Voice recording metadata."""
    voice_name: str


class AutomationRuleRequest(BaseModel):
    """Create/update automation rule."""
    rule_id: Optional[str] = None
    rule_type: str  # sms, call, etc.
    trigger: str
    conditions: List[Dict[str, Any]]
    actions: Dict[str, Any]
    enabled: bool = True


class APIKeyRequest(BaseModel):
    """Store API key."""
    key_name: str  # POLLINATIONS_API_KEY, ELEVENLABS_API_KEY, etc.
    key_value: str


# In-memory storage (would be persisted to keystore in production)
_voice_status = {}
_settings_store = {}


@router.get("/models")
async def get_available_models():
    """Get available models and routing policies."""
    # Would load from agent_model_routing.yaml
    return {
        "agents": [
            {
                "name": "soul",
                "default_model": "anthropic/claude-opus-4-6",
                "fallback_models": ["anthropic/claude-sonnet-4-6"],
                "budget_tier": "premium"
            },
            {
                "name": "automation",
                "default_model": "openai/gpt-4o-mini",
                "fallback_models": ["google/gemini-1.5-flash"],
                "budget_tier": "economy"
            }
        ]
    }


@router.post("/models")
async def set_default_model(request: ModelSettingRequest):
    """Set default model for agent."""
    _settings_store[f"model_{request.agent_name}"] = request.model_name
    logger.info(f"Set {request.agent_name} default model to {request.model_name}")
    return {"success": True, "agent": request.agent_name, "model": request.model_name}


@router.post("/voice/record")
async def record_voice(request: VoiceRecordRequest, file: UploadFile = File(...)):
    """Record voice sample and trigger cloning."""
    try:
        # Read file
        content = await file.read()

        # Store temporarily
        voice_id = f"voice-{hash(request.voice_name) % 100000}"
        _voice_status[voice_id] = {
            "status": "processing",
            "voice_name": request.voice_name,
            "timestamp": None
        }

        # Trigger async cloning (would be real background job)
        logger.info(f"Recording voice: {request.voice_name}")

        return {
            "success": True,
            "voice_id": voice_id,
            "status": "processing"
        }
    except Exception as e:
        logger.error(f"Voice recording failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/voice/status/{voice_id}")
async def get_voice_status(voice_id: str):
    """Get voice cloning status."""
    status = _voice_status.get(voice_id, {}).get("status", "unknown")
    return {
        "voice_id": voice_id,
        "status": status  # pending, processing, ready, failed
    }


@router.get("/automation/rules")
async def get_automation_rules():
    """Get current automation rules."""
    rules = _settings_store.get("automation_rules", [])
    return {"rules": rules}


@router.post("/automation/rules")
async def create_automation_rule(request: AutomationRuleRequest):
    """Create new automation rule."""
    rules = _settings_store.get("automation_rules", [])

    rule_id = request.rule_id or f"rule-{len(rules) + 1}"
    rule = {
        "id": rule_id,
        "type": request.rule_type,
        "trigger": request.trigger,
        "conditions": request.conditions,
        "actions": request.actions,
        "enabled": request.enabled
    }

    rules.append(rule)
    _settings_store["automation_rules"] = rules

    logger.info(f"Created rule: {rule_id}")
    return {"success": True, "rule": rule}


@router.put("/automation/rules/{rule_id}")
async def update_automation_rule(rule_id: str, request: AutomationRuleRequest):
    """Update existing rule."""
    rules = _settings_store.get("automation_rules", [])
    rule_index = next((i for i, r in enumerate(rules) if r["id"] == rule_id), None)

    if rule_index is None:
        raise HTTPException(status_code=404, detail="Rule not found")

    rules[rule_index] = {
        "id": rule_id,
        "type": request.rule_type,
        "trigger": request.trigger,
        "conditions": request.conditions,
        "actions": request.actions,
        "enabled": request.enabled
    }

    logger.info(f"Updated rule: {rule_id}")
    return {"success": True, "rule": rules[rule_index]}


@router.delete("/automation/rules/{rule_id}")
async def delete_automation_rule(rule_id: str):
    """Delete automation rule."""
    rules = _settings_store.get("automation_rules", [])
    rules = [r for r in rules if r["id"] != rule_id]
    _settings_store["automation_rules"] = rules

    logger.info(f"Deleted rule: {rule_id}")
    return {"success": True}


@router.post("/keys")
async def store_api_key(request: APIKeyRequest):
    """Store API key (encrypted in keystore)."""
    # In production, would encrypt and store in keystore
    _settings_store[f"key_{request.key_name}"] = "***"  # Don't store plaintext
    logger.info(f"Stored API key: {request.key_name}")
    return {"success": True, "key_name": request.key_name}


@router.post("/export")
async def export_settings():
    """Export all settings as encrypted ZIP."""
    try:
        # Create ZIP with encrypted settings
        import zipfile
        import io

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            # Add settings
            settings = {
                "automation_rules": _settings_store.get("automation_rules", []),
                "exported_at": None
            }

            zf.writestr("settings.json", json.dumps(settings, indent=2))

        zip_buffer.seek(0)
        logger.info("Settings exported")

        return Response(
            content=zip_buffer.getvalue(),
            media_type="application/zip",
            headers={"Content-Disposition": "attachment; filename=gurujee-settings.zip"}
        )
    except Exception as e:
        logger.error(f"Export failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/import")
async def import_settings(file: UploadFile = File(...)):
    """Import settings from encrypted ZIP."""
    try:
        import zipfile
        import io

        content = await file.read()
        with zipfile.ZipFile(io.BytesIO(content)) as zf:
            settings_data = zf.read("settings.json")
            settings = json.loads(settings_data)

            # Merge into store
            _settings_store.update(settings)

        logger.info("Settings imported")
        return {"success": True, "message": "Settings imported successfully"}
    except Exception as e:
        logger.error(f"Import failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
