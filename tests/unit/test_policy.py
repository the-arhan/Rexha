"""Unit tests for security policy, path isolation, and Windows path canonicalization."""

import pytest
from pathlib import Path
from rexha.orchestration.policy import PolicyEngine, PermissionTier


def test_safe_action_evaluation():
    policy = PolicyEngine()
    decision = policy.evaluate("system.get_status", {})
    assert decision.allowed is True
    assert decision.tier == PermissionTier.SAFE
    assert decision.requires_confirmation is False


def test_standard_action_evaluation():
    policy = PolicyEngine()
    decision = policy.evaluate("application.open", {"executable": "notepad.exe"})
    assert decision.allowed is True
    assert decision.tier == PermissionTier.STANDARD
    assert decision.requires_confirmation is False


def test_consequential_action_requires_confirmation():
    policy = PolicyEngine()
    decision = policy.evaluate("process.terminate", {"pid": 1234})
    assert decision.allowed is True
    assert decision.tier == PermissionTier.CONSEQUENTIAL
    assert decision.requires_confirmation is True


def test_unregistered_action_denied():
    policy = PolicyEngine()
    decision = policy.evaluate("unregistered.dangerous.action", {})
    assert decision.allowed is False


def test_path_traversal_detection():
    policy = PolicyEngine()
    assert policy.is_safe_path("documents/safe_note.txt") is True
    # Path traversal attempts blocked
    assert policy.is_safe_path("../../Windows/System32/config/SAM") is False
    assert policy.is_safe_path(r"C:\Windows\System32\config\SAM") is False

    # Blocked during evaluation
    decision = policy.evaluate("files.read", {"path": r"..\..\sensitive.txt"})
    assert decision.allowed is False


def test_dos_device_names_rejected():
    policy = PolicyEngine()
    # Test DOS device names at root and with extensions
    assert policy.is_safe_path("CON") is False
    assert policy.is_safe_path("con.txt") is False
    assert policy.is_safe_path("PRN") is False
    assert policy.is_safe_path("AUX") is False
    assert policy.is_safe_path("NUL") is False
    assert policy.is_safe_path("nul.dat") is False
    assert policy.is_safe_path("COM1") is False
    assert policy.is_safe_path("COM9.log") is False
    assert policy.is_safe_path("LPT1") is False
    assert policy.is_safe_path(r"subfolder\CON") is False
    assert policy.is_safe_path(r"data\NUL.txt") is False

    decision = policy.evaluate("files.read", {"path": "CON"})
    assert decision.allowed is False


def test_nt_device_namespaces_rejected():
    policy = PolicyEngine()
    assert policy.is_safe_path(r"\\.\PhysicalDrive0") is False
    assert policy.is_safe_path(r"\\?\C:\Windows\System32") is False
    assert policy.is_safe_path(r"\\.\pipe\rexha_ipc") is False

    decision = policy.evaluate("files.write", {"path": r"\\.\PhysicalDrive0", "content": "bad"})
    assert decision.allowed is False


def test_allowed_roots_isolation_for_writes(tmp_path):
    allowed_root = tmp_path / "sandbox"
    allowed_root.mkdir()
    outside_root = tmp_path / "outside"
    outside_root.mkdir()

    policy = PolicyEngine(allowed_roots=[allowed_root])

    # Safe inside allowed root
    inside_file = str(allowed_root / "test.txt")
    assert policy.is_safe_path(inside_file, check_allowed_roots=True) is True

    # Denied outside allowed root for write operations
    outside_file = str(outside_root / "test.txt")
    assert policy.is_safe_path(outside_file, check_allowed_roots=True) is False

    # Evaluation confirms rejection
    dec_inside = policy.evaluate("files.write", {"path": inside_file, "content": "ok"})
    assert dec_inside.allowed is True

    dec_outside = policy.evaluate("files.write", {"path": outside_file, "content": "bad"})
    assert dec_outside.allowed is False
