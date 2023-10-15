"""Manage logging config."""
from pathlib import Path
from typing import Any, Dict, Optional

from pydantic import AliasChoices, Field

from nskit.common.configuration import BaseConfiguration
from nskit.common.logging.formatter import BASE_FORMAT_STR, LoggingFormatter

JSON_ENV_VAR = 'LOG_JSON'
LOGLEVEL_ENV_VAR = 'LOGLEVEL'
LOGFILE_ENV_VAR = 'LOGFILE'
LOGFORMATSTRING_ENV_VAR = 'LOG_FORMAT'
DEFAULT_LOGLEVEL = 'INFO'


class LoggingConfig(BaseConfiguration):
    """This is a basic config for logging."""

    # TODO setup as settings
    level: str = Field(DEFAULT_LOGLEVEL, description='Set the log level for the logger')
    logfile: Optional[Path] = Field(None, validation_alias=AliasChoices('logfile', LOGFILE_ENV_VAR), description='Set the log file for the logger')
    format_string: str = Field(BASE_FORMAT_STR, validation_alias=AliasChoices('format_string', LOGFORMATSTRING_ENV_VAR), description='Set the log format for the logger')
    json_format: bool = Field(True, validation_alias=AliasChoices('json_format', JSON_ENV_VAR), serialization_alias='json', description='Output JSON Logs', alias='json')
    extra: Dict[str, Any] = Field(default_factory=dict, description="Extra kwargs")

    @property
    def formatter(self):
        """Return the logging formatter for the format string."""
        return LoggingFormatter(self.format_string)
