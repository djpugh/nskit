"""License file handler."""
from datetime import date
from enum import Enum
from functools import lru_cache
from pathlib import Path
import sys
from typing import Any, Callable, Dict, Optional, Union

from ghapi.all import GhApi
from pydantic import Field

from nskit.mixer.components.file import File
from nskit.mixer.components.filesystem_object import TemplateStr
from nskit.mixer.utilities import Resource


class LicenseOptionsEnum(Enum):
    """License Options for the license file.

    Built from Github API licenses.get_all_commonly_used.
    """
    AGPL_3_0 = 'agpl-3.0'
    Apache_2_0 = 'apache-2.0'
    BSD_2_Clause = 'bsd-2-clause'
    BSD_3_Clause = 'bsd-3-clause'
    BSL_1_0 = 'bsl-1.0'
    CC0_1_0 = 'cc0-1.0'
    EPL_2_0 = 'epl-2.0'
    GPL_2_0 = 'gpl-2.0'
    GPL_3_0 = 'gpl-3.0'
    LGPL_2_1 = 'lgpl-2.1'
    MIT = 'mit'
    MPL_2_0 = 'mpl-2.0'
    Unlicense = 'unlicense'

    @classmethod
    def contains(cls, value):
        """Return True if `value` is in `cls`.

        BACKPORT FROM PYTHON 3.12

        `value` is in `cls` if:
        1) `value` is a member of `cls`, or
        2) `value` is the value of one of the `cls`'s members.
        """
        if sys.version_info.major <= 3 and sys.version_info.minor < 12:
            if isinstance(value, cls):
                return True
            try:
                return value in cls._value2member_map_
            except TypeError:
                return value in cls._unhashable_values_
        return value in cls


def get_license_filename(context: Optional[Dict[str, Any]] = None):
    """Callable to set the default license file name."""
    # Can't do in LicenseOptionsEnum pre 3.12
    if LicenseOptionsEnum.contains(context.get('license', None)):
        # Handle naming
        license_name = LicenseOptionsEnum(context.get('license', None))
        # COPYING
        if license_name in [
            LicenseOptionsEnum.AGPL_3_0,
            LicenseOptionsEnum.GPL_2_0,
            LicenseOptionsEnum.GPL_3_0,
        ]:
            name = 'COPYING'
        # COPYING.LESSER
        elif license_name in [
            LicenseOptionsEnum.LGPL_2_1,
        ]:
            name = 'COPYING.LESSER'
        # LICENSE
        elif license_name in [
            LicenseOptionsEnum.MIT,
            LicenseOptionsEnum.Apache_2_0,
            LicenseOptionsEnum.BSD_2_Clause,
            LicenseOptionsEnum.BSD_3_Clause,
            LicenseOptionsEnum.BSL_1_0,
            LicenseOptionsEnum.CC0_1_0,
            LicenseOptionsEnum.EPL_2_0,
            LicenseOptionsEnum.MIT,
            LicenseOptionsEnum.MPL_2_0
        ]:
            name = "LICENSE"
        # UNLICENSE
        elif license_name in [LicenseOptionsEnum.Unlicense]:
            name = 'UNLICENSE'
        return name


@lru_cache()
def _get_license_content(license: LicenseOptionsEnum):
    # Cache results as a static method to make testing etc. better on rates/rate limiting
    license_content = GhApi().licenses.get(license.value)
    return license_content


def get_license_content(context: Dict[str, Any]):
    """Render the content of the license."""
    # We implement some specifics based on the implementation instructions in Github licenses api get
    # Can't do in LicenseOptionsEnum pre 3.12
    if LicenseOptionsEnum.contains(context.get('license', None)):
        license_name = LicenseOptionsEnum(context.get('license', None))
        license_content = _get_license_content(license_name)
        content = license_content.body
        # [year] [fullname] to be replaced
        if license_name in [
            LicenseOptionsEnum.BSD_2_Clause,
            LicenseOptionsEnum.BSD_3_Clause,
            LicenseOptionsEnum.MIT,
        ]:
            content = content.replace('[year]', '{{license_year}}').replace('[fullname]', '{{repo.name}} Developers')
        context['license_year'] = context.get('license_year', date.today().year)
        return content


class LicenseFile(File):
    """License File created by downloading from Github."""

    name: Optional[Union[TemplateStr, str, Callable]] = Field(get_license_filename, validate_default=True, description='The name of the license file')
    content: Union[Resource, str, bytes, Path, Callable] = Field(get_license_content, description='The file content')
