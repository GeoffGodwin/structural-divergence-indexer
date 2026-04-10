### Milestone 9: CLI Polish and Output Formatting

**Scope:** Polish all CLI commands with consistent Rich formatting, proper TTY detection, `--no-color`/`NO_COLOR` support, `--quiet`/`--verbose` behavior, and tab completion. Add sparkline trend visualization. Ensure all commands handle edge cases gracefully with helpful error messages. This milestone takes the functional commands from previous milestones and makes them production-quality.

**Deliverables:**
- Rich-formatted tables for `sdi show`, `sdi boundaries`, `sdi catalog`
- Colored diff output for `sdi diff` (red for removed, green for added)
- Sparkline trend visualization for `sdi trend` in text mode
- Consistent TTY detection: auto-switch to uncolored output when stdout is not a TTY
- `--no-color` flag and `NO_COLOR` env var support on all commands
- `--quiet` suppresses everything except errors and requested data
- `--verbose` adds full detail (complete pattern lists, all boundary members)
- Tab completion for bash, zsh, and fish
- Helpful error messages with suggestions (e.g., "Run 'sdi init' to generate a default configuration")
- `--debug` flag that sets log level to DEBUG and shows tracebacks on errors
- Consistent stderr logging format: `[LEVEL] message` with color when stderr is TTY

**Files to create or modify:**
- `src/sdi/cli/__init__.py` (refine global options, TTY detection)
- `src/sdi/cli/snapshot_cmd.py` (Rich progress bar)
- `src/sdi/cli/diff_cmd.py` (colored diff)
- `src/sdi/cli/trend_cmd.py` (sparklines)
- `src/sdi/cli/show_cmd.py` (Rich tables)
- `src/sdi/cli/boundaries_cmd.py` (Rich tree display)
- `src/sdi/cli/catalog_cmd.py` (Rich tables)
- `src/sdi/cli/check_cmd.py` (colored pass/fail)
- `tests/integration/test_cli_output.py`

**Acceptance criteria:**
- All text output uses Rich library for formatting
- `sdi show` renders a structured table with boundary summary and pattern overview
- `sdi diff` shows additions in green and removals in red (when colored)
- `sdi trend` displays sparkline characters for each dimension over time
- Piping any command to a file produces uncolored, clean text (TTY detection)
- `NO_COLOR=1` disables all color on all commands
- `--quiet` with any command shows only the essential output (data, not progress)
- `--verbose` with `sdi show` includes full pattern catalog details
- `eval "$(_SDI_COMPLETE=bash_source sdi)"` enables tab completion in bash
- Error messages suggest next steps: "No snapshots found. Run 'sdi snapshot' first."
- `SDI_LOG_LEVEL=DEBUG sdi snapshot` shows per-file parse timings and Leiden iteration count
- `--debug` flag sets `SDI_LOG_LEVEL=DEBUG` for the invocation

**Tests:**
- `tests/integration/test_cli_output.py`:
  - Each command produces non-empty stdout (or stderr for errors)
  - JSON output from each command is valid JSON (parseable by `json.loads`)
  - CSV output from `sdi trend` has correct column count
  - Piped output (simulated non-TTY) contains no ANSI escape codes
  - `--quiet` suppresses progress bar output
  - Error messages include actionable suggestions

**Watch For:**
- Rich's auto-detection of TTY may conflict with Click's. Use `rich.console.Console(force_terminal=...)` explicitly based on the `--no-color` / `NO_COLOR` state.
- Sparklines require Unicode support. Fall back to ASCII bar characters if the terminal does not support Unicode (rare, but document).
- Tab completion generation is shell-specific. Test all three shells (bash, zsh, fish) or at minimum bash and zsh.
- `--quiet` and `--verbose` are mutually exclusive. Handle both being specified with a clear error.

**Seeds Forward:**
- Polished CLI output is the user-facing quality bar for v1 release.
- Tab completion setup instructions go in `README.md`.
- The error message patterns established here (with suggestions) should be consistent across all future commands.

---
