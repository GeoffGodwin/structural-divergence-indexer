## Summary
M17 adds a `patterns.scope_exclude` config key accepting gitignore-style glob patterns that filter files from Stage 4 (pattern catalog) without affecting the dependency graph or community detection. The change touches config loading, catalog assembly, snapshot hashing, and CLI output. No authentication, cryptography, network communication, or command execution is involved. The surface area is small and well-bounded: patterns arrive from a user-controlled local TOML file, are validated as strings, and are passed to `pathspec.PathSpec.match_file()` — a pure string-matching operation that never touches the filesystem. No security issues were found.

## Findings
None

## Verdict
CLEAN
