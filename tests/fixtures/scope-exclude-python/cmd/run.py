"""Command runner with one variant error-handling pattern (Shape 2).

try/except with exception alias ('as e') and a raise in the handler —
structurally distinct from Shape 1 because of the as-clause and raise_statement.
"""


def run_command(cmd):
    """Execute a command, re-raising as RuntimeError on OS failure."""
    try:
        result = execute(cmd)
    except OSError as e:
        raise RuntimeError("Command failed") from e
    return result


def invoke(action):
    """Invoke action, re-raising on IO failure."""
    try:
        response = action()
    except OSError as e:
        raise RuntimeError("Action failed") from e
    return response
