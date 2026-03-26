"""Generic CLI for nskit recipes."""

import json
import os
from pathlib import Path
from typing import Annotated, Optional, Union

import questionary
import typer
import yaml
from rich import print as rich_print
from rich.console import Console
from rich.table import Table

from nskit.client import DiscoveryClient, RecipeClient, UpdateClient
from nskit.client.backends import create_backend_from_config
from nskit.client.backends.base import RecipeBackend
from nskit.client.context import ContextProvider
from nskit.client.derived_evaluator import DerivedFieldEvaluator
from nskit.client.engines import LocalEngine
from nskit.client.env_resolver import EnvVarResolver
from nskit.client.field_parser import FieldParser
from nskit.client.models import RecipeInfo
from nskit.client.utils import get_required_fields_as_dict
from nskit.common.models.diff import DiffMode
from nskit.mixer.components.recipe import Recipe

TREE_IGNORE = {".git", "__pycache__", ".venv", "node_modules"}


def _commit_and_maybe_push(
    project_path: Path,
    repo_name: str,
    description: str,
    create_repo: bool,
    vcs_client,
    console: Console,
) -> None:
    """Commit generated files and optionally create a remote repo and push.

    Args:
        project_path: Path to the generated project.
        repo_name: Repository name.
        description: Repository description.
        create_repo: Whether the user opted to create a remote repo.
        vcs_client: Detected VCS repo client (or ``None``).
        console: Rich console for output.
    """
    import subprocess  # nosec B404

    if not (project_path / ".git").is_dir():
        return

    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "nskit",
        "GIT_AUTHOR_EMAIL": "nskit@noreply",
        "GIT_COMMITTER_NAME": "nskit",
        "GIT_COMMITTER_EMAIL": "nskit@noreply",
    }
    subprocess.run(  # nosec B603, B607
        ["git", "add", "."],
        cwd=project_path,
        capture_output=True,
        check=True,
    )
    subprocess.run(  # nosec B603, B607
        ["git", "commit", "-m", "Initial commit from recipe", "--no-verify"],
        cwd=project_path,
        capture_output=True,
        check=True,
        env=env,
    )
    console.print("[green]✓ Committed initial files[/green]")

    if create_repo and vcs_client is not None:
        try:
            from nskit.recipes.repository_client import RepositoryClient

            rc = RepositoryClient(vcs_client=vcs_client)
            info = rc.create_and_push(repo_name, project_path, description=description)
            console.print(f"[green]✓ Created and pushed to {info.url}[/green]")
        except Exception as e:
            console.print(f"[yellow]⚠ Failed to create repository: {e}[/yellow]")


def _print_tree(directory: Path, console: Console, prefix: str = "") -> None:
    """Print a directory tree to the console."""
    from rich.markup import escape

    entries = sorted(directory.iterdir(), key=lambda p: (p.is_file(), p.name))
    entries = [e for e in entries if e.name not in TREE_IGNORE]
    for i, entry in enumerate(entries):
        is_last = i == len(entries) - 1
        connector = "└── " if is_last else "├── "
        name = escape(entry.name)
        style = "bold" if entry.is_dir() else ""
        console.print(f"{prefix}{connector}[{style}]{name}[/{style}]" if style else f"{prefix}{connector}{name}")
        if entry.is_dir():
            _print_tree(entry, console, prefix + ("    " if is_last else "│   "))


def create_cli(
    recipe_entrypoint: str,
    app_name: str = "nskit",
    app_help: str = "CLI for managing nskit recipes.",
    backend: Optional[Union[RecipeBackend, dict, Path, str]] = None,
) -> typer.Typer:
    """Create a CLI app for a recipe entrypoint.

    Args:
        recipe_entrypoint: The entrypoint name for recipe discovery (e.g., 'nskit.recipes')
        app_name: Name of the CLI application
        app_help: Help text for the CLI application
        backend: Optional backend for recipe discovery (enables list/update commands).
                Can be a RecipeBackend instance, dict config, or path to config file.

    Returns:
        Configured Typer application
    """
    app = typer.Typer(name=app_name, help=app_help, no_args_is_help=True)

    # Create client if backend provided
    if backend:
        # Convert config to backend if needed
        if not hasattr(backend, "list_recipes"):
            backend = create_backend_from_config(backend)

        client = RecipeClient(backend)
        engine = client.engine
    else:
        client = None
        backend = None

    @app.command(name="list", help="List available recipes.")
    def list_recipes():
        """List available recipes from backend or installed entry points."""
        if client:
            recipes = client.list_recipes()
        else:
            # Discover from entry points
            from nskit.common.extensions import get_extension_names

            names = get_extension_names(recipe_entrypoint)
            recipes = [RecipeInfo(name=n, versions=["local"]) for n in names]

        if not recipes:
            rich_print("[yellow]No recipes found[/yellow]")
            return

        table = Table(title="Available Recipes")
        table.add_column("Name", style="cyan")
        table.add_column("Versions", style="green")
        table.add_column("Description", style="white")

        for recipe in recipes:
            versions_str = ", ".join(recipe.versions[:3])
            if len(recipe.versions) > 3:
                versions_str += f" (+{len(recipe.versions) - 3} more)"
            table.add_row(recipe.name, versions_str, recipe.description or "")

        rich_print(table)

    @app.command(help="Initialize a recipe.")
    def init(
        recipe: Annotated[str, typer.Option(help="The name of the recipe to initialize.")],
        input_yaml_path: Annotated[
            Optional[Path], typer.Option(help="Path to the input YAML file for the recipe.")
        ] = None,
        output_base_path: Annotated[
            Optional[Path],
            typer.Option(help="Base output path for the recipe. Defaults to current directory."),
        ] = None,
        output_override_path: Annotated[
            Optional[Path],
            typer.Option(help="Override path for the recipe output. Defaults to recipe name."),
        ] = None,
        local: Annotated[
            bool,
            typer.Option("--local", help="Use locally installed packages instead of Docker (development mode)."),
        ] = False,
    ):
        """Initialize a recipe from the configured entrypoint."""
        if input_yaml_path is not None:
            with open(input_yaml_path) as file:
                input_data = yaml.safe_load(file)
                if input_data is None:
                    input_data = {}
        else:
            # Interactive mode: prompt for fields
            console = Console()
            env_resolver = EnvVarResolver()
            derived_eval = DerivedFieldEvaluator()
            ctx_values = ContextProvider().get_context()
            ctx_mappings = {"email": "git_email", "owner": "git_name"}

            r = Recipe.load(recipe, entrypoint=recipe_entrypoint, initialize=False)
            fields = get_required_fields_as_dict(r)

            # Extract RecipeField metadata (env_var, template, prompt_text)
            field_meta = {}
            model_fields = getattr(r, "model_fields", {})
            for fname, finfo in model_fields.items():
                extra = finfo.json_schema_extra or {}
                if isinstance(extra, dict):
                    field_meta[fname] = extra

            input_data = {}
            if fields:
                console.print(f"\n[bold cyan]Configure {recipe}[/bold cyan]\n")
                for field_name, field_type in fields.items():
                    # Resolve default chain: env_var → template → context → static
                    default = None
                    top_field = field_name.split(".")[0]
                    meta = field_meta.get(top_field, {})

                    # 1. Explicit env_var from RecipeField
                    if meta.get("env_var"):
                        default = env_resolver.resolve(meta["env_var"])

                    # 2. Convention-based env var
                    if default is None:
                        env_name = f"RECIPE_{field_name.upper().replace('.', '_')}"
                        default = env_resolver.resolve(env_name)

                    # 3. Template expression from RecipeField
                    if default is None and meta.get("template"):
                        try:
                            default = derived_eval.evaluate(meta["template"], {**input_data, "ctx": ctx_values})
                        except Exception:  # nosec B110
                            pass

                    # 4. Context provider fallback
                    if default is None:
                        short = field_name.rsplit(".", 1)[-1]
                        default = ctx_values.get(ctx_mappings.get(short, short))

                    prompt = meta.get("prompt_text", field_name)

                    if field_type == "bool":
                        input_data[field_name] = questionary.confirm(
                            prompt,
                            default=bool(default) if default is not None else False,
                        ).ask()
                    elif meta.get("options"):
                        input_data[field_name] = questionary.select(
                            prompt,
                            choices=meta["options"],
                            default=str(default) if default else None,
                        ).ask()
                    else:
                        value = questionary.text(
                            prompt,
                            default=str(default) if default else "",
                        ).ask()
                        if value is None:
                            raise typer.Abort()
                        input_data[field_name] = value
                console.print()
                input_data = FieldParser().create_nested_dict(input_data)

        # Detect VCS provider and ask about repo creation
        create_repo = False
        from nskit.client.recipes import _detect_repo_client

        vcs_client, vcs_provider = _detect_repo_client()
        if vcs_client is not None:
            create_repo = questionary.confirm(f"Create repository in {vcs_provider}?", default=True).ask()

        # Use client if available
        if client:
            # Override engine based on --local flag
            if local:
                client.engine = LocalEngine()

            # Determine output directory
            if output_override_path:
                output_dir = Path(output_override_path)
            elif output_base_path:
                output_dir = output_base_path / recipe
            else:
                output_dir = Path.cwd() / recipe

            # Get version (use latest if not specified)
            versions = client.get_recipe_versions(recipe)
            version = versions[0] if versions else "latest"

            # Initialize recipe
            result = client.initialize_recipe(
                recipe=recipe,
                version=version,
                parameters=input_data,
                output_dir=output_dir,
            )

            if not result.success:
                typer.echo(f"Error: {', '.join(result.errors)}", err=True)
                raise typer.Exit(1)
            console = Console()
            console.print(f"\n[green bold]✓ Created {recipe}[/green bold] at [cyan]{output_dir}[/cyan]\n")
            _print_tree(output_dir, console)
            console.print()
            _commit_and_maybe_push(
                output_dir, recipe, input_data.get("description", ""), create_repo, vcs_client, console
            )
        else:
            # Fallback: no backend, use Recipe.load directly
            try:
                r = Recipe.load(recipe, entrypoint=recipe_entrypoint, **input_data)
                result = r.create(base_path=output_base_path, override_path=output_override_path)
                project_path = next(iter(result.keys())) if result else (output_base_path or Path.cwd())

                # Save recipe config for future updates
                from nskit.client.config import ConfigManager, RecipeConfig, RecipeMetadata

                cfg = RecipeConfig(
                    input=input_data,
                    metadata=RecipeMetadata(
                        recipe_name=recipe,
                        docker_image=f"{recipe}:local",
                    ),
                )
                ConfigManager(Path(project_path)).save_config(cfg)

                console = Console()
                console.print(f"\n[green bold]✓ Created {recipe}[/green bold] at [cyan]{project_path}[/cyan]\n")
                _print_tree(Path(project_path), console)
                console.print()
                _commit_and_maybe_push(
                    Path(project_path), recipe, input_data.get("description", ""), create_repo, vcs_client, console
                )
            except Exception as exc:
                # Format validation errors nicely
                msg = str(exc)
                if "validation error" in msg.lower():
                    console = Console()
                    console.print("\n[red bold]Invalid input:[/red bold]\n")
                    for line in msg.split("\n"):
                        line = line.strip()
                        if not line or "For further information" in line:
                            continue
                        if line.startswith("Input should"):
                            console.print(f"  [yellow]→ {line}[/yellow]")
                        elif not line[0].isdigit():
                            console.print(f"  [red]{line}[/red]")
                    console.print("\n[dim]Use get-required-fields to see expected fields.[/dim]")
                    raise typer.Exit(1) from None
                raise

    @app.command(help="Get required fields for a recipe.")
    def get_required_fields(
        recipe: Annotated[str, typer.Option(help="The name of the recipe to get the input fields for.")],
    ):
        """Get required fields for a recipe as JSON."""

        r = Recipe.load(recipe, entrypoint=recipe_entrypoint, initialize=False)
        print(json.dumps(get_required_fields_as_dict(r)))

    # Add backend-dependent commands
    if client:

        @app.command(help="Update project to newer recipe version.")
        def update(
            target_version: Annotated[Optional[str], typer.Option(help="Target version (defaults to latest)")] = None,
            project_path: Annotated[
                Optional[Path], typer.Option(help="Project path (defaults to current directory)")
            ] = None,
            dry_run: Annotated[bool, typer.Option(help="Show what would be updated without making changes")] = False,
            diff_mode: Annotated[str, typer.Option(help="Diff mode: three-way (default) or two-way")] = "three-way",
        ):
            """Update a recipe-based project to newer version."""

            update_client = UpdateClient(backend, engine=engine)
            proj_path = project_path or Path.cwd()
            mode = DiffMode.TWO_WAY if diff_mode == "two-way" else DiffMode.THREE_WAY

            # Check for updates
            if not target_version:
                latest = update_client.check_update_available(proj_path)
                if not latest:
                    rich_print("[green]Project is up to date[/green]")
                    return
                target_version = latest
                rich_print(f"[cyan]Updating to version {target_version}[/cyan]")

            # Perform update
            result = update_client.update_project(
                project_path=proj_path,
                target_version=target_version,
                diff_mode=mode,
                dry_run=dry_run,
            )

            if result.success:
                rich_print(f"[green]✓ Updated {len(result.files_updated)} files[/green]")
                if result.files_with_conflicts:
                    rich_print(f"[yellow]⚠ {len(result.files_with_conflicts)} files have conflicts[/yellow]")
                    for file in result.files_with_conflicts:
                        rich_print(f"  - {file}")
            else:
                rich_print("[red]✗ Update failed[/red]")
                for error in result.errors:
                    rich_print(f"  {error}")

        @app.command(help="Check for recipe updates.")
        def check(
            project_path: Annotated[
                Optional[Path], typer.Option(help="Project path (defaults to current directory)")
            ] = None,
        ):
            """Check if updates are available for the project."""

            update_client = UpdateClient(backend, engine=engine)
            proj_path = project_path or Path.cwd()

            latest = update_client.check_update_available(proj_path)
            if latest:
                rich_print(f"[yellow]Update available: {latest}[/yellow]")
                rich_print("Run 'update' command to upgrade")
            else:
                rich_print("[green]Project is up to date[/green]")

        @app.command(help="Discover available recipes.")
        def discover(
            search: Annotated[Optional[str], typer.Option(help="Search term to filter recipes")] = None,
        ):
            """Discover available recipes from the backend."""
            discovery_client = DiscoveryClient(backend)
            recipes = discovery_client.discover_recipes(search_term=search)

            if not recipes:
                rich_print("[yellow]No recipes found[/yellow]")
                return

            table = Table(title="Discovered Recipes")
            table.add_column("Name", style="cyan")
            table.add_column("Latest Version", style="green")
            table.add_column("Description", style="white")

            for recipe in recipes:
                latest = recipe.versions[0] if recipe.versions else "N/A"
                table.add_row(recipe.name, latest, recipe.description or "")

            rich_print(table)

    return app
