"""Unit tests for structured action execution engine, verification, and confirmation tokens."""

import time
import pytest
from pathlib import Path
from rexha.orchestration.actions import (
    ActionExecutionEngine,
    StructuredAction,
    ConfirmationTokenManager,
)
from rexha.orchestration.policy import PolicyEngine, PermissionTier
from rexha.services.native_client import NativeCoreClient


def test_action_execution_safe():
    client = NativeCoreClient(auto_fallback=True)
    engine = ActionExecutionEngine(native_client=client)

    action = StructuredAction(
        action_name="system.ping",
        tier=PermissionTier.SAFE,
    )
    result = engine.execute(action)
    assert result.success is True
    assert result.verified is True
    assert result.data.get("pong") is True


def test_action_execution_consequential_blocked_without_confirmation():
    client = NativeCoreClient(auto_fallback=True)
    engine = ActionExecutionEngine(native_client=client)

    action = StructuredAction(
        action_name="process.terminate",
        arguments={"pid": 9999},
        tier=PermissionTier.CONSEQUENTIAL,
    )
    result = engine.execute(action, confirmed_by_user=False)
    assert result.success is False
    assert "confirmation" in result.error.lower()


def test_unregistered_action_fails():
    client = NativeCoreClient(auto_fallback=True)
    engine = ActionExecutionEngine(native_client=client)

    action = StructuredAction(
        action_name="nonexistent.action",
        tier=PermissionTier.SAFE,
    )
    result = engine.execute(action)
    assert result.success is False


def test_confirmation_token_lifecycle():
    mgr = ConfirmationTokenManager(default_ttl=1.0)
    args = {"pid": 1234, "force": True}

    # Issue token
    token = mgr.issue_token("process.terminate", args, ttl_seconds=0.5)
    assert isinstance(token, str) and len(token) > 10

    # Reject argument mismatch
    ok, err = mgr.validate_and_consume(token, "process.terminate", {"pid": 9999})
    assert ok is False
    assert "arguments do not match" in err

    # Valid token can be consumed once
    token2 = mgr.issue_token("process.terminate", args, ttl_seconds=0.5)
    ok, err = mgr.validate_and_consume(token2, "process.terminate", args)
    assert ok is True

    # Single-use: already consumed token must fail
    ok, err = mgr.validate_and_consume(token2, "process.terminate", args)
    assert ok is False
    assert "already consumed" in err.lower() or "invalid" in err.lower()

    # Expired token rejection
    token3 = mgr.issue_token("process.terminate", args, ttl_seconds=0.1)
    time.sleep(0.15)
    ok, err = mgr.validate_and_consume(token3, "process.terminate", args)
    assert ok is False
    assert "expired" in err.lower()


def test_consequential_action_execution_with_token(tmp_path):
    client = NativeCoreClient(auto_fallback=True)
    policy = PolicyEngine(allowed_roots=[tmp_path])
    token_mgr = ConfirmationTokenManager()
    engine = ActionExecutionEngine(native_client=client, policy_engine=policy, token_manager=token_mgr)

    test_file = str(tmp_path / "test_write.txt")
    args = {"path": test_file, "content": "Verified content"}

    action = StructuredAction(
        action_name="files.write",
        arguments=args,
        tier=PermissionTier.CONSEQUENTIAL,
    )

    # Execution without token fails
    res_no_token = engine.execute(action)
    assert res_no_token.success is False

    # Execution with valid token succeeds and is verified
    token = token_mgr.issue_token("files.write", args)
    res_with_token = engine.execute(action, confirmation_token=token)
    assert res_with_token.success is True
    assert res_with_token.verified is True
    assert Path(test_file).read_text(encoding="utf-8") == "Verified content"

    # Reuse of the same token fails (single-use)
    res_reuse = engine.execute(action, confirmation_token=token)
    assert res_reuse.success is False
