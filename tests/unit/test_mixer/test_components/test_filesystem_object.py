from pathlib import Path
import unittest
from unittest.mock import patch

from nskit.mixer.components.filesystem_object import FileSystemObject, TemplateStr


class TemplateStrTestCase(unittest.TestCase):

    def test_call_no_jinja(self):
        t = TemplateStr('ab')
        self.assertEqual(t(), 'ab')

    def test_call_jinja(self):
        t = TemplateStr('a{{b}}')
        self.assertEqual(t(), 'a')
        self.assertEqual(t(dict(b=3)), 'a3')


class FileSystemObjectTestCase(unittest.TestCase):

    def setUp(self):
        self._patch = patch.object(FileSystemObject, '__abstractmethods__', set())
        self._patch.start()

    def tearDown(self) -> None:
        self._patch.stop()

    def test_init(self):
        f = FileSystemObject(id_=1, name='a')
        self.assertEqual(f.id_, 1)
        self.assertEqual(f.name, 'a')

    def test_init_no_id(self):
        f = FileSystemObject(name='a')
        self.assertIsNone(f.id_)
        self.assertEqual(f.name, 'a')

    def test_init_callable_name(self):
        def test_name():
            return 'b'
        f = FileSystemObject(name=test_name)
        self.assertIsNone(f.id_)
        self.assertEqual(f.name(), 'b')

    def test_init_templatestr_name(self):
        f = FileSystemObject(name='{{a}}')
        self.assertIsNone(f.id_)
        self.assertIsInstance(f.name, TemplateStr)
        self.assertEqual(f.name, '{{a}}')

    def test_render_name_str(self):
        f = FileSystemObject(name='a')
        self.assertEqual(f.render_name({'a': 1}), 'a')

    def test_render_name_callable(self):
        def test_name(context):
            return context.get('a', 'b')
        f = FileSystemObject(name=test_name)
        self.assertEqual(f.render_name({'a': 1}), 1)
        self.assertEqual(f.render_name({}), 'b')

    def test_render_name_templatestr(self):
        f = FileSystemObject(name='a{{b}}')
        self.assertEqual(f.render_name({'b': 1}), 'a1')
        self.assertEqual(f.render_name({}), 'a')

    def test_repr_str(self):
        f = FileSystemObject(name='a')
        self.assertEqual(repr(f), 'a = FileSystemObject(name: a)')

    def test_repr_callable(self):
        def test_name(context):
            return context.get('a', 'b')
        f = FileSystemObject(name=test_name)
        self.assertEqual(repr(f), '<callable> = FileSystemObject(name: <callable>)')
        self.assertEqual(f._repr({'a': 'c'}), 'c = FileSystemObject(name: <callable>)')

    def test_repr_templatestr(self):
        f = FileSystemObject(name='a{{b}}')
        self.assertEqual(repr(f), 'a{{b}} = FileSystemObject(name <TemplateStr>: a{{b}})')
        self.assertEqual(f._repr({'b': 'c'}), 'ac = FileSystemObject(name <TemplateStr>: a{{b}})')

    def test_get_path_override(self):
        f = FileSystemObject(name='a')
        f2 = FileSystemObject(name='a{{b}}')
        self.assertEqual(f.get_path(Path.cwd(), {}, Path('x')), Path.cwd()/'x')
        self.assertEqual(f2.get_path(Path.cwd(), {}, Path('x')), Path.cwd()/'x')
        self.assertEqual(f2.get_path(Path.cwd(), {'b': 'c'}, Path('x')), Path.cwd()/'x')

    def test_get_path_no_override(self):
        f = FileSystemObject(name='a')
        f2 = FileSystemObject(name='a{{b}}')
        self.assertEqual(f.get_path(Path.cwd(), {}), Path.cwd()/'a')
        self.assertEqual(f2.get_path(Path.cwd(), {}), Path.cwd()/'a')
        self.assertEqual(f2.get_path(Path.cwd(), {'b': 'c'}), Path.cwd()/'ac')

    def test_get_path_no_name(self):

        def test_callable(context):
            return None

        f = FileSystemObject(name=test_callable)
        self.assertIsNone(f.get_path(Path.cwd(), {}))

    def test_write(self):
        with self.assertRaises(NotImplementedError):
            FileSystemObject(name='a').write(None, {})

    def test_dryrun(self):
        with self.assertRaises(NotImplementedError):
            FileSystemObject(name='a').dryrun(None, {})

    def test_validate(self):
        with self.assertRaises(NotImplementedError):
            FileSystemObject(name='a').validate(None, {})