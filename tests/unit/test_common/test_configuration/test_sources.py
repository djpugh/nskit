import unittest

from pydantic import BaseModel

from nskit.common.configuration.sources import FileConfigSettingsSource
from nskit.common.contextmanagers import ChDir
from nskit.common.io import json, toml, yaml


class FileConfigSettingsSourceTestCase(unittest.TestCase):

    def setUp(self):
        self.file_config = {'a': 'a', 'b': 2}

        class Settings(BaseModel):
            a: str
            b: int

        self.settings_cls = Settings

    def test_get_field_value_json(self):
        self.settings_cls.model_config = {'config_file_path': 'test.json'}
        src = FileConfigSettingsSource(self.settings_cls)
        with ChDir():
            with open('test.json', 'w') as f:
                json.dump(self.file_config, f)
            self.assertEqual(src.get_field_value(None, 'a'), ('a', 'a', False))
        # Loaded into files
        self.assertEqual(src.get_field_value(None, 'b'), (2, 'b', False))

    def test_get_field_value_JSON(self):
        self.settings_cls.model_config = {'config_file_path': 'test.JSON'}
        src = FileConfigSettingsSource(self.settings_cls)
        with ChDir():
            with open('test.JSON', 'w') as f:
                json.dump(self.file_config, f)
            self.assertEqual(src.get_field_value(None, 'a'), ('a', 'a', False))
        # Loaded into files
        self.assertEqual(src.get_field_value(None, 'b'), (2, 'b', False))

    def test_get_field_value_jsn(self):
        self.settings_cls.model_config = {'config_file_path': 'test.jsn'}
        src = FileConfigSettingsSource(self.settings_cls)
        with ChDir():
            with open('test.jsn', 'w') as f:
                json.dump(self.file_config, f)
            self.assertEqual(src.get_field_value(None, 'a'), ('a', 'a', False))
        # Loaded into files
        self.assertEqual(src.get_field_value(None, 'b'), (2, 'b', False))

    def test_get_field_value_yaml(self):
        self.settings_cls.model_config = {'config_file_path': 'test.yaml'}
        src = FileConfigSettingsSource(self.settings_cls)
        with ChDir():
            with open('test.yaml', 'w') as f:
                yaml.dump(self.file_config, f)
            self.assertEqual(src.get_field_value(None, 'a'), ('a', 'a', False))
        # Loaded into files
        self.assertEqual(src.get_field_value(None, 'b'), (2, 'b', False))

    def test_get_field_value_YAML(self):
        self.settings_cls.model_config = {'config_file_path': 'test.YAML'}
        src = FileConfigSettingsSource(self.settings_cls)
        with ChDir():
            with open('test.YAML', 'w') as f:
                yaml.dump(self.file_config, f)
            self.assertEqual(src.get_field_value(None, 'a'), ('a', 'a', False))
        # Loaded into files
        self.assertEqual(src.get_field_value(None, 'b'), (2, 'b', False))

    def test_get_field_value_yml(self):
        self.settings_cls.model_config = {'config_file_path': 'test.yml'}
        src = FileConfigSettingsSource(self.settings_cls)
        with ChDir():
            with open('test.yml', 'w') as f:
                yaml.dump(self.file_config, f)
            self.assertEqual(src.get_field_value(None, 'a'), ('a', 'a', False))
        # Loaded into files
        self.assertEqual(src.get_field_value(None, 'b'), (2, 'b', False))

    def test_get_field_value_toml(self):
        self.settings_cls.model_config = {'config_file_path': 'test.toml'}
        src = FileConfigSettingsSource(self.settings_cls)
        with ChDir():
            with open('test.toml', 'w') as f:
                toml.dump(self.file_config, f)
            self.assertEqual(src.get_field_value(None, 'a'), ('a', 'a', False))
        # Loaded into files
        self.assertEqual(src.get_field_value(None, 'b'), (2, 'b', False))

    def test_get_field_value_TOML(self):
        self.settings_cls.model_config = {'config_file_path': 'test.TOML'}
        src = FileConfigSettingsSource(self.settings_cls)
        with ChDir():
            with open('test.TOML', 'w') as f:
                toml.dump(self.file_config, f)
            self.assertEqual(src.get_field_value(None, 'a'), ('a', 'a', False))
        # Loaded into files
        self.assertEqual(src.get_field_value(None, 'b'), (2, 'b', False))

    def test_get_field_value_tml(self):
        self.settings_cls.model_config = {'config_file_path': 'test.tml'}
        src = FileConfigSettingsSource(self.settings_cls)
        with ChDir():
            with open('test.tml', 'w') as f:
                toml.dump(self.file_config, f)
            self.assertEqual(src.get_field_value(None, 'a'), ('a', 'a', False))
        # Loaded into files
        self.assertEqual(src.get_field_value(None, 'b'), (2, 'b', False))

    def test_call(self):
        test_files = {'json': ['test.json', 'test.jsn', 'test.JSON', 'test.JSN'],
                      'yaml': ['test.yaml', 'test.yml', 'test.YAML', 'test.YMl'],
                      'toml': ['test.toml', 'test.tml', 'test.TOML', 'test.TMl']}
        for ext, file_names in test_files.items():
            for file_name in file_names:

                with self.subTest(format=ext, file=file_name):
                    self.settings_cls.model_config = {'config_file_path': file_name}
                    src = FileConfigSettingsSource(self.settings_cls)
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
                        self.assertEqual(src(), self.file_config)
