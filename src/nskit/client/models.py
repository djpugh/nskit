"""Result models for recipe operations."""
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class RecipeInfo(BaseModel):
    """Information about a recipe."""
    name: str
    versions: List[str]
    description: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class RecipeResult(BaseModel):
    """Result of recipe initialization."""
    success: bool
    project_path: Path
    recipe_name: str
    recipe_version: str
    files_created: List[Path] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class UpdateResult(BaseModel):
    """Result of recipe update."""
    success: bool
    files_updated: List[str] = Field(default_factory=list)
    files_with_conflicts: List[str] = Field(default_factory=list)
    clean_merges: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class RepositoryInfo(BaseModel):
    """Information about a created repository."""
    name: str
    url: str
    clone_url: Optional[str] = None
    created_at: Optional[datetime] = None
    description: Optional[str] = None
    settings: Dict[str, Any] = Field(default_factory=dict)
