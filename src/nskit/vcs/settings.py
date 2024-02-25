"""Codebase Settings."""
from __future__ import annotations

from pathlib import Path
import sys
from typing import Optional, Union

if sys.version_info.major <= 3 and sys.version_info.minor <= 8:
    from typing_extensions import Annotated
else:
    from typing import Annotated

from pydantic import Field, field_validator, model_validator, ValidationError

from nskit._logging import logger_factory
from nskit.common.configuration import BaseConfiguration, SettingsConfigDict
from nskit.vcs.namespace_validator import ValidationEnum
from nskit.vcs.providers import ProviderEnum
from nskit.vcs.providers.abstract import VCSProviderSettings
from nskit.vcs.repo import NamespaceValidationRepo

logger = logger_factory.get_logger(__name__)


class CodebaseSettings(BaseConfiguration):
    """Codebase settings object."""
    model_config = SettingsConfigDict(env_file='.env', env_prefix='NSKIT_VCS_CODEBASE_', dotenv_extra='ignore')

    default_branch: str = 'main'
    vcs_provider: Annotated[ProviderEnum, Field(validate_default=True)] = None
    namespace_validation_repo: Optional[Union[NamespaceValidationRepo, str]] = None
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
                except (ImportError, ValueError, ValidationError):
                    # This provider didn't work
                    logger.info(f'{provider.value} Not Configured.')
        if cls.model_fields['vcs_provider'].annotation(value).extension is None:
            raise ValueError('Extension Not Found')
        return value

    @model_validator(mode='after')
    def _validate_namespace_validation_repo_default(self):
        if self.namespace_validation_repo is None and Path('.namespaces').exists():
            # Can we handle the root pathing
            self.namespace_validation_repo = '.namespaces'
        if isinstance(self.namespace_validation_repo, str):
            self.namespace_validation_repo = NamespaceValidationRepo(name=self.namespace_validation_repo,
                                                                     local_dir=Path(self.namespace_validation_repo),
                                                                     provider_client=self.provider_settings.repo_client)
        return self

    @property
    def provider_settings(self) -> VCSProviderSettings:
        """Get the instantiated provider settings."""
        if self._provider_settings is None:
            self._provider_settings = self.vcs_provider.extension()
        return self._provider_settings
