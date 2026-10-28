"""Regression test for package import and CLI module launch configuration."""

import subprocess
import sys
import time
from pathlib import Path


def test_rexha_package_importable() -> None:
    """Verify that 'rexha' is directly importable without relying on 'src.' prefix."""
    import rexha
    from rexha.app import RexhaApp
    from rexha.core.state_machine import AssistantState

    assert hasattr(rexha, "__version__")
    assert RexhaApp is not None
    assert AssistantState.SLEEPING.value == "SLEEPING"


def test_python_m_rexha_invocation() -> None:
    """Verify that 'python -m rexha' launches as a subprocess without ModuleNotFoundError."""
    project_root = Path(__file__).resolve().parent.parent.parent

    proc = subprocess.Popen(
        [sys.executable, "-m", "rexha"],
        cwd=str(project_root),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    try:
        # Give the process enough time to initialize QApplication and UI
        time.sleep(1.8)

        # Check if process terminated prematurely due to an import error
        poll_result = proc.poll()
        if poll_result is not None:
            stdout, stderr = proc.communicate(timeout=2)
            assert "ModuleNotFoundError" not in stderr, f"Failed with ModuleNotFoundError:\n{stderr}"
            assert poll_result == 0, f"Process exited unexpectedly with code {poll_result}:\n{stderr}"
        else:
            # Process is running and healthy; terminate cleanly
            proc.terminate()
            proc.wait(timeout=3)
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait(timeout=3)


def test_python_m_src_rexha_invocation_fallback() -> None:
    """Verify that even legacy 'python -m src.rexha' resolves without ModuleNotFoundError."""
    project_root = Path(__file__).resolve().parent.parent.parent

    proc = subprocess.Popen(
        [sys.executable, "-m", "src.rexha"],
        cwd=str(project_root),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    try:
        time.sleep(1.8)
        poll_result = proc.poll()
        if poll_result is not None:
            stdout, stderr = proc.communicate(timeout=2)
            assert "ModuleNotFoundError" not in stderr, f"Failed with ModuleNotFoundError:\n{stderr}"
            assert poll_result == 0, f"Process exited unexpectedly with code {poll_result}:\n{stderr}"
        else:
            proc.terminate()
            proc.wait(timeout=3)
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait(timeout=3)
