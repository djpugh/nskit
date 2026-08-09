"""Field parser for recipe field specifications."""

from __future__ import annotations

import json
import types
from enum import Enum
from typing import Any, Literal, Optional, Union, get_args, get_origin

from pydantic import BaseModel
from pydantic.fields import FieldInfo

from nskit.client.field_models import ConditionalRule, FieldSpec, FieldType, InputFieldsResponse

# Origins that represent a union, so ``Optional[X]`` can be told apart from a
# container like ``list[X]``. ``types.UnionType`` covers the PEP 604 ``X | None``
# spelling and only exists from 3.10.
_UNION_ORIGINS: set[Any] = {Union}
if hasattr(types, "UnionType"):  # pragma: no cover - version dependent
    _UNION_ORIGINS.add(types.UnionType)

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
        recurse_nested: bool = True,
        exclude: Optional[set[str]] = None,
    ) -> InputFieldsResponse:
        """Extract ``FieldSpec`` instances from a Pydantic Recipe subclass.

        Uses the model's ``model_fields`` to introspect field metadata and
        maps Pydantic ``FieldInfo`` attributes to ``FieldSpec`` attributes.

        Nested ``BaseModel`` fields are walked by default and emitted as
        dot-notation leaves (``repository.codeowner_email``), which is the
        inverse of :meth:`create_nested_dict` — so collected values can be fed
        straight back through it to rebuild the nested input structure.

        Args:
            recipe_class: A Pydantic ``BaseModel`` subclass (typically a
                ``Recipe`` subclass).
            include_base: Whether to include base ``Recipe`` fields. Note that
                ``name`` is *not* treated as a base field even when this is
                ``False``, because it is user-supplied on every recipe; pass it
                in ``exclude`` to drop it.
            recurse_nested: Walk nested ``BaseModel`` fields and emit their
                leaves with dotted names. When ``False`` a nested model is
                emitted as a single ``OBJECT`` field.
            exclude: Field names to skip, in addition to the base fields.
                Matched against the top-level field name.

        Returns:
            ``InputFieldsResponse`` containing the extracted field specs.
        """
        from nskit.mixer.components.recipe import Recipe

        base_field_names: set[str] = set()
        if not include_base:
            # ``name`` lives on the base Recipe but is genuinely user-supplied,
            # so it is kept even when base fields are excluded.
            base_field_names = set(Recipe.model_fields.keys()) - {"name"}
        base_field_names |= exclude or set()

        fields = self._extract(
            recipe_class,
            prefix="",
            skip=base_field_names,
            recurse_nested=recurse_nested,
        )
        return InputFieldsResponse(fields=fields)

    def _extract(
        self,
        model_class: type,
        prefix: str,
        skip: set[str],
        recurse_nested: bool,
    ) -> list[FieldSpec]:
        """Recursively build ``FieldSpec``s for ``model_class``."""
        fields: list[FieldSpec] = []
        for name, field_info in model_class.model_fields.items():
            if name in skip or name.startswith("_"):
                continue
            full_name = f"{prefix}{name}"

            nested = self._nested_model(field_info.annotation)
            if recurse_nested and nested is not None:
                fields.extend(
                    self._extract(
                        nested,
                        prefix=f"{full_name}.",
                        # ``skip`` only applies to top-level names.
                        skip=set(),
                        recurse_nested=recurse_nested,
                    )
                )
                continue

            fields.append(self._field_info_to_spec(full_name, field_info))
        return fields

    @staticmethod
    def _nested_model(annotation: Any) -> Optional[type]:
        """Return the ``BaseModel`` subclass for ``annotation``, else ``None``.

        Unwraps ``Optional[Model]`` / ``Model | None`` so an optional nested
        model still recurses. Only *unions* are unwrapped: a container such as
        ``list[Model]`` is deliberately not treated as a nested model, because a
        list cannot be represented as dot-notation leaves — flattening it would
        emit ``items.value`` and silently lose the fact that it is a sequence.
        """
        candidate = annotation
        origin = get_origin(annotation)
        if origin is not None:
            if origin not in _UNION_ORIGINS:
                return None
            args = [a for a in get_args(annotation) if a is not type(None)]
            if len(args) != 1:
                return None
            candidate = args[0]
        if isinstance(candidate, type) and issubclass(candidate, BaseModel):
            return candidate
        return None

    def _field_info_to_spec(self, name: str, field_info: FieldInfo) -> FieldSpec:
        """Convert a Pydantic FieldInfo to a FieldSpec."""
        field_type = self._resolve_field_type(field_info.annotation)
        extra = field_info.json_schema_extra or {}

        # ``is_required()`` is pydantic's own answer and already accounts for
        # PydanticUndefined defaults, ``Field(...)`` and default factories.
        # Deriving it from ``default is None`` instead under-reports required
        # fields, because ``Field(...)`` leaves the default as
        # ``PydanticUndefined`` rather than ``None``.
        required = field_info.is_required()
        default = None if required else field_info.default
        if default is ...:
            default = None

        options: list[str] | None = extra.get("options")
        # A Literal or Enum annotation is a closed set of values, so surface its
        # members as the available options unless the field declares its own.
        # Without this an enum field is reported as ENUM with no choices, which
        # tells a prompting UI nothing.
        if options is None:
            options = self._literal_options(field_info.annotation) or self._enum_options(field_info.annotation)
        if options and field_type in (FieldType.STR, FieldType.BOOL):
            field_type = FieldType.ENUM

        conditional_rules_raw = extra.get("conditional_rules", [])
        conditional_rules = [ConditionalRule.model_validate(r) for r in conditional_rules_raw]

        return FieldSpec(
            name=name,
            type=field_type,
            required=required,
            default=default,
            display_name=extra.get("display_name"),
            description=field_info.description,
            help_text=extra.get("help_text"),
            prompt_text=extra.get("prompt_text"),
            env_var=extra.get("env_var"),
            template=extra.get("template"),
            options=options,
            options_provider=extra.get("options_provider"),
            default_provider=extra.get("default_provider"),
            conditional_rules=conditional_rules,
            # A single-valued Literal is pinned by the model, so there is
            # nothing to ask; treat it as hidden unless declared otherwise.
            hidden=bool(extra.get("hidden", self._is_pinned(field_info.annotation))),
        )

    @staticmethod
    def _literal_options(annotation: Any) -> Optional[list[str]]:
        """Return a ``Literal``'s members as strings, else ``None``.

        Unwraps ``Optional[Literal[...]]`` so an optional literal is covered.
        """
        candidates = [annotation]
        if get_origin(annotation) is not None and get_origin(annotation) is not Literal:
            candidates = [a for a in get_args(annotation) if a is not type(None)]
        for candidate in candidates:
            if get_origin(candidate) is Literal:
                return [str(value) for value in get_args(candidate)]
        return None

    @staticmethod
    def _enum_options(annotation: Any) -> Optional[list[str]]:
        """Return an ``Enum``'s member values as strings, else ``None``.

        Unwraps ``Optional[Enum]`` so an optional enum still reports its choices.
        """
        candidates = [annotation]
        if get_origin(annotation) in _UNION_ORIGINS:
            candidates = [a for a in get_args(annotation) if a is not type(None)]
        for candidate in candidates:
            if isinstance(candidate, type) and issubclass(candidate, Enum):
                return [str(member.value) for member in candidate]
        return None

    @classmethod
    def _is_pinned(cls, annotation: Any) -> bool:
        """True when the annotation admits exactly one value (``Literal[x]``)."""
        options = cls._literal_options(annotation)
        return options is not None and len(options) == 1

    def _resolve_field_type(self, annotation: Any) -> FieldType:
        """Map a Python type annotation to a FieldType."""
        if annotation is None:
            return FieldType.STR

        origin = get_origin(annotation)
        if origin is Literal:
            # A Literal is a closed set of values, i.e. an enumeration. Its
            # members are values rather than types, so resolving the first arg
            # as a type would fall through to STR.
            return FieldType.ENUM
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
