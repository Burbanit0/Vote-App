"""Root confinement for the run explorer: every file it reads resolves inside its root.

A run directory is whatever a batch wrote there, and a symlink inside one can point
anywhere on the host. The explorer never follows one out of its root: `run_catalog`
refuses to list a run whose files escape, and `run_registry` skips a file (or the
runner's outer directory) that does.
"""
from __future__ import annotations

from pathlib import Path


def inside(path: Path, root: Path) -> bool:
    """True when `path` resolves inside `root`, symlinks followed on both sides.

    A path that cannot be resolved at all (a symlink loop, a permission error on a
    parent) is treated as outside: the explorer refuses what it cannot vouch for.
    """
    try:
        return path.resolve().is_relative_to(root.resolve())
    except OSError:
        return False
