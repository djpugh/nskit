"""Docker execution engine."""

from __future__ import annotations

import os
import subprocess  # nosec B404
import tempfile
from pathlib import Path
from typing import Any

import yaml as pyyaml

from nskit.client.backends.settings import EngineTimeouts
from nskit.client.engines.base import RecipeEngine
from nskit.client.models import RecipeResult
from nskit.client.validation import validate_image_url, validate_recipe_name


class DockerEngine(RecipeEngine):
    """Execute recipes in Docker containers."""

    def __init__(self, skip_pull: bool = False, timeouts: EngineTimeouts | dict | None = None) -> None:
        """Initialise the Docker engine.

        Args:
            skip_pull: Skip pulling the image (useful for locally built images).
            timeouts: Timeout configuration for Docker operations.
        """
        self.skip_pull = skip_pull
        if isinstance(timeouts, dict):
            self.timeouts = EngineTimeouts(**timeouts)
        else:
            self.timeouts = timeouts or EngineTimeouts()

    def execute(
        self,
        recipe: str,
        version: str,
        parameters: dict[str, Any],
        output_dir: Path,
        image_url: str | None = None,
        entrypoint: str | None = None,
    ) -> RecipeResult:
        """Execute recipe in a Docker container.

        Writes parameters to a YAML file, mounts it into the container,
        and invokes the nskit CLI ``init`` command.

        Args:
            recipe: Recipe name.
            version: Recipe version.
            parameters: Recipe input parameters.
            output_dir: Host directory for generated output.
            image_url: Docker image URL (required).
            entrypoint: Not used for Docker engine.

        Returns:
            Recipe execution result.
        """
        if not image_url:
            raise ValueError("Docker engine requires image_url")

        validate_image_url(image_url)
        validate_recipe_name(recipe)

        errors: list[str] = []
        warnings: list[str] = []

        try:
            if not self.skip_pull:
                subprocess.run(  # nosec B603, B607
                    ["docker", "pull", image_url],
                    check=True,
                    capture_output=True,
                    timeout=self.timeouts.pull,
                )

            # Write parameters as YAML (matches CLI --input-yaml-path)
            with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
                pyyaml.safe_dump(parameters, f, default_flow_style=False)
                input_file = Path(f.name)
            # Ensure readable by non-root container user
            input_file.chmod(0o644)

            try:
                output_dir.mkdir(parents=True, exist_ok=True)

                cmd = [
                    "docker",
                    "run",
                    "--rm",
                ]
                # Run as host user so output files have correct ownership
                if hasattr(os, "getuid"):
                    cmd += ["--user", f"{os.getuid()}:{os.getgid()}"]
                cmd += [
                    "-e",
                    "HOME=/tmp",
                    "-e",
                    f"LOG_JSON={os.environ.get('LOG_JSON', 'true')}",
                    "-e",
                    f"LOGLEVEL={os.environ.get('LOGLEVEL', 'INFO')}",
                    "-v",
                    f"{output_dir.absolute()}:/app/output",
                    "-v",
                    f"{input_file.absolute()}:/app/input.yml:ro",
                    image_url,
                    "init",
                    "--recipe",
                    recipe,
                    "--input-yaml-path",
                    "/app/input.yml",
                    "--output-override-path",
                    "/app/output",
                ]

                result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=self.timeouts.run)  # nosec B603, B607

                if result.stderr:
                    warnings.append(result.stderr.strip())

                # Collect created files
                files_created = [str(p.relative_to(output_dir)) for p in output_dir.rglob("*") if p.is_file()]

                return RecipeResult(
                    success=True,
                    project_path=output_dir,
                    recipe_name=recipe,
                    recipe_version=version,
                    files_created=files_created,
                    warnings=warnings,
                )
            finally:
                input_file.unlink(missing_ok=True)

        except subprocess.CalledProcessError as e:
            detail = e.stderr.strip() if e.stderr else str(e)
            errors.append(detail)
            return RecipeResult(
                success=False,
                project_path=output_dir,
                recipe_name=recipe,
                recipe_version=version,
                errors=errors,
                warnings=warnings,
            )
        except Exception as e:
            errors.append(str(e))
            return RecipeResult(
                success=False,
                project_path=output_dir,
                recipe_name=recipe,
                recipe_version=version,
                errors=errors,
                warnings=warnings,
            )
