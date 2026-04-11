## Summary

M07 adds snapshot delta computation (`delta.py`), trend extraction (`trend.py`), snapshot assembly (`assembly.py`), and extensions to the `Snapshot` model (`model.py`). The change set is pure local computation: no network calls, no authentication, no SQL, no subprocess invocations, and no secrets. Deserialization uses `json.loads()` and explicit dataclass constructors throughout — no `pickle`, `eval`, or `exec`. The one noteworthy surface is a path construction in `assembly.py` where `config.snapshots.dir` (a user-controlled config string) is joined to `repo_root` without a bounds check, enabling a write-outside-repository scenario via a crafted config file. Risk is low given the local CLI threat model (the user already controls the filesystem), but it is fixable.

## Findings

- [LOW] [category:A01] [assembly.py:122] fixable:yes — `snapshots_dir = repo_root / config.snapshots.dir` joins a user-supplied config string to the repo root without verifying the result stays inside the repository. A config entry such as `dir = "../../etc/cron.d"` would redirect atomic snapshot writes to an arbitrary filesystem location. Fix: after constructing `snapshots_dir`, assert `snapshots_dir.resolve().is_relative_to(repo_root.resolve())` and raise `SystemExit(2)` with a descriptive message if not.

## Verdict
FINDINGS_PRESENT
