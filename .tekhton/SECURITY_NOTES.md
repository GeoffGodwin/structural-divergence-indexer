# Security Notes

Generated: 2026-04-24 13:07:51

## Non-Blocking Findings (MEDIUM/LOW)
- [LOW] [category:A05] [boundaries_cmd.py:166] fixable:yes — `subprocess.run([editor, str(spec_path)], check=False)` passes `os.environ.get("EDITOR")` as a single token in the argument list. Users who set `EDITOR="code --wait"` or any other multi-word editor command (common for VS Code, Sublime, etc.) will receive a `FileNotFoundError` because the entire string is treated as the executable name rather than as a command with arguments. Shell injection is not possible (shell=False, list form), but the invocation is broken for the most common multi-word EDITOR values. Fix: `import shlex` and replace with `subprocess.run([*shlex.split(editor), str(spec_path)], check=False)`.
