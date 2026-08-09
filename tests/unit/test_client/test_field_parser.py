"""Unit tests for FieldParser."""

from __future__ import annotations

import json
import unittest

from nskit.client.field_models import FieldSpec, FieldType, InputFieldsResponse
from nskit.client.field_parser import FieldParser


class TestFieldParserParseFieldsOutput(unittest.TestCase):
    """Tests for FieldParser.parse_fields_output."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.parser = FieldParser()

    def test_parse_dict_format(self) -> None:
        """Parses a dict-format JSON with fields and metadata."""
        data = {
            "fields": [
                {"name": "project_name", "type": "str", "required": True},
                {"name": "use_docker", "type": "bool", "default": False},
            ],
            "metadata": {"version": "1.0"},
        }
        result = self.parser.parse_fields_output(json.dumps(data))
        self.assertIsInstance(result, InputFieldsResponse)
        self.assertEqual(len(result.fields), 2)
        self.assertEqual(result.fields[0].name, "project_name")
        self.assertEqual(result.fields[1].type, FieldType.BOOL)
        self.assertEqual(result.metadata["version"], "1.0")

    def test_parse_list_format(self) -> None:
        """Parses a list-format JSON of field dicts."""
        data = [{"name": "name", "type": "str"}]
        result = self.parser.parse_fields_output(json.dumps(data))
        self.assertEqual(len(result.fields), 1)
        self.assertEqual(result.fields[0].name, "name")

    def test_parse_invalid_json_raises(self) -> None:
        """Raises ValueError on invalid JSON."""
        with self.assertRaises(ValueError):
            self.parser.parse_fields_output("{not valid json")

    def test_parse_unexpected_format_raises(self) -> None:
        """Raises ValueError on unexpected top-level type."""
        with self.assertRaises(ValueError):
            self.parser.parse_fields_output('"just a string"')


class TestFieldParserCreateNestedDict(unittest.TestCase):
    """Tests for FieldParser.create_nested_dict."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.parser = FieldParser()

    def test_simple_keys(self) -> None:
        """Non-dotted keys remain at top level."""
        result = self.parser.create_nested_dict({"a": 1, "b": 2})
        self.assertEqual(result, {"a": 1, "b": 2})

    def test_dotted_keys(self) -> None:
        """Dotted keys are converted to nested dicts."""
        result = self.parser.create_nested_dict({"a.b.c": 1, "d": 2})
        self.assertEqual(result, {"a": {"b": {"c": 1}}, "d": 2})

    def test_shared_prefix(self) -> None:
        """Keys sharing a prefix merge into the same nested dict."""
        result = self.parser.create_nested_dict({"a.b": 1, "a.c": 2})
        self.assertEqual(result, {"a": {"b": 1, "c": 2}})

    def test_empty_dict(self) -> None:
        """Empty input returns empty dict."""
        self.assertEqual(self.parser.create_nested_dict({}), {})

    def test_deeply_nested(self) -> None:
        """Four-level dotted key produces four-level nesting."""
        result = self.parser.create_nested_dict({"a.b.c.d": 42})
        self.assertEqual(result, {"a": {"b": {"c": {"d": 42}}}})

    def test_mixed_dotted_and_flat(self) -> None:
        """Flat and dotted keys coexist correctly."""
        result = self.parser.create_nested_dict({"x": 1, "a.b": 2, "a.c.d": 3})
        self.assertEqual(result, {"x": 1, "a": {"b": 2, "c": {"d": 3}}})


class TestFieldParserGetFieldPrompt(unittest.TestCase):
    """Tests for FieldParser.get_field_prompt."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.parser = FieldParser()

    def test_prompt_text_takes_priority(self) -> None:
        """prompt_text is returned when set."""
        field = FieldSpec(name="x", prompt_text="Enter X")
        self.assertEqual(self.parser.get_field_prompt(field), "Enter X")

    def test_display_name_fallback(self) -> None:
        """display_name is used when prompt_text is absent."""
        field = FieldSpec(name="x", display_name="Project X")
        self.assertEqual(self.parser.get_field_prompt(field), "Project X")

    def test_name_fallback(self) -> None:
        """Field name is used as last resort."""
        field = FieldSpec(name="project_name")
        self.assertEqual(self.parser.get_field_prompt(field), "project_name")


class TestFieldParserFromRecipeModel(unittest.TestCase):
    """Tests for FieldParser.from_recipe_model."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        from typing import Literal, Optional

        from pydantic import BaseModel, Field

        self.parser = FieldParser()

        class Repository(BaseModel):
            codeowner_name: str = Field(..., json_schema_extra={"display_name": "Owner"})
            description: str = ""

        class Model(BaseModel):
            name: str = "default-name"
            mandatory: str = Field(...)
            optional: Optional[str] = None
            repository: Repository = Field(...)
            maybe_repo: Optional[Repository] = None
            pinned: Literal[True] = True
            choice: Literal["a", "b"] = "a"
            explicitly_hidden: str = Field("x", json_schema_extra={"hidden": True})

        self.Model = Model

    def _specs(self, **kwargs) -> dict:
        return {f.name: f for f in self.parser.from_recipe_model(self.Model, **kwargs).fields}

    def test_field_with_ellipsis_default_is_required(self) -> None:
        """``Field(...)`` is reported required.

        Regression test: deriving ``required`` from ``default is None`` reported
        ``False`` here, because ``Field(...)`` leaves the default as
        ``PydanticUndefined`` rather than ``None``.
        """
        self.assertTrue(self._specs()["mandatory"].required)

    def test_optional_field_is_not_required(self) -> None:
        """A field with a default is not required."""
        specs = self._specs()
        self.assertFalse(specs["optional"].required)
        self.assertFalse(specs["name"].required)

    def test_default_is_reported_for_optional_fields(self) -> None:
        """Optional fields carry their default; required fields do not."""
        specs = self._specs()
        self.assertEqual(specs["name"].default, "default-name")
        self.assertIsNone(specs["mandatory"].default)

    def test_nested_models_emit_dotted_leaves(self) -> None:
        """Nested BaseModel fields are walked into dot-notation leaves."""
        specs = self._specs()
        self.assertIn("repository.codeowner_name", specs)
        self.assertIn("repository.description", specs)
        self.assertNotIn("repository", specs)

    def test_nested_leaf_keeps_its_metadata(self) -> None:
        """Metadata on a nested leaf survives the walk."""
        self.assertEqual(self._specs()["repository.codeowner_name"].display_name, "Owner")

    def test_optional_nested_model_recurses(self) -> None:
        """``Optional[Model]`` is unwrapped and still recursed."""
        self.assertIn("maybe_repo.codeowner_name", self._specs())

    def test_dotted_leaves_round_trip_through_create_nested_dict(self) -> None:
        """Emitted dotted names rebuild the nested shape."""
        values = {"repository.codeowner_name": "Jo", "repository.description": "d"}
        self.assertEqual(
            self.parser.create_nested_dict(values),
            {"repository": {"codeowner_name": "Jo", "description": "d"}},
        )

    def test_recurse_nested_false_emits_object(self) -> None:
        """Opting out emits the nested model as a single OBJECT field."""
        specs = self._specs(recurse_nested=False)
        self.assertIn("repository", specs)
        self.assertEqual(specs["repository"].type, FieldType.OBJECT)
        self.assertNotIn("repository.codeowner_name", specs)

    def test_name_is_kept_when_base_fields_excluded(self) -> None:
        """``name`` survives ``include_base=False`` because users supply it."""
        self.assertIn("name", self._specs())

    def test_exclude_drops_named_fields(self) -> None:
        """``exclude`` removes top-level fields."""
        self.assertNotIn("name", self._specs(exclude={"name"}))

    def test_single_valued_literal_is_enum_and_hidden(self) -> None:
        """``Literal[True]`` is a pinned value: ENUM, one option, hidden."""
        spec = self._specs()["pinned"]
        self.assertEqual(spec.type, FieldType.ENUM)
        self.assertEqual(spec.options, ["True"])
        self.assertTrue(spec.hidden)

    def test_multi_valued_literal_is_enum_and_prompted(self) -> None:
        """A multi-member Literal is a real choice, so it is not hidden."""
        spec = self._specs()["choice"]
        self.assertEqual(spec.type, FieldType.ENUM)
        self.assertEqual(spec.options, ["a", "b"])
        self.assertFalse(spec.hidden)

    def test_explicit_hidden_metadata_is_honoured(self) -> None:
        """``json_schema_extra={"hidden": True}`` hides a field."""
        self.assertTrue(self._specs()["explicitly_hidden"].hidden)

    def test_ordinary_fields_are_not_hidden(self) -> None:
        """Fields without a pin or a hidden flag are prompted."""
        self.assertFalse(self._specs()["mandatory"].hidden)

    def test_list_of_models_is_not_flattened(self) -> None:
        """``list[Model]`` is not treated as a nested model.

        Regression test: any single-argument generic used to be unwrapped, so
        ``list[Leaf]`` emitted ``items.value`` — losing the fact that it is a
        sequence, which dot-notation cannot express.
        """
        from pydantic import BaseModel

        class Leaf(BaseModel):
            value: str = ""

        class WithList(BaseModel):
            items: list[Leaf] = []

        names = {f.name for f in self.parser.from_recipe_model(WithList).fields}
        self.assertIn("items", names)
        self.assertNotIn("items.value", names)

    def test_deeply_nested_models_flatten_fully(self) -> None:
        """Recursion continues through more than one level of nesting."""
        from pydantic import BaseModel

        class Leaf(BaseModel):
            value: str = ""

        class Mid(BaseModel):
            leaf: Leaf = Leaf()

        class Top(BaseModel):
            mid: Mid = Mid()

        names = {f.name for f in self.parser.from_recipe_model(Top).fields}
        self.assertEqual(names, {"mid.leaf.value"})

    def test_enum_field_reports_its_members_as_options(self) -> None:
        """An Enum field surfaces its choices.

        Regression test: enum fields were reported as ENUM with ``options=None``,
        which tells a prompting UI nothing about what to offer.
        """
        from enum import Enum

        from pydantic import BaseModel

        class Colour(str, Enum):
            red = "red"
            blue = "blue"

        class WithEnum(BaseModel):
            colour: Colour = Colour.red

        spec = next(f for f in self.parser.from_recipe_model(WithEnum).fields)
        self.assertEqual(spec.type, FieldType.ENUM)
        self.assertEqual(spec.options, ["red", "blue"])

    def test_optional_enum_reports_options(self) -> None:
        """``Optional[Enum]`` still surfaces its choices."""
        from enum import Enum
        from typing import Optional

        from pydantic import BaseModel

        class Colour(str, Enum):
            red = "red"

        class WithOptionalEnum(BaseModel):
            colour: Optional[Colour] = None

        spec = next(f for f in self.parser.from_recipe_model(WithOptionalEnum).fields)
        self.assertEqual(spec.options, ["red"])

    def test_explicit_options_override_inferred_ones(self) -> None:
        """A field's own declared options win over inference."""
        from enum import Enum

        from pydantic import BaseModel, Field

        class Colour(str, Enum):
            red = "red"
            blue = "blue"

        class WithOverride(BaseModel):
            colour: Colour = Field(Colour.red, json_schema_extra={"options": ["red"]})

        spec = next(f for f in self.parser.from_recipe_model(WithOverride).fields)
        self.assertEqual(spec.options, ["red"])


class TestFieldParserProviderJsonRoundTrip(unittest.TestCase):
    """Tests that provider names survive JSON serialisation (the Docker path).

    When a recipe runs in Docker, the container returns FieldSpec as JSON.
    The host parses it via parse_fields_output. Provider names must survive
    this round-trip.
    """

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.parser = FieldParser()

    def test_options_provider_survives_json_round_trip(self) -> None:
        """options_provider serialises to JSON and deserialises back."""
        spec = FieldSpec(
            name="domain",
            type=FieldType.STR,
            options_provider="org_domains",
            default="fallback",
        )
        json_str = json.dumps({"fields": [spec.model_dump()]})
        parsed = self.parser.parse_fields_output(json_str)
        self.assertEqual(parsed.fields[0].options_provider, "org_domains")

    def test_default_provider_survives_json_round_trip(self) -> None:
        """default_provider serialises to JSON and deserialises back."""
        spec = FieldSpec(
            name="account_id",
            type=FieldType.STR,
            default_provider="resolve_account",
        )
        json_str = json.dumps({"fields": [spec.model_dump()]})
        parsed = self.parser.parse_fields_output(json_str)
        self.assertEqual(parsed.fields[0].default_provider, "resolve_account")

    def test_both_providers_survive_round_trip(self) -> None:
        """A field can have both providers and they both survive serialisation."""
        spec = FieldSpec(
            name="x",
            type=FieldType.STR,
            options_provider="opts",
            default_provider="dflt",
        )
        json_str = json.dumps({"fields": [spec.model_dump()]})
        parsed = self.parser.parse_fields_output(json_str)
        self.assertEqual(parsed.fields[0].options_provider, "opts")
        self.assertEqual(parsed.fields[0].default_provider, "dflt")

    def test_full_docker_simulation(self) -> None:
        """Simulate full Docker path: recipe model -> JSON -> parse -> handler resolves.

        This is the real integration test: a recipe class is introspected by
        FieldParser, the resulting FieldSpecs are serialised to JSON (as a Docker
        container would emit), parsed back by the host, then fed to an
        InteractiveHandler with registered providers.
        """
        from unittest.mock import patch

        from pydantic import BaseModel, Field

        from nskit.client.interactive import InteractiveHandler

        # 1. Define a recipe-like model
        class FakeRecipe(BaseModel):
            name: str = "test-project"
            region: str = Field("", json_schema_extra={"options_provider": "regions"})
            vpc_id: str = Field("", json_schema_extra={"default_provider": "vpc_for_region"})

        # 2. Recipe side: introspect to FieldSpecs
        fields_response = self.parser.from_recipe_model(FakeRecipe)

        # 3. Simulate Docker serialisation round-trip
        json_str = json.dumps({"fields": [f.model_dump() for f in fields_response.fields]})
        parsed = self.parser.parse_fields_output(json_str)

        # 4. Host side: handler with providers resolves everything
        handler = InteractiveHandler(
            options_providers={"regions": lambda: ["eu-west-1", "us-east-1"]},
            default_providers={"vpc_for_region": lambda cv: f"vpc-{cv.get('region', '?')}"},
        )

        with (
            patch.object(handler, "_prompt_choice_field", return_value="eu-west-1"),
            patch.object(handler, "_prompt_str_field", side_effect=lambda f, d: d),
        ):
            result = handler.collect_field_values(parsed)

        self.assertEqual(result["name"], "test-project")
        self.assertEqual(result["region"], "eu-west-1")
        self.assertEqual(result["vpc_id"], "vpc-eu-west-1")


class TestFieldParserResolveFieldType(unittest.TestCase):
    """Tests for FieldParser._resolve_field_type."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.parser = FieldParser()

    def test_none_annotation(self) -> None:
        """None annotation defaults to STR."""
        self.assertEqual(self.parser._resolve_field_type(None), FieldType.STR)

    def test_optional_unwraps(self) -> None:
        """Optional[X] unwraps to the inner type."""
        from typing import Optional

        self.assertEqual(self.parser._resolve_field_type(Optional[int]), FieldType.INT)

    def test_enum_subclass(self) -> None:
        """Enum subclass maps to ENUM."""
        from enum import Enum

        class Colour(Enum):
            RED = "red"

        self.assertEqual(self.parser._resolve_field_type(Colour), FieldType.ENUM)

    def test_basemodel_subclass(self) -> None:
        """BaseModel subclass maps to OBJECT."""
        from pydantic import BaseModel

        class Nested(BaseModel):
            x: int = 0

        self.assertEqual(self.parser._resolve_field_type(Nested), FieldType.OBJECT)

    def test_unknown_type_defaults_to_str(self) -> None:
        """Unmapped type falls back to STR."""
        self.assertEqual(self.parser._resolve_field_type(bytes), FieldType.STR)

    def test_bool_maps_to_bool(self) -> None:
        """bool maps to BOOL rather than being caught by the int mapping."""
        self.assertEqual(self.parser._resolve_field_type(bool), FieldType.BOOL)

    def test_literal_maps_to_enum(self) -> None:
        """A Literal is a closed value set, so ENUM."""
        from typing import Literal

        self.assertEqual(self.parser._resolve_field_type(Literal["a", "b"]), FieldType.ENUM)

    def test_bare_union_without_args_defaults_to_str(self) -> None:
        """A generic that unwraps to nothing usable falls back to STR."""
        from typing import Optional

        self.assertEqual(self.parser._resolve_field_type(Optional[None]), FieldType.STR)

    def test_nested_model_returns_none_for_containers(self) -> None:
        """Only unions unwrap; containers are not nested models."""
        from typing import Optional

        from pydantic import BaseModel

        class Inner(BaseModel):
            x: int = 0

        self.assertIs(self.parser._nested_model(Inner), Inner)
        self.assertIs(self.parser._nested_model(Optional[Inner]), Inner)
        self.assertIsNone(self.parser._nested_model(list[Inner]))
        self.assertIsNone(self.parser._nested_model(dict[str, Inner]))
        self.assertIsNone(self.parser._nested_model(str))


class TestFieldParserProviderExtraction(unittest.TestCase):
    """Tests for FieldParser extracting options_provider and default_provider."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.parser = FieldParser()

    def test_options_provider_extracted_from_json_schema_extra(self) -> None:
        """options_provider declared via json_schema_extra appears in FieldSpec."""
        from pydantic import BaseModel, Field

        class WithOptionsProvider(BaseModel):
            domain: str = Field(
                "default",
                json_schema_extra={"options_provider": "org_domains"},
            )

        spec = next(f for f in self.parser.from_recipe_model(WithOptionsProvider).fields)
        self.assertEqual(spec.options_provider, "org_domains")

    def test_default_provider_extracted_from_json_schema_extra(self) -> None:
        """default_provider declared via json_schema_extra appears in FieldSpec."""
        from pydantic import BaseModel, Field

        class WithDefaultProvider(BaseModel):
            account_id: str = Field(
                "",
                json_schema_extra={"default_provider": "lookup_account"},
            )

        spec = next(f for f in self.parser.from_recipe_model(WithDefaultProvider).fields)
        self.assertEqual(spec.default_provider, "lookup_account")

    def test_both_providers_on_same_field(self) -> None:
        """A field can declare both options_provider and default_provider."""
        from pydantic import BaseModel, Field

        class WithBoth(BaseModel):
            thing: str = Field(
                "",
                json_schema_extra={
                    "options_provider": "list_things",
                    "default_provider": "best_thing",
                },
            )

        spec = next(f for f in self.parser.from_recipe_model(WithBoth).fields)
        self.assertEqual(spec.options_provider, "list_things")
        self.assertEqual(spec.default_provider, "best_thing")

    def test_no_provider_fields_are_none(self) -> None:
        """Fields without providers have None for both provider attributes."""
        from pydantic import BaseModel

        class Plain(BaseModel):
            name: str = "x"

        spec = next(f for f in self.parser.from_recipe_model(Plain).fields)
        self.assertIsNone(spec.options_provider)
        self.assertIsNone(spec.default_provider)

    def test_providers_survive_json_round_trip(self) -> None:
        """Provider names serialise to JSON and deserialise back correctly."""
        from pydantic import BaseModel, Field

        class WithProvider(BaseModel):
            domain: str = Field(
                "default",
                json_schema_extra={"options_provider": "org_domains"},
            )

        original = self.parser.from_recipe_model(WithProvider)
        json_str = original.model_dump_json()
        restored = self.parser.parse_fields_output(json_str)
        self.assertEqual(restored.fields[0].options_provider, "org_domains")

    def test_recipe_field_helper_passes_providers(self) -> None:
        """RecipeField() convenience function passes providers through."""
        from pydantic import BaseModel

        from nskit.mixer.components.recipe import RecipeField

        class WithRecipeField(BaseModel):
            domain: str = RecipeField(
                "default",
                options_provider="org_domains",
                default_provider="best_domain",
            )

        spec = next(f for f in self.parser.from_recipe_model(WithRecipeField).fields)
        self.assertEqual(spec.options_provider, "org_domains")
        self.assertEqual(spec.default_provider, "best_domain")


if __name__ == "__main__":
    unittest.main()
