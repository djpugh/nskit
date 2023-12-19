from pathlib import Path
import unittest

from nskit.common.contextmanagers import ChDir
from nskit.mixer.components.file import File
from nskit.mixer.utilities import Resource


class FileTestCase(unittest.TestCase):

    def test_render_content_str(self):
        f = File(name='test.txt', content='Dryrun')
        self.assertEqual(f.render_content({}), 'Dryrun')
        self.assertEqual(f.render_content({'a': 1}), 'Dryrun')

    def test_render_content_resource_inferred(self):
        f = File(name='test.txt', content='nskit.mixer:__init__.py')
        self.assertIsInstance(f.content, Resource)
        self.assertIn('nskit.mixer', f.render_content({}))
        self.assertIn('nskit.mixer', f.render_content({'a': 1}))

    def test_render_content_resource_explicit(self):
        f = File(name='test.txt', content=Resource('nskit.mixer:__init__.py'))
        self.assertIsInstance(f.content, Resource)
        self.assertIn('nskit.mixer', f.render_content({}))
        self.assertIn('nskit.mixer', f.render_content({'a': 1}))

    def test_render_content_path(self):
        with ChDir():
            with open('test_content.txt', 'w') as f:
                f.write('a{{b}}')
            f = File(name='test.txt', content=Path('test_content.txt'))
            self.assertEqual(f.render_content({}), 'a')
            self.assertEqual(f.render_content({'b': 1}), 'a1')

    def test_render_content_jinja(self):
        f = File(name='test.txt', content='Dryrun{{a}}')
        self.assertEqual(f.render_content({}), 'Dryrun')
        self.assertEqual(f.render_content({'a': 1}), 'Dryrun1')

    def test_render_content_callable(self):

        def test_callable(context):
            if context.get('a', None):
                return 'Dryrun {{a}}'
            return 'Dryrun'

        f = File(name='test.txt', content=test_callable)
        self.assertEqual(f.render_content({}), 'Dryrun')
        self.assertEqual(f.render_content({'a': 1}), 'Dryrun 1')

    def test_write_no_override(self):
        with ChDir():
            f = File(name='test.txt', content='Dryrun{{a}}')
            f.write(Path.cwd(), {})
            with open('test.txt') as fp:
                self.assertEqual(fp.read(), 'Dryrun')
            f.write(Path.cwd(), {'a': 1})
            with open('test.txt') as fp:
                self.assertEqual(fp.read(), 'Dryrun1')

    def test_write_override(self):
        with ChDir():
            f = File(name='test.txt', content='Dryrun{{a}}')
            f.write(Path.cwd(), {}, Path('test2.txt'))
            self.assertTrue(Path('test2.txt').exists())
            self.assertFalse(Path('test.txt').exists())
            with open('test2.txt') as fp:
                self.assertEqual(fp.read(), 'Dryrun')

    def test_write_no_content(self):

        def test_callable(context):
            return None

        with ChDir():
            self.assertFalse(Path('test.txt').exists())
            f = File(name='test.txt', content=test_callable)
            f.write(Path.cwd(), {}, Path('test2.txt'))
            self.assertFalse(Path('test.txt').exists())

    def test_dryrun_no_override(self):
        f = File(name='test.txt', content='Dryrun')
        self.assertEqual(f.dryrun(Path('test_folder'), {}), {Path('test_folder/test.txt'): "Dryrun"})

    def test_dryrun_override(self):
        f = File(name='test.txt', content='Dryrun')
        self.assertEqual(f.dryrun(Path('test_folder'), {}, Path('test2.txt')), {Path('test_folder/test2.txt'): "Dryrun"})

    def test_dryrun_no_content(self):

        def test_callable(context):
            return None

        f = File(name='test.txt', content=test_callable)
        resp = f.dryrun(Path.cwd(), {}, Path('test2.txt'))
        self.assertEqual(resp, {})

    def test_validate_ok(self):
        with ChDir():
            f = File(name='test.txt', content='Dryrun{{a}}')
            f.write(Path.cwd(), {})
            missing, errors, ok = f.validate(Path.cwd(), {})
            self.assertEqual(missing, [])
            self.assertEqual(errors, [])
            self.assertEqual(ok, [Path('test.txt').absolute()])

        with ChDir():
            f = File(name='test.txt', content='Dryrun{{a}}')
            f.write(Path.cwd(), {}, Path('test2.txt'))
            missing, errors, ok = f.validate(Path.cwd(), {}, Path('test2.txt'))
            self.assertEqual(missing, [])
            self.assertEqual(errors, [])
            self.assertEqual(ok, [Path('test2.txt').absolute()])

    def test_validate_missing(self):
        with ChDir():
            f = File(name='test.txt', content='Dryrun{{a}}')
            missing, errors, ok = f.validate(Path.cwd(), {})
            self.assertEqual(missing, [Path('test.txt').absolute()])
            self.assertEqual(errors, [])
            self.assertEqual(ok, [])

    def test_validate_wrong(self):
        with ChDir():
            f = File(name='test.txt', content='Dryrun{{a}}')
            f.write(Path.cwd(), {})
            missing, errors, ok = f.validate(Path.cwd(), {'a': 1})
            self.assertEqual(missing, [])
            self.assertEqual(errors, [Path('test.txt').absolute()])
            self.assertEqual(ok, [])

        with ChDir():
            f = File(name='test.txt', content='Dryrun{{a}}')
            f.write(Path.cwd(), {}, Path('test2.txt'))
            missing, errors, ok = f.validate(Path.cwd(), {'a': 1}, Path('test2.txt'))
            self.assertEqual(missing, [])
            self.assertEqual(errors, [Path('test2.txt').absolute()])
            self.assertEqual(ok, [])

    def test_validate_no_content(self):
        def test_callable(context):
            return None

        f = File(name='test.txt', content=test_callable)
        missing, error, ok= f.validate(Path.cwd(), {}, Path('test2.txt'))
        self.assertEqual(missing, [])
        self.assertEqual(error, [])
        self.assertEqual(ok, [])

    def test_define_with_string_content(self):
        f = File(name='test.txt', content='Dryrun{{a}}')
        self.assertEqual(f.render_content({'a': 3}), 'Dryrun3')

    def test_define_with_resource_string(self):
        f = File(name='test.txt', content='nskit.mixer:__init__.py')
        self.assertNotEqual(f.render_content({}), 'nskit.mixer:__init__.py')