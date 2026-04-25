# Human Notes
<!-- notes-format: v2 -->
<!-- IDs are auto-managed by Tekhton. Do not remove note: comments. -->

Add your observations below as unchecked items. The pipeline will inject
unchecked items into the next coder run and archive them when done.

Use `- [ ]` for new notes. Use `- [x]` to mark items you want to defer/skip.

Prefix each note with a priority tag so the pipeline can scope runs correctly:
- `[BUG]` — something is broken, needs fixing before new features
- `[FEAT]` — new mechanic or system, architectural work
- `[POLISH]` — visual/UX improvement, no logic changes

## Features
- [ ] [FEAT] Configurable snapshot storage modes — make `[snapshots] storage_mode` a `.sdi/config.toml` key with three values to control what lands in version control. Motivation: snapshot JSONs grow with codebase size (observed ~5–7KB on bifl-tracker @ 23 files, can reach ~500KB on large monorepos). At 100 merges, naïve full-storage mode adds ~50MB working-tree weight, though git pack-file compression of JSON (~85–90%) cuts the actual repo cost to ~5–7MB. Still worth fixing for big repos, and giving teams an opt-in path is the right shape — defaulting `full` keeps backward compatibility for everyone already running SDI. Proposed values: **`full`** (current behavior, all snapshots committed to `.sdi/snapshots/`); **`slim`** (only a `.sdi/trend.jsonl` ledger is committed, with one row per snapshot containing `{timestamp, commit_sha, snapshot_version, divergence: {...4 absolutes + 4 deltas...}, file_count, language_breakdown}`; `.sdi/snapshots/` is added to `.gitignore` and full snapshots stay local for `sdi diff` / `sdi catalog` against recent history); **`tiered`** (slim ledger always committed, plus full snapshots committed only at configured intervals — e.g. every Nth capture or whenever the working commit has a git tag). Implementation sketch: (1) add `storage_mode` (default `"full"`), `trend_ledger` (default `".sdi/trend.jsonl"`), and `tiered_full_every` (default `10`) to `[snapshots]` in `config.py`; (2) at the end of `sdi snapshot`'s storage step, always append the slim row to `trend_ledger` (cheap, harmless even in `full` mode for forward compatibility), then conditionally retain the full file based on mode; (3) update `sdi init` to add `.sdi/snapshots/` to `.gitignore` only when `storage_mode != "full"`; (4) rewire `sdi trend` to read from `trend_ledger` first and fall back to scanning `.sdi/snapshots/*.json` if the ledger is absent or older than the snapshot dir (covers `full`-mode users who never had a ledger written); (5) make `sdi catalog <ref>` and `sdi diff` surface a clear error message when the requested snapshot exists in the ledger but its full JSON has been pruned ("snapshot for <commit> stored as slim entry only — re-run `sdi snapshot --commit <ref>` locally to materialize the catalog"); (6) document the `--commit` rehydration workflow as the standard remediation path. Tradeoff: `slim`/`tiered` users lose the ability to retroactively run `sdi catalog <old_commit>` directly from history without re-snapshotting, which IS useful for diagnosing structural drift after the fact — that's the value being traded for repo size, hence configurable rather than forced. Open question worth surfacing during implementation: should the slim ledger entry include `graph_metrics` summary (node/edge counts, hub_concentration, density)? Adds ~50 bytes per row, lets `sdi check` work fully against ledger-only history.

## Bugs

## Polish
