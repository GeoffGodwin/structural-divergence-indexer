"""Tests for the shell language adapter (sdi.parsing.shell)."""

from __future__ import annotations

from pathlib import Path

from tests.conftest import requires_shell_adapter


@requires_shell_adapter
class TestShellImports:
    """Adapter correctly extracts static source/. includes."""

    def _parse(self, tmp_path: Path, src: str) -> object:
        from sdi.parsing.shell import ShellAdapter

        script = tmp_path / "script.sh"
        script.write_text(src, encoding="utf-8")
        adapter = ShellAdapter(repo_root=tmp_path)
        return adapter.parse_file(script, src.encode())

    def test_source_with_dot_slash(self, tmp_path: Path) -> None:
        record = self._parse(tmp_path, "source ./x.sh\n")
        assert "x.sh" in record.imports[0]

    def test_dot_with_dot_slash(self, tmp_path: Path) -> None:
        record = self._parse(tmp_path, ". ./x.sh\n")
        assert "x.sh" in record.imports[0]

    def test_source_resolves_to_repo_relative(self, tmp_path: Path) -> None:
        sub = tmp_path / "scripts"
        sub.mkdir()
        script = sub / "main.sh"
        script.write_text("source ./helper.sh\n", encoding="utf-8")
        from sdi.parsing.shell import ShellAdapter

        adapter = ShellAdapter(repo_root=tmp_path)
        record = adapter.parse_file(script, b"source ./helper.sh\n")
        assert record.imports == ["scripts/helper.sh"]

    def test_dynamic_var_rejected(self, tmp_path: Path) -> None:
        record = self._parse(tmp_path, 'source "$DIR/x.sh"\n')
        assert record.imports == []

    def test_dynamic_command_sub_rejected(self, tmp_path: Path) -> None:
        record = self._parse(tmp_path, "source $(which foo)\n")
        assert record.imports == []

    def test_dynamic_expansion_rejected(self, tmp_path: Path) -> None:
        record = self._parse(tmp_path, "source ${LIB}/x.sh\n")
        assert record.imports == []


@requires_shell_adapter
class TestShellSymbols:
    """Adapter extracts function names from both declaration forms."""

    def _symbols(self, tmp_path: Path, src: str) -> list[str]:
        from sdi.parsing.shell import ShellAdapter

        script = tmp_path / "s.sh"
        script.write_text(src, encoding="utf-8")
        adapter = ShellAdapter(repo_root=tmp_path)
        return adapter.parse_file(script, src.encode()).symbols

    def test_paren_form(self, tmp_path: Path) -> None:
        assert "foo" in self._symbols(tmp_path, "foo() { echo hi; }\n")

    def test_function_keyword_form(self, tmp_path: Path) -> None:
        assert "bar" in self._symbols(tmp_path, "function bar { echo hi; }\n")

    def test_both_forms_in_same_file(self, tmp_path: Path) -> None:
        src = "foo() { echo 1; }\nfunction bar { echo 2; }\n"
        syms = self._symbols(tmp_path, src)
        assert "foo" in syms
        assert "bar" in syms


@requires_shell_adapter
class TestShellErrorHandling:
    """Adapter detects error_handling pattern instances with distinct hashes."""

    def _instances(self, tmp_path: Path, src: str) -> list[dict]:
        from sdi.parsing.shell import ShellAdapter

        script = tmp_path / "s.sh"
        script.write_text(src, encoding="utf-8")
        adapter = ShellAdapter(repo_root=tmp_path)
        record = adapter.parse_file(script, src.encode())
        return [
            i for i in record.pattern_instances if i["category"] == "error_handling"
        ]

    def test_set_e(self, tmp_path: Path) -> None:
        assert len(self._instances(tmp_path, "set -e\n")) == 1

    def test_set_euo_pipefail(self, tmp_path: Path) -> None:
        assert len(self._instances(tmp_path, "set -euo pipefail\n")) == 1

    def test_trap_err(self, tmp_path: Path) -> None:
        assert len(self._instances(tmp_path, "trap cleanup ERR\n")) == 1

    def test_exit_nonzero(self, tmp_path: Path) -> None:
        assert len(self._instances(tmp_path, "exit 1\n")) == 1

    def test_distinct_hashes(self, tmp_path: Path) -> None:
        src = "set -e\ntrap cleanup ERR\nexit 1\n"
        instances = self._instances(tmp_path, src)
        assert len(instances) == 3
        hashes = {i["ast_hash"] for i in instances}
        assert len(hashes) == 3, "set -e, trap ERR, exit 1 must have distinct hashes"

    def test_exit_zero_not_error_handling(self, tmp_path: Path) -> None:
        assert self._instances(tmp_path, "exit 0\n") == []


@requires_shell_adapter
class TestShellLogging:
    """Adapter detects logging pattern instances with distinct hashes."""

    def _logging(self, tmp_path: Path, src: str) -> list[dict]:
        from sdi.parsing.shell import ShellAdapter

        script = tmp_path / "s.sh"
        script.write_text(src, encoding="utf-8")
        adapter = ShellAdapter(repo_root=tmp_path)
        record = adapter.parse_file(script, src.encode())
        return [i for i in record.pattern_instances if i["category"] == "logging"]

    def test_echo(self, tmp_path: Path) -> None:
        assert len(self._logging(tmp_path, 'echo "hello"\n')) == 1

    def test_printf(self, tmp_path: Path) -> None:
        assert len(self._logging(tmp_path, 'printf "%s\\n" "msg"\n')) == 1

    def test_logger(self, tmp_path: Path) -> None:
        assert len(self._logging(tmp_path, 'logger "error"\n')) == 1

    def test_distinct_hashes(self, tmp_path: Path) -> None:
        src = 'echo "a"\nprintf "%s" "b"\nlogger "c"\n'
        instances = self._logging(tmp_path, src)
        assert len(instances) == 3
        hashes = {i["ast_hash"] for i in instances}
        assert len(hashes) == 3, "echo, printf, logger must have distinct hashes"


@requires_shell_adapter
class TestShellListBail:
    """Adapter detects error_handling for ||/&& list nodes whose right side bails.

    When the bail command is exit/return, two instances fire: one from the
    list node (_check_list_node) and one from the standalone command detection
    (_is_nonzero_exit_or_return). Using ``false`` as the bail command isolates
    the list-node path because ``false`` alone never triggers the command handler.
    """

    def _instances(self, tmp_path: Path, src: str) -> list[dict]:
        from sdi.parsing.shell import ShellAdapter

        script = tmp_path / "s.sh"
        script.write_text(src, encoding="utf-8")
        adapter = ShellAdapter(repo_root=tmp_path)
        record = adapter.parse_file(script, src.encode())
        return [
            i for i in record.pattern_instances if i["category"] == "error_handling"
        ]

    def test_or_list_false_isolated(self, tmp_path: Path) -> None:
        """cmd || false isolates the list-bail path: exactly one instance, no double-count."""
        instances = self._instances(tmp_path, "check_health || false\n")
        assert len(instances) == 1

    def test_or_list_exit_produces_two_instances(self, tmp_path: Path) -> None:
        """cmd || exit 1 fires both the list-bail path and the standalone exit-nonzero path."""
        instances = self._instances(tmp_path, 'do_deploy "$env" || exit 1\n')
        assert len(instances) == 2

    def test_or_list_return_produces_two_instances(self, tmp_path: Path) -> None:
        """cmd || return 1 fires both the list-bail path and the standalone return-nonzero path."""
        instances = self._instances(tmp_path, "validate_args || return 1\n")
        assert len(instances) == 2

    def test_and_list_exit_produces_two_instances(self, tmp_path: Path) -> None:
        """cmd && exit 1 fires both the list-bail path and the standalone exit-nonzero path."""
        instances = self._instances(tmp_path, "is_error && exit 1\n")
        assert len(instances) == 2

    def test_or_list_non_bail_command_not_error_handling(self, tmp_path: Path) -> None:
        """cmd || echo 'fail' must NOT produce an error_handling instance."""
        instances = self._instances(tmp_path, 'run_step || echo "failed"\n')
        assert instances == []

    def test_or_list_false_has_ast_hash(self, tmp_path: Path) -> None:
        """The list-bail instance (isolated via false) must carry a non-empty ast_hash."""
        instances = self._instances(tmp_path, "do_thing || false\n")
        assert len(instances) == 1
        assert instances[0]["ast_hash"]

    def test_or_list_false_has_location(self, tmp_path: Path) -> None:
        """The list-bail instance (isolated via false) must carry a location with a line key."""
        instances = self._instances(tmp_path, "do_thing || false\n")
        assert len(instances) == 1
        assert "line" in instances[0]["location"]


@requires_shell_adapter
class TestShellEdgeCases:
    """Edge cases: empty file, broken script, hash stability."""

    def test_empty_file(self, tmp_path: Path) -> None:
        from sdi.parsing.shell import ShellAdapter

        script = tmp_path / "empty.sh"
        script.write_bytes(b"")
        adapter = ShellAdapter(repo_root=tmp_path)
        record = adapter.parse_file(script, b"")
        assert record.imports == []
        assert record.symbols == []
        assert record.pattern_instances == []

    def test_broken_script_returns_none_via_safe(self, tmp_path: Path) -> None:
        from sdi.parsing.shell import ShellAdapter

        script = tmp_path / "broken.sh"
        broken = b"set -e\nif [[\n"
        script.write_bytes(broken)
        adapter = ShellAdapter(repo_root=tmp_path)
        # parse_file_safe must not raise; broken scripts return None or a record
        result = adapter.parse_file_safe(script, broken, repo_root=tmp_path)
        # tree-sitter-bash is error-tolerant; it returns a partial tree.
        # The important constraint is: no exception escapes.
        assert result is None or hasattr(result, "file_path")

    def test_hash_stability(self, tmp_path: Path) -> None:
        from sdi.parsing.shell import ShellAdapter

        src = b"set -euo pipefail\ntrap cleanup ERR\nexit 1\n"
        script = tmp_path / "stable.sh"
        script.write_bytes(src)
        adapter = ShellAdapter(repo_root=tmp_path)
        record1 = adapter.parse_file(script, src)
        record2 = adapter.parse_file(script, src)
        hashes1 = [i["ast_hash"] for i in record1.pattern_instances]
        hashes2 = [i["ast_hash"] for i in record2.pattern_instances]
        assert hashes1 == hashes2


@requires_shell_adapter
class TestShellErrorHandlingExtended:
    """M14: additional error_handling shapes beyond M13 baseline."""

    def _instances(self, tmp_path: Path, src: str) -> list[dict]:
        from sdi.parsing.shell import ShellAdapter

        script = tmp_path / "s.sh"
        script.write_text(src, encoding="utf-8")
        adapter = ShellAdapter(repo_root=tmp_path)
        record = adapter.parse_file(script, src.encode())
        return [i for i in record.pattern_instances if i["category"] == "error_handling"]

    def test_trap_exit_signal(self, tmp_path: Path) -> None:
        assert len(self._instances(tmp_path, "trap cleanup EXIT\n")) == 1

    def test_trap_int_signal(self, tmp_path: Path) -> None:
        assert len(self._instances(tmp_path, "trap cleanup INT\n")) == 1

    def test_trap_quit_signal(self, tmp_path: Path) -> None:
        assert len(self._instances(tmp_path, "trap cleanup QUIT\n")) == 1

    def test_trap_multiple_signals_one_instance(self, tmp_path: Path) -> None:
        # trap cleanup ERR EXIT — one trap command → one instance
        assert len(self._instances(tmp_path, "trap cleanup ERR EXIT\n")) == 1

    def test_if_exit_nonzero(self, tmp_path: Path) -> None:
        src = "if ! check; then exit 1; fi\n"
        instances = self._instances(tmp_path, src)
        # if_statement fires one instance; exit 1 command fires another
        assert len(instances) == 2

    def test_if_statement_distinct_hash_from_exit_cmd(self, tmp_path: Path) -> None:
        src = "if ! check; then exit 1; fi\n"
        instances = self._instances(tmp_path, src)
        assert len({i["ast_hash"] for i in instances}) == 2

    def test_test_command_with_command_substitution(self, tmp_path: Path) -> None:
        src = "if [ -z $(get_val) ]; then exit 1; fi\n"
        instances = self._instances(tmp_path, src)
        categories = [i["ast_hash"] for i in instances]
        assert len(categories) >= 1  # test_command + if_statement + exit 1

    def test_double_bracket_with_command_substitution(self, tmp_path: Path) -> None:
        src = "[[ -n $(check_status) ]] && exit 1\n"
        instances = self._instances(tmp_path, src)
        assert any(True for _ in instances)  # at minimum one instance

    def test_five_new_shapes_distinct_from_m13(self, tmp_path: Path) -> None:
        src = (
            "set -euo pipefail\n"
            "trap cleanup ERR\n"
            "trap done EXIT\n"
            "if ! foo; then exit 1; fi\n"
            "bar || false\n"
        )
        instances = self._instances(tmp_path, src)
        hashes = {i["ast_hash"] for i in instances}
        # set-euo, trap-ERR, trap-EXIT (same hash as trap-ERR if args differ),
        # if-exit (if_statement shape), exit 1 cmd, list-bail false — at least 4 distinct
        assert len(hashes) >= 4


# ---------------------------------------------------------------------------
# M14: async_patterns
# ---------------------------------------------------------------------------


@requires_shell_adapter
class TestShellAsyncPatterns:
    """M14: async_patterns detection — background, wait, pipelines, xargs."""

    def _async(self, tmp_path: Path, src: str) -> list[dict]:
        from sdi.parsing.shell import ShellAdapter

        script = tmp_path / "s.sh"
        script.write_text(src, encoding="utf-8")
        adapter = ShellAdapter(repo_root=tmp_path)
        record = adapter.parse_file(script, src.encode())
        return [i for i in record.pattern_instances if i["category"] == "async_patterns"]

    def test_background_ampersand(self, tmp_path: Path) -> None:
        src = "run_job &\nwait\n"
        instances = self._async(tmp_path, src)
        cats = [i["category"] for i in instances]
        assert cats.count("async_patterns") >= 1

    def test_wait_command(self, tmp_path: Path) -> None:
        assert len(self._async(tmp_path, "wait\n")) == 1

    def test_wait_with_args(self, tmp_path: Path) -> None:
        assert len(self._async(tmp_path, "wait $pid\n")) >= 1

    def test_wide_pipeline_three_stages(self, tmp_path: Path) -> None:
        src = "cat data.txt | grep foo | wc -l\n"
        assert len(self._async(tmp_path, src)) == 1

    def test_wide_pipeline_four_stages(self, tmp_path: Path) -> None:
        src = "cat f | sort | uniq | wc -l\n"
        assert len(self._async(tmp_path, src)) == 1

    def test_two_stage_pipeline_not_async(self, tmp_path: Path) -> None:
        src = "cat f | grep foo\n"
        assert len(self._async(tmp_path, src)) == 0

    def test_xargs_minus_p(self, tmp_path: Path) -> None:
        assert len(self._async(tmp_path, "find . -name '*.sh' | xargs -P 4 shellcheck\n")) == 1

    def test_xargs_max_procs_long(self, tmp_path: Path) -> None:
        assert len(self._async(tmp_path, "xargs --max-procs 8 process\n")) == 1

    def test_xargs_without_p_not_async(self, tmp_path: Path) -> None:
        assert len(self._async(tmp_path, "xargs echo\n")) == 0

    def test_background_and_wait_distinct_hashes(self, tmp_path: Path) -> None:
        src = "run_job &\nwait\n"
        instances = self._async(tmp_path, src)
        hashes = {i["ast_hash"] for i in instances}
        assert len(hashes) == 2


# ---------------------------------------------------------------------------
# M14: data_access allow-list
# ---------------------------------------------------------------------------


@requires_shell_adapter
class TestShellDataAccess:
    """M14: data_access detection for command allow-list."""

    def _data(self, tmp_path: Path, src: str) -> list[dict]:
        from sdi.parsing.shell import ShellAdapter

        script = tmp_path / "s.sh"
        script.write_text(src, encoding="utf-8")
        adapter = ShellAdapter(repo_root=tmp_path)
        record = adapter.parse_file(script, src.encode())
        return [i for i in record.pattern_instances if i["category"] == "data_access"]

    def test_curl(self, tmp_path: Path) -> None:
        assert len(self._data(tmp_path, 'curl -sf "http://example.com"\n')) == 1

    def test_psql(self, tmp_path: Path) -> None:
        assert len(self._data(tmp_path, "psql -U admin -d mydb -c 'SELECT 1'\n")) == 1

    def test_kubectl(self, tmp_path: Path) -> None:
        assert len(self._data(tmp_path, "kubectl get pods\n")) == 1

    def test_jq(self, tmp_path: Path) -> None:
        assert len(self._data(tmp_path, "jq '.version' package.json\n")) == 1

    def test_aws(self, tmp_path: Path) -> None:
        assert len(self._data(tmp_path, "aws s3 cp src s3://bucket/\n")) == 1

    def test_curl_psql_kubectl_distinct_hashes(self, tmp_path: Path) -> None:
        src = 'curl -sf "http://example.com"\npsql -U a -d b\nkubectl get pods\n'
        from sdi.parsing.shell import ShellAdapter

        script = tmp_path / "s.sh"
        script.write_text(src, encoding="utf-8")
        adapter = ShellAdapter(repo_root=tmp_path)
        record = adapter.parse_file(script, src.encode())
        data_hashes = {i["ast_hash"] for i in record.pattern_instances if i["category"] == "data_access"}
        assert len(data_hashes) == 3, "curl, psql, kubectl must have distinct hashes"

    def test_unknown_command_not_data_access(self, tmp_path: Path) -> None:
        assert self._data(tmp_path, "my_custom_cmd arg\n") == []


# ---------------------------------------------------------------------------
# M14: logging >&2 redirect
# ---------------------------------------------------------------------------


@requires_shell_adapter
class TestShellLoggingRedirect:
    """M14: logging >&2 redirect produces a shape distinct from bare echo."""

    def _logging(self, tmp_path: Path, src: str) -> list[dict]:
        from sdi.parsing.shell import ShellAdapter

        script = tmp_path / "s.sh"
        script.write_text(src, encoding="utf-8")
        adapter = ShellAdapter(repo_root=tmp_path)
        record = adapter.parse_file(script, src.encode())
        return [i for i in record.pattern_instances if i["category"] == "logging"]

    def test_stderr_redirect_detected(self, tmp_path: Path) -> None:
        instances = self._logging(tmp_path, 'echo "error" >&2\n')
        assert len(instances) >= 1

    def test_stderr_redirect_distinct_from_bare_echo(self, tmp_path: Path) -> None:
        bare = self._logging(tmp_path, 'echo "hello"\n')
        redirected = self._logging(tmp_path, 'echo "hello" >&2\n')
        bare_hashes = {i["ast_hash"] for i in bare}
        redirected_hashes = {i["ast_hash"] for i in redirected}
        # The redirected form (redirected_statement) must produce at least one
        # hash not present in the bare echo set
        assert redirected_hashes - bare_hashes, (
            ">&2 redirect must produce a distinct hash from bare echo"
        )


# ---------------------------------------------------------------------------
# M14: Reproducibility across shell-heavy fixture
# ---------------------------------------------------------------------------


@requires_shell_adapter
class TestShellHeavyReproducibility:
    """Parsing shell-heavy twice yields identical (category, ast_hash) multisets."""

    def test_shell_heavy_reproducibility(self) -> None:
        from pathlib import Path

        from sdi.parsing.shell import ShellAdapter

        fixture = Path(__file__).parent.parent / "fixtures" / "shell-heavy"
        adapter = ShellAdapter(repo_root=fixture.resolve())

        def collect(fixture_dir: Path) -> list[tuple[str, str]]:
            result = []
            for sh_file in sorted(fixture_dir.rglob("*.sh")):
                data = sh_file.read_bytes()
                record = adapter.parse_file(sh_file.resolve(), data)
                for inst in record.pattern_instances:
                    result.append((inst["category"], inst["ast_hash"]))
            return sorted(result)

        run1 = collect(fixture)
        run2 = collect(fixture)
        assert run1 == run2, "Parsing shell-heavy twice must yield identical results"
