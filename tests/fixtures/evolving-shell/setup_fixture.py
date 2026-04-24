"""Create an evolving shell fixture with 4 commits of progressive drift.

C1 (baseline): 5 scripts, set -e + echo only.
C2 (drift):    adds trap ERR, cmd || exit 1 (list-bail + exit-1), echo >&2 = +4 shapes.
C3 (consolidation): replace set -e with set -euo pipefail; remove || exit 1 = net -1.
C4 (regression): add if-exit form + xargs -P = +2 shapes.

Can be run standalone: python setup_fixture.py [output_dir]
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from textwrap import dedent


def _git(args: list[str], cwd: Path) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dedent(content).lstrip(), encoding="utf-8")


def create_evolving_fixture(target_dir: Path) -> Path:
    """Materialise the evolving-shell git fixture at target_dir.

    Args:
        target_dir: Directory to create (must not exist).

    Returns:
        Path to the created git repository.
    """
    target_dir = target_dir.resolve()
    target_dir.mkdir(parents=True, exist_ok=True)

    _git(["init", "-b", "main"], cwd=target_dir)
    _git(["config", "user.email", "test@example.com"], cwd=target_dir)
    _git(["config", "user.name", "Test"], cwd=target_dir)

    # ------------------------------------------------------------------ C1
    # Shapes: {set -e (E1), echo (L1)}
    _write(target_dir / "setup.sh", """\
        #!/usr/bin/env bash
        set -e
        echo "Setting up environment"
        """)
    _write(target_dir / "cleanup.sh", """\
        #!/usr/bin/env bash
        set -e
        echo "Cleaning up"
        """)
    _write(target_dir / "run.sh", """\
        #!/usr/bin/env bash
        set -e
        source ./setup.sh
        echo "Running"
        """)
    _write(target_dir / "check.sh", """\
        #!/usr/bin/env bash
        set -e
        source ./setup.sh
        echo "Checking"
        """)
    _write(target_dir / "deploy.sh", """\
        #!/usr/bin/env bash
        set -e
        echo "Deploying"
        """)
    _git(["add", "."], cwd=target_dir)
    _git(["commit", "-m", "C1: baseline — set -e and echo only"], cwd=target_dir)

    # ------------------------------------------------------------------ C2
    # Adds: trap ERR (E_trap), list-bail || exit 1 (E_list), exit 1 cmd (E_exit1),
    #       echo >&2 redirect (L_stderr). Total +4 new shapes.
    _write(target_dir / "setup.sh", """\
        #!/usr/bin/env bash
        set -e

        cleanup() {
            echo "Cleanup triggered"
        }
        trap cleanup ERR

        echo "Setting up environment"
        """)
    _write(target_dir / "deploy.sh", """\
        #!/usr/bin/env bash
        set -e

        verify_env() {
            local env="$1"
            case "$env" in
                staging|production) ;;
                *) exit 1 ;;
            esac
        }

        do_deploy() {
            echo "Deploying to $1"
        }

        verify_env "${1:-staging}"
        echo "Starting deploy" >&2
        do_deploy "${1:-staging}" || exit 1
        echo "Deploy complete"
        """)
    _git(["add", "."], cwd=target_dir)
    _git(["commit", "-m", "C2: drift — trap ERR, || exit 1, echo >&2"], cwd=target_dir)

    # ------------------------------------------------------------------ C3
    # Removes || exit 1 (E_list gone).
    # Changes set -e to set -euo pipefail (E1 gone, E_setuo added).
    # Keeps standalone exit 1 in verify_env (E_exit1 persists).
    # Net: +1 (E_setuo) -2 (E1, E_list) = -1.
    for name in ("setup.sh", "cleanup.sh", "run.sh", "check.sh"):
        content = (target_dir / name).read_text()
        (target_dir / name).write_text(content.replace("set -e\n", "set -euo pipefail\n"))

    _write(target_dir / "deploy.sh", """\
        #!/usr/bin/env bash
        set -euo pipefail

        verify_env() {
            local env="$1"
            case "$env" in
                staging|production) ;;
                *) exit 1 ;;
            esac
        }

        do_deploy() {
            echo "Deploying to $1"
        }

        verify_env "${1:-staging}"
        echo "Starting deploy" >&2
        do_deploy "${1:-staging}"
        echo "Deploy complete"
        """)
    _git(["add", "."], cwd=target_dir)
    _git(["commit", "-m", "C3: consolidation — set -euo, remove || exit 1"], cwd=target_dir)

    # ------------------------------------------------------------------ C4
    # Adds if-exit form (E_if, new structural shape for if_statement).
    # exit 1 command (E_exit1) already present from verify_env — not new.
    # Adds xargs -P async pattern (A_xargs). Net: +2.
    _write(target_dir / "check.sh", """\
        #!/usr/bin/env bash
        set -euo pipefail
        source ./setup.sh

        check_prereqs() {
            if ! command -v curl >/dev/null 2>&1; then
                exit 1
            fi
        }

        find . -name "*.sh" | xargs -P 4 bash -n
        check_prereqs
        echo "Checking"
        """)
    _git(["add", "."], cwd=target_dir)
    _git(["commit", "-m", "C4: regression — if-exit form + xargs -P"], cwd=target_dir)

    return target_dir


if __name__ == "__main__":
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/evolving-shell-fixture")
    created = create_evolving_fixture(out)
    print(f"Created evolving-shell fixture at {created}")
