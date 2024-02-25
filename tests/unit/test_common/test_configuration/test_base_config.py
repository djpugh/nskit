import unittest

from pydantic import ConfigDict, ValidationError

from nskit.common.configuration import BaseConfiguration, SettingsConfigDict
from nskit.common.contextmanagers import ChDir
from nskit.common.io import json, toml, yaml


class BaseConfigurationTestCase(unittest.TestCase):

    def setUp(self):
        self.file_config = {'a': 'a', 'b': 2}

        class Settings(BaseConfiguration):
            a: str
            b: int

        self.settings_cls = Settings
        self.expected = Settings(**self.file_config)

    def test_load_file_source_config_filepath(self):
        test_files = {'json': ['test.json', 'test.jsn', 'test.JSON', 'test.JSN'],
                      'yaml': ['test.yaml', 'test.yml', 'test.YAML', 'test.YMl'],
                      'toml': ['test.toml', 'test.tml', 'test.TOML', 'test.TMl']}
        for ext, file_names in test_files.items():
            for file_name in file_names:

                with self.subTest(format=ext, file=file_name):
                    self.settings_cls.model_config = {'config_file': file_name}
                    arg = 'w'
                    if ext == 'json':
                        dumper = json.dump
                    elif ext == 'yaml':
                        dumper = yaml.dump
                    elif ext == 'toml':
                        dumper = toml.dump

                    with ChDir():
                        with open(file_name, arg) as f:
                            dumper(self.file_config, f)
                        self.assertEqual(self.settings_cls(), self.expected)

    def test_load_file_source_filetype_filepath(self):
        test_files = {'json': ['test.json', 'test.jsn', 'test.JSON', 'test.JSN'],
                      'yaml': ['test.yaml', 'test.yml', 'test.YAML', 'test.YMl'],
                      'toml': ['test.toml', 'test.tml', 'test.TOML', 'test.TMl']}
        for ext, file_names in test_files.items():
            for file_name in file_names:

                with self.subTest(format=ext, file=file_name):
                    self.settings_cls.model_config = {f'{ext}_file': file_name}
                    arg = 'w'
                    if ext == 'json':
                        dumper = json.dump
                    elif ext == 'yaml':
                        dumper = yaml.dump
                    elif ext == 'toml':
                        dumper = toml.dump

                    with ChDir():
                        with open(file_name, arg) as f:
                            dumper(self.file_config, f)
                        self.assertEqual(self.settings_cls(), self.expected)

    def test_no_properties(self):

        class TestModel(BaseConfiguration):
            a: str = 'a'
            b: int = 1

        t = TestModel()
        self.assertEqual(t.model_dump(), {'a': 'a', 'b': 1 })

    def test_no_properties_exclude(self):

        class TestModel(BaseConfiguration):
            a: str = 'a'
            b: int = 1

        t = TestModel()
        self.assertEqual(t.model_dump(exclude=['a']), {'b': 1 })
        self.assertEqual(t.model_dump(exclude={'a'}), {'b': 1 })

    def test_properties(self):

        class TestModel(BaseConfiguration):
            a: str = 'a'
            b: int = 1

            @property
            def c(self):
                return 1.2

        t = TestModel()
        self.assertEqual(t.model_dump(), {'a': 'a', 'b': 1, 'c': 1.2})

    def test_properties_exclude(self):

        class TestModel(BaseConfiguration):
            a: str = 'a'
            b: int = 1

            @property
            def c(self):
                return 1.2

        t = TestModel()
        self.assertEqual(t.model_dump(exclude=['a', 'c']), {'b': 1 })
        self.assertEqual(t.model_dump(exclude={'a'}), {'b': 1 , 'c': 1.2})

    def test_properties_excluded(self):

        class TestModel(BaseConfiguration):
            a: str = 'a'
            b: int = 1
            _excluded_properties = ['d']

            @property
            def c(self):
                return 1.2

            @property
            def d(self):
                return True

        t = TestModel()
        self.assertEqual(t._excluded_properties, ['d'])
        self.assertEqual(t.model_dump(exclude=['a', 'c']), {'b': 1 })
        self.assertEqual(t.model_dump(exclude={'a'}), {'b': 1 , 'c': 1.2})
        self.assertEqual(t.model_dump(), {'a': 'a', 'b': 1 , 'c': 1.2})
        self.assertEqual(t.model_dump(include={'a', 'd'}), {'a': 'a' , 'd': True})

    def test_dump_toml(self):
        self.assertEqual(self.expected.model_dump_toml(), toml.dumps(self.file_config))

    def test_dump_yaml(self):
        self.assertEqual(self.expected.model_dump_yaml(), yaml.dumps(self.file_config))

    def test_nested_properties(self):

        class ASettings(BaseConfiguration):
            model_config = ConfigDict(extra='ignore')
            c: str = 'a'
            d: int = 1

            @property
            def a(self):
                return True
        class TestModel(BaseConfiguration):
            a: ASettings
            b: int

        t = TestModel(a=ASettings(), b=2)

    def test_dotenv_extra_ignore(self):

        class ASettings(BaseConfiguration):
            model_config = SettingsConfigDict(env_prefix='AX_', env_file='.env', dotenv_extra='ignore')
            c: str = 'a'
            d: int = 1

            @property
            def a(self):
                return True
        class TestModel(BaseConfiguration):
            model_config = SettingsConfigDict(env_prefix='TM_', env_file='.env', dotenv_extra='ignore')
            a: ASettings
            b: int

        with ChDir():
            with open('.env', 'w') as f:
                f.write('AX_D=3\nTM_B=4\nAX_R=123\nTM_EE=44')
            t = TestModel(a=ASettings())
            self.assertEqual(t.b, 4)
            self.assertEqual(t.a.d, 3)
            self.assertEqual(t.a.c, 'a')

    def test_dotenv_extra_forbid_error(self):

        class ASettings(BaseConfiguration):
            model_config = SettingsConfigDict(env_prefix='AX_', env_file='.env', dotenv_extra='forbid')
            c: str = 'a'
            d: int = 1

            @property
            def a(self):
                return True
        class TestModel(BaseConfiguration):
            model_config = SettingsConfigDict(env_prefix='TM_', env_file='.env', dotenv_extra='forbid')
            a: ASettings
            b: int

        with ChDir():
            with open('.env', 'w') as f:
                f.write('AX_D=3\nTM_B=4\nAX_R=123\nTM_EE=44')
            with self.assertRaises(ValidationError):
                TestModel(a=ASettings())

    def test_dotenv_extra_forbid_ok(self):

        class ASettings(BaseConfiguration):
            model_config = SettingsConfigDict(env_prefix='AX_', dotenv_extra='forbid')
            c: str = 'a'
            d: int = 1

            @property
            def a(self):
                return True
        class TestModel(BaseConfiguration):
            model_config = SettingsConfigDict(env_prefix='TM_', env_file='.env', dotenv_extra='forbid')
            a: ASettings
            b: int

        with ChDir():
            with open('.env', 'w') as f:
                f.write('TM_B=4\n')
            t = TestModel(a=ASettings())
            self.assertEqual(t.b, 4)
            self.assertEqual(t.a.d, 1)
            self.assertEqual(t.a.c, 'a')

