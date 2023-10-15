from io import StringIO
import json as py_json
import unittest

from nskit.common.io import json


class JSONTestCase(unittest.TestCase):

    def test_loads(self):
        self.assertEqual(json.loads('{"a": 1}'), {'a': 1})

    def test_dumps(self):
        self.assertEqual(json.dumps({'a': 1}), '{"a":1}')

    def test_load(self):
        s = StringIO('{"a": 1}')
        self.assertEqual(json.load(s), {'a': 1})

    def test_dump(self):
        s = StringIO()
        json.dump({'a': 1}, s)
        self.assertEqual(s.getvalue(), '{"a":1}')

    def test_round_trip_loads_dumps_loads(self):
        self.assertEqual(json.loads(json.dumps(json.loads('{"a":1}'))), {'a': 1})

    def test_round_trip_load_dump_load(self):
        s = StringIO('{"a": 1}')
        s2 = StringIO()
        json.dump(json.load(s), s2)
        s2.seek(0)
        self.assertEqual(json.load(s2), {'a': 1})

    def test_py_json_loads(self):
        self.assertEqual(py_json.loads(json.dumps({"a":1})), {'a': 1})

    def test_py_json_dumps(self):
        self.assertEqual(json.loads(py_json.dumps({"a":1})), {'a': 1})