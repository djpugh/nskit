"""
Load SDK Settings
"""
from typing import Annotated, Optional, Union

from pydantic import Field, field_validator, ValidationError
from pydantic_settings import SettingsConfigDict

from nskit._logging import logger_factory
from nskit.common.configuration import BaseConfiguration
from nskit.common.extensions import ExtensionsEnum
from nskit.vcs.namespace_validator import ValidationEnum
from nskit.vcs.providers import ProviderEnum
from nskit.vcs.providers._base import VCSProviderSettings
from nskit.vcs.repo import NamespaceValidationRepo



logger = logger_factory.get_logger(__name__)


class CodebaseSettings(BaseConfiguration):
    model_config = SettingsConfigDict(env_file='.env')

    default_branch: str = 'main'
    vcs_provider: Annotated[ProviderEnum, Field(validate_default=True)] = None
    namespace_validation_repo: Optional[NamespaceValidationRepo] = None
    validation_level: ValidationEnum = ValidationEnum.none
    _provider_settings = None

    @field_validator('vcs_provider', mode='before')
    @classmethod
    def _validate_vcs_provider(cls, value):
        if value is None:
            for provider in cls.model_fields['vcs_provider'].annotation:
                logger.debug(f'Trying {provider.value}, last configured will be loaded.')
                try:
                    if provider.extension:
                        provider.extension()
                    else:
                        raise ValueError('Extension not found')
                    # The last provider to correctly initialise will be used
                    logger.info(f'{provider.value} Configured.')
                    value = provider
                except (ValueError, ValidationError):
                    # This provider didn't work
                    logger.info(f'{provider.value} Not Configured.')
        return value

    @property
    def provider_settings(self) -> VCSProviderSettings:
        if self._provider_settings is None:
            self._provider_settings = self.vcs_provider.extension()
        return self._provider_settings