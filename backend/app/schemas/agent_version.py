import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ToolManifestEntry(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    risk: str | None = Field(default=None, max_length=100)

    model_config = ConfigDict(extra="allow")


class AgentVersionCreate(BaseModel):
    version: str = Field(min_length=1, max_length=100)
    model_name: str = Field(min_length=1, max_length=255)
    prompt_hash: str = Field(min_length=1, max_length=128)
    code_hash: str = Field(min_length=1, max_length=128)
    tool_manifest: list[ToolManifestEntry]
    capability_manifest: dict[str, Any]
    permissions: dict[str, Any]

    @field_validator("tool_manifest")
    @classmethod
    def tool_names_must_be_unique(cls, tools: list[ToolManifestEntry]) -> list[ToolManifestEntry]:
        names = [tool.name for tool in tools]
        if len(names) != len(set(names)):
            raise ValueError("tool_manifest tool names must be unique")
        return tools


class AgentVersionRead(AgentVersionCreate):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    agent_id: uuid.UUID
    deployment_fingerprint: str
    created_at: datetime


class ChangedField(BaseModel):
    changed: bool
    before: str | None = None
    after: str | None = None


class CapabilityModification(BaseModel):
    name: str
    before: Any
    after: Any


class PermissionsDiff(BaseModel):
    changed: bool
    changes: list[CapabilityModification]


class ToolsDiff(BaseModel):
    added: list[str]
    removed: list[str]


class CapabilitiesDiff(ToolsDiff):
    modified: list[CapabilityModification]


class VersionDiff(BaseModel):
    from_version: str
    to_version: str
    changed: bool
    model: ChangedField
    prompt: ChangedField
    code: ChangedField
    tools: ToolsDiff
    capabilities: CapabilitiesDiff
    permissions: PermissionsDiff
