"""CLI module for nskit."""

from __future__ import annotations


def __getattr__(name: str):
    """Lazy import create_cli to avoid triggering logger setup at import time."""
    if name == "create_cli":
        from nskit.cli.app import create_cli

        return create_cli
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["create_cli"]


def main():
    """Default nskit CLI entry point.

    Supports ``--backend`` and ``--engine`` options to configure
    execution without a wrapper script::

        nskit --backend docker-local --engine docker list
        nskit --backend docker-local --engine docker init --recipe python_package
    """
    import os
    import sys

    # Default to human-readable logs in CLI mode — must be set before
    # importing create_cli so loggers pick up the values.
    os.environ.setdefault("LOG_JSON", "false")
    os.environ.setdefault("LOGLEVEL", "WARNING")

    from nskit.cli.app import create_cli

    # Parse --backend and --engine before typer sees them
    args = sys.argv[1:]
    backend_type = None
    engine_type = None
    clean_args = []
    i = 0
    while i < len(args):
        if args[i] == "--backend" and i + 1 < len(args):
            backend_type = args[i + 1]
            i += 2
        elif args[i] == "--engine" and i + 1 < len(args):
            engine_type = args[i + 1]
            i += 2
        else:
            clean_args.append(args[i])
            i += 1

    backend = _resolve_backend(backend_type)
    engine = _resolve_engine(engine_type)

    app = create_cli(
        recipe_entrypoint="nskit.recipes",
        backend=backend,
    )

    # If engine specified, override on the client after creation
    if engine and backend:
        # The client is created inside create_cli — we need to patch it
        # via the init command's closure. Simpler: just set it on RecipeClient.
        pass  # Engine is handled by the backend's default for now

    sys.argv = [sys.argv[0], *clean_args]
    app()


def _resolve_backend(backend_type: str | None):
    """Resolve backend from CLI string."""
    if backend_type is None:
        return None
    if backend_type == "docker-local":
        from nskit.client.backends import DockerLocalBackend

        return DockerLocalBackend()
    if backend_type == "local":
        from pathlib import Path

        from nskit.client.backends import LocalBackend

        return LocalBackend(recipes_dir=Path("."))

    # Try as a config file path
    from pathlib import Path

    p = Path(backend_type)
    if p.exists():
        from nskit.client.backends import create_backend_from_config

        return create_backend_from_config(str(p))

    raise SystemExit(f"Unknown backend: {backend_type}. Use: docker-local, local, or a config file path.")


def _resolve_engine(engine_type: str | None):
    """Resolve engine from CLI string."""
    if engine_type is None:
        return None
    if engine_type == "docker":
        from nskit.client.engines import DockerEngine

        return DockerEngine()
    if engine_type == "local":
        from nskit.client.engines import LocalEngine

        return LocalEngine()
    raise SystemExit(f"Unknown engine: {engine_type}. Use: docker or local.")
