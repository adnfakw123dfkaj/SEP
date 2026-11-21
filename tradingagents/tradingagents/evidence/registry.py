"""Evidence reference registry (REQ-FR-004).

Every source a report cites — a tool call, a market snapshot, a news or social
item — is registered here once, keyed by a stable id. The report writer attaches
``EvidenceRef`` ids to substantive claims; the fidelity checker resolves each id
here to confirm the claim points at a real source, so a number can be traced back
rather than trusted.
"""

from __future__ import annotations

from tradingagents.contracts.evidence import EvidenceRef


class EvidenceRegistry:
    """In-memory (per-run) index of evidence references."""

    def __init__(self):
        self._refs: dict[str, EvidenceRef] = {}

    def register(self, ref: EvidenceRef) -> EvidenceRef:
        """Register ``ref`` by its id (last write wins for a re-fetch of the same id)."""
        self._refs[ref.id] = ref
        return ref

    def register_many(self, refs) -> None:
        for ref in refs:
            self.register(ref)

    def get(self, ref_id: str) -> EvidenceRef | None:
        return self._refs.get(ref_id)

    def contains(self, ref_id: str) -> bool:
        return ref_id in self._refs

    def ids(self) -> list[str]:
        return list(self._refs)

    def all(self) -> list[EvidenceRef]:
        return list(self._refs.values())

    def __len__(self) -> int:
        return len(self._refs)
