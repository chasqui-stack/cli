"""Chasqui CLI — `uvx chasqui new <name>` / `chasqui generate module <name>` /
`chasqui add channel <name>`."""

from pathlib import Path
from typing import Optional

import typer

from chasqui import __version__, add_channel, module_gen, preflight, scaffold, stack, wizard

app = typer.Typer(
    name="chasqui",
    help="The Chasqui stack generator — WhatsApp AI agents, omakase.",
    no_args_is_help=True,
)
generate_app = typer.Typer(help="Code generators (à la `rails generate`).", no_args_is_help=True)
app.add_typer(generate_app, name="generate")
add_app = typer.Typer(
    help="Add pieces to an existing project (run from the project root).",
    no_args_is_help=True,
)
app.add_typer(add_app, name="add")


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"chasqui {__version__} (stack {stack.STACK_TAG})")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        False, "--version", callback=_version_callback, is_eager=True,
        help="Show the CLI and pinned stack versions.",
    ),
) -> None:
    pass


@app.command()
def new(
    name: str = typer.Argument(..., help="Project name (lowercase, dashes)"),
    defaults: bool = typer.Option(
        False, "--defaults", help="Skip the wizard — placeholder config, CI-friendly."
    ),
    skip_provision: bool = typer.Option(
        False, "--skip-provision", help="Write files only; no uv/npm/createdb/migrate."
    ),
    ref: str = typer.Option(
        stack.STACK_TAG, "--ref", help="Stack tag/branch to scaffold (default: pinned tag)."
    ),
    channels: Optional[str] = typer.Option(
        None, "--channels",
        help="Comma-separated channels to install (whatsapp,telegram,web). "
        "Overrides the wizard pick; handy with --defaults.",
    ),
    source: Optional[Path] = typer.Option(
        None, "--source", help="Local stack checkout to copy instead of downloading (dev)."
    ),
) -> None:
    """Scaffold a configured Chasqui project: wizard → .envs → provision."""
    try:
        slug = scaffold.validate_name(name)

        typer.echo("🔎 Preflight:")
        for check in preflight.run_checks():
            mark = "✅" if check.found else "⚠️ "
            hint = "" if check.found else f"  ({check.hint})"
            typer.echo(f"  {mark} {check.name}: {check.detail}{hint}")
        typer.echo("")

        answers = (
            wizard.default_answers(slug) if defaults else wizard.run_wizard(slug)
        )
        if channels:
            picked = [c.strip() for c in channels.split(",") if c.strip()]
            unknown = [c for c in picked if c not in stack.CHANNEL_SERVICES]
            if unknown:
                raise scaffold.ScaffoldError(
                    f"unknown channel(s): {', '.join(unknown)} "
                    f"(available: {', '.join(stack.CHANNEL_SERVICES)})"
                )
            if picked:
                answers.channels = picked
        scaffold.run_new(
            answers,
            target_parent=Path.cwd(),
            ref=ref,
            source=source,
            skip_provision=skip_provision,
            echo=typer.echo,
        )
        typer.echo("")
        typer.echo("Teach your coding agent to extend this stack:")
        typer.echo("  npx skills add chasqui-stack/skills --skill '*'")
    except (scaffold.ScaffoldError, Exception) as exc:
        if isinstance(exc, typer.Exit):
            raise
        typer.secho(f"error: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc


@add_app.command("channel")
def add_channel_cmd(
    name: str = typer.Argument(..., help="Channel to add: whatsapp | telegram | web"),
    defaults: bool = typer.Option(
        False, "--defaults", help="Skip the questions — placeholder config, CI-friendly."
    ),
    skip_provision: bool = typer.Option(
        False, "--skip-provision", help="Write files only; no uv sync / npm install."
    ),
    ref: Optional[str] = typer.Option(
        None, "--ref",
        help="Stack tag/branch to fetch (default: the tag the project was "
        "scaffolded from, per its README).",
    ),
    source: Optional[Path] = typer.Option(
        None, "--source", help="Local stack checkout to copy instead of downloading (dev)."
    ),
) -> None:
    """Retrofit a channel gateway into an existing Chasqui project."""
    try:
        if name not in stack.CHANNEL_SERVICES:
            raise add_channel.AddChannelError(
                f"unknown channel: {name} "
                f"(available: {', '.join(stack.CHANNEL_SERVICES)})"
            )
        project_dir = add_channel.detect_project(Path.cwd())

        resolved_ref = ref or add_channel.detect_stack_ref(project_dir)
        if resolved_ref is None:
            resolved_ref = stack.STACK_TAG
            typer.echo(
                f"⚠️  Could not detect the project's stack tag — using the "
                f"CLI's pinned {resolved_ref} (override with --ref)."
            )

        answers = add_channel.base_answers(project_dir, name)
        if not defaults:
            wizard.run_channel_wizard(name, answers)

        add_channel.run_add(
            name,
            answers,
            project_dir=project_dir,
            ref=resolved_ref,
            source=source,
            skip_provision=skip_provision,
            echo=typer.echo,
        )
    except Exception as exc:
        if isinstance(exc, typer.Exit):
            raise
        typer.secho(f"error: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc


@generate_app.command("module")
def gen_module(
    name: str = typer.Argument(..., help="Module name (snake_case)"),
    with_models: bool = typer.Option(
        False, "--with-models", help="Add a SQLModel table registered via register_models()."
    ),
    with_admin: bool = typer.Option(
        False, "--with-admin", help="Add admin routes under /admin/modules/<name>."
    ),
) -> None:
    """Scaffold a Tool Module (ARCHITECTURE §8) inside a Chasqui project."""
    try:
        created = module_gen.generate(
            name, cwd=Path.cwd(), with_models=with_models, with_admin=with_admin
        )
    except module_gen.ModuleGenError as exc:
        typer.secho(f"error: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc

    for path in created:
        typer.echo(f"  create  {path}")
    typer.echo("\nNext steps:")
    if with_models:
        typer.echo('  cd core && make makemigrations m="add ' + name + ' tables" && make migrate')
    typer.echo("  enable the tool in the admin panel (/tools) and write the real logic")


if __name__ == "__main__":
    app()
