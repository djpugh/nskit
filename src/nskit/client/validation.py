"""Input validation for recipe names, versions, and image URLs."""

from __future__ import annotations

import re

# Allowed: alphanumeric, hyphens, underscores, dots, forward slashes
_SAFE_NAME_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._/-]*$")
_SAFE_VERSION_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._+-]*$")
_SAFE_IMAGE_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._/:@-]*$")


def validate_recipe_name(name: str) -> str:
    """Validate and return a recipe name, or raise ValueError."""
    if not name or not _SAFE_NAME_RE.match(name):
        raise ValueError(f"Invalid recipe name: {name!r}")
    return name


def validate_version(version: str) -> str:
    """Validate and return a version string, or raise ValueError."""
    if not version or not _SAFE_VERSION_RE.match(version):
        raise ValueError(f"Invalid version: {version!r}")
    return version


def validate_image_url(url: str) -> str:
    """Validate and return a Docker image URL, or raise ValueError."""
    if not url or not _SAFE_IMAGE_RE.match(url):
        raise ValueError(f"Invalid image URL: {url!r}")
    return url
