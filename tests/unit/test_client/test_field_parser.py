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


if __name__ == "__main__":
    unittest.main()
