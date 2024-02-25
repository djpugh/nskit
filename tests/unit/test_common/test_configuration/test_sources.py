import unittest

from pydantic import BaseModel

from nskit.common.configuration.sources import (
    JsonConfigSettingsSource,
    TomlConfigSettingsSource,
    YamlConfigSettingsSource,
)
from nskit.common.contextmanagers import ChDir
from nskit.common.io import json, toml, yaml


class JsonConfigSettingsSourceTestCase(unittest.TestCase):

    def setUp(self):
        self.file_config = {'a': 'a', 'b': 2}

        class Settings(BaseModel):
            a: str
            b: int

        self.settings_cls = Settings

    def test_call(self):
        with ChDir():
            src = JsonConfigSettingsSource(self.settings_cls, 'test.json')
            arg = 'w'
            with open('test.json', arg) as f:
                json.dump(self.file_config, f)
            self.assertEqual(src(), self.file_config)


class YamlConfigSettingsSourceTestCase(unittest.TestCase):

    def setUp(self):
        self.file_config = {'a': 'a', 'b': 2}

        class Settings(BaseModel):
            a: str
            b: int

        self.settings_cls = Settings

    def test_call(self):
        with ChDir():
            src = YamlConfigSettingsSource(self.settings_cls, 'test.yaml')
            arg = 'w'
            with open('test.yaml', arg) as f:
                yaml.dump(self.file_config, f)
            self.assertEqual(src(), self.file_config)


class TomlConfigSettingsSourceTestCase(unittest.TestCase):

    def setUp(self):
        self.file_config = {'a': 'a', 'b': 2}

        class Settings(BaseModel):
            a: str
            b: int

        self.settings_cls = Settings

    def test_call(self):
        with ChDir():
            src = TomlConfigSettingsSource(self.settings_cls, 'test.toml')
            arg = 'w'
            with open('test.toml', arg) as f:
                toml.dump(self.file_config, f)
            self.assertEqual(src(), self.file_config)
