import unittest

from nskit.common.configuration import BaseConfiguration
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

    def test_load_file_source(self):
        test_files = {'json': ['test.json', 'test.jsn', 'test.JSON', 'test.JSN'],
                      'yaml': ['test.yaml', 'test.yml', 'test.YAML', 'test.YMl'],
                      'toml': ['test.toml', 'test.tml', 'test.TOML', 'test.TMl']}
        for ext, file_names in test_files.items():
            for file_name in file_names:

                with self.subTest(format=ext, file=file_name):
                    self.settings_cls.model_config = {'config_file_path': file_name}
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
