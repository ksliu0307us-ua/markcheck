"""Allow MarkCheck to run as ``python -m markcheck``."""

from __future__ import annotations

from .cli import main


if __name__ == "__main__":
    raise SystemExit(main())
