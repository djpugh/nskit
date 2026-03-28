"""Read OCI image labels from a registry without pulling layers.

Uses the OCI Distribution Spec:
1. GET /v2/<name>/manifests/<tag> → manifest with config digest
2. GET /v2/<name>/blobs/<config_digest> → config JSON with labels
"""

from __future__ import annotations

import json
import ssl
import subprocess  # nosec B404
from urllib.request import Request, urlopen

from nskit._logging import logger_factory

logger = logger_factory.get_logger(__name__)


def read_remote_labels(image_url: str, token: str | None = None) -> dict[str, str]:
    """Read labels from a remote OCI image without pulling.

    Args:
        image_url: Full image URL (e.g. ``ghcr.io/myorg/recipe:v1.0.0``).
        token: Optional bearer token for authentication.

    Returns:
        Dict of labels, or empty dict on failure.
    """
    try:
        registry, name, tag = _parse_image_url(image_url)
        manifest = _get_manifest(registry, name, tag, token)
        config_digest = manifest.get("config", {}).get("digest")
        if not config_digest:
            return {}
        config = _get_blob(registry, name, config_digest, token)
        return config.get("config", {}).get("Labels", {})
    except Exception:  # nosec B110
        logger.debug("Failed to read remote labels for %s", image_url, exc_info=True)
        return {}


def read_local_labels(image_url: str) -> dict[str, str]:
    """Read labels from a locally available Docker image.

    Args:
        image_url: Image reference (e.g. ``myorg/recipe:v1.0.0``).

    Returns:
        Dict of labels, or empty dict if image not found.
    """
    try:
        result = subprocess.run(  # nosec B603, B607
            ["docker", "inspect", image_url, "--format", "{{json .Config.Labels}}"],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return {}
    if result.returncode == 0 and result.stdout.strip():
        try:
            return json.loads(result.stdout.strip()) or {}
        except json.JSONDecodeError:
            pass
    return {}


def get_recipe_name(labels: dict[str, str]) -> str | None:
    """Extract recipe name from nskit labels."""
    return labels.get("nskit.recipe.name") or None


def _parse_image_url(image_url: str) -> tuple[str, str, str]:
    """Parse ``registry/name:tag`` into components."""
    if ":" in image_url.rsplit("/", 1)[-1]:
        ref, tag = image_url.rsplit(":", 1)
    else:
        ref, tag = image_url, "latest"

    parts = ref.split("/", 1)
    if len(parts) == 1 or "." not in parts[0]:
        # Docker Hub
        registry = "registry-1.docker.io"
        name = ref if "/" in ref else f"library/{ref}"
    else:
        registry = parts[0]
        name = parts[1]

    return registry, name, tag


def _registry_request(url: str, token: str | None, accept: str = "application/vnd.oci.image.manifest.v1+json") -> dict:
    """Make an authenticated request to a registry."""
    headers = {"Accept": f"{accept}, application/vnd.docker.distribution.manifest.v2+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = Request(url, headers=headers)
    ssl_ctx = ssl.create_default_context()
    with urlopen(req, timeout=10, context=ssl_ctx) as resp:  # nosec B310
        return json.loads(resp.read())


def _get_manifest(registry: str, name: str, tag: str, token: str | None) -> dict:
    return _registry_request(f"https://{registry}/v2/{name}/manifests/{tag}", token)


def _get_blob(registry: str, name: str, digest: str, token: str | None) -> dict:
    return _registry_request(
        f"https://{registry}/v2/{name}/blobs/{digest}",
        token,
        accept="application/vnd.oci.image.config.v1+json",
    )
