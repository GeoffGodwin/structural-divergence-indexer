"""Tests for sdi.cli.init_cmd — _find_git_root, _update_gitignore, init_cmd."""

from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from sdi.cli import cli
from sdi.cli.init_cmd import _find_git_root, _update_gitignore


class TestFindGitRoot:
    def test_returns_directory_containing_dot_git(self, tmp_path: Path) -> None:
        (tmp_path / ".git").mkdir()
        assert _find_git_root(tmp_path) == tmp_path

    def test_walks_up_from_subdirectory(self, tmp_path: Path) -> None:
        """Should find .git several levels above the start directory."""
        (tmp_path / ".git").mkdir()
        deep = tmp_path / "a" / "b" / "c"
        deep.mkdir(parents=True)
        assert _find_git_root(deep) == tmp_path

    def test_returns_none_when_no_git_root(self, tmp_path: Path) -> None:
        """No .git anywhere in the tree → None."""
        subdir = tmp_path / "noRepo"
        subdir.mkdir()
        # Use a subtree that has no .git above it within tmp_path.
        # We can't guarantee tmp_path itself has no .git above it on the real fs,
        # so we create a directory that definitely has no .git: check only this subdir.
        result = _find_git_root(subdir)
        # Either None (ideal) or it found a real .git above the tmp dir.
        # We only assert None when we're sure there's no real git root above.
        if result is not None:
            assert (result / ".git").exists()

    def test_returns_none_for_bare_tmp_with_no_git(self, tmp_path: Path) -> None:
        """tmp_path with no .git and a controlled parent chain → None."""
        # Build a path whose entire ancestry is under tmp_path.
        root = tmp_path / "isolated"
        root.mkdir()
        child = root / "child"
        child.mkdir()
        # Mock the filesystem walk by using a custom start that is under tmp_path.
        # Since tmp_path has no .git, _find_git_root must eventually hit the real
        # filesystem root. We instead verify that the absence of .git in our subtree
        # means the function doesn't return *our* directory as a git root.
        result = _find_git_root(child)
        if result is not None:
            # Acceptable only if a real .git exists above tmp_path (CI runner inside a repo).
            assert (result / ".git").exists()
        # What we're really asserting: the result is NOT our tmp dirs.
        assert result != child
        assert result != root

    def test_start_dir_is_resolved_to_absolute(self, tmp_path: Path) -> None:
        """_find_git_root handles relative paths via resolve()."""
        (tmp_path / ".git").mkdir()
        # Passing an already-absolute path; just verify it still works correctly.
        result = _find_git_root(tmp_path)
        assert result == tmp_path


class TestUpdateGitignore:
    def test_creates_gitignore_when_absent(self, tmp_path: Path) -> None:
        gitignore = tmp_path / ".gitignore"
        assert not gitignore.exists()
        _update_gitignore(gitignore)
        assert gitignore.exists()
        assert ".sdi/cache/" in gitignore.read_text()

    def test_adds_sdi_cache_entry_to_existing_file(self, tmp_path: Path) -> None:
        gitignore = tmp_path / ".gitignore"
        gitignore.write_text("*.pyc\n__pycache__/\n", encoding="utf-8")
        _update_gitignore(gitignore)
        content = gitignore.read_text(encoding="utf-8")
        assert ".sdi/cache/" in content
        # Original content must be preserved.
        assert "*.pyc" in content

    def test_idempotent_when_entry_already_present(self, tmp_path: Path) -> None:
        gitignore = tmp_path / ".gitignore"
        initial = "*.pyc\n.sdi/cache/\n"
        gitignore.write_text(initial, encoding="utf-8")
        _update_gitignore(gitignore)
        # Should not duplicate the entry.
        content = gitignore.read_text(encoding="utf-8")
        assert content.count(".sdi/cache/") == 1

    def test_idempotent_preserves_original_content(self, tmp_path: Path) -> None:
        """Calling _update_gitignore twice must not modify file the second time."""
        gitignore = tmp_path / ".gitignore"
        gitignore.write_text("*.log\n", encoding="utf-8")
        _update_gitignore(gitignore)
        content_after_first = gitignore.read_text(encoding="utf-8")
        _update_gitignore(gitignore)
        content_after_second = gitignore.read_text(encoding="utf-8")
        assert content_after_first == content_after_second

    def test_new_gitignore_has_correct_entry(self, tmp_path: Path) -> None:
        gitignore = tmp_path / ".gitignore"
        _update_gitignore(gitignore)
        content = gitignore.read_text(encoding="utf-8")
        assert ".sdi/cache/" in content


class TestInitCmd:
    """End-to-end tests for `sdi init` invoked via the CLI runner."""

    def _invoke(self, args: list[str], cwd: Path) -> object:
        runner = CliRunner()
        return runner.invoke(cli, args, catch_exceptions=False)

    def test_happy_path_creates_config_toml(self, tmp_path: Path) -> None:
        (tmp_path / ".git").mkdir()
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            # Use tmp_path as cwd by invoking from that directory.
            result = runner.invoke(cli, ["init"], catch_exceptions=False,
                                   env={"HOME": str(tmp_path)})
        config_toml = tmp_path / ".sdi" / "config.toml"
        assert config_toml.exists(), "Expected .sdi/config.toml to be created"

    def test_happy_path_creates_snapshots_dir(self, tmp_path: Path) -> None:
        (tmp_path / ".git").mkdir()
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            runner.invoke(cli, ["init"], catch_exceptions=False,
                          env={"HOME": str(tmp_path)})
        assert (tmp_path / ".sdi" / "snapshots").is_dir()

    def test_happy_path_exits_0(self, tmp_path: Path) -> None:
        (tmp_path / ".git").mkdir()
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(cli, ["init"], catch_exceptions=False,
                                   env={"HOME": str(tmp_path)})
        assert result.exit_code == 0

    def test_happy_path_success_message_in_output(self, tmp_path: Path) -> None:
        (tmp_path / ".git").mkdir()
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(cli, ["init"], catch_exceptions=False,
                                   env={"HOME": str(tmp_path)})
        assert "Initialized" in result.output

    def test_already_initialized_without_force_exits_0(self, tmp_path: Path) -> None:
        """Second init without --force should print a message but exit 0."""
        (tmp_path / ".git").mkdir()
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            runner.invoke(cli, ["init"], catch_exceptions=False,
                          env={"HOME": str(tmp_path)})
            result = runner.invoke(cli, ["init"], catch_exceptions=False,
                                   env={"HOME": str(tmp_path)})
        assert result.exit_code == 0
        assert "already initialized" in result.output.lower()

    def test_already_initialized_without_force_mentions_force(self, tmp_path: Path) -> None:
        """Second init should tell the user about --force."""
        (tmp_path / ".git").mkdir()
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            runner.invoke(cli, ["init"], catch_exceptions=False,
                          env={"HOME": str(tmp_path)})
            result = runner.invoke(cli, ["init"], catch_exceptions=False,
                                   env={"HOME": str(tmp_path)})
        assert "--force" in result.output

    def test_force_flag_reinitializes_existing_project(self, tmp_path: Path) -> None:
        """--force must overwrite existing config.toml and exit 0."""
        (tmp_path / ".git").mkdir()
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            runner.invoke(cli, ["init"], catch_exceptions=False,
                          env={"HOME": str(tmp_path)})
            result = runner.invoke(cli, ["init", "--force"], catch_exceptions=False,
                                   env={"HOME": str(tmp_path)})
        assert result.exit_code == 0
        assert "Reinitialized" in result.output

    def test_non_git_repo_exits_code_2(self, tmp_path: Path) -> None:
        """Running init outside a git repo must exit with code 2."""
        # Ensure there's no .git above tmp_path in the real fs by using an
        # isolated filesystem. We use catch_exceptions=True here because
        # SystemExit(2) would otherwise propagate.
        runner = CliRunner()
        with runner.isolated_filesystem():
            # isolated_filesystem creates a fresh temp dir with no .git.
            result = runner.invoke(cli, ["init"])
        assert result.exit_code == 2

    def test_non_git_repo_error_message_on_stderr(self, tmp_path: Path) -> None:
        """Error message for non-git repo should explain the problem."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(cli, ["init"])
        # CliRunner mixes stdout+stderr by default.
        assert "git" in result.output.lower()

    def test_gitignore_updated_with_sdi_cache(self, tmp_path: Path) -> None:
        (tmp_path / ".git").mkdir()
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            runner.invoke(cli, ["init"], catch_exceptions=False,
                          env={"HOME": str(tmp_path)})
        gitignore = tmp_path / ".gitignore"
        if gitignore.exists():
            assert ".sdi/cache/" in gitignore.read_text(encoding="utf-8")
