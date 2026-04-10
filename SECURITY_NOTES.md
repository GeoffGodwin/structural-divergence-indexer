# Security Notes

Generated: 2026-04-10 18:09:09

## Non-Blocking Findings (MEDIUM/LOW)
- [LOW] [category:A05] [src/sdi/parsing/discovery.py:50] fixable:yes — Incomplete fix: the empty-spec branch on line 50 still passes `"gitwildmatch"` to `pathspec.PathSpec.from_lines()` while line 52 was correctly updated to `"gitignore"`. This is the deprecated factory name and will emit deprecation warnings when no `.gitignore` file is present. Not a security issue but a correctness gap in the stated fix. Change line 50 to `pathspec.PathSpec.from_lines("gitignore", [])`.
