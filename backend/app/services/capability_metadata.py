from dataclasses import dataclass


@dataclass(frozen=True)
class CapabilityMetadata:
    effect: str
    risk_domain: str

    @property
    def sensitive(self) -> bool:
        return self.effect in {"financial", "destructive"}


_DEMO_CAPABILITIES: dict[str, CapabilityMetadata] = {
    "catalog.read": CapabilityMetadata(effect="read", risk_domain="data"),
    "purchase.create": CapabilityMetadata(effect="write", risk_domain="commerce"),
    "payment.execute": CapabilityMetadata(effect="financial", risk_domain="payments"),
    "bank.transfer": CapabilityMetadata(effect="financial", risk_domain="payments"),
}
_UNKNOWN_CAPABILITY = CapabilityMetadata(effect="unknown", risk_domain="unknown")


def metadata_for(capability_name: str) -> CapabilityMetadata:
    """Return explicit demo metadata; unknown capabilities receive no inherited trust."""
    return _DEMO_CAPABILITIES.get(capability_name, _UNKNOWN_CAPABILITY)
