# Security Notes

Generated: 2026-04-11 14:24:31

## Non-Blocking Findings (MEDIUM/LOW)
- [LOW] [category:A01] [assembly.py:122] fixable:yes — `snapshots_dir = repo_root / config.snapshots.dir` joins a user-supplied config string to the repo root without verifying the result stays inside the repository. A config entry such as `dir = "../../etc/cron.d"` would redirect atomic snapshot writes to an arbitrary filesystem location. Fix: after constructing `snapshots_dir`, assert `snapshots_dir.resolve().is_relative_to(repo_root.resolve())` and raise `SystemExit(2)` with a descriptive message if not.
