"""M14 unit tests for the shell language adapter — extended pattern shapes."""

from __future__ import annotations

from pathlib import Path

from tests.conftest import requires_shell_adapter


def _parse(tmp_path: Path, src: str) -> object:
    from sdi.parsing.shell import ShellAdapter

    script = tmp_path / "s.sh"
    script.write_text(src, encoding="utf-8")
    adapter = ShellAdapter(repo_root=tmp_path)
    return adapter.parse_file(script, src.encode())


def _by_cat(tmp_path: Path, src: str, category: str) -> list[dict]:
    return [i for i in _parse(tmp_path, src).pattern_instances if i["category"] == category]


# ---------------------------------------------------------------------------
# Extended error_handling shapes
# ---------------------------------------------------------------------------


@requires_shell_adapter
class TestShellErrorHandlingExtended:
    """Five new error_handling shapes beyond M13 baseline."""

    def test_trap_exit_signal(self, tmp_path: Path) -> None:
        assert len(_by_cat(tmp_path, "trap cleanup EXIT\n", "error_handling")) == 1

    def test_trap_int_signal(self, tmp_path: Path) -> None:
        assert len(_by_cat(tmp_path, "trap cleanup INT\n", "error_handling")) == 1

    def test_trap_quit_signal(self, tmp_path: Path) -> None:
        assert len(_by_cat(tmp_path, "trap cleanup QUIT\n", "error_handling")) == 1

    def test_trap_term_signal(self, tmp_path: Path) -> None:
        assert len(_by_cat(tmp_path, "trap cleanup TERM\n", "error_handling")) == 1

    def test_if_exit_fires_two_instances(self, tmp_path: Path) -> None:
        src = "if ! check; then exit 1; fi\n"
        instances = _by_cat(tmp_path, src, "error_handling")
        # if_statement shape + exit 1 cmd shape = 2 distinct instances
        assert len(instances) == 2

    def test_if_exit_two_distinct_hashes(self, tmp_path: Path) -> None:
        src = "if ! check; then exit 1; fi\n"
        instances = _by_cat(tmp_path, src, "error_handling")
        assert len({i["ast_hash"] for i in instances}) == 2

    def test_if_return_nonzero(self, tmp_path: Path) -> None:
        src = 'validate() { if [ -z "$1" ]; then return 1; fi; }\n'
        instances = _by_cat(tmp_path, src, "error_handling")
        assert len(instances) >= 1

    def test_test_command_sub_detected(self, tmp_path: Path) -> None:
        src = "if [ -z $(get_val) ]; then exit 1; fi\n"
        instances = _by_cat(tmp_path, src, "error_handling")
        assert len(instances) >= 1

    def test_double_bracket_sub_detected(self, tmp_path: Path) -> None:
        src = "[[ -n $(check_status) ]] && exit 1\n"
        instances = _by_cat(tmp_path, src, "error_handling")
        assert len(instances) >= 1

    def test_five_new_shapes_have_distinct_hashes(self, tmp_path: Path) -> None:
        src = "set -euo pipefail\ntrap cleanup ERR\ntrap done EXIT\nif ! foo; then exit 1; fi\nbar || false\n"
        instances = _by_cat(tmp_path, src, "error_handling")
        assert len({i["ast_hash"] for i in instances}) >= 4


# ---------------------------------------------------------------------------
# async_patterns
# ---------------------------------------------------------------------------


@requires_shell_adapter
class TestShellAsyncPatterns:
    """async_patterns detection for background, wait, pipelines, xargs."""

    def test_wait_command(self, tmp_path: Path) -> None:
        assert len(_by_cat(tmp_path, "wait\n", "async_patterns")) == 1

    def test_wait_with_args(self, tmp_path: Path) -> None:
        assert len(_by_cat(tmp_path, "wait $pid\n", "async_patterns")) >= 1

    def test_background_ampersand(self, tmp_path: Path) -> None:
        src = "run_job &\nwait\n"
        assert len(_by_cat(tmp_path, src, "async_patterns")) >= 1

    def test_wide_pipeline_three_stages(self, tmp_path: Path) -> None:
        src = "cat data.txt | grep foo | wc -l\n"
        assert len(_by_cat(tmp_path, src, "async_patterns")) == 1

    def test_two_stage_pipeline_not_async(self, tmp_path: Path) -> None:
        assert len(_by_cat(tmp_path, "cat f | grep foo\n", "async_patterns")) == 0

    def test_xargs_minus_p(self, tmp_path: Path) -> None:
        assert len(_by_cat(tmp_path, "xargs -P 4 shellcheck\n", "async_patterns")) == 1

    def test_xargs_max_procs_long(self, tmp_path: Path) -> None:
        assert len(_by_cat(tmp_path, "xargs --max-procs 8 process\n", "async_patterns")) == 1

    def test_xargs_without_p_not_async(self, tmp_path: Path) -> None:
        assert len(_by_cat(tmp_path, "xargs echo\n", "async_patterns")) == 0

    def test_background_and_wait_distinct_hashes(self, tmp_path: Path) -> None:
        src = "run_job &\nwait\n"
        instances = _by_cat(tmp_path, src, "async_patterns")
        assert len({i["ast_hash"] for i in instances}) == 2


# ---------------------------------------------------------------------------
# data_access allow-list
# ---------------------------------------------------------------------------


@requires_shell_adapter
class TestShellDataAccess:
    """data_access command allow-list detection."""

    def test_curl(self, tmp_path: Path) -> None:
        assert len(_by_cat(tmp_path, 'curl -sf "http://example.com"\n', "data_access")) == 1

    def test_psql(self, tmp_path: Path) -> None:
        assert len(_by_cat(tmp_path, "psql -U admin -d mydb\n", "data_access")) == 1

    def test_kubectl(self, tmp_path: Path) -> None:
        assert len(_by_cat(tmp_path, "kubectl get pods\n", "data_access")) == 1

    def test_jq(self, tmp_path: Path) -> None:
        assert len(_by_cat(tmp_path, "jq '.version' package.json\n", "data_access")) == 1

    def test_curl_psql_kubectl_jq_distinct_hashes(self, tmp_path: Path) -> None:
        src = 'curl -sf "http://x"\npsql -U a\nkubectl get pods\njq . f.json\n'
        instances = _by_cat(tmp_path, src, "data_access")
        assert len({i["ast_hash"] for i in instances}) == 4

    def test_unknown_command_not_data_access(self, tmp_path: Path) -> None:
        assert _by_cat(tmp_path, "my_custom_cmd arg\n", "data_access") == []


# ---------------------------------------------------------------------------
# logging >&2 redirect
# ---------------------------------------------------------------------------


@requires_shell_adapter
class TestShellLoggingRedirect:
    """>&2 redirect produces a shape distinct from bare echo."""

    def test_stderr_redirect_detected(self, tmp_path: Path) -> None:
        assert len(_by_cat(tmp_path, 'echo "error" >&2\n', "logging")) >= 1

    def test_stderr_redirect_distinct_hash_from_bare_echo(self, tmp_path: Path) -> None:
        bare = {i["ast_hash"] for i in _by_cat(tmp_path, 'echo "hello"\n', "logging")}
        redir = {i["ast_hash"] for i in _by_cat(tmp_path, 'echo "hello" >&2\n', "logging")}
        assert redir - bare, ">&2 redirect must produce at least one hash absent from bare echo"


# ---------------------------------------------------------------------------
# Reproducibility across shell-heavy fixture
# ---------------------------------------------------------------------------


@requires_shell_adapter
class TestShellHeavyReproducibility:
    """Parsing shell-heavy twice yields identical (category, ast_hash) multisets."""

    def test_shell_heavy_reproducibility(self) -> None:
        from sdi.parsing.shell import ShellAdapter

        fixture = Path(__file__).parent.parent / "fixtures" / "shell-heavy"
        adapter = ShellAdapter(repo_root=fixture.resolve())

        def collect() -> list[tuple[str, str]]:
            result = []
            for sh_file in sorted(fixture.rglob("*.sh")):
                data = sh_file.read_bytes()
                record = adapter.parse_file(sh_file.resolve(), data)
                for inst in record.pattern_instances:
                    result.append((inst["category"], inst["ast_hash"]))
            return sorted(result)

        assert collect() == collect()
