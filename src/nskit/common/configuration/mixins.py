import inspect
from typing import Any, Callable, Dict, List

from pydantic import BaseModel, model_serializer, SerializationInfo
from pydantic_settings import BaseSettings


class PropertyDumpMixin:

    _excluded_properties: List[str] = []

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

    def __get_properties(self, include = None, exclude=None):
        # Avoid Circular Improts
        property_names = self.__get_defined_model_properties()
        included_properties = {}
        for property_name in property_names:
            if (include and property_name in include) or \
                (exclude and property_name not in exclude) or \
                (include is None and exclude is None and property_name not in self._excluded_properties):
                included_properties[property_name] = getattr(self, property_name)
        return included_properties
