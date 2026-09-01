import hashlib
import json
from typing import Any


def deployment_fingerprint(
    *,
    model_name: str,
    prompt_hash: str,
    code_hash: str,
    tool_manifest: dict[str, Any] | list[Any],
    capability_manifest: dict[str, Any] | list[Any],
    permissions: dict[str, Any] | list[Any],
) -> str:
    """Return a stable SHA-256 digest for a deployed agent definition."""
    payload = {
        "model_name": model_name,
        "prompt_hash": prompt_hash,
        "code_hash": code_hash,
        "tool_manifest": tool_manifest,
        "capability_manifest": capability_manifest,
        "permissions": permissions,
    }
    normalized = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()
