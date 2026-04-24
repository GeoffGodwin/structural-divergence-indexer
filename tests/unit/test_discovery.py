"""Tests for sdi.parsing.discovery — file discovery and language detection."""

from __future__ import annotations

from pathlib import Path

from sdi.parsing.discovery import detect_language, discover_files


class TestDetectLanguage:
    def test_python(self) -> None:
        assert detect_language(Path("foo.py")) == "python"

    def test_javascript(self) -> None:
        assert detect_language(Path("foo.js")) == "javascript"

    def test_javascript_mjs(self) -> None:
        assert detect_language(Path("foo.mjs")) == "javascript"

    def test_typescript(self) -> None:
        assert detect_language(Path("foo.ts")) == "typescript"

    def test_typescript_tsx(self) -> None:
        assert detect_language(Path("foo.tsx")) == "typescript"

    def test_go(self) -> None:
        assert detect_language(Path("foo.go")) == "go"

    def test_java(self) -> None:
        assert detect_language(Path("foo.java")) == "java"

    def test_rust(self) -> None:
        assert detect_language(Path("foo.rs")) == "rust"

    def test_unknown_extension_returns_none(self) -> None:
        assert detect_language(Path("foo.xyz")) is None

    def test_no_extension_returns_none(self) -> None:
        assert detect_language(Path("Makefile")) is None

    def test_case_insensitive(self) -> None:
        assert detect_language(Path("FOO.PY")) == "python"

    def test_markdown_is_unsupported(self) -> None:
        assert detect_language(Path("README.md")) is None


class TestShellExtensions:
    """Shell extension mapping and fish exclusion."""

    def test_sh_maps_to_shell(self) -> None:
        assert detect_language(Path("foo.sh")) == "shell"

    def test_bash_maps_to_shell(self) -> None:
        assert detect_language(Path("foo.bash")) == "shell"

    def test_zsh_maps_to_shell(self) -> None:
        assert detect_language(Path("foo.zsh")) == "shell"

    def test_ksh_maps_to_shell(self) -> None:
        assert detect_language(Path("foo.ksh")) == "shell"

    def test_dash_maps_to_shell(self) -> None:
        assert detect_language(Path("foo.dash")) == "shell"

    def test_ash_maps_to_shell(self) -> None:
        assert detect_language(Path("foo.ash")) == "shell"

    def test_fish_not_mapped(self) -> None:
        assert detect_language(Path("foo.fish")) is None


class TestShebangDetection:
    """Shebang-based discovery for extensionless scripts."""

    def _make_executable(self, path: Path) -> None:
        import stat

        path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    def test_env_bash_shebang_discovered(self, tmp_path: Path) -> None:
        script = tmp_path / "myscript"
        script.write_text("#!/usr/bin/env bash\necho hi\n", encoding="utf-8")
        self._make_executable(script)
        results = discover_files(tmp_path)
        langs = {lang for _, lang in results}
        assert "shell" in langs

    def test_env_python3_shebang_not_discovered(self, tmp_path: Path) -> None:
        script = tmp_path / "myscript"
        script.write_text("#!/usr/bin/env python3\nprint('hi')\n", encoding="utf-8")
        self._make_executable(script)
        results = discover_files(tmp_path)
        langs = {lang for _, lang in results}
        assert "shell" not in langs

    def test_no_exec_bit_not_discovered(self, tmp_path: Path) -> None:
        script = tmp_path / "myscript"
        script.write_text("#!/bin/bash\necho hi\n", encoding="utf-8")
        # No exec bit set
        results = discover_files(tmp_path)
        langs = {lang for _, lang in results}
        assert "shell" not in langs

    def test_extension_takes_precedence_no_content_read(self, tmp_path: Path) -> None:
        # .txt file with a bash shebang — extension does NOT map to shell
        script = tmp_path / "script.txt"
        script.write_text("#!/bin/bash\necho hi\n", encoding="utf-8")
        self._make_executable(script)
        results = discover_files(tmp_path)
        langs = {lang for _, lang in results}
        assert "shell" not in langs


class TestDiscoverFiles:
    def test_empty_directory(self, tmp_path: Path) -> None:
        results = discover_files(tmp_path)
        assert results == []

    def test_finds_python_files(self, tmp_path: Path) -> None:
        (tmp_path / "a.py").write_text("x = 1")
        (tmp_path / "b.py").write_text("y = 2")
        results = discover_files(tmp_path)
        paths = [p for p, _ in results]
        assert tmp_path / "a.py" in paths
        assert tmp_path / "b.py" in paths

    def test_detects_correct_language(self, tmp_path: Path) -> None:
        (tmp_path / "a.py").write_text("x = 1")
        results = discover_files(tmp_path)
        assert len(results) == 1
        assert results[0][1] == "python"

    def test_skips_unsupported_extensions(self, tmp_path: Path) -> None:
        (tmp_path / "README.md").write_text("# readme")
        (tmp_path / "data.json").write_text("{}")
        (tmp_path / "main.py").write_text("x = 1")
        results = discover_files(tmp_path)
        assert len(results) == 1
        assert results[0][1] == "python"

    def test_respects_gitignore(self, tmp_path: Path) -> None:
        (tmp_path / ".gitignore").write_text("ignored.py\n")
        (tmp_path / "ignored.py").write_text("x = 1")
        (tmp_path / "included.py").write_text("y = 2")
        results = discover_files(tmp_path)
        paths = [p for p, _ in results]
        assert tmp_path / "included.py" in paths
        assert tmp_path / "ignored.py" not in paths

    def test_respects_exclude_patterns(self, tmp_path: Path) -> None:
        vendor = tmp_path / "vendor"
        vendor.mkdir()
        (vendor / "lib.py").write_text("x = 1")
        (tmp_path / "main.py").write_text("y = 2")
        results = discover_files(tmp_path, exclude_patterns=["**/vendor/**"])
        paths = [p for p, _ in results]
        assert tmp_path / "main.py" in paths
        assert vendor / "lib.py" not in paths

    def test_excludes_git_directory(self, tmp_path: Path) -> None:
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        (git_dir / "config").write_text("[core]")
        # Create a .py file inside .git (shouldn't be discovered)
        (git_dir / "hook.py").write_text("x = 1")
        (tmp_path / "main.py").write_text("y = 2")
        results = discover_files(tmp_path)
        paths = [p for p, _ in results]
        assert tmp_path / "main.py" in paths
        assert git_dir / "hook.py" not in paths

    def test_hidden_py_files_included_unless_gitignored(self, tmp_path: Path) -> None:
        (tmp_path / ".hidden.py").write_text("x = 1")
        results = discover_files(tmp_path)
        paths = [p for p, _ in results]
        assert tmp_path / ".hidden.py" in paths

    def test_nested_directories(self, tmp_path: Path) -> None:
        sub = tmp_path / "sub" / "pkg"
        sub.mkdir(parents=True)
        (sub / "module.py").write_text("x = 1")
        results = discover_files(tmp_path)
        paths = [p for p, _ in results]
        assert sub / "module.py" in paths

    def test_gitignore_directory_pattern(self, tmp_path: Path) -> None:
        (tmp_path / ".gitignore").write_text("__pycache__/\n")
        cache = tmp_path / "__pycache__"
        cache.mkdir()
        (cache / "foo.py").write_text("x = 1")
        (tmp_path / "main.py").write_text("y = 2")
        results = discover_files(tmp_path)
        paths = [p for p, _ in results]
        assert tmp_path / "main.py" in paths
        assert cache / "foo.py" not in paths

    def test_multiple_exclude_patterns(self, tmp_path: Path) -> None:
        (tmp_path / "main.py").write_text("y = 2")
        build_dir = tmp_path / "build"
        build_dir.mkdir()
        (build_dir / "out.py").write_text("x = 1")
        dist_dir = tmp_path / "dist"
        dist_dir.mkdir()
        (dist_dir / "bundle.py").write_text("z = 3")
        results = discover_files(
            tmp_path,
            exclude_patterns=["**/build/**", "**/dist/**"],
        )
        paths = [p for p, _ in results]
        assert tmp_path / "main.py" in paths
        assert build_dir / "out.py" not in paths
        assert dist_dir / "bundle.py" not in paths

    def test_multi_language_discovery(self, tmp_path: Path) -> None:
        (tmp_path / "main.py").write_text("x = 1")
        (tmp_path / "app.ts").write_text("const x = 1;")
        (tmp_path / "server.go").write_text("package main")
        results = discover_files(tmp_path)
        languages = {lang for _, lang in results}
        assert "python" in languages
        assert "typescript" in languages
        assert "go" in languages
