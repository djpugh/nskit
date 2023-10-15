"""Configuration Mixins."""
import inspect
from typing import Any, Callable

from pydantic import BaseModel, model_serializer, SerializationInfo
from pydantic_settings import BaseSettings


class PropertyDumpMixin:
    """Mixin to dump properties when doing model_dump."""

    def model_post_init(self, __context: Any):
        """Make sure excluded properties is created."""
        if not hasattr(self, '_excluded_properties') or self._excluded_properties is None:
            self._excluded_properties = []
        super().model_post_init(__context)

    @model_serializer(mode='wrap')
    def _property_dump(self, handler: Callable, info: SerializationInfo):
        value = handler(self)
        # Add properties if they are included/excluded
        value.update(self.__get_properties(info.include, info.exclude))
        return value

    def __get_defined_model_properties(self):

        properties = inspect.getmembers(self.__class__, lambda o: isinstance(o, property))
        # Based on object -> BaseModel -> BaseSettings
        standard_settings_properties = inspect.getmembers(BaseSettings, lambda o: isinstance(o, property))
        standard_model_properties = inspect.getmembers(BaseModel, lambda o: isinstance(o, property))
        property_names = [u[0] for u in properties if u not in standard_settings_properties+standard_model_properties and not u[0].startswith('_')]
        return property_names

    def __get_properties(self, include=None, exclude=None):
        property_names = self.__get_defined_model_properties()
        included_properties = {}
        if not hasattr(self, '_excluded_properties') or self._excluded_properties is None:
            self._excluded_properties = []
        for property_name in property_names:
            if (include and property_name in include) or \
              (exclude and property_name not in exclude and property_name not in self._excluded_properties) or \
              (include is None and exclude is None and property_name not in self._excluded_properties):
                included_properties[property_name] = getattr(self, property_name)
        return included_properties
