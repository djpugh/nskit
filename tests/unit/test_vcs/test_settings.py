from __future__ import annotations

from pathlib import Path
import sys
import unittest
from unittest.mock import call, create_autospec, MagicMock, patch
import uuid

if sys.version_info.major >= 3 and sys.version_info.minor >= 9:
    from typing import Annotated
else:
    from typing_extensions import Annotated

from pydantic import Field, ValidationError
from pydantic_settings import SettingsConfigDict

from nskit.common.contextmanagers import ChDir, Env, TestExtension
from nskit.common.extensions import ExtensionsEnum
from nskit.vcs import settings
from nskit.vcs.namespace_validator import NamespaceValidator
from nskit.vcs.providers import ENTRYPOINT
from nskit.vcs.providers.abstract import VCSProviderSettings
from nskit.vcs.repo import NamespaceValidationRepo, RepoClient
from nskit.vcs.settings import CodebaseSettings


class VCSSettingsTestCase(unittest.TestCase):

    def setUp(self):

        self._MockedRepoClientKls = create_autospec(RepoClient)
        self._mocked_repo_client = self._MockedRepoClientKls()

        class DummyVCSProviderSettings(VCSProviderSettings):

            test_abacus: str

            @property
            def repo_client(self2):
                return self._mocked_repo_client

        self._provider_settings_cls = DummyVCSProviderSettings
        self._entrypoint = f'nskit.vcs.providers.e{uuid.uuid4()}'

    def extension(self, solo=True):
        return TestExtension('dummy', self._entrypoint, self._provider_settings_cls, solo=solo)

    def patched_settings(self):
        PatchedProviderEnum = ExtensionsEnum.from_entrypoint('PatchedProviderEnum', self._entrypoint)

        class PatchedSettings(CodebaseSettings):
            model_config = SettingsConfigDict(env_file=None)
            vcs_provider: Annotated[PatchedProviderEnum, Field(validate_default=True)] = None

        return PatchedSettings

    def env(self, **override):
        override.update({'TEST_ABACUS': 'A'})
        return Env(override=override)

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

    def test_namespaces_validation_repo_from_str(self):

        with ChDir():  # Make sure theres no .env file when running tests
            # Create the namespaces dir
            Path('.namespaces23').mkdir(parents=True)
            nsv = NamespaceValidator(options=[{'a': ['b', 'c']}])
            Path('.namespaces23/namespaces.yaml').write_text(nsv.model_dump_yaml())
            with self.extension():
                PatchedSettings = self.patched_settings()
                with Env(override={'TEST_ABACUS': 'A'}):
                    s = PatchedSettings(namespace_validation_repo='.namespaces23')
                    self.assertIsInstance(s.namespace_validation_repo, NamespaceValidationRepo)
                    self.assertEqual(s.namespace_validation_repo.local_dir.name, '.namespaces23')

    def test_namespaces_validation_repo_from_env(self):

        with ChDir():  # Make sure theres no .env file when running tests
            # Create the namespaces dir
            Path('.namespaces23').mkdir(parents=True)
            nsv = NamespaceValidator(options=[{'a': ['b', 'c']}])
            Path('.namespaces23/namespaces.yaml').write_text(nsv.model_dump_yaml())
            with self.extension():
                PatchedSettings = self.patched_settings()
                with Env(override={'TEST_ABACUS': 'A', 'NSKIT_VCS_CODEBASE_NAMESPACE_VALIDATION_REPO': '.namespaces23'}):
                    s = PatchedSettings()
                    self.assertIsInstance(s.namespace_validation_repo, NamespaceValidationRepo)
                    self.assertEqual(s.namespace_validation_repo.local_dir.name, '.namespaces23')

    def test_namespaces_validation_repo_not_exists(self):

        with ChDir():  # Make sure theres no .env file when running tests
            # Create the namespaces dir
            Path('.namespaces23').mkdir(parents=True)
            nsv = NamespaceValidator(options=[{'a': ['b', 'c']}])
            Path('.namespaces23/namespaces.yaml').write_text(nsv.model_dump_yaml())
            with self.extension():
                PatchedSettings = self.patched_settings()
                with Env(override={'TEST_ABACUS': 'A'}):
                    s = PatchedSettings()
                    self.assertIsNone(s.namespace_validation_repo)

    def test_namespaces_validation_repo_from_default(self):

        with ChDir():  # Make sure theres no .env file when running tests
            # Create the namespaces dir
            Path('.namespaces').mkdir(parents=True)
            nsv = NamespaceValidator(options=[{'a': ['b', 'c']}])
            Path('.namespaces/namespaces.yaml').write_text(nsv.model_dump_yaml())
            with self.extension():
                PatchedSettings = self.patched_settings()
                with Env(override={'TEST_ABACUS': 'A'}):
                    s = PatchedSettings()
                    self.assertIsInstance(s.namespace_validation_repo, NamespaceValidationRepo)
                    self.assertEqual(s.namespace_validation_repo.local_dir.name, '.namespaces')


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
