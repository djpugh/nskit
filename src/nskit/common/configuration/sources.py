"""Add settings sources."""
from __future__ import annotations as _annotations

from pathlib import Path
from typing import Any

from pydantic.config import ExtraValues
from pydantic_settings import BaseSettings
from pydantic_settings.sources import (
    DotEnvSettingsSource as _DotEnvSettingsSource,
    DotenvType,
    ENV_FILE_SENTINEL,
    JsonConfigSettingsSource as _JsonConfigSettingsSource,
    TomlConfigSettingsSource as _TomlConfigSettingsSource,
    YamlConfigSettingsSource as _YamlConfigSettingsSource,
)

from nskit.common.io import json, toml, yaml


class JsonConfigSettingsSource(_JsonConfigSettingsSource):
    """Use the nskit.common.io.json loading to load settings from a json file."""
    def _read_file(self, file_path: Path) -> dict[str, Any]:
        encoding = self.json_file_encoding or 'utf-8'
        file_contents = file_path.read_text(encoding)
        return json.loads(file_contents)

    def __call__(self):
        """Make the file reading at the source instantiation."""
        self.init_kwargs = self._read_files(self.json_file_path)
        return super().__call__()


class TomlConfigSettingsSource(_TomlConfigSettingsSource):
    """Use the nskit.common.io.toml loading to load settings from a toml file."""
    def _read_file(self, file_path: Path) -> dict[str, Any]:
        file_contents = file_path.read_text()
        return toml.loads(file_contents)

    def __call__(self):
        """Make the file reading at the source instantiation."""
        self.init_kwargs = self._read_files(self.toml_file_path)
        return super().__call__()


class YamlConfigSettingsSource(_YamlConfigSettingsSource):
    """Use the nskit.common.io.yaml loading to load settings from a yaml file."""
    def _read_file(self, file_path: Path) -> dict[str, Any]:
        encoding = self.yaml_file_encoding or 'utf-8'
        file_contents = file_path.read_text(encoding)
        return yaml.loads(file_contents)

    def __call__(self):
        """Make the file reading at the source instantiation."""
        self.init_kwargs = self._read_files(self.yaml_file_path)
        return super().__call__()


class DotEnvSettingsSource(_DotEnvSettingsSource):
    """Fixes change of behaviour in pydantic-settings 2.2.0 with extra allowed handling.

    Adds dotenv_extra variable that is set to replicate previous behaviour (ignore).
    """

    def __init__(
        self,
        settings_cls: type[BaseSettings],
        env_file: DotenvType | None = ENV_FILE_SENTINEL,
        env_file_encoding: str | None = None,
        case_sensitive: bool | None = None,
        env_prefix: str | None = None,
        env_nested_delimiter: str | None = None,
        env_ignore_empty: bool | None = None,
        env_parse_none_str: str | None = None,
        dotenv_extra: ExtraValues | None = 'ignore'
    ) -> None:
        """Wrapper for init function to add dotenv_extra handling."""
        self.dotenv_extra = dotenv_extra
        super().__init__(
            settings_cls,
            env_file,
            env_file_encoding,
            case_sensitive,
            env_prefix,
            env_nested_delimiter,
            env_ignore_empty,
            env_parse_none_str
        )

    def __call__(self) -> dict[str, Any]:
        """Wraps call logic introduced in 2.2.0, but is backwards compatible to 2.1.0 and earlier versions."""
        data: dict[str, Any] = super().__call__()
        to_pop = []
        for key in data.keys():
            matched = False
            for field_name, field in self.settings_cls.model_fields.items():
                for field_alias, field_env_name, _ in self._extract_field_info(field, field_name):
                    if key == field_env_name or key == field_alias:
                        matched = True
                        break
                if matched:
                    break
            if not matched and self.dotenv_extra == 'ignore':
                to_pop.append(key)
        for key in to_pop:
            data.pop(key)
        return data
