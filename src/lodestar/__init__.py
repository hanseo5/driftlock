"""Lodestar — the deterministic gate engine behind the Lodestar harness.

The Markdown skills carry agent behaviour; this package validates the artifact
contracts, applies runner transitions, runs the quality and spec gates, plans
execution, and drives a deterministic dry-run.
"""
from __future__ import annotations

from .cli import main

__version__ = "0.1.0"
__all__ = ["main", "__version__"]
