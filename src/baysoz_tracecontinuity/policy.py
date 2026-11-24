"""Auditable policy controls for Baysöz Labs <baysozlabs@proton.me>."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any


@dataclass(frozen=True)
class Policy:
    max_depth: int = 64
    skew_tolerance_ns: int = 1_000_000
    require_error_type: bool = True
    disabled_rules: frozenset[str] = frozenset()

    def enabled(self, rule_id: str) -> bool:
        return rule_id not in self.disabled_rules

    @classmethod
    def from_mapping(cls, data: Any) -> Policy:
        if not isinstance(data, dict):
            raise ValueError("policy must be a JSON object")
        known = {"max_depth", "skew_tolerance_ns", "require_error_type", "disabled_rules"}
        unknown = sorted(set(data) - known)
        if unknown:
            raise ValueError(f"unknown policy keys: {', '.join(unknown)}")
        policy = cls()
        updates: dict[str, Any] = {}
        for key in ("max_depth", "skew_tolerance_ns"):
            if key in data:
                value = data[key]
                if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                    raise ValueError(f"{key} must be a non-negative integer")
                updates[key] = value
        if "require_error_type" in data:
            if not isinstance(data["require_error_type"], bool):
                raise ValueError("require_error_type must be a boolean")
            updates["require_error_type"] = data["require_error_type"]
        if "disabled_rules" in data:
            raw = data["disabled_rules"]
            if not isinstance(raw, list) or not all(isinstance(item, str) for item in raw):
                raise ValueError("disabled_rules must be an array of rule identifiers")
            updates["disabled_rules"] = frozenset(raw)
        return replace(policy, **updates)
