"""Main CLI entry point for Selecta."""

import click

from selecta.cli.env import env
from selecta.cli.spotify import spotify


@click.group()
@click.version_option()
def cli():
    """Selecta - A unified music library manager for Rekordbox, Spotify, and Discogs."""
    pass


# Add subcommands
cli.add_command(env)
cli.add_command(spotify)


@cli.command(help="Print shell completion instructions")
@click.argument(
    "shell",
    type=click.Choice(["bash", "zsh", "fish"]),
    default="bash",
    required=False,
)
def completion(shell: str) -> None:
    """Print shell completion setup instructions for the specified shell.

    Args:
        shell: The shell type (bash, zsh, or fish)
    """
    shell_instructions = {
        "bash": """
# Add this to ~/.bashrc:
eval "$(_SELECTA_COMPLETE=bash_source selecta)"

# Or, to save the script and source it separately:
_SELECTA_COMPLETE=bash_source selecta > ~/.selecta-complete.bash
echo '. ~/.selecta-complete.bash' >> ~/.bashrc
""",
        "zsh": """
# Add this to ~/.zshrc:
eval "$(_SELECTA_COMPLETE=zsh_source selecta)"

# Or, to save the script and source it separately:
_SELECTA_COMPLETE=zsh_source selecta > ~/.selecta-complete.zsh
echo '. ~/.selecta-complete.zsh' >> ~/.zshrc
""",
        "fish": """
# Add this to ~/.config/fish/config.fish:
eval (env _SELECTA_COMPLETE=fish_source selecta)

# Or, to save the script and source it separately:
_SELECTA_COMPLETE=fish_source selecta > ~/.config/fish/selecta-complete.fish
echo 'source ~/.config/fish/selecta-complete.fish' >> ~/.config/fish/config.fish
""",
    }

    click.echo(f"Shell completion setup for {shell}:\n")
    click.echo(shell_instructions[shell])
    click.echo("After adding the above, restart your shell or source the configuration file.")


if __name__ == "__main__":
    cli()
