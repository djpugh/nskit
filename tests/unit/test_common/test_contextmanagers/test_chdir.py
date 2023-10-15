from pathlib import Path
import tempfile
import unittest

from nskit.common.contextmanagers import ChDir


class ChDirTestCase(unittest.TestCase):

    def test_tempdir(self):
        start_dir = Path.cwd()
        with ChDir() as d:
            intermediate_dir = Path.cwd()
            self.assertTrue(Path(d).parts[-1].startswith(tempfile.gettempprefix()))
            self.assertIn(tempfile.gettempdir(), str(d))
        self.assertEqual(Path.cwd(), start_dir)
        self.assertNotEqual(Path.cwd(), intermediate_dir)

    def test_not_tempdir(self):
        with tempfile.TemporaryDirectory() as td:
            start_dir = Path.cwd()
            with ChDir(Path(td)/'test_dir') as d:
                intermediate_dir = Path.cwd()
                self.assertEqual(str(intermediate_dir.parts[-1]), 'test_dir')
                self.assertEqual((Path(td)/'test_dir').resolve(), intermediate_dir.resolve())
            self.assertEqual(Path.cwd(), start_dir)
            self.assertNotEqual(Path.cwd(), intermediate_dir)