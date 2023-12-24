from datetime import date
from functools import wraps
from pathlib import Path
import unittest

from fastcore.net import HTTP403ForbiddenError

from nskit.common.contextmanagers import ChDir
from nskit.mixer.components.license_file import LicenseFile, LicenseOptionsEnum


class LicenseFileFunctionalTestCase(unittest.TestCase):

    @staticmethod
    def skip_if_rate_limited():
        raise unittest.SkipTest('Rate Limited')

    def test_write_license(self):
        with ChDir():
            self.assertFalse(Path('LICENSE').exists())
            self.assertFalse(Path('COPYING').exists())
            self.assertFalse(Path('COPYING.LESSER').exists())
            self.assertFalse(Path('UNLICENSE').exists())
            pre = [u for u in Path.cwd().glob('*')]
            license_file = LicenseFile()
            try:
                resp = license_file.write(Path('.'), {'license':'mit', 'repo': {'name': 'test_repo2'}})
            except HTTP403ForbiddenError:
                self.skip_if_rate_limited()
            post = [u for u in Path.cwd().glob('*')]
            self.assertTrue(Path('LICENSE').exists())
            self.assertFalse(Path('COPYING').exists())
            self.assertFalse(Path('COPYING.LESSER').exists())
            self.assertFalse(Path('UNLICENSE').exists())
            self.assertNotEqual(pre, post)
            self.assertEqual(list(resp.keys()), [Path('LICENSE')])
            self.assertIn(f'{date.today().year} ', resp[Path('LICENSE')])
            self.assertIn(' test_repo2 Developers', resp[Path('LICENSE')])

    def test_dry_run_license(self):
        license_file = LicenseFile()
        try:
            resp = license_file.dryrun(Path('.'), {'license':'mit', 'repo': {'name': 'test_repo2'}})
        except HTTP403ForbiddenError:
            self.skip_if_rate_limited()

        self.assertEqual(list(resp.keys()), [Path('LICENSE')])
        self.assertIn(f'{date.today().year} ', resp[Path('LICENSE')])
        self.assertIn(' test_repo2 Developers', resp[Path('LICENSE')])

    def test_validate_license_ok(self):
        with ChDir():
            license_file = LicenseFile()
            try:
                license_file.write(Path('.'), {'license':'mit', 'repo': {'name': 'test_repo2'}})
                missing, errors, ok = license_file.validate(Path('.'), {'license':'mit', 'repo': {'name': 'test_repo2'}})
            except HTTP403ForbiddenError:
                self.skip_if_rate_limited()
            self.assertEqual(missing, [])
            self.assertEqual(errors, [])
            self.assertEqual(ok, [Path('LICENSE')])

    def test_validate_license_missing(self):
        with ChDir():
            license_file = LicenseFile()
            try:
               missing, errors, ok = license_file.validate(Path('.'), {'license':'mit', 'repo': {'name': 'test_repo2'}})
            except HTTP403ForbiddenError:
                self.skip_if_rate_limited()
            self.assertEqual(missing, [Path('LICENSE')])
            self.assertEqual(errors, [])
            self.assertEqual(ok, [])

    def test_validate_license_error(self):
        with ChDir():
            license_file = LicenseFile()
            # License doesn't have the year fullname replacement
            try:
                license_file.write(Path('.'), {'license': 'mpl-2.0'})
                missing, errors, ok = license_file.validate(Path('.'), {'license':'mit', 'repo': {'name': 'test_repo2'}})
            except HTTP403ForbiddenError:
                self.skip_if_rate_limited()
            self.assertEqual(missing, [])
            self.assertEqual(errors, [Path('LICENSE')])
            self.assertEqual(ok, [])

    def test_override_year(self):
        license_file = LicenseFile()
        try:
            resp = license_file.dryrun(Path('.'), {'license':'mit', 'repo': {'name': 'test_repo2'}, 'license_year': 1880})
        except HTTP403ForbiddenError:
            self.skip_if_rate_limited()

        self.assertEqual(list(resp.keys()), [Path('LICENSE')])
        self.assertIn('1880', resp[Path('LICENSE')])
        self.assertIn(' test_repo2 Developers', resp[Path('LICENSE')])

    def test_each_license_render_content(self):
        for license_name in LicenseOptionsEnum:
            with self.subTest(license=license_name):
                # Test that it renders content
                try:
                    license_content = LicenseFile().render_content(context={'license': license_name, 'repo': {'name': 'test_repo_name'}})
                except HTTP403ForbiddenError:
                    self.skip_if_rate_limited()
                self.assertIsNotNone(license_content)
                self.assertNotIn('[year]', license_content)
                self.assertNotIn('[fullname]', license_content)
                self.assertGreater(len(license_content), 1)
                if license in [LicenseOptionsEnum.MIT, LicenseOptionsEnum.BSD_2_Clause, LicenseOptionsEnum.BSD_3_Clause]:
                    self.assertIn(f'{date.today().year}', license_content)
                    self.assertIn('test_repo_name', license_content)
