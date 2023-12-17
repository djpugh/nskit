from __future__ import annotations

import sys
import unittest
import uuid

if sys.version_info.major >= 3 and sys.version_info.minor >= 9:
    from typing import Annotated
else:
    from typing_extensions import Annotated

from pydantic import Field, ValidationError
from pydantic_settings import SettingsConfigDict

from nskit.common.contextmanagers import Env, TestExtension
from nskit.common.extensions import ExtensionsEnum
from nskit.vcs import settings
from nskit.vcs.providers import ENTRYPOINT
from nskit.vcs.providers.abstract import VCSProviderSettings
from nskit.vcs.settings import CodebaseSettings


class VCSSettingsTestCase(unittest.TestCase):


    def test_default_init_failed(self):

        class PatchedSettings(CodebaseSettings):
            model_config = SettingsConfigDict(env_file=None)

        with self.assertRaises(ValidationError):
            with Env(environ={}):
                PatchedSettings(model_config=dict(env_file=f'{uuid.uuid4()}.env'))

    def test_default_init_test_with_non_valid_provider(self):

        class DummyVCSProviderSettings(VCSProviderSettings):

            test_abacus: str

            @property
            def repo_client(self):
                return None

        class PatchedSettings(CodebaseSettings):
            model_config = SettingsConfigDict(env_file=None)

        with TestExtension('dummy', ENTRYPOINT, DummyVCSProviderSettings, solo=True):
            settings.ProviderEnum._patch()
            with Env(remove=['TEST_ABACUS']):
                with self.assertRaises(ValidationError):
                    PatchedSettings(model_config=dict(env_file=f'{uuid.uuid4()}.env'))


    def test_default_init_test_with_valid_provider_found(self):

        class DummyVCSProviderSettings(VCSProviderSettings):

            test_abacus: str

            @property
            def repo_client(self):
                return None

        entrypoint = f'nskit.vcs.providers.e{uuid.uuid4()}'
        with TestExtension('dummy', entrypoint, DummyVCSProviderSettings):
            PatchedProviderEnum = ExtensionsEnum.from_entrypoint('PatchedProviderEnum', entrypoint)

            class PatchedSettings(CodebaseSettings):
                model_config = SettingsConfigDict(env_file=None)
                vcs_provider: Annotated[PatchedProviderEnum, Field(validate_default=True)] = None


            with Env(override={'TEST_ABACUS': 'A'}):
                s = PatchedSettings()
                self.assertEqual(s.vcs_provider.value, 'dummy')


    def test_default_init_test_with_valid_provider_set(self):

        class DummyVCSProviderSettings(VCSProviderSettings):

            test_abacus: str

            @property
            def repo_client(self):
                return None

        entrypoint = f'nskit.vcs.providers.e{uuid.uuid4()}'
        with TestExtension('dummy', entrypoint, DummyVCSProviderSettings):
            PatchedProviderEnum = ExtensionsEnum.from_entrypoint('PatchedProviderEnum', entrypoint)

            class PatchedSettings(CodebaseSettings):
                model_config = SettingsConfigDict(env_file=None)
                vcs_provider: Annotated[PatchedProviderEnum, Field(validate_default=True)] = None


            with Env(override={'TEST_ABACUS': 'A'}):
                s = PatchedSettings(vcs_provider='dummy')
                self.assertEqual(s.vcs_provider.value, 'dummy')


    def test_provider_settings(self):

        class DummyVCSProviderSettings(VCSProviderSettings):

            test_abacus: str

            @property
            def repo_client(self):
                return None

        entrypoint = f'nskit.vcs.providers.e{uuid.uuid4()}'
        with TestExtension('dummy', entrypoint, DummyVCSProviderSettings):
            PatchedProviderEnum = ExtensionsEnum.from_entrypoint('PatchedProviderEnum', entrypoint)

            class PatchedSettings(CodebaseSettings):
                model_config = SettingsConfigDict(env_file=None)
                vcs_provider: Annotated[PatchedProviderEnum, Field(validate_default=True)] = None


            with Env(override={'TEST_ABACUS': 'A'}):
                s = PatchedSettings()
                ps = s.provider_settings
            self.assertIsInstance(ps, DummyVCSProviderSettings)
            self.assertEqual(ps.test_abacus, 'A')
