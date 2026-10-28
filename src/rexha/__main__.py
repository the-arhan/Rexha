"""CLI and module entry point for launching Rexha."""

import sys
from rexha.app import RexhaApp


def main() -> None:
    """Launch the Rexha Desktop Assistant."""
    app = RexhaApp()
    sys.exit(app.run())


if __name__ == "__main__":
    main()
