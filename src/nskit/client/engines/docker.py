"""Docker execution engine."""
import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List

from nskit.client.engines.base import RecipeEngine
from nskit.client.models import RecipeResult


class DockerEngine(RecipeEngine):
    """Execute recipes in Docker containers."""

    def execute(
        self,
        recipe: str,
        version: str,
        parameters: Dict[str, Any],
        output_dir: Path,
        image_url: str = None,
        entrypoint: str = None,
    ) -> RecipeResult:
        """Execute recipe in Docker container.
        
        Args:
            recipe: Recipe name
            version: Recipe version
            parameters: Recipe parameters
            output_dir: Output directory
            image_url: Docker image URL (required)
            entrypoint: Not used for Docker engine
            
        Returns:
            Recipe execution result
        """
        if not image_url:
            raise ValueError("Docker engine requires image_url")

        errors = []
        warnings: List[str] = []

        try:
            # Pull image
            subprocess.run(
                ["docker", "pull", image_url],
                check=True,
                capture_output=True,
            )

            # Write parameters to temp file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                json.dump(parameters, f)
                input_file = Path(f.name)

            try:
                # Run container
                cmd = [
                    "docker", "run", "--rm",
                    "-v", f"{output_dir.absolute()}:/app/output",
                    "-v", f"{input_file.absolute()}:/app/input.json",
                    image_url,
                    "recipe", "init",
                    "--recipe", recipe,
                    "--input-json", "/app/input.json",
                    "--output", "/app/output"
                ]
                
                subprocess.run(cmd, capture_output=True, text=True, check=True)
                
                # Collect created files
                files_created = [
                    str(p.relative_to(output_dir)) 
                    for p in output_dir.rglob("*") 
                    if p.is_file()
                ]

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
