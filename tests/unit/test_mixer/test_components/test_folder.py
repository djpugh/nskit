import os
from pathlib import Path
import unittest

from nskit.common.contextmanagers import ChDir
from nskit.mixer.components.file import File
from nskit.mixer.components.folder import Folder


class FolderTestCase(unittest.TestCase):

    def setUp(self):
        self._folder = Folder(
            name='test',
            contents=[
                Folder(
                    id_='a',
                    name='folder',
                    contents=[
                        File(
                            id_='b',
                            name='test{{a}}.txt',
                            content='test')
                        ]
                    ),
                Folder(
                    id_='b',
                    name='folder2',
                    contents=[
                        File(
                            id_='b',
                            name='test2.txt',
                            content='test2{{a}}')
                        ]
                )
                ]
            )

    def test_write_no_override(self):
        with ChDir():
            path_contents = self._folder.write(Path.cwd(), {'a': 1})
            with open('test/folder/test1.txt') as fp:
                self.assertEqual(fp.read(), 'test')
            with open('test/folder2/test2.txt') as fp:
                self.assertEqual(fp.read(), 'test21')
            self.assertEqual(list(path_contents.keys())[0], Path('test').absolute())

    def test_write_override(self):
        with ChDir():
            path_contents = self._folder.write(Path.cwd(), {'a': 1}, Path('abc'))
            with open('abc/folder/test1.txt') as fp:
                self.assertEqual(fp.read(), 'test')
            with open('abc/folder2/test2.txt') as fp:
                self.assertEqual(fp.read(), 'test21')
            self.assertEqual(list(path_contents.keys())[0], Path('abc').absolute())

    def test_dryrun_no_override(self):
        self.assertEqual(
            self._folder.dryrun(Path('.'), {'a': 1}),
            {Path('test'): {
                Path('test/folder'):
                    {Path('test/folder/test1.txt'): 'test'},
                Path('test/folder2'):
                    {Path('test/folder2/test2.txt'): 'test21'}
                }
            }
        )

    def test_dryrun_override(self):
        self.assertEqual(
            self._folder.dryrun(Path('.'), {'a': 1}, Path('abc')),
            {Path('abc'): {
                Path('abc/folder'):
                    {Path('abc/folder/test1.txt'): 'test'},
                Path('abc/folder2'):
                    {Path('abc/folder2/test2.txt'): 'test21'}
                }
            }
        )

    def test_validate_ok(self):
        with ChDir():
            self._folder.write(Path.cwd(), {'a': 1})
            missing, errors, ok = self._folder.validate(Path.cwd(), {'a': 1})
            self.assertEqual(missing, [])
            self.assertEqual(errors, [])
            self.assertEqual(set(ok), {
                Path('test').absolute(),
                Path('test').absolute()/'folder',
                Path('test').absolute()/'folder'/'test1.txt',
                Path('test').absolute(),
                Path('test').absolute()/'folder2',
                Path('test').absolute()/'folder2'/'test2.txt'
                })
    def test_validate_missing_contents(self):
        with ChDir():
            self._folder.write(Path.cwd(), {'a': 1})
            # Delete file
            os.remove(str(Path('test').absolute()/'folder'/'test1.txt'))
            missing, errors, ok = self._folder.validate(Path.cwd(), {'a': 1})
            self.assertEqual(missing, [Path('test').absolute()/'folder'/'test1.txt'])
            self.assertEqual(errors, [])
            self.assertEqual(set(ok), {
                Path('test').absolute()/'folder2',
                Path('test').absolute()/'folder2'/'test2.txt'})

    def test_validate_missing(self):
        with ChDir():
            missing, errors, ok = self._folder.validate(Path.cwd(), {'a': 1})
            self.assertEqual(ok, [])
            self.assertEqual(errors, [])
            self.assertEqual(set(missing), {
                Path('test').absolute(),
                Path('test').absolute()/'folder',
                Path('test').absolute()/'folder'/'test1.txt',
                Path('test').absolute(),
                Path('test').absolute()/'folder2',
                Path('test').absolute()/'folder2'/'test2.txt'
                })
    def test_validate_missing_override(self):
        with ChDir():
            self._folder.write(Path.cwd(), {'a': 1})
            missing, errors, ok = self._folder.validate(Path.cwd(), {'a': 1}, Path('abc'))
            self.assertEqual(ok, [])
            self.assertEqual(errors, [])
            self.assertEqual(set(missing), {
                Path('abc').absolute(),
                Path('abc').absolute()/'folder',
                Path('abc').absolute()/'folder'/'test1.txt',
                Path('abc').absolute(),
                Path('abc').absolute()/'folder2',
                Path('abc').absolute()/'folder2'/'test2.txt'
                })

    def test_validate_incorrect_contents_wrong(self):
        with ChDir():
            self._folder.write(Path.cwd(), {'a': 1})
            with open(str(Path('test')/'folder'/'test1.txt'), 'w') as f:
                f.write('abacus')
            missing, errors, ok = self._folder.validate(Path.cwd(), {'a': 1})
            self.assertEqual(missing, [])
            self.assertEqual(errors, [Path('test').absolute()/'folder'/'test1.txt'])
            self.assertEqual(set(ok), {
                Path('test').absolute()/'folder2',
                Path('test').absolute()/'folder2'/'test2.txt'
                })

    def test_index_ok_id(self):
        i = self._folder.index('a')
        self.assertEqual(i, 0)
        f = self._folder.contents[i]
        self.assertIsInstance(f, Folder)
        self.assertEqual(f.name, 'folder')
        self.assertEqual(f.id_, 'a')

    def test_index_ok_name(self):
        i = self._folder.index('folder')
        self.assertEqual(i, 0)
        f = self._folder.contents[i]
        self.assertIsInstance(f, Folder)
        self.assertEqual(f.name, 'folder')
        self.assertEqual(f.id_, 'a')

    def test_index_not_found(self):
        with self.assertRaises(KeyError):
            self._folder.index('abacus')

    def test_getitem_id(self):
        f = self._folder['a']
        self.assertIsInstance(f, Folder)
        self.assertEqual(f.name, 'folder')
        self.assertEqual(f.id_, 'a')
        self.assertEqual(f, self._folder.contents[0])

    def test_getitem_name(self):
        f = self._folder['folder']
        self.assertIsInstance(f, Folder)
        self.assertEqual(f.name, 'folder')
        self.assertEqual(f.id_, 'a')
        self.assertEqual(f, self._folder.contents[0])

    def test_getitem_not_found(self):
        with self.assertRaises(KeyError):
            self._folder['abacus']

    def test_setitem_id(self):
        f = Folder(name='b')
        self._folder['a'] = f
        self.assertEqual(f, self._folder.contents[0])
        self.assertIsInstance(self._folder.contents[0], Folder)
        self.assertNotEqual(self._folder.contents[0].name, 'folder')
        self.assertNotEqual(self._folder.contents[0].id_, 'a')
        self.assertEqual(len(self._folder.contents), 2)

    def test_setitem_name(self):
        f = Folder(name='b')
        self._folder['folder'] = f
        self.assertEqual(f, self._folder.contents[0])
        self.assertIsInstance(self._folder.contents[0], Folder)
        self.assertNotEqual(self._folder.contents[0].name, 'folder')
        self.assertNotEqual(self._folder.contents[0].id_, 'a')
        self.assertEqual(len(self._folder.contents), 2)

    def test_setitem_missing(self):
        f = Folder(name='b')
        self._folder['abacus'] = f
        self.assertEqual(f, self._folder.contents[2])
        self.assertIsInstance(self._folder.contents[2], Folder)
        self.assertEqual(self._folder.contents[0].name, 'folder')
        self.assertEqual(self._folder.contents[0].id_, 'a')
        self.assertNotEqual(self._folder.contents[2].name, 'folder')
        self.assertNotEqual(self._folder.contents[2].id_, 'a')
        self.assertEqual(self._folder.contents[2].name, 'b')
        self.assertEqual(len(self._folder.contents), 3)

    def test_repr(self):
        out = repr(self._folder)
        self.assertEqual(out, "test = Folder(name: test):\n|- folder = Folder(id: a, name: folder):\n  |- test{{a}}.txt = File(id: b, name <TemplateStr>: test{{a}}.txt)\n|- folder2 = Folder(id: b, name: folder2):\n  |- test2.txt = File(id: b, name: test2.txt)")
