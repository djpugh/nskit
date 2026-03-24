"""Generic CLI for nskit recipes."""
import json
from pathlib import Path
from typing import Annotated, Optional, Union


from rich import print as rich_print
from rich.table import Table
import typer
import yaml


from nskit.client import RecipeClient, UpdateClient, DiscoveryClient

from nskit.client.diff.models import DiffMode
from nskit.client.backends import create_backend_from_config
from nskit.client.engines import LocalEngine
from nskit.client.utils import get_required_fields_as_dict
from nskit.mixer.components.recipe import Recipe


def create_cli(
    recipe_entrypoint: str,
    app_name: str = "nskit",
    app_help: str = "CLI for managing nskit recipes.",
    backend: Optional[Union['RecipeBackend', dict, Path, str]] = None,
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
        if not hasattr(backend, 'list_recipes'):
            backend = create_backend_from_config(backend)

        client = RecipeClient(backend)
    else:
        client = None
        backend = None

    @app.command(help="Initialize a recipe.")
    def init(
        recipe: Annotated[str, typer.Option(help="The name of the recipe to initialize.")],
        input_yaml_path: Annotated[
            Optional[Path], typer.Option(help="Path to the input YAML file for the recipe.")
        ] = None,
        output_base_path: Annotated[
            Optional[Path],
            typer.Option(
                help="Base output path for the recipe. Defaults to current directory."
            ),
        ] = None,
        output_override_path: Annotated[
            Optional[Path],
            typer.Option(
                help="Override path for the recipe output. Defaults to recipe name."
            ),
        ] = None,
        local: Annotated[
            bool,
            typer.Option(
                "--local",
                help="Use locally installed packages instead of Docker (development mode)."
            ),
        ] = False,
    ):
        """Initialize a recipe from the configured entrypoint."""
        if input_yaml_path is not None:
            with open(input_yaml_path) as file:
                input_data = yaml.safe_load(file)
                if input_data is None:
                    input_data = {}
        else:
            input_data = {}

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
        else:
            # Fallback: no backend, use Recipe.load directly
            r = Recipe.load(recipe, entrypoint=recipe_entrypoint, **input_data)
            r.create(base_path=output_base_path, override_path=output_override_path)

    @app.command(help="Get required fields for a recipe.")
    def get_required_fields(
        recipe: Annotated[
            str, typer.Option(help="The name of the recipe to get the input fields for.")
        ],
    ):
        """Get required fields for a recipe as JSON."""

        r = Recipe.load(recipe, entrypoint=recipe_entrypoint, initialize=False)
        print(json.dumps(get_required_fields_as_dict(r)))

    # Add list command if backend provided
    if client:
        @app.command(help="List available recipes.")
        def list():
            """List all available recipes from the backend."""

            recipes = client.list_recipes()

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
                table.add_row(
                    recipe.name,
                    versions_str,
                    recipe.description or ""
                )

            rich_print(table)

        @app.command(help="Update project to newer recipe version.")
        def update(
            target_version: Annotated[
                Optional[str],
                typer.Option(help="Target version (defaults to latest)")
            ] = None,
            project_path: Annotated[
                Optional[Path],
                typer.Option(help="Project path (defaults to current directory)")
            ] = None,
            dry_run: Annotated[
                bool,
                typer.Option(help="Show what would be updated without making changes")
            ] = False,
        ):
            """Update a recipe-based project to newer version."""

            update_client = UpdateClient(backend)
            proj_path = project_path or Path.cwd()

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
                diff_mode=DiffMode.THREE_WAY,
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
                Optional[Path],
                typer.Option(help="Project path (defaults to current directory)")
            ] = None,
        ):
            """Check if updates are available for the project."""

            update_client = UpdateClient(backend)
            proj_path = project_path or Path.cwd()

            latest = update_client.check_update_available(proj_path)
            if latest:
                rich_print(f"[yellow]Update available: {latest}[/yellow]")
                rich_print("Run 'update' command to upgrade")
            else:
                rich_print("[green]Project is up to date[/green]")

        @app.command(help="Discover available recipes.")
        def discover(
            search: Annotated[
                Optional[str],
                typer.Option(help="Search term to filter recipes")
            ] = None,
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
                table.add_row(
                    recipe.name,
                    latest,
                    recipe.description or ""
                )

            rich_print(table)

    return app
