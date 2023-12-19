from datetime import date
from functools import wraps
from pathlib import Path
import unittest
from unittest.mock import MagicMock, patch

from fastcore.net import HTTP404NotFoundError

from nskit.common.contextmanagers import ChDir
from nskit.mixer.components import license_file
from nskit.mixer.components.license_file import (
    _get_license_content,
    LicenseFile,
    LicenseOptionsEnum,
)


def mock_gh_api(func):

    @patch.object(license_file, 'GhApi', autospec=True)
    @wraps(func)
    def mocked_call(self, GhApi):
        licenses = MagicMock()
        license_content_mit = MagicMock()
        license_content_mit.body = '[year] [fullname] abc'
        license_content_other = MagicMock()
        license_content_other.body = 'abc'
        def get(license):
            if license in ['mit', 'bsd-2-clause', 'bsd-3-clause']:
                return license_content_mit
            elif license in LicenseOptionsEnum:
                return license_content_other
            else:
                raise HTTP404NotFoundError(None, None, None)

        licenses.get.side_effect = get
        client = GhApi()
        GhApi.reset_mock()
        client.licenses = licenses
        return func(self, GhApi)

    return mocked_call


class LicenseFileTestCase(unittest.TestCase):

    # @patch.object(license_file, 'GhApi', autospec=True)
    @mock_gh_api
    def test_get_license_content_cache(self, GhApi):
        # We need to clear the cache here on the test
        _get_license_content.cache_clear()
        self.assertEqual(f'{date.today().year} test_repo Developers abc', LicenseFile().render_content({'license': 'mit', 'name': 'test_repo'}))
        GhApi.assert_called_once_with()
        GhApi().licenses.get.assert_called_once_with('mit')
        GhApi().licenses.get.reset_mock()
        GhApi.reset_mock()
        self.assertEqual(f'{date.today().year} test_repo2 Developers abc', LicenseFile().render_content({'license': 'mit', 'name': 'test_repo2'}))
        GhApi.assert_not_called()
        GhApi().licenses.get.assert_not_called()

    def test_write_no_license(self):
        with ChDir():
            self.assertFalse(Path('LICENSE').exists())
            self.assertFalse(Path('COPYING').exists())
            self.assertFalse(Path('COPYING.LESSER').exists())
            self.assertFalse(Path('UNLICENSE').exists())
            pre = [u for u in Path.cwd().glob('*')]
            resp = LicenseFile().write(Path('.'), {'license':'not-a-license'})
            post = [u for u in Path.cwd().glob('*')]
            self.assertFalse(Path('LICENSE').exists())
            self.assertFalse(Path('COPYING').exists())
            self.assertFalse(Path('COPYING.LESSER').exists())
            self.assertFalse(Path('UNLICENSE').exists())
            self.assertEqual(pre, post)
            self.assertEqual(resp, {})

    def test_dry_run_no_license(self):
        dry_run = LicenseFile().dryrun(Path('.'), {'license':'not-a-license'})
        self.assertEqual(dry_run, {})

    def test_validate_no_license(self):
        with ChDir():
            self.assertFalse(Path('LICENSE').exists())
            self.assertFalse(Path('COPYING').exists())
            self.assertFalse(Path('COPYING.LESSER').exists())
            self.assertFalse(Path('UNLICENSE').exists())
            pre = [u for u in Path.cwd().glob('*')]
            license = LicenseFile()
            resp = license.write(Path('.'), {'license':'not-a-license'})
            post = [u for u in Path.cwd().glob('*')]
            self.assertEqual(pre, post)
            self.assertEqual(resp, {})
            missing, errors, ok = license.validate(Path('.'), {'license': 'not-a-license'})
            self.assertEqual(missing, [])
            self.assertEqual(errors, [])
            self.assertEqual(ok, [])

    @mock_gh_api
    def test_write_license(self, GhApi):
        with ChDir():
            self.assertFalse(Path('LICENSE').exists())
            self.assertFalse(Path('COPYING').exists())
            self.assertFalse(Path('COPYING.LESSER').exists())
            self.assertFalse(Path('UNLICENSE').exists())
            pre = [u for u in Path.cwd().glob('*')]
            license = LicenseFile()
            resp = license.write(Path('.'), {'license':'mit', 'name': 'test_repo2'})
            post = [u for u in Path.cwd().glob('*')]
            self.assertTrue(Path('LICENSE').exists())
            self.assertFalse(Path('COPYING').exists())
            self.assertFalse(Path('COPYING.LESSER').exists())
            self.assertFalse(Path('UNLICENSE').exists())
            self.assertNotEqual(pre, post)
            self.assertEqual(resp, {Path('LICENSE'): f'{date.today().year} test_repo2 Developers abc'})

    @mock_gh_api
    def test_dry_run_license(self, GhApi):
        license = LicenseFile()
        resp = license.dryrun(Path('.'), {'license':'mit', 'name': 'test_repo2'})
        self.assertEqual(resp, {Path('LICENSE'): f'{date.today().year} test_repo2 Developers abc'})

    @mock_gh_api
    def test_validate_license_ok(self, GhApi):
        with ChDir():
            license = LicenseFile()
            resp = license.write(Path('.'), {'license':'mit', 'name': 'test_repo2'})
            missing, errors, ok = license.validate(Path('.'), {'license':'mit', 'name': 'test_repo2'})
            self.assertEqual(missing, [])
            self.assertEqual(errors, [])
            self.assertEqual(ok, [Path('LICENSE')])

    @mock_gh_api
    def test_validate_license_missing(self, GhApi):
        with ChDir():
            license = LicenseFile()
            missing, errors, ok = license.validate(Path('.'), {'license':'mit', 'name': 'test_repo2'})
            self.assertEqual(missing, [Path('LICENSE')])
            self.assertEqual(errors, [])
            self.assertEqual(ok, [])

    @mock_gh_api
    def test_validate_license_error(self, GhApi):
        with ChDir():
            license = LicenseFile()
            # License doesn't have the year fullname replacement
            license.write(Path('.'), {'license': 'mpl-2.0'})
            missing, errors, ok = license.validate(Path('.'), {'license':'mit', 'name': 'test_repo2'})
            self.assertEqual(missing, [])
            self.assertEqual(errors, [Path('LICENSE')])
            self.assertEqual(ok, [])

    @mock_gh_api
    def test_override_year(self, GhApi):
        license = LicenseFile()
        resp = license.dryrun(Path('.'), {'license':'mit', 'name': 'test_repo2', 'license_year': 2022})
        self.assertEqual(resp, {Path('LICENSE'): '2022 test_repo2 Developers abc'})

    def test_license_filename(self):
        for license in [
            LicenseOptionsEnum.MIT,
            LicenseOptionsEnum.Apache_2_0,
            LicenseOptionsEnum.BSD_2_Clause,
            LicenseOptionsEnum.BSD_3_Clause,
            LicenseOptionsEnum.BSL_1_0,
            LicenseOptionsEnum.CC0_1_0,
            LicenseOptionsEnum.EPL_2_0,
            LicenseOptionsEnum.MIT,
            LicenseOptionsEnum.MPL_2_0
            ]:
            with self.subTest(license=license):
                self.assertEqual(LicenseFile().render_name(context={'license': license}), 'LICENSE')

    def test_copying_filename(self):
        for license in [
            LicenseOptionsEnum.AGPL_3_0,
            LicenseOptionsEnum.GPL_2_0,
            LicenseOptionsEnum.GPL_3_0,
            ]:
            with self.subTest(license=license):
                self.assertEqual(LicenseFile().render_name(context={'license': license}), 'COPYING')

    def test_copying_lesser_filename(self):
        for license in [
            LicenseOptionsEnum.LGPL_2_1
            ]:
            with self.subTest(license=license):
                self.assertEqual(LicenseFile().render_name(context={'license': license}), 'COPYING.LESSER')

    def test_unlicense_filename(self):
        for license in [
            LicenseOptionsEnum.Unlicense
            ]:
            with self.subTest(license=license):
                self.assertEqual(LicenseFile().render_name(context={'license': license}), 'UNLICENSE')

    def test_no_license_render_name(self):
        self.assertIsNone(LicenseFile().render_name())

    def test_mismatching_license_render_name(self):
        self.assertIsNone(LicenseFile().render_name(context={'license': 'abcdef'}))

    def test_no_license_render_content(self):
        self.assertIsNone(LicenseFile().render_content(context={}))

    def test_mismatching_license_render_content(self):
        self.assertIsNone(LicenseFile().render_content(context={'license': 'abcdef'}))

    def test_each_license_render_name(self):
        for license in LicenseOptionsEnum:
            with self.subTest(license=license):
                # Test that it renders name
                self.assertIsNotNone(LicenseFile().render_name(context={'license': license}))

    @mock_gh_api
    def test_each_license_render_content(self, GhApi):
        for license in LicenseOptionsEnum:
            with self.subTest(license=license):
                # Test that it renders content
                license_content = LicenseFile().render_content(context={'license': license, 'name': 'test_repo_name'})
                self.assertIsNotNone(license_content)
                self.assertNotIn('[year]', license_content)
                self.assertNotIn('[fullname]', license_content)
                self.assertGreater(len(license_content), 1)
                if license in [LicenseOptionsEnum.MIT, LicenseOptionsEnum.BSD_2_Clause, LicenseOptionsEnum.BSD_3_Clause]:
                    self.assertIn(f'{date.today().year}', license_content)
                    self.assertIn('test_repo_name', license_content)
