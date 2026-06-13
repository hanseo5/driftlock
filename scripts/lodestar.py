#!/usr/bin/env python3
"""Dev convenience shim.

Runs the Lodestar CLI straight from a source checkout, without installing the
package. For a real install use `uv tool install` / `uvx` / `pip install` (see
the README) and call the `lodestar` command directly.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from lodestar import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
