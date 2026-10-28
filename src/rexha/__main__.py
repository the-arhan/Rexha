"""CLI and module entry point for launching Rexha."""

import sys
from pathlib import Path

# Ensure 'src' is on sys.path even if launched directly or as python -m src.rexha
_src_dir = str(Path(__file__).resolve().parent.parent)
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

from rexha.app import RexhaApp


def main() -> None:
    """Launch the Rexha Desktop Assistant."""
    app = RexhaApp()
    sys.exit(app.run())


if __name__ == "__main__":
    main()
