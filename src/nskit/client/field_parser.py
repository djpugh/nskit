"""Field parser for recipe field specifications."""
from __future__ import annotations

import json
from enum import Enum
from typing import Any, get_args, get_origin

from pydantic import BaseModel
from pydantic.fields import FieldInfo

from nskit.client.field_models import ConditionalRule, FieldSpec, FieldType, InputFieldsResponse

# Mapping from Python types to FieldType
_TYPE_MAP: dict[type, FieldType] = {
    str: FieldType.STR,
    int: FieldType.INT,
    float: FieldType.FLOAT,
    bool: FieldType.BOOL,
    list: FieldType.LIST,
    dict: FieldType.DICT,
}


class FieldParser:
    """Parses recipe field specifications.

    Can extract ``FieldSpec`` instances from:
    1. JSON output from Docker-based recipes (``parse_fields_output``)
    2. Pydantic Recipe model introspection (``from_recipe_model``)
    """

    def parse_fields_output(self, json_output: str) -> InputFieldsResponse:
        """Parse JSON field output from a Docker-based recipe.

        Args:
            json_output: JSON string containing field definitions.

        Returns:
            Parsed ``InputFieldsResponse`` with field specifications.

        Raises:
            ValueError: If the JSON is invalid or cannot be parsed.
        """
        try:
            data = json.loads(json_output)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON field output: {exc}") from exc

        if isinstance(data, dict):
            return InputFieldsResponse.model_validate(data)

        if isinstance(data, list):
            fields = [FieldSpec.model_validate(item) for item in data]
            return InputFieldsResponse(fields=fields)

        raise ValueError(f"Unexpected field output format: expected dict or list, got {type(data).__name__}")

    def create_nested_dict(self, flat_dict: dict[str, Any]) -> dict[str, Any]:
        """Convert a flat dictionary with dot-notation keys to a nested dictionary.

        Args:
            flat_dict: Dictionary with dot-separated keys
                (e.g. ``{"a.b.c": 1, "d": 2}``).

        Returns:
            Nested dictionary (e.g. ``{"a": {"b": {"c": 1}}, "d": 2}``).
        """
        result: dict[str, Any] = {}
        for key, value in flat_dict.items():
            parts = key.split(".")
            current = result
            for part in parts[:-1]:
                current = current.setdefault(part, {})
            current[parts[-1]] = value
        return result

    def get_field_prompt(self, field: FieldSpec) -> str:
        """Generate prompt text for a field.

        Args:
            field: Field specification.

        Returns:
            Prompt string for the field.
        """
        if field.prompt_text:
            return field.prompt_text
        if field.display_name:
            return f"{field.display_name}"
        return f"{field.name}"

    def from_recipe_model(
        self,
        recipe_class: type,
        include_base: bool = False,
    ) -> InputFieldsResponse:
        """Extract ``FieldSpec`` instances from a Pydantic Recipe subclass.

        Uses the model's ``model_fields`` to introspect field metadata and
        maps Pydantic ``FieldInfo`` attributes to ``FieldSpec`` attributes.

        Args:
            recipe_class: A Pydantic ``BaseModel`` subclass (typically a
                ``Recipe`` subclass).
            include_base: Whether to include base ``Recipe`` fields.

        Returns:
            ``InputFieldsResponse`` containing the extracted field specs.
        """
        from nskit.mixer.components.recipe import Recipe

        base_field_names: set[str] = set()
        if not include_base:
            base_field_names = set(Recipe.model_fields.keys())

        fields: list[FieldSpec] = []
        for name, field_info in recipe_class.model_fields.items():
            if name in base_field_names:
                continue
            if name.startswith("_"):
                continue

            field_spec = self._field_info_to_spec(name, field_info)
            fields.append(field_spec)

        return InputFieldsResponse(fields=fields)

    def _field_info_to_spec(self, name: str, field_info: FieldInfo) -> FieldSpec:
        """Convert a Pydantic FieldInfo to a FieldSpec."""
        field_type = self._resolve_field_type(field_info.annotation)
        extra = field_info.json_schema_extra or {}

        default = field_info.default
        if default is ...:
            default = None
            required = True
        else:
            required = default is None and field_info.is_required()

        options: list[str] | None = extra.get("options")
        if field_type == FieldType.STR and options:
            field_type = FieldType.ENUM

        conditional_rules_raw = extra.get("conditional_rules", [])
        conditional_rules = [ConditionalRule.model_validate(r) for r in conditional_rules_raw]

        return FieldSpec(
            name=name,
            type=field_type,
            required=required,
            default=default,
            description=field_info.description,
            prompt_text=extra.get("prompt_text"),
            env_var=extra.get("env_var"),
            template=extra.get("template"),
            options=options,
            conditional_rules=conditional_rules,
        )

    def _resolve_field_type(self, annotation: Any) -> FieldType:
        """Map a Python type annotation to a FieldType."""
        if annotation is None:
            return FieldType.STR

        origin = get_origin(annotation)
        if origin is not None:
            # Handle Optional[X] → unwrap to X
            args = get_args(annotation)
            non_none = [a for a in args if a is not type(None)]
            if non_none:
                return self._resolve_field_type(non_none[0])
            return FieldType.STR

        if isinstance(annotation, type):
            if issubclass(annotation, bool):
                return FieldType.BOOL
            if issubclass(annotation, Enum):
                return FieldType.ENUM
            if issubclass(annotation, BaseModel):
                return FieldType.OBJECT
            return _TYPE_MAP.get(annotation, FieldType.STR)

        return FieldType.STR
