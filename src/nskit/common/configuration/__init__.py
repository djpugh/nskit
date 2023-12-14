"""Base configuration class.

Includes:
    - properties in model dumps
    - file based config loading (json/toml/yaml)
    - model dumping to toml & yaml
"""
from __future__ import annotations

from typing import Any

from pydantic_settings import BaseSettings as _BaseSettings
from pydantic_settings import PydanticBaseSettingsSource as _PydanticBaseSettingsSource
from pydantic_settings import SettingsConfigDict as _SettingsConfigDict

from nskit.common.configuration.mixins import PropertyDumpMixin
from nskit.common.configuration.sources import FileConfigSettingsSource
from nskit.common.io import json, toml, yaml


class BaseConfiguration(PropertyDumpMixin, _BaseSettings):
    """A Pydantic BaseSettings type object with Properties included in model dump, and yaml and toml integrations."""

    model_config = _SettingsConfigDict(env_file_encoding='utf-8')

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[_BaseSettings],
        init_settings: _PydanticBaseSettingsSource,
        env_settings: _PydanticBaseSettingsSource,
        dotenv_settings: _PydanticBaseSettingsSource,
        file_secret_settings: _PydanticBaseSettingsSource,
    ) -> tuple[_PydanticBaseSettingsSource, ...]:
        """Create settings loading, including the FileConfigSettingsSource."""
        # TODO This probably needs a tweak to handle complex structures.
        return (
            FileConfigSettingsSource(settings_cls),
            init_settings,
            env_settings,
            dotenv_settings,
            file_secret_settings,
        )

    def model_dump_toml(
            self,
            *,
            indent: int | None = None,
            include: Any = None,
            exclude: Any = None,
            by_alias: bool = False,
            exclude_unset: bool = False,
            exclude_defaults: bool = False,
            exclude_none: bool = False,
            round_trip: bool = False,
            warnings: bool = True):
        """Dump model to TOML."""
        # We go via JSON to include indent etc.
        return toml.dumps(json.loads(self.model_dump_json(
            indent=indent,
            include=include,
            exclude=exclude,
            by_alias=by_alias,
            exclude_unset=exclude_unset,
            exclude_defaults=exclude_defaults,
            exclude_none=exclude_none,
            round_trip=round_trip,
            warnings=warnings
        )))

    def model_dump_yaml(
            self,
            *,
            indent: int | None = None,
            include: Any = None,
            exclude: Any = None,
            by_alias: bool = False,
            exclude_unset: bool = False,
            exclude_defaults: bool = False,
            exclude_none: bool = False,
            round_trip: bool = False,
            warnings: bool = True):
        """Dump model to YAML."""
        # We go via JSON to include indent etc.
        return yaml.dumps(json.loads(self.model_dump_json(
            indent=indent,
            include=include,
            exclude=exclude,
            by_alias=by_alias,
            exclude_unset=exclude_unset,
            exclude_defaults=exclude_defaults,
            exclude_none=exclude_none,
            round_trip=round_trip,
            warnings=warnings
        )))
