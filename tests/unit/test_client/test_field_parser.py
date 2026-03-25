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


if __name__ == "__main__":
    unittest.main()
