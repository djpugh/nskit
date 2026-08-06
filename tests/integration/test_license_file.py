import unittest
from contextlib import contextmanager
from datetime import date
from pathlib import Path

from fastcore.net import HTTP403ForbiddenError

from nskit.common.contextmanagers import ChDir
from nskit.mixer.components.license_file import LicenseFile, LicenseOptionsEnum

# These tests fetch licence text from the GitHub API unauthenticated, so they are
# rate limited on shared CI runners. The error type depends on the ghapi major:
# 1.x raises fastcore's HTTP403ForbiddenError, while 2.x wraps transport errors in
# fastspec's APIError. Both are caught so the skip works either way.
_API_ERRORS: tuple = (HTTP403ForbiddenError,)
try:
    from fastspec.errors import APIError
except ImportError:  # ghapi 1.x does not use fastspec
    pass
else:
    _API_ERRORS += (APIError,)


@contextmanager
def skip_if_rate_limited():
    """Skip the test if the GitHub API rate limit was hit, otherwise re-raise.

    Only rate limiting is tolerated. Any other API failure is a real result and is
    left to fail, so this cannot quietly mask a broken client.
    """
    try:
        yield
    except _API_ERRORS as exc:
        if "rate limit" in str(exc).lower():
            raise unittest.SkipTest(f"GitHub API rate limited: {exc}") from None
        raise


class LicenseFileFunctionalTestCase(unittest.TestCase):
    def test_write_license(self):
        with ChDir():
            self.assertFalse(Path("LICENSE").exists())
            self.assertFalse(Path("COPYING").exists())
            self.assertFalse(Path("COPYING.LESSER").exists())
            self.assertFalse(Path("UNLICENSE").exists())
            pre = list(Path.cwd().glob("*"))
            license_file = LicenseFile()
            with skip_if_rate_limited():
                resp = license_file.write(Path("."), {"license": "mit", "repo": {"name": "test_repo2"}})
            post = list(Path.cwd().glob("*"))
            self.assertTrue(Path("LICENSE").exists())
            self.assertFalse(Path("COPYING").exists())
            self.assertFalse(Path("COPYING.LESSER").exists())
            self.assertFalse(Path("UNLICENSE").exists())
            self.assertNotEqual(pre, post)
            self.assertEqual(list(resp.keys()), [Path("LICENSE")])
            self.assertIn(f"{date.today().year} ", resp[Path("LICENSE")])
            self.assertIn(" test_repo2 Developers", resp[Path("LICENSE")])

    def test_dry_run_license(self):
        license_file = LicenseFile()
        with skip_if_rate_limited():
            resp = license_file.dryrun(Path("."), {"license": "mit", "repo": {"name": "test_repo2"}})

        self.assertEqual(list(resp.keys()), [Path("LICENSE")])
        self.assertIn(f"{date.today().year} ", resp[Path("LICENSE")])
        self.assertIn(" test_repo2 Developers", resp[Path("LICENSE")])

    def test_validate_license_ok(self):
        with ChDir():
            license_file = LicenseFile()
            with skip_if_rate_limited():
                license_file.write(Path("."), {"license": "mit", "repo": {"name": "test_repo2"}})
                missing, errors, ok = license_file.validate(
                    Path("."), {"license": "mit", "repo": {"name": "test_repo2"}}
                )
            self.assertEqual(missing, [])
            self.assertEqual(errors, [])
            self.assertEqual(ok, [Path("LICENSE")])

    def test_validate_license_missing(self):
        with ChDir():
            license_file = LicenseFile()
            with skip_if_rate_limited():
                missing, errors, ok = license_file.validate(
                    Path("."), {"license": "mit", "repo": {"name": "test_repo2"}}
                )
            self.assertEqual(missing, [Path("LICENSE")])
            self.assertEqual(errors, [])
            self.assertEqual(ok, [])

    def test_validate_license_error(self):
        with ChDir():
            license_file = LicenseFile()
            # License doesn't have the year fullname replacement
            with skip_if_rate_limited():
                license_file.write(Path("."), {"license": "mpl-2.0"})
                missing, errors, ok = license_file.validate(
                    Path("."), {"license": "mit", "repo": {"name": "test_repo2"}}
                )
            self.assertEqual(missing, [])
            self.assertEqual(errors, [Path("LICENSE")])
            self.assertEqual(ok, [])

    def test_override_year(self):
        license_file = LicenseFile()
        with skip_if_rate_limited():
            resp = license_file.dryrun(
                Path("."), {"license": "mit", "repo": {"name": "test_repo2"}, "license_year": 1880}
            )

        self.assertEqual(list(resp.keys()), [Path("LICENSE")])
        self.assertIn("1880", resp[Path("LICENSE")])
        self.assertIn(" test_repo2 Developers", resp[Path("LICENSE")])

    def test_each_license_render_content(self):
        for license_name in LicenseOptionsEnum:
            with self.subTest(license=license_name):
                # Test that it renders content
                with skip_if_rate_limited():
                    license_content = LicenseFile().render_content(
                        context={"license": license_name, "repo": {"name": "test_repo_name"}}
                    )
                self.assertIsNotNone(license_content)
                self.assertNotIn("[year]", license_content)
                self.assertNotIn("[fullname]", license_content)
                self.assertGreater(len(license_content), 1)
                if license_name in [
                    LicenseOptionsEnum.MIT,
                    LicenseOptionsEnum.BSD_2_Clause,
                    LicenseOptionsEnum.BSD_3_Clause,
                ]:
                    self.assertIn(f"{date.today().year}", license_content)
                    self.assertIn("test_repo_name", license_content)


class SkipIfRateLimitedTestCase(unittest.TestCase):
    """The helper must skip on rate limiting only."""

    def test_covers_both_ghapi_error_types(self):
        """Whichever ghapi is installed, its transport error is caught."""
        self.assertIn(HTTP403ForbiddenError, _API_ERRORS)
        try:
            from fastspec.errors import APIError
        except ImportError:
            self.assertEqual(_API_ERRORS, (HTTP403ForbiddenError,))
        else:
            self.assertIn(APIError, _API_ERRORS)

    @unittest.skipUnless(len(_API_ERRORS) > 1, "fastspec (ghapi 2.x) not installed")
    def test_skips_on_rate_limit(self):
        from fastspec.errors import APIError

        with self.assertRaises(unittest.SkipTest):
            with skip_if_rate_limited():
                raise APIError("API rate limit exceeded for 1.2.3.4")

    @unittest.skipUnless(len(_API_ERRORS) > 1, "fastspec (ghapi 2.x) not installed")
    def test_reraises_other_api_errors(self):
        """A non-rate-limit API failure is a real result, not something to skip."""
        from fastspec.errors import APIError

        with self.assertRaises(APIError):
            with skip_if_rate_limited():
                raise APIError("Not Found")

    def test_reraises_unrelated_errors(self):
        """Matching on the message alone must not swallow other exception types."""
        with self.assertRaises(ValueError):
            with skip_if_rate_limited():
                raise ValueError("rate limit")


if __name__ == "__main__":
    unittest.main()
