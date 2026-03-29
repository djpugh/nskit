"""Orchestrator for recipe initialisation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from nskit.client.backends.base import RecipeBackend
from nskit.client.config import ConfigManager, RecipeConfig, RecipeMetadata
from nskit.client.engines.base import RecipeEngine
from nskit.client.exceptions import InitError
from nskit.client.interactive import InteractiveHandler
from nskit.client.models import RecipeResult
from nskit.client.recipes import RecipeClient
from nskit.client.version_resolver import VersionResolver


class InitManager:
    """Orchestrator for the full recipe initialisation flow.

    Coordinates recipe discovery, field collection (interactive or
    file-based), recipe execution, and configuration persistence.

    Args:
        backend: Recipe backend for discovery and fetching.
        engine: Recipe engine for execution.
        config_dir: Config directory name (default ``.recipe``).
        config_filename: Config file name (default ``config.yml``).
    """

    def __init__(
        self,
        backend: RecipeBackend,
        engine: RecipeEngine,
        config_dir: str = ".recipe",
        config_filename: str = "config.yml",
    ) -> None:
        self.client = RecipeClient(backend, engine)
        self.backend = backend
        self.engine = engine
        self.config_dir = config_dir
        self.config_filename = config_filename

    def initialize(
        self,
        recipe_name: str | None = None,
        version: str | None = None,
        input_yaml_path: Path | None = None,
        output_dir: Path = Path("."),
        force: bool = False,
        interactive_handler: InteractiveHandler | None = None,
    ) -> RecipeResult:
        """Run the full initialisation flow.

        Discovers recipes, collects field values (interactively or from
        a YAML file), executes the recipe, and persists configuration.

        Args:
            recipe_name: Recipe to initialise. If ``None`` and an
                interactive handler is provided, the user is prompted
                to select one.
            version: Target version. Resolves to latest if ``None``.
            input_yaml_path: Path to a YAML file with pre-filled values.
                Mutually exclusive with interactive mode.
            output_dir: Directory to generate the project in.
            force: Allow initialisation in a non-empty directory.
            interactive_handler: Handler for interactive prompts. Required
                when *input_yaml_path* is ``None``.

        Returns:
            Result of the recipe execution.

        Raises:
            InitError: If initialisation fails or is cancelled.
        """
        # Resolve recipe
        if recipe_name is None:
            recipe_name = self._select_recipe(interactive_handler)

        # Resolve version
        resolver = VersionResolver(self.backend)
        resolved_version = resolver.resolve_version(recipe_name, version)

        # Collect parameters
        parameters = self._collect_parameters(recipe_name, input_yaml_path, interactive_handler)

        # Confirm with user if interactive
        if interactive_handler is not None and input_yaml_path is None:
            if not interactive_handler.confirm_initialisation(recipe_name, output_dir, parameters):
                raise InitError("Initialisation cancelled by user")

        # Execute recipe
        result = self.client.initialize_recipe(
            recipe=recipe_name,
            version=resolved_version,
            parameters=parameters,
            output_dir=output_dir,
            force=force,
        )

        if not result.success:
            raise InitError(
                f"Recipe initialisation failed for '{recipe_name}'",
                details="; ".join(result.errors),
            )

        # Persist config
        self._persist_config(output_dir, recipe_name, resolved_version, parameters)

        return result

    def _select_recipe(self, interactive_handler: InteractiveHandler | None) -> str:
        """Select a recipe interactively or raise an error."""
        if interactive_handler is None:
            raise InitError("No recipe name provided and no interactive handler available")

        recipes = self.client.list_recipes()
        if not recipes:
            raise InitError("No recipes available from the configured backend")

        selected = interactive_handler.select_recipe(recipes)
        if selected is None:
            raise InitError("Recipe selection cancelled by user")
        return selected.name

    def _collect_parameters(
        self,
        recipe_name: str,
        input_yaml_path: Path | None,
        interactive_handler: InteractiveHandler | None,
    ) -> dict[str, Any]:
        """Collect recipe parameters from YAML or interactively."""
        if input_yaml_path is not None:
            return self._load_yaml_parameters(input_yaml_path)

        if interactive_handler is None:
            raise InitError("No input YAML file and no interactive handler provided")

        # For now, return empty dict — the interactive handler's
        # collect_field_values requires an InputFieldsResponse which
        # comes from the recipe engine. This will be wired up when
        # the engine supports field introspection.
        return {}

    def _load_yaml_parameters(self, path: Path) -> dict[str, Any]:
        """Load parameters from a YAML file."""
        if not path.exists():
            raise InitError(f"Input YAML file not found: {path}")
        try:
            raw = path.read_text(encoding="utf-8")
            data = yaml.safe_load(raw)
            if not isinstance(data, dict):
                raise InitError(f"Expected a mapping in {path}, got {type(data).__name__}")
            return data
        except yaml.YAMLError as exc:
            raise InitError(f"Invalid YAML in {path}", details=str(exc)) from exc

    def _persist_config(
        self,
        output_dir: Path,
        recipe_name: str,
        version: str,
        parameters: dict[str, Any],
    ) -> None:
        """Persist recipe configuration after successful init."""
        from datetime import datetime, timezone

        config_mgr = ConfigManager(output_dir, self.config_dir, self.config_filename)

        try:
            image_url = self.backend.get_image_url(recipe_name, version)
        except NotImplementedError:
            image_url = f"{recipe_name}:{version}"

        now = datetime.now(tz=timezone.utc)
        config = RecipeConfig(
            input=parameters,
            metadata=RecipeMetadata(
                recipe_name=recipe_name,
                docker_image=image_url,
                created_at=now,
                updated_at=now,
            ),
        )
        config_mgr.save_config(config)
