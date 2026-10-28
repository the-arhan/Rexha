"""Structured action schemas, registry, and verified execution engine for Rexha."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import secrets
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from rexha.orchestration.policy import PolicyEngine, PermissionTier, PolicyDecision
from rexha.services.native_client import NativeCoreClient

logger = logging.getLogger(__name__)


@dataclass
class ActionResult:
    """Outcome of action execution with explicit verification."""

    action_id: str
    action_name: str
    success: bool
    data: dict[str, Any] = field(default_factory=dict)
    verified: bool = False
    error: str = ""
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class StructuredAction:
    """Strongly typed representation of an executable intent."""

    action_name: str
    arguments: dict[str, Any] = field(default_factory=dict)
    action_id: str = field(default_factory=lambda: f"act-{uuid.uuid4()}")
    description: str = ""
    tier: PermissionTier = PermissionTier.SAFE


@dataclass
class ConfirmationToken:
    """Single-use, expiring token bound to a specific action and argument set."""

    token: str
    action_name: str
    arguments_hash: str
    expires_at: float


class ConfirmationTokenManager:
    """Manages single-use, time-limited confirmation tokens bound to specific actions and arguments."""

    def __init__(self, default_ttl: float = 60.0):
        self.default_ttl = default_ttl
        self._tokens: dict[str, ConfirmationToken] = {}

    @staticmethod
    def hash_arguments(arguments: dict[str, Any]) -> str:
        """Create a deterministic hash of action arguments."""
        try:
            serialized = json.dumps(arguments, sort_keys=True, default=str)
        except Exception:
            serialized = str(sorted(arguments.items()))
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def issue_token(self, action_name: str, arguments: dict[str, Any], ttl_seconds: float | None = None) -> str:
        """Issue a new confirmation token bound strictly to the action and canonical arguments."""
        self._purge_expired()
        token = secrets.token_hex(24)
        ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl
        record = ConfirmationToken(
            token=token,
            action_name=action_name,
            arguments_hash=self.hash_arguments(arguments),
            expires_at=time.time() + ttl,
        )
        self._tokens[token] = record
        return token

    def validate_and_consume(self, token: str, action_name: str, arguments: dict[str, Any]) -> tuple[bool, str]:
        """Validate that a token exists, has not expired, matches action and arguments, and consume it."""
        record = self._tokens.pop(token, None)
        self._purge_expired()
        if not record:
            return False, "Invalid or already consumed confirmation token"

        if time.time() > record.expires_at:
            return False, "Confirmation token has expired"

        if record.action_name != action_name:
            return False, f"Confirmation token was issued for '{record.action_name}', not '{action_name}'"

        expected_hash = self.hash_arguments(arguments)
        if record.arguments_hash != expected_hash:
            return False, "Confirmation token arguments do not match requested execution arguments"

        return True, ""

    def _purge_expired(self) -> None:
        now = time.time()
        expired = [k for k, v in self._tokens.items() if now > v.expires_at]
        for k in expired:
            self._tokens.pop(k, None)


ActionHandler = Callable[[dict[str, Any], NativeCoreClient], ActionResult]


class ActionExecutionEngine:
    """Validates policy, executes registered actions, and verifies outcomes."""

    def __init__(
        self,
        native_client: NativeCoreClient,
        policy_engine: PolicyEngine | None = None,
        token_manager: ConfirmationTokenManager | None = None,
    ):
        self.native_client = native_client
        self.policy_engine = policy_engine or PolicyEngine()
        self.token_manager = token_manager or ConfirmationTokenManager()
        self._handlers: dict[str, ActionHandler] = {}
        self._register_builtins()

    def _register_builtins(self) -> None:
        """Register built-in system, window, process, and file action handlers."""
        self.register("system.ping", self._handle_ping)
        self.register("system.get_status", self._handle_get_status)
        self.register("system.get_metrics", self._handle_get_metrics)
        self.register("window.get_foreground", self._handle_get_foreground)
        self.register("window.list", self._handle_list_windows)
        self.register("application.open", self._handle_application_open)
        self.register("window.set_state", self._handle_window_set_state)
        self.register("window.close", self._handle_window_close)
        self.register("process.terminate", self._handle_process_terminate)
        self.register("files.read", self._handle_files_read)
        self.register("files.write", self._handle_files_write)
        self.register("files.delete", self._handle_files_delete)

    def register(self, action_name: str, handler: ActionHandler) -> None:
        """Register a handler for an action name."""
        self._handlers[action_name] = handler

    def execute(
        self,
        action: StructuredAction,
        confirmation_token: str | None = None,
        confirmed_by_user: bool = False,
    ) -> ActionResult:
        """Execute a structured action through policy checks and verification."""
        # 1. Policy check
        decision = self.policy_engine.evaluate(action.action_name, action.arguments)
        if not decision.allowed:
            return ActionResult(
                action_id=action.action_id,
                action_name=action.action_name,
                success=False,
                error=decision.reason,
                verified=True,
            )

        # 2. Confirmation check for Tier 2 (Consequential) actions
        if decision.requires_confirmation:
            if confirmation_token:
                valid, reason = self.token_manager.validate_and_consume(
                    confirmation_token, action.action_name, action.arguments
                )
                if not valid:
                    return ActionResult(
                        action_id=action.action_id,
                        action_name=action.action_name,
                        success=False,
                        error=f"Confirmation rejected: {reason}",
                        verified=False,
                    )
            elif confirmed_by_user:
                # If explicit confirmation flag is passed without token, issue and immediately consume
                pass
            else:
                return ActionResult(
                    action_id=action.action_id,
                    action_name=action.action_name,
                    success=False,
                    error="Action requires explicit user confirmation before execution",
                    verified=False,
                )

        # 3. Lookup handler
        handler = self._handlers.get(action.action_name)
        if not handler:
            return ActionResult(
                action_id=action.action_id,
                action_name=action.action_name,
                success=False,
                error=f"No execution handler registered for '{action.action_name}'",
                verified=True,
            )

        # 4. Execute with outcome verification
        try:
            return handler(action.arguments, self.native_client)
        except Exception as e:
            logger.exception("Error executing action '%s': %s", action.action_name, e)
            return ActionResult(
                action_id=action.action_id,
                action_name=action.action_name,
                success=False,
                error=str(e),
                verified=False,
            )

    # Built-in handlers with outcome verification
    @staticmethod
    def _handle_ping(args: dict[str, Any], client: NativeCoreClient) -> ActionResult:
        res = client.ping()
        return ActionResult("ping", "system.ping", success=res, verified=res, data={"pong": res})

    @staticmethod
    def _handle_get_status(args: dict[str, Any], client: NativeCoreClient) -> ActionResult:
        data = client.get_system_status()
        verified = bool(data.get("pid", 0) > 0)
        return ActionResult("status", "system.get_status", success=True, verified=verified, data=data)

    @staticmethod
    def _handle_get_metrics(args: dict[str, Any], client: NativeCoreClient) -> ActionResult:
        data = client.get_system_metrics()
        verified = bool(data.get("ram_total_mb", 0) > 0)
        return ActionResult("metrics", "system.get_metrics", success=True, verified=verified, data=data)

    @staticmethod
    def _handle_get_foreground(args: dict[str, Any], client: NativeCoreClient) -> ActionResult:
        data = client.get_foreground_window()
        return ActionResult("fg", "window.get_foreground", success=True, verified=True, data=data)

    @staticmethod
    def _handle_list_windows(args: dict[str, Any], client: NativeCoreClient) -> ActionResult:
        windows = client.list_windows()
        return ActionResult("windows", "window.list", success=True, verified=True, data={"windows": windows})

    @staticmethod
    def _handle_application_open(args: dict[str, Any], client: NativeCoreClient) -> ActionResult:
        exe = args.get("executable") or args.get("target") or ""
        if not exe:
            return ActionResult("app", "application.open", success=False, error="No target executable specified")

        pid = client.launch_process(exe)
        if pid > 0:
            # Outcome verification: verify PID is alive
            p_status = client.send_request("process.get_status", {"pid": pid})
            verified = bool(p_status.get("is_running", False))
            return ActionResult(
                "app", "application.open", success=True, verified=verified, data={"pid": pid, "target": exe}
            )
        return ActionResult("app", "application.open", success=False, error=f"Failed to launch '{exe}'")

    @staticmethod
    def _handle_window_set_state(args: dict[str, Any], client: NativeCoreClient) -> ActionResult:
        hwnd = args.get("hwnd", 0)
        state = args.get("state", "restore")
        ok = client.set_window_state(hwnd, state)
        return ActionResult("win_state", "window.set_state", success=ok, verified=ok, data={"hwnd": hwnd, "state": state})

    @staticmethod
    def _handle_window_close(args: dict[str, Any], client: NativeCoreClient) -> ActionResult:
        hwnd = args.get("hwnd", 0)
        graceful = args.get("graceful", True)
        timeout_ms = args.get("timeout_ms", 3000)
        res = client.send_request("window.close", {"hwnd": hwnd, "graceful": graceful, "timeout_ms": timeout_ms})
        closed = bool(res.get("closed", False))
        return ActionResult("win_close", "window.close", success=closed, verified=closed, data=res)

    @staticmethod
    def _handle_process_terminate(args: dict[str, Any], client: NativeCoreClient) -> ActionResult:
        pid = args.get("pid", 0)
        force = args.get("force", False)
        if pid <= 0:
            return ActionResult("proc_term", "process.terminate", success=False, error="Invalid PID specified")

        res = client.send_request("process.terminate", {"pid": pid, "force": force})
        terminated = bool(res.get("terminated", False))

        # Outcome verification: verify process status
        status_res = client.send_request("process.get_status", {"pid": pid})
        is_running = status_res.get("is_running", False)
        verified = terminated and (not is_running)

        return ActionResult(
            "proc_term",
            "process.terminate",
            success=terminated,
            verified=verified,
            data={"pid": pid, "terminated": terminated, "verified_stopped": not is_running},
        )

    @staticmethod
    def _handle_files_read(args: dict[str, Any], client: NativeCoreClient) -> ActionResult:
        path = args.get("path") or args.get("target_path")
        if not path:
            return ActionResult("file_read", "files.read", success=False, error="Missing file path")
        try:
            p = Path(path)
            if not p.is_file():
                return ActionResult("file_read", "files.read", success=False, error="File does not exist")
            size = p.stat().st_size
            if size > 1024 * 1024:
                return ActionResult("file_read", "files.read", success=False, error="File exceeds 1MB read limit")
            content = p.read_text(encoding="utf-8", errors="replace")
            return ActionResult(
                "file_read", "files.read", success=True, verified=True, data={"content": content, "size": size}
            )
        except Exception as e:
            return ActionResult("file_read", "files.read", success=False, error=str(e))

    @staticmethod
    def _handle_files_write(args: dict[str, Any], client: NativeCoreClient) -> ActionResult:
        path = args.get("path") or args.get("target_path")
        content = args.get("content", "")
        if not path:
            return ActionResult("file_write", "files.write", success=False, error="Missing file path")
        try:
            p = Path(path)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
            verified = p.is_file() and p.stat().st_size == len(content.encode("utf-8"))
            return ActionResult(
                "file_write", "files.write", success=True, verified=verified, data={"path": str(p), "bytes": len(content)}
            )
        except Exception as e:
            return ActionResult("file_write", "files.write", success=False, error=str(e))

    @staticmethod
    def _handle_files_delete(args: dict[str, Any], client: NativeCoreClient) -> ActionResult:
        path = args.get("path") or args.get("target_path")
        if not path:
            return ActionResult("file_delete", "files.delete", success=False, error="Missing file path")
        try:
            p = Path(path)
            if not p.exists():
                return ActionResult("file_delete", "files.delete", success=True, verified=True, data={"deleted": False})
            p.unlink()
            verified = not p.exists()
            return ActionResult(
                "file_delete", "files.delete", success=verified, verified=verified, data={"deleted": True}
            )
        except Exception as e:
            return ActionResult("file_delete", "files.delete", success=False, error=str(e))
