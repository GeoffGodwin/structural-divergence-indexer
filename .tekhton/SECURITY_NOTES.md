# Security Notes

Generated: 2026-04-26 09:03:53

## Non-Blocking Findings (MEDIUM/LOW)
- [LOW] [category:A05] [tests/integration/test_shell_pipeline.py:57] fixable:yes — `dest.chmod(dest.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)` grants group- and world-execute to fixture files in tmp_path even when the source only had user-execute. Test temp directories are ephemeral and low-risk, but the pattern silently widens permissions beyond the source intent. Fix: set only `S_IXUSR`, or mirror exact source permission bits with `shutil.copymode`.
