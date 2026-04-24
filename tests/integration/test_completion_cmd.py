"""Integration tests for the sdi completion command.

Verifies that `sdi completion <shell>` emits the correct eval line to
stdout, a bracketed hint to stderr, and exits 0.  Invalid shell names
must exit non-zero.
"""

from __future__ import annotations

import pytest
from click.testing import CliRunner

from sdi.cli import cli
from sdi.cli.completion_cmd import _INSTRUCTIONS


@pytest.fixture
def runner() -> CliRunner:
    # CliRunner mixes stderr into result.output by default in this Click version.
    return CliRunner()


# ---------------------------------------------------------------------------
# Exit code
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("shell", ["bash", "zsh", "fish"])
def test_completion_exits_zero(runner: CliRunner, shell: str) -> None:
    result = runner.invoke(cli, ["completion", shell], catch_exceptions=False)
    assert result.exit_code == 0, f"exit {result.exit_code}: {result.output}"


def test_completion_invalid_shell_exits_nonzero(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["completion", "powershell"])
    assert result.exit_code != 0


# ---------------------------------------------------------------------------
# stdout — eval line
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("shell", ["bash", "zsh", "fish"])
def test_completion_eval_line_in_output(runner: CliRunner, shell: str) -> None:
    """The line that users evaluate in their shell profile must be in output."""
    eval_line, _ = _INSTRUCTIONS[shell]
    result = runner.invoke(cli, ["completion", shell], catch_exceptions=False)
    assert eval_line in result.output, (
        f"Expected eval line {eval_line!r} not found in output:\n{result.output}"
    )


def test_completion_bash_eval_line_exact(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["completion", "bash"], catch_exceptions=False)
    assert 'eval "$(_SDI_COMPLETE=bash_source sdi)"' in result.output


def test_completion_zsh_eval_line_exact(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["completion", "zsh"], catch_exceptions=False)
    assert 'eval "$(_SDI_COMPLETE=zsh_source sdi)"' in result.output


def test_completion_fish_eval_line_exact(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["completion", "fish"], catch_exceptions=False)
    assert "_SDI_COMPLETE=fish_source sdi | source" in result.output


# ---------------------------------------------------------------------------
# stderr — hint line (folded into result.output by mix_stderr=True)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("shell", ["bash", "zsh", "fish"])
def test_completion_hint_prefixed_with_hash(runner: CliRunner, shell: str) -> None:
    """The hint must be emitted with a leading '# ' so it is a shell comment."""
    _, hint = _INSTRUCTIONS[shell]
    expected_hint = f"# {hint}"
    result = runner.invoke(cli, ["completion", shell], catch_exceptions=False)
    assert expected_hint in result.output, (
        f"Expected hint {expected_hint!r} not found in output:\n{result.output}"
    )


def test_completion_bash_hint_exact(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["completion", "bash"], catch_exceptions=False)
    assert '# Add to ~/.bashrc' in result.output


def test_completion_zsh_hint_exact(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["completion", "zsh"], catch_exceptions=False)
    assert '# Add to ~/.zshrc' in result.output


def test_completion_fish_hint_exact(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["completion", "fish"], catch_exceptions=False)
    assert '# Add to ~/.config/fish' in result.output


# ---------------------------------------------------------------------------
# Output ordering: eval line before hint
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("shell", ["bash", "zsh", "fish"])
def test_completion_eval_line_before_hint(runner: CliRunner, shell: str) -> None:
    """The eval line (stdout) must appear before the hint comment (stderr)."""
    eval_line, hint = _INSTRUCTIONS[shell]
    result = runner.invoke(cli, ["completion", shell], catch_exceptions=False)
    eval_pos = result.output.find(eval_line)
    hint_pos = result.output.find(f"# {hint}")
    assert eval_pos != -1, "eval line not found"
    assert hint_pos != -1, "hint not found"
    assert eval_pos < hint_pos, "eval line should appear before the hint"
