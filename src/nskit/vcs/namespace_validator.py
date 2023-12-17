"""Namespace Validator for validating if a name is in a namespace."""
from enum import Enum
import re
import sys
from typing import Dict, List, Optional, Union

from pydantic import field_validator, ValidationInfo

from nskit.common.configuration import BaseConfiguration

if sys.version_info.major <= 3 and sys.version_info.minor <= 11:
    from typing_extensions import TypeAliasType
else:
    from typing import TypeAliasType

REPO_SEPARATOR = '-'
_DELIMITERS = ['.', ',', '-']

NamespaceOptionsType = TypeAliasType('NamespaceOptionsType', List[Union[str, Dict[str, 'NamespaceOptionsType']]])


class ValidationEnum(Enum):
    """Enum for validation level."""
    strict = 2
    warn = 1
    none = 0


class NamespaceValidator(BaseConfiguration):
    """Namespace Validator object."""
    options: Optional[NamespaceOptionsType]
    repo_separator: str = REPO_SEPARATOR
    delimiters: List[str] = _DELIMITERS

    __delimiters_regexp = None
    # Validate delimiters to add repo_separator

    @field_validator('delimiters', mode='after')
    @classmethod
    def _validate_repo_separator_in_delimiters(cls, v: List[str], info: ValidationInfo):
        if info.data['repo_separator'] not in v:
            v.append(info.data['repo_separator'])
        return v

    @property
    def _delimiters_regexp(self):
        if self.__delimiters_regexp is None:
            self.__delimiters_regexp = '|'.join(map(re.escape, self.delimiters))
        return self.__delimiters_regexp

    def to_parts(self, name: str):
        """Break the name into the namespace parts."""
        if self.options:
            return re.split(self._delimiters_regexp, name)
        return [name]

    def to_repo_name(self, name: str):
        """Convert the name to the appropriate name with a given repo separator."""
        return self.repo_separator.join(self.to_parts(name))

    def validate_name(self, proposed_name: str):
        """Validate a proposed name."""
        name_parts = self.to_parts(proposed_name)
        if self.options:
            result, message = self._validate_level(name_parts, self.options)
            message = message.format(key='<root>')
        else:
            result = True
            message = 'no constraints set'
        return result, message

    def _validate_level(
            self,
            name_parts: List[str],
            partial_namespace: List[Union[str, Dict]]):
        not_matched = []
        for key in partial_namespace:
            # If it is a dict, then there are mappings of <section>: [<subsection 1>, <subsection 2>]
            if isinstance(key, dict):
                for sub_key, new_partial_namespace in key.items():
                    if sub_key == name_parts[0]:
                        # This maps to a section with subsections, so we need to validate those
                        result, message = self._validate_level(name_parts[1:], new_partial_namespace)
                        if not result:
                            message = message.format(key=sub_key)
                        return result, message
                    not_matched.append(sub_key)
            # Otherwise it is a string
            elif key == name_parts[0]:
                return True, 'ok'
            else:
                not_matched.append(key)
        return False, f'Does not match valid names for {{key}}: {", ".join(not_matched)}, with delimiters: {self.delimiters}'
