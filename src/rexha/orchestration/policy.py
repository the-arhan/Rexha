"""Centralized security and permission policy enforcement for Rexha."""

from __future__ import annotations

import logging
import os
import re
from enum import IntEnum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class PermissionTier(IntEnum):
    """Execution permission levels."""

    SAFE = 0           # Read-only queries, system metrics, foreground window. No side effects.
    STANDARD = 1       # Application launch, window restore/minimize. Normal desktop side effects.
    CONSEQUENTIAL = 2  # Process kill, file modification, terminal execution. Requires explicit confirmation.


class PolicyDecision:
    """Outcome of a policy evaluation."""

    def __init__(
        self,
        allowed: bool,
        tier: PermissionTier,
        requires_confirmation: bool,
        reason: str = "",
    ):
        self.allowed = allowed
        self.tier = tier
        self.requires_confirmation = requires_confirmation
        self.reason = reason

    def __repr__(self) -> str:
        return f"<PolicyDecision allowed={self.allowed} tier={self.tier.name} confirm={self.requires_confirmation}>"


# Default action tier registrations
ACTION_TIERS: dict[str, PermissionTier] = {
    "system.ping": PermissionTier.SAFE,
    "system.get_status": PermissionTier.SAFE,
    "system.get_metrics": PermissionTier.SAFE,
    "window.get_foreground": PermissionTier.SAFE,
    "window.list": PermissionTier.SAFE,
    "ui.sleep": PermissionTier.SAFE,
    "application.open": PermissionTier.STANDARD,
    "window.set_state": PermissionTier.STANDARD,
    "files.read": PermissionTier.SAFE,
    "files.search": PermissionTier.SAFE,
    "window.close": PermissionTier.CONSEQUENTIAL,
    "process.terminate": PermissionTier.CONSEQUENTIAL,
    "files.write": PermissionTier.CONSEQUENTIAL,
    "files.delete": PermissionTier.CONSEQUENTIAL,
    "command.execute": PermissionTier.CONSEQUENTIAL,
}

FORBIDDEN_SYSTEM_PATHS = [
    Path(r"C:\Windows\System32\config"),
    Path(r"C:\Windows\System32\drivers"),
]

# Windows reserved DOS device names
DOS_DEVICE_REGEX = re.compile(
    r"^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(\..*)?$",
    re.IGNORECASE,
)


class PolicyEngine:
    """Enforces execution boundaries, permission tiers, and safe path restrictions."""

    def __init__(self, allowed_roots: list[Path | str] | None = None):
        self.allowed_roots = [
            Path(p).resolve() for p in (allowed_roots or [Path.home(), Path("E:\\Projects"), Path(".")])
        ]

    def evaluate(self, action_name: str, arguments: dict[str, Any]) -> PolicyDecision:
        """Evaluate an action against security rules."""
        if action_name not in ACTION_TIERS:
            return PolicyDecision(
                allowed=False,
                tier=PermissionTier.CONSEQUENTIAL,
                requires_confirmation=False,
                reason=f"Action '{action_name}' is not registered in the security catalog",
            )

        tier = ACTION_TIERS[action_name]

        # File path security validation
        if "path" in arguments or "target_path" in arguments:
            path_val = arguments.get("path") or arguments.get("target_path")
            is_write = action_name in ("files.write", "files.delete")
            if not self.is_safe_path(str(path_val), check_allowed_roots=is_write):
                return PolicyDecision(
                    allowed=False,
                    tier=tier,
                    requires_confirmation=False,
                    reason=f"Access denied: path '{path_val}' violates security isolation policy",
                )

        requires_confirm = (tier == PermissionTier.CONSEQUENTIAL)
        return PolicyDecision(
            allowed=True,
            tier=tier,
            requires_confirmation=requires_confirm,
            reason="Approved under registered policy tier",
        )

    def is_safe_path(self, target_path: str, check_allowed_roots: bool = False) -> bool:
        """Ensure file operations stay out of sensitive system directories, traversal attempts, and device paths."""
        if not target_path or not isinstance(target_path, str):
            return False

        # Reject path traversal
        if ".." in target_path:
            return False

        # Reject Windows NT device namespace prefixes
        clean_path = target_path.strip().replace("/", "\\")
        if clean_path.startswith(("\\\\.\\", "\\\\?\\")):
            return False

        # Check for reserved DOS device names in any path segment
        parts = Path(clean_path).parts
        for part in parts:
            stem = part.split("\\")[-1]
            if DOS_DEVICE_REGEX.match(stem):
                return False

        try:
            # Canonicalize path resolving symlinks and junctions
            real_path_str = os.path.realpath(os.path.abspath(target_path))
            resolved = Path(real_path_str)
        except Exception:
            return False

        # Block Windows system configuration / SAM directories
        for forbidden in FORBIDDEN_SYSTEM_PATHS:
            try:
                if resolved.is_relative_to(forbidden):
                    return False
            except AttributeError:
                if str(resolved).lower().startswith(str(forbidden).lower()):
                    return False

        # For write/delete operations, ensure path is inside at least one allowed root
        if check_allowed_roots:
            is_within_root = False
            for root in self.allowed_roots:
                try:
                    if resolved.is_relative_to(root):
                        is_within_root = True
                        break
                except AttributeError:
                    if str(resolved).lower().startswith(str(root).lower()):
                        is_within_root = True
                        break
            if not is_within_root:
                return False

        return True
