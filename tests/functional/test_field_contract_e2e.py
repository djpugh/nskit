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


# ---------------------------------------------------------------------------
# Provider end-to-end tests
# ---------------------------------------------------------------------------

# Simulates a platform recipe that uses providers — no Docker mocks, real
# FieldParser + InteractiveHandler running the full chain.


class _ProviderRecipe(BaseModel):
    """A recipe-like model using options_provider and default_provider.

    Not a real Recipe subclass (avoids needing contents/hooks) — just proves
    the field contract round-trips with providers.
    """

    from pydantic import Field

    name: str = "provider-test"
    domain: str = Field(
        "",
        json_schema_extra={
            "options_provider": "test_domains",
            "display_name": "Domain",
        },
    )
    account_id: str = Field(
        "",
        json_schema_extra={
            "default_provider": "test_account_lookup",
            "prompt_text": "Account ID",
        },
    )
    region: str = Field(
        "eu-west-1",
        json_schema_extra={
            "options_provider": "test_regions",
            "default_provider": "test_default_region",
        },
    )


# Provider implementations (would live in a CLI plugin in production)
_DOMAIN_ACCOUNTS = {
    "analytics": "111111111111",
    "genomics": "222222222222",
    "platform": "333333333333",
}


def _test_domains_provider():
    return list(_DOMAIN_ACCOUNTS.keys())


def _test_account_lookup(collected_values):
    domain = collected_values.get("domain")
    return _DOMAIN_ACCOUNTS.get(domain)


def _test_regions_provider():
    return ["eu-west-1", "us-east-1", "ap-southeast-1"]


def _test_default_region(collected_values):
    # Platform domain always uses eu-west-1, others get us-east-1
    domain = collected_values.get("domain", "")
    return "eu-west-1" if domain == "platform" else "us-east-1"


def _collect_with_providers(
    recipe_class,
    user_choices: dict[str, str],
    options_providers: dict,
    default_providers: dict,
):
    """Run the full chain with providers: parse → collect → nested dict.

    ``user_choices`` maps field name to the value the user would select/type.
    Fields not in ``user_choices`` accept the resolved default.
    """
    parser = FieldParser()
    fields = parser.from_recipe_model(recipe_class)

    handler = InteractiveHandler(
        options_providers=options_providers,
        default_providers=default_providers,
    )

    def fake_prompt(field, default):
        if field.name in user_choices:
            return user_choices[field.name]
        return default

    with patch.object(handler, "_prompt_field", side_effect=fake_prompt):
        collected = handler.collect_field_values(fields)

    assert collected is not None, "collection was cancelled"
    return parser.create_nested_dict(collected)


class TestProviderFieldContractEndToEnd(unittest.TestCase):
    """Full end-to-end tests for field providers through the contract chain.

    No mocking of FieldParser or InteractiveHandler internals — only the
    prompt method (simulating user input). Providers run as real callables.
    """

    def test_options_provider_populates_and_user_selects(self) -> None:
        """Domain field gets options from provider; user picks one."""
        result = _collect_with_providers(
            _ProviderRecipe,
            user_choices={"domain": "genomics"},
            options_providers={
                "test_domains": _test_domains_provider,
                "test_regions": _test_regions_provider,
            },
            default_providers={
                "test_account_lookup": _test_account_lookup,
                "test_default_region": _test_default_region,
            },
        )
        self.assertEqual(result["domain"], "genomics")

    def test_default_provider_resolves_from_earlier_field(self) -> None:
        """Account ID auto-resolves from the selected domain."""
        result = _collect_with_providers(
            _ProviderRecipe,
            user_choices={"domain": "analytics"},
            options_providers={
                "test_domains": _test_domains_provider,
                "test_regions": _test_regions_provider,
            },
            default_providers={
                "test_account_lookup": _test_account_lookup,
                "test_default_region": _test_default_region,
            },
        )
        self.assertEqual(result["account_id"], "111111111111")

    def test_default_provider_uses_domain_context(self) -> None:
        """Region default varies based on selected domain."""
        # Platform domain → eu-west-1
        result = _collect_with_providers(
            _ProviderRecipe,
            user_choices={"domain": "platform"},
            options_providers={
                "test_domains": _test_domains_provider,
                "test_regions": _test_regions_provider,
            },
            default_providers={
                "test_account_lookup": _test_account_lookup,
                "test_default_region": _test_default_region,
            },
        )
        self.assertEqual(result["region"], "eu-west-1")

        # Non-platform domain → us-east-1
        result = _collect_with_providers(
            _ProviderRecipe,
            user_choices={"domain": "genomics"},
            options_providers={
                "test_domains": _test_domains_provider,
                "test_regions": _test_regions_provider,
            },
            default_providers={
                "test_account_lookup": _test_account_lookup,
                "test_default_region": _test_default_region,
            },
        )
        self.assertEqual(result["region"], "us-east-1")

    def test_user_can_override_provider_default(self) -> None:
        """User-supplied value wins even when provider resolves a default."""
        result = _collect_with_providers(
            _ProviderRecipe,
            user_choices={"domain": "genomics", "account_id": "999999999999"},
            options_providers={
                "test_domains": _test_domains_provider,
                "test_regions": _test_regions_provider,
            },
            default_providers={
                "test_account_lookup": _test_account_lookup,
                "test_default_region": _test_default_region,
            },
        )
        self.assertEqual(result["account_id"], "999999999999")

    def test_constructed_model_accepts_provider_resolved_values(self) -> None:
        """Values resolved by providers pass pydantic validation on the model."""
        result = _collect_with_providers(
            _ProviderRecipe,
            user_choices={"domain": "platform"},
            options_providers={
                "test_domains": _test_domains_provider,
                "test_regions": _test_regions_provider,
            },
            default_providers={
                "test_account_lookup": _test_account_lookup,
                "test_default_region": _test_default_region,
            },
        )
        # This is the key assertion: pydantic accepts the resolved values
        recipe = _ProviderRecipe(**result)
        self.assertEqual(recipe.domain, "platform")
        self.assertEqual(recipe.account_id, "333333333333")
        self.assertEqual(recipe.region, "eu-west-1")

    def test_json_round_trip_preserves_provider_contract(self) -> None:
        """Fields survive JSON serialisation and providers still resolve.

        Simulates the Docker path without needing a real container.
        """
        import json

        parser = FieldParser()

        # Introspect → serialise (what a container would emit)
        fields_response = parser.from_recipe_model(_ProviderRecipe)
        json_str = json.dumps({"fields": [f.model_dump() for f in fields_response.fields]})

        # Parse back (what the host does)
        parsed = parser.parse_fields_output(json_str)

        # Resolve with providers
        handler = InteractiveHandler(
            options_providers={
                "test_domains": _test_domains_provider,
                "test_regions": _test_regions_provider,
            },
            default_providers={
                "test_account_lookup": _test_account_lookup,
                "test_default_region": _test_default_region,
            },
        )

        def fake_prompt(field, default):
            choices = {"domain": "analytics"}
            return choices.get(field.name, default)

        with patch.object(handler, "_prompt_field", side_effect=fake_prompt):
            collected = handler.collect_field_values(parsed)

        nested = parser.create_nested_dict(collected)
        recipe = _ProviderRecipe(**nested)
        self.assertEqual(recipe.domain, "analytics")
        self.assertEqual(recipe.account_id, "111111111111")
        self.assertEqual(recipe.region, "us-east-1")

    def test_missing_provider_degrades_gracefully(self) -> None:
        """Unregistered providers don't crash — fields get static defaults."""
        result = _collect_with_providers(
            _ProviderRecipe,
            user_choices={"domain": "typed-manually", "account_id": "typed-id"},
            options_providers={},  # No providers registered
            default_providers={},
        )
        # Values come from user input / static defaults
        self.assertEqual(result["domain"], "typed-manually")
        self.assertEqual(result["account_id"], "typed-id")
        self.assertEqual(result["region"], "eu-west-1")  # static default


if __name__ == "__main__":
    unittest.main()
