"""sdi completion — print shell completion setup instructions."""

from __future__ import annotations

import click

_INSTRUCTIONS: dict[str, tuple[str, str]] = {
    "bash": (
        'eval "$(_SDI_COMPLETE=bash_source sdi)"',
        'Add to ~/.bashrc, or run: eval "$(sdi completion bash)"',
    ),
    "zsh": (
        'eval "$(_SDI_COMPLETE=zsh_source sdi)"',
        'Add to ~/.zshrc, or run: eval "$(sdi completion zsh)"',
    ),
    "fish": (
        "_SDI_COMPLETE=fish_source sdi | source",
        "Add to ~/.config/fish/completions/sdi.fish, or pipe: sdi completion fish | source",
    ),
}


@click.command("completion")
@click.argument("shell", type=click.Choice(["bash", "zsh", "fish"]))
def completion_cmd(shell: str) -> None:
    """Print the shell completion setup command for bash, zsh, or fish.

    The output is the line to evaluate (or source) in your shell profile
    to enable tab completion for all sdi subcommands and flags.

    Args:
        shell: Target shell — one of bash, zsh, fish.

    Examples:

        eval "$(sdi completion bash)"    # bash: add to ~/.bashrc

        eval "$(sdi completion zsh)"     # zsh: add to ~/.zshrc

        sdi completion fish | source     # fish: pipe to source
    """
    eval_line, hint = _INSTRUCTIONS[shell]
    click.echo(eval_line)
    click.echo(f"# {hint}", err=True)
