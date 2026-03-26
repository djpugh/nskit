"""Result models for recipe operations."""

from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, Field


class RecipeInfo(BaseModel):
    """Information about a recipe."""

    name: str
    versions: list[str]
    description: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class RecipeResult(BaseModel):
    """Result of recipe initialization."""

    success: bool
    project_path: Path
    recipe_name: str
    recipe_version: str
    files_created: list[Path] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class UpdateResult(BaseModel):
    """Result of recipe update."""

    success: bool
    files_updated: list[str] = Field(default_factory=list)
    files_with_conflicts: list[str] = Field(default_factory=list)
    clean_merges: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class RepositoryInfo(BaseModel):
    """Information about a created repository."""

    name: str
    url: str
    clone_url: Optional[str] = None
    created_at: Optional[datetime] = None
    description: Optional[str] = None
    settings: dict[str, Any] = Field(default_factory=dict)
