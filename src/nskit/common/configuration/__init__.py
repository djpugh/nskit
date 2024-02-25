"""Base configuration class.

Includes:
    - properties in model dumps
    - file based config loading (json/toml/yaml)
    - model dumping to toml & yaml
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from pydantic.config import ExtraValues
from pydantic_settings import (
    BaseSettings as _BaseSettings,
    PydanticBaseSettingsSource as _PydanticBaseSettingsSource,
    SettingsConfigDict as _SettingsConfigDict,
)
from pydantic_settings.sources import PathType

from nskit.common.configuration.mixins import PropertyDumpMixin
from nskit.common.configuration.sources import (
    DotEnvSettingsSource,
    JsonConfigSettingsSource,
    TomlConfigSettingsSource,
    YamlConfigSettingsSource,
)
from nskit.common.io import json, toml, yaml


class SettingsConfigDict(_SettingsConfigDict):
    """Customised Settings Config Dict."""
    dotenv_extra: Optional[ExtraValues] = 'ignore'
    config_file: Optional[PathType] = None
    config_file_encoding: Optional[str] = None


class BaseConfiguration(PropertyDumpMixin, _BaseSettings):
    """A Pydantic BaseSettings type object with Properties included in model dump, and yaml and toml integrations."""

    model_config = SettingsConfigDict(env_file_encoding='utf-8')

    def settings_customise_sources(
        cls,
        settings_cls: type[_BaseSettings],
        init_settings: _PydanticBaseSettingsSource,
        env_settings: _PydanticBaseSettingsSource,
        dotenv_settings: _PydanticBaseSettingsSource,
        file_secret_settings: _PydanticBaseSettingsSource,
    ) -> tuple[_PydanticBaseSettingsSource, ...]:
        """Create settings loading, including the FileConfigSettingsSource."""
        config_files = cls.model_config.get('config_file')
        config_file_encoding = cls.model_config.get('config_file_encoding')
        file_types = {'json' : ['.json', '.jsn'],
                      'yaml': ['.yaml', '.yml'],
                      'toml': ['.toml', '.tml']}
        if config_files:
            if isinstance(config_files, (Path, str)):
                config_files = [config_files]
        else:
            config_files = []

        split_config_files = {}
        for file_type, suffixes in file_types.items():
            original = cls.model_config.get(f'{file_type}_file')
            if original and isinstance(original, (Path, str)):
                split_config_files[file_type] = [original]
            elif original:
                split_config_files[file_type] = original
            else:
                split_config_files[file_type] = []
            for config_file in config_files:
                if Path(config_file).suffix.lower() in suffixes:
                    split_config_files[file_type].append(config_file)
        return (
            init_settings,
            env_settings,
            JsonConfigSettingsSource(settings_cls,
                                     split_config_files['json'],
                                     cls.model_config.get('json_file_encoding') or config_file_encoding),
            YamlConfigSettingsSource(settings_cls,
                                     split_config_files['yaml'],
                                     cls.model_config.get('yaml_file_encoding') or config_file_encoding),
            TomlConfigSettingsSource(settings_cls,
                                     split_config_files['toml']),
            DotEnvSettingsSource(settings_cls,
                                 dotenv_settings.env_file,
                                 dotenv_settings.env_file_encoding,
                                 dotenv_settings.case_sensitive,
                                 dotenv_settings.env_prefix,
                                 dotenv_settings.env_nested_delimiter,
                                 dotenv_settings.env_ignore_empty,
                                 dotenv_settings.env_parse_none_str,
                                 cls.model_config.get('dotenv_extra', 'ignore')),
            file_secret_settings
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
