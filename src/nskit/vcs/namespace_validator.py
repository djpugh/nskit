import re
import sys
from typing import Dict, List, Optional, Union

from pydantic import Field, field_validator, ValidationInfo

from nskit.common.configuration import BaseConfiguration

if sys.version_info.minor >= 9:
    from typing import TypeAliasType
else:
    from typing_extensions import TypeAliasType

REPO_SEPARATOR = '-'
_DELIMITERS = ['.', ',', '-']

NamespaceOptionsType = TypeAliasType('NamespaceOptionsType', List[Union[str, Dict[str, 'NamespaceOptionsType']]])


class NamespaceValidator(BaseConfiguration):
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

    def to_parts(self, name):
        return re.split(self._delimiters_regexp, name)

    def to_repo_name(self, name):
        return self.repo_separator.join(self.to_parts(name))

    def validate_name(self, proposed_name):
        name_parts = self.to_parts(proposed_name)
        if self.options:
            return self._validate_level(name_parts, self.options)
        return True, 'no constraints set'

    def _validate_level(
            self,
            name_parts: List[str],
            partial_namespace: List[Union[str, Dict]]
        ):
        not_matched = []
        for key in partial_namespace:
            # If it is a dict, then there are mappings of <section>: [<subsection 1>, <subsection 2>]
            if isinstance(key, dict):
                for key, new_partial_namespace in key.items():
                    if key == name_parts[0]:
                        # This maps to a section with subsections, so we need to validate those
                        result, message = self._validate_level(name_parts[1:], new_partial_namespace)
                        if not result:
                            message = message.format(key=key)
                        return result, message
                    not_matched.append(key)
            # Otherwise it is a string
            elif key == name_parts[0]:
                return True, 'ok'
            else:
                not_matched.append(key)
        return False, f'Does not match valid names for {{key}}: {", ".join(not_matched)}'
