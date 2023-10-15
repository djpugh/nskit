from io import StringIO
import unittest

from nskit.common.io import yaml


class YAMLTestCase(unittest.TestCase):

    def test_loads(self):
        self.assertEqual(yaml.loads('a: 1\n'), {'a': 1})

    def test_dumps(self):
        self.assertEqual(yaml.dumps({'a': 1}), 'a: 1\n')

    def test_load(self):
        s = StringIO('a: 1\n')
        self.assertEqual(yaml.load(s), {'a': 1})

    def test_dump(self):
        s = StringIO()
        yaml.dump({'a': 1}, s)
        self.assertEqual(s.getvalue(), 'a: 1\n')

    def test_round_trip_loads_dumps_loads(self):
        self.assertEqual(yaml.loads(yaml.dumps(yaml.loads('a: 1\n'))), {'a': 1})

    def test_round_trip_load_dump_load(self):
        s = StringIO('a: 1\n')
        s2 = StringIO()
        yaml.dump(yaml.load(s), s2)
        s2.seek(0)
        self.assertEqual(yaml.load(s2), {'a': 1})
