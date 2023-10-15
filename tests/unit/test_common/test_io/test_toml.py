from io import StringIO
import tomllib as py_toml
import unittest

from nskit.common.io import toml


class TOMLTestCase(unittest.TestCase):

    def test_loads(self):
        self.assertEqual(toml.loads('a = 1\n'), {'a': 1})

    def test_dumps(self):
        self.assertEqual(toml.dumps({'a': 1}), 'a = 1\n')

    def test_load(self):
        s = StringIO('a = 1\n')
        self.assertEqual(toml.load(s), {'a': 1})

    def test_dump(self):
        s = StringIO()
        toml.dump({'a': 1}, s)
        self.assertEqual(s.getvalue(), 'a = 1\n')

    def test_round_trip_loads_dumps_loads(self):
        self.assertEqual(toml.loads(toml.dumps(toml.loads('a = 1\n'))), {'a': 1})

    def test_round_trip_load_dump_load(self):
        s = StringIO('a = 1\n')
        s2 = StringIO()
        toml.dump(toml.load(s), s2)
        s2.seek(0)
        self.assertEqual(toml.load(s2), {'a': 1})

    def test_py_toml_loads(self):
        self.assertEqual(py_toml.loads(toml.dumps({"a":1})), {'a': 1})
