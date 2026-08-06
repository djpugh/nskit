"""End-to-end tests for the field contract, against a real recipe.

The unit tests cover each half of the contract in isolation: ``FieldParser``
producing ``FieldSpec``s, and ``InteractiveHandler`` consuming them. Neither
proves the halves fit together, so a value could be reported one way and
collected another and both suites would still pass.

These tests drive the whole chain against ``nskit.recipes.python.package``:

    recipe model -> FieldParser -> InteractiveHandler -> create_nested_dict
                 -> recipe construction -> render

The final construct-and-render step is what makes this end to end: if the
emitted field names, nesting or types do not match what the model actually
accepts, pydantic rejects the collected values.
"""

from __future__ import annotations

import unittest
from typing import Literal
from unittest.mock import patch

from pydantic import BaseModel

from nskit.client.field_models import FieldType
from nskit.client.field_parser import FieldParser
from nskit.client.interactive import InteractiveHandler
from nskit.common.contextmanagers import ChDir
from nskit.recipes.python.package import PackageRecipe

# Answers keyed by the dotted field name the parser is expected to emit. Values
# are deliberately realistic (a valid email and URL) so pydantic's own
# validation is exercised rather than bypassed.
_ANSWERS = {
    "name": "e2e-contract-pkg",
    "repo.owner": "Test Owner",
    "repo.email": "test@example.com",
    "repo.url": "https://example.com/test",
    "repo.description": "Field contract e2e",
}


class _PinnedRecipe(PackageRecipe):
    """A recipe pinning a value, to prove pinned fields are never prompted."""

    language: Literal["python"] = "python"


class _Maintainer(BaseModel):
    """A plain nested model, used inside a list below."""

    name: str = ""
    email: str = ""


class _ListRecipe(PackageRecipe):
    """A recipe with a ``list`` of plain nested models.

    ``PackageRecipe.contents`` is a ``list[File | Folder]``, whose inner type is
    a union rather than a single model — so it never flattens regardless of
    whether the container check is correct, making it useless as a guard. This
    field's inner type *is* a plain ``BaseModel``, so it would be flattened into
    ``maintainers.name`` if containers were mistaken for nested models.
    """

    maintainers: list[_Maintainer] = []


def _collect(recipe_class: type, answers: dict[str, str]) -> dict:
    """Run parser -> handler -> nested rebuild, returning recipe kwargs.

    Prompts are answered from ``answers`` by field name; a field with no answer
    falls back to its resolved default, mirroring a user pressing enter.
    """
    parser = FieldParser()
    fields = parser.from_recipe_model(recipe_class)
    handler = InteractiveHandler()

    prompted: list[str] = []

    def fake_prompt(field, default):
        prompted.append(field.name)
        return answers.get(field.name, default)

    with patch.object(handler, "_prompt_field", side_effect=fake_prompt):
        collected = handler.collect_field_values(fields)

    assert collected is not None, "collection was cancelled"
    return parser.create_nested_dict(collected), prompted, fields


class TestFieldContractRoundTrip(unittest.TestCase):
    """The emitted contract round-trips into a valid, renderable recipe."""

    def test_collected_values_construct_the_recipe(self) -> None:
        """Values collected via the contract are accepted by the model.

        This is the assertion that ties the two halves together: any drift in
        field naming or nesting shows up as a pydantic ValidationError.
        """
        kwargs, _prompted, _fields = _collect(PackageRecipe, _ANSWERS)
        recipe = PackageRecipe(**kwargs)
        self.assertEqual(recipe.name, "e2e-contract-pkg")
        self.assertEqual(recipe.repo.owner, "Test Owner")

    def test_nested_values_are_rebuilt_under_the_right_key(self) -> None:
        """Dotted leaves rebuild into the nested model the recipe expects."""
        kwargs, _prompted, _fields = _collect(PackageRecipe, _ANSWERS)
        self.assertIn("repo", kwargs)
        self.assertEqual(kwargs["repo"]["owner"], "Test Owner")
        # The dotted form must not survive into the constructor kwargs.
        self.assertNotIn("repo.owner", kwargs)

    def test_recipe_renders_with_collected_values(self) -> None:
        """The constructed recipe renders, so collected values reach templates."""
        kwargs, _prompted, _fields = _collect(PackageRecipe, _ANSWERS)
        recipe = PackageRecipe(**kwargs)
        with ChDir():
            tree = recipe.dryrun()
        self.assertTrue(tree, "recipe rendered no files")

    def test_nested_leaves_are_prompted_individually(self) -> None:
        """The user is asked for nested leaves, not for the nested object."""
        _kwargs, prompted, _fields = _collect(PackageRecipe, _ANSWERS)
        self.assertIn("repo.owner", prompted)
        self.assertIn("repo.email", prompted)
        self.assertNotIn("repo", prompted)

    def test_required_nested_leaves_are_reported_required(self) -> None:
        """Required leaves of a required nested model are marked required.

        Regression guard for the ``required`` derivation: ``repo.owner`` and
        friends are declared with ``Field(...)``, which used to report as
        optional.
        """
        _kwargs, _prompted, fields = _collect(PackageRecipe, _ANSWERS)
        by_name = {f.name: f for f in fields.fields}
        for name in ("repo.owner", "repo.email", "repo.url"):
            with self.subTest(field=name):
                self.assertTrue(by_name[name].required, f"{name} should be required")

    def test_optional_leaf_is_not_required(self) -> None:
        """A nested leaf with a default is not required."""
        _kwargs, _prompted, fields = _collect(PackageRecipe, _ANSWERS)
        by_name = {f.name: f for f in fields.fields}
        self.assertFalse(by_name["repo.description"].required)

    def test_enum_field_offers_its_choices(self) -> None:
        """A real enum field surfaces selectable options.

        ``license`` is an ``Optional[LicenseOptionsEnum]``; without inferred
        options a prompting UI would show a free-text box for a closed set.
        """
        _kwargs, _prompted, fields = _collect(PackageRecipe, _ANSWERS)
        licence = next(f for f in fields.fields if f.name == "license")
        self.assertEqual(licence.type, FieldType.ENUM)
        self.assertIn("apache-2.0", licence.options or [])

    def test_list_of_models_is_not_flattened(self) -> None:
        """A ``list`` of nested models is never split into dotted leaves.

        Flattening would emit ``maintainers.name``, losing the fact that it is a
        sequence and producing a key the model cannot accept back.
        """
        _kwargs, _prompted, fields = _collect(_ListRecipe, _ANSWERS)
        names = {f.name for f in fields.fields}
        self.assertIn("maintainers", names)
        self.assertFalse(
            {n for n in names if n.startswith("maintainers.")},
            "list of models was flattened into dotted leaves",
        )

    def test_list_of_unions_is_also_left_alone(self) -> None:
        """``contents`` (``list[File | Folder]``) is likewise not flattened."""
        _kwargs, _prompted, fields = _collect(PackageRecipe, _ANSWERS)
        names = {f.name for f in fields.fields}
        self.assertFalse({n for n in names if n.startswith("contents.")})


class TestPinnedFieldEndToEnd(unittest.TestCase):
    """A pinned field is never prompted, but still reaches the recipe."""

    def test_pinned_field_is_not_prompted(self) -> None:
        """The user is not asked for a value the recipe has pinned."""
        _kwargs, prompted, _fields = _collect(_PinnedRecipe, _ANSWERS)
        self.assertNotIn("language", prompted)

    def test_pinned_field_still_reaches_the_recipe(self) -> None:
        """The pinned value is collected and accepted by the model.

        Guards both halves at once: the parser must mark it hidden, and the
        handler must keep its default rather than discarding it.
        """
        kwargs, _prompted, _fields = _collect(_PinnedRecipe, _ANSWERS)
        self.assertEqual(kwargs.get("language"), "python")
        recipe = _PinnedRecipe(**kwargs)
        self.assertEqual(recipe.language, "python")

    def test_pinned_field_reports_as_a_closed_choice(self) -> None:
        """A pinned Literal is reported as an ENUM of one, and hidden."""
        _kwargs, _prompted, fields = _collect(_PinnedRecipe, _ANSWERS)
        language = next(f for f in fields.fields if f.name == "language")
        self.assertEqual(language.type, FieldType.ENUM)
        self.assertEqual(language.options, ["python"])
        self.assertTrue(language.hidden)

    def test_other_fields_are_still_prompted(self) -> None:
        """Pinning one field does not suppress collection of the rest."""
        _kwargs, prompted, _fields = _collect(_PinnedRecipe, _ANSWERS)
        self.assertIn("repo.owner", prompted)


if __name__ == "__main__":
    unittest.main()
