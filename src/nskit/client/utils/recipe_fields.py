from typing import get_args, get_origin

from pydantic import BaseModel


def get_required_fields_as_dict(model: BaseModel, prefix: str = "") -> dict[str, str]:
    """Get required fields from a Pydantic model, including functionally required fields.

    Functionally required fields are those with non-nullable type annotations (like str)
    but have None as default value, which causes Pydantic validation errors during
    instantiation even though field.is_required() returns False.

    Args:
        model: Pydantic model or model class to inspect
        prefix: Prefix for nested field names

    Returns:
        Dictionary mapping field names to type names
    """
    # Handle both instances and classes
    fields = model.model_fields

    required_fields = {}

    for field_name, field in fields.items():
        full_field_name = f"{prefix}{field_name}"

        # Check if field is explicitly required OR functionally required
        is_functionally_required = _is_functionally_required_field(field)

        if field.is_required() or is_functionally_required:
            # If the field is a submodel, recurse
            if isinstance(field.annotation, type) and issubclass(field.annotation, BaseModel):
                nested = get_required_fields_as_dict(field.annotation, prefix=full_field_name + ".")
                required_fields.update(nested)
            else:
                type_name = getattr(field.annotation, "__name__", str(field.annotation))
                required_fields[full_field_name] = type_name

    return required_fields


def _is_functionally_required_field(field) -> bool:
    """Check if a field is functionally required.

    A field is functionally required if:
    1. It has a default value of None
    2. Its type annotation is non-nullable (doesn't include None/Optional)

    This catches cases like: name: str = Field(None, ...) where the field
    will fail validation if instantiated with None despite having a default.
    """
    # If field doesn't have a default or default is not None, not functionally required
    if not hasattr(field, "default") or field.default is not None:
        return False

    # Get the field's type annotation
    annotation = field.annotation

    # Handle Union types (like Optional[str] which is Union[str, None])
    origin = get_origin(annotation)
    if origin is not None:
        # For Union types, check if None is one of the args
        if hasattr(annotation, "__args__"):
            args = get_args(annotation)
            # If None/NoneType is in the union, it's nullable
            if type(None) in args or None in args:
                return False

    # Handle direct Optional types
    if hasattr(annotation, "__origin__") and annotation.__origin__ is type(None):
        return False

    # If we get here, it's a non-nullable type with None default - functionally required
    return True
