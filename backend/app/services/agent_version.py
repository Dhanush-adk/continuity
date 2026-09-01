import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.db.repositories import agent_version as versions
from app.models.agent_version import AgentVersion
from app.schemas.agent_version import (
    AgentVersionCreate,
    CapabilitiesDiff,
    CapabilityModification,
    ChangedField,
    PermissionsDiff,
    ToolsDiff,
    VersionDiff,
)
from app.services.fingerprint import deployment_fingerprint


def create(db: Session, agent_id: uuid.UUID, payload: AgentVersionCreate) -> AgentVersion:
    values = payload.model_dump()
    fingerprint_values = {key: value for key, value in values.items() if key != "version"}
    version = AgentVersion(
        agent_id=agent_id,
        deployment_fingerprint=deployment_fingerprint(**fingerprint_values),
        **values,
    )
    return versions.add(db, version)


def list_for_agent(db: Session, agent_id: uuid.UUID) -> list[AgentVersion]:
    return versions.list_for_agent(db, agent_id)


def get(db: Session, agent_id: uuid.UUID, version_id: uuid.UUID) -> AgentVersion | None:
    return versions.get(db, agent_id, version_id)


def _tool_names(manifest: list[Any]) -> set[str]:
    return {str(tool["name"]) for tool in manifest if isinstance(tool, dict) and "name" in tool}


def _changed_field(before: str, after: str) -> ChangedField:
    changed = before != after
    return ChangedField(
        changed=changed,
        before=before if changed else None,
        after=after if changed else None,
    )


def _mapping_changes(
    before: dict[str, Any], after: dict[str, Any]
) -> tuple[list[str], list[str], list[CapabilityModification]]:
    added = sorted(after.keys() - before.keys())
    removed = sorted(before.keys() - after.keys())
    modified = [
        CapabilityModification(name=name, before=before[name], after=after[name])
        for name in sorted(before.keys() & after.keys())
        if before[name] != after[name]
    ]
    return added, removed, modified


def diff(first: AgentVersion, second: AgentVersion) -> VersionDiff:
    first_tools = _tool_names(first.tool_manifest)
    second_tools = _tool_names(second.tool_manifest)
    tools = ToolsDiff(
        added=sorted(second_tools - first_tools),
        removed=sorted(first_tools - second_tools),
    )
    capabilities_added, capabilities_removed, capabilities_modified = _mapping_changes(
        first.capability_manifest, second.capability_manifest
    )
    capabilities = CapabilitiesDiff(
        added=capabilities_added,
        removed=capabilities_removed,
        modified=capabilities_modified,
    )
    _, _, permission_changes = _mapping_changes(first.permissions, second.permissions)
    permissions = PermissionsDiff(changed=bool(permission_changes), changes=permission_changes)
    model = _changed_field(first.model_name, second.model_name)
    prompt = _changed_field(first.prompt_hash, second.prompt_hash)
    code = _changed_field(first.code_hash, second.code_hash)
    changed = any(
        (
            model.changed,
            prompt.changed,
            code.changed,
            bool(tools.added or tools.removed),
            bool(capabilities.added or capabilities.removed or capabilities.modified),
            permissions.changed,
        )
    )
    return VersionDiff(
        from_version=first.version,
        to_version=second.version,
        changed=changed,
        model=model,
        prompt=prompt,
        code=code,
        tools=tools,
        capabilities=capabilities,
        permissions=permissions,
    )
