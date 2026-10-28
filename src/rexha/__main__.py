"""CLI and module entry point for launching Rexha."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Ensure 'src' is on sys.path even if launched directly or as python -m src.rexha
_src_dir = str(Path(__file__).resolve().parent.parent)
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

from rexha.app import RexhaApp


def main() -> None:
    """Parse CLI options and launch the Rexha Desktop Assistant."""
    parser = argparse.ArgumentParser(description="Rexha Desktop Assistant & Automation Platform")
    parser.add_argument("--no-native", action="store_true", help="Run without spawning the native C++ core")
    parser.add_argument("--db-path", type=str, default="", help="Custom path to SQLite database")

    args = parser.parse_args()

    app_kwargs = {"enable_native_core": not args.no_native}
    if args.db_path:
        app_kwargs["db_path"] = args.db_path

    app = RexhaApp(**app_kwargs)
    sys.exit(app.run())


if __name__ == "__main__":
    main()
