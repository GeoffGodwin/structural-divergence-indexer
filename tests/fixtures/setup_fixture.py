#!/usr/bin/env python3
"""Build the evolving fixture: a real git repo with progressive structural drift.

This module is both a standalone script and an importable helper.

Standalone usage:
    python tests/fixtures/setup_fixture.py [output_dir]

Importable usage:
    from tests.fixtures.setup_fixture import create_evolving_fixture
    repo = create_evolving_fixture(tmp_path / "repo")
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Commit content — each dict is written as a batch commit
# ---------------------------------------------------------------------------

_FILES_COMMIT_1: dict[str, str] = {
    "__init__.py": "",
    "module_a.py": (
        "def process(data: str) -> str:\n"
        "    try:\n"
        "        return data.strip()\n"
        "    except AttributeError:\n"
        '        return ""\n'
    ),
    "module_b.py": (
        "def compute(values: list) -> int:\n"
        "    try:\n"
        "        return sum(values)\n"
        "    except TypeError:\n"
        "        return 0\n"
    ),
}

_FILES_COMMIT_2: dict[str, str] = {
    "module_c.py": (
        "def validate(text: str) -> bool:\n"
        "    try:\n"
        "        return bool(text.strip())\n"
        "    except AttributeError:\n"
        "        return False\n"
    ),
}

_FILES_COMMIT_3: dict[str, str] = {
    "module_d.py": (
        "def transform(item: object) -> object:\n"
        "    try:\n"
        "        return str(item).upper()\n"
        "    except (ValueError, TypeError) as exc:\n"
        '        print(f"Error: {exc}")\n'
        "        return None\n"
        "    finally:\n"
        "        pass\n"
    ),
}

_FILES_COMMIT_4: dict[str, str] = {
    "module_e.py": (
        "import asyncio\n\n"
        "async def fetch(url: str) -> str:\n"
        "    await asyncio.sleep(0)\n"
        "    return url\n\n"
        "async def process(data: str) -> str:\n"
        "    await asyncio.sleep(0)\n"
        "    return data.strip() if data else ''\n"
    ),
}

_FILES_COMMIT_5: dict[str, str] = {
    "module_f.py": (
        "def parse(text: str) -> float:\n"
        "    try:\n"
        "        return float(text)\n"
        "    except ValueError:\n"
        "        raise\n"
        "    except TypeError:\n"
        "        return 0.0\n"
        "    else:\n"
        "        pass\n"
        "    return 0.0\n"
    ),
    "module_g.py": (
        "import logging\n\n"
        "logger = logging.getLogger(__name__)\n\n"
        "def report(msg: str) -> None:\n"
        "    logger.info(msg)\n"
        "    logger.warning('done: %s', msg)\n"
    ),
}

_COMMITS: list[tuple[dict[str, str], str]] = [
    (_FILES_COMMIT_1, "chore: initial project baseline"),
    (_FILES_COMMIT_2, "feat: add validation module"),
    (_FILES_COMMIT_3, "feat: add transform with multi-exception handling"),
    (_FILES_COMMIT_4, "feat: add async processing module"),
    (_FILES_COMMIT_5, "feat: add parse and logging modules"),
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _git(args: list[str], cwd: Path) -> None:
    """Run a git command, raising on failure."""
    subprocess.run(args, cwd=cwd, check=True, capture_output=True)


def _commit_files(files: dict[str, str], message: str, repo: Path) -> None:
    """Write files, stage them, and create a commit."""
    for name, content in files.items():
        (repo / name).write_text(content, encoding="utf-8")
    _git(["git", "add", "."], repo)
    _git(["git", "commit", "-m", message], repo)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def create_evolving_fixture(target_dir: Path) -> Path:
    """Build an evolving fixture at *target_dir*.

    Creates a real git repository with 5 commits that progressively increase
    structural diversity: baseline, multi-exception handling, async patterns,
    and logging patterns introduce different structural shapes across runs.

    Args:
        target_dir: Directory to create the repository in. Created if absent.

    Returns:
        Path to the initialized repository (same as *target_dir*).
    """
    target_dir.mkdir(parents=True, exist_ok=True)
    _git(["git", "init"], target_dir)
    _git(["git", "config", "user.email", "fixture@example.com"], target_dir)
    _git(["git", "config", "user.name", "Fixture Bot"], target_dir)

    for files, message in _COMMITS:
        _commit_files(files, message, target_dir)

    return target_dir


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python setup_fixture.py <output-path>", file=sys.stderr)
        sys.exit(1)
    out = Path(sys.argv[1])
    create_evolving_fixture(out)
    print(f"Evolving fixture created at {out}")
