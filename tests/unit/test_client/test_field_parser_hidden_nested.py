"""Test that FieldParser._extract skips nested models marked hidden."""

import unittest

from pydantic import BaseModel, Field

from nskit.client.field_parser import FieldParser


class InnerSettings(BaseModel):
    private: bool = True
    has_wiki: bool = False
    has_issues: bool = True


class RepoMetadata(BaseModel):
    description: str = ""
    settings: InnerSettings = Field(
        default_factory=InnerSettings,
        json_schema_extra={"hidden": True},
    )


class MyRecipe(BaseModel):
    name: str
    repository: RepoMetadata = Field(default_factory=RepoMetadata)


class TestFieldParserHiddenNestedModel(unittest.TestCase):
    """FieldParser._extract respects hidden on nested model fields."""

    def setUp(self):
        self.parser = FieldParser()
        self.response = self.parser.from_recipe_model(MyRecipe, include_base=True)
        self.field_names = {f.name for f in self.response.fields}

    def test_visible_nested_leaves_emitted(self):
        """Non-hidden nested model leaves are present."""
        self.assertIn("repository.description", self.field_names)

    def test_hidden_nested_leaves_excluded(self):
        """Leaves under a hidden nested model are omitted."""
        self.assertNotIn("repository.settings.private", self.field_names)
        self.assertNotIn("repository.settings.has_wiki", self.field_names)
        self.assertNotIn("repository.settings.has_issues", self.field_names)

    def test_top_level_fields_emitted(self):
        """Top-level fields unaffected."""
        self.assertIn("name", self.field_names)

    def test_non_hidden_nested_model_recurses(self):
        """A nested model without hidden still recurses into leaves."""
        # repository itself is not hidden, so its leaves appear
        self.assertIn("repository.description", self.field_names)
