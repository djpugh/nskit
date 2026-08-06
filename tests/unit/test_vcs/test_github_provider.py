"""Unit tests for the GithubRepoClient contents/branch/pages/release helpers."""

from __future__ import annotations

import base64
import unittest
from unittest.mock import MagicMock, patch

from fastcore.net import HTTP404NotFoundError
from pydantic import ValidationError

from nskit.vcs.providers.github import GithubRepoClient, GithubSettings
from nskit.vcs.providers.github import provider as github_module
from nskit.vcs.providers.github.rulesets import Enforcement, Ruleset


def _not_found() -> HTTP404NotFoundError:
    """Build a 404 the way fastcore raises it, without a live request."""
    return HTTP404NotFoundError("url", "hdrs", "fp")


class GithubRepoClientTestCase(unittest.TestCase):
    """Base case wiring a client to a mocked API client."""

    def setUp(self) -> None:
        """Patch the client factory and build a client against a fake org.

        The provider constructs clients via ``ghapi_compat.sync_ghapi`` rather
        than ``GhApi`` directly, so that is what has to be patched.
        """
        patcher = patch.object(github_module, "sync_ghapi")
        self.addCleanup(patcher.stop)
        self.gh_api_cls = patcher.start()
        self.api = self.gh_api_cls.return_value
        settings = GithubSettings(token="secret-token", organisation="acme", use_gh_cli=False)
        self.client = GithubRepoClient(settings)
        self.org = "acme"


class TestGetFileContents(GithubRepoClientTestCase):
    """Reading file contents."""

    def test_decodes_base64_content(self) -> None:
        """Content is base64-decoded to text."""
        self.api.repos.get_content.return_value = {"content": base64.b64encode(b"hello: world").decode("ascii")}
        self.assertEqual(self.client.get_file_contents("repo", "cfg.yaml"), "hello: world")

    def test_passes_ref_when_given(self) -> None:
        """An explicit ref is forwarded."""
        self.api.repos.get_content.return_value = {"content": base64.b64encode(b"x").decode("ascii")}
        self.client.get_file_contents("repo", "cfg.yaml", ref="v1")
        self.api.repos.get_content.assert_called_once_with(self.org, "repo", "cfg.yaml", ref="v1")

    def test_missing_file_returns_none(self) -> None:
        """A 404 is reported as None rather than raising."""
        self.api.repos.get_content.side_effect = _not_found()
        self.assertIsNone(self.client.get_file_contents("repo", "nope.yaml"))


class TestCreateOrUpdateFile(GithubRepoClientTestCase):
    """Writing a single file."""

    def test_new_file_sends_no_sha(self) -> None:
        """Creating a file omits the blob sha."""
        self.api.repos.get_content.side_effect = _not_found()
        self.client.create_or_update_file("repo", "a.txt", "body", "msg", branch="main")
        _, kwargs = self.api.repos.create_or_update_file_contents.call_args
        self.assertNotIn("sha", kwargs)
        self.assertEqual(base64.b64decode(kwargs["content"]).decode(), "body")
        self.assertEqual(kwargs["branch"], "main")

    def test_existing_file_sends_sha(self) -> None:
        """Updating a file supplies the existing sha, which GitHub requires."""
        self.api.repos.get_content.return_value = {"sha": "abc123"}
        self.client.create_or_update_file("repo", "a.txt", "body", "msg")
        _, kwargs = self.api.repos.create_or_update_file_contents.call_args
        self.assertEqual(kwargs["sha"], "abc123")


class TestBranches(GithubRepoClientTestCase):
    """Branch creation."""

    def test_create_branch_points_at_source_head(self) -> None:
        """A new branch is created at the source branch's head sha."""
        self.api.git.get_ref.return_value = {"object": {"sha": "deadbeef"}}
        self.client.create_branch("repo", "feature", "main")
        self.api.git.get_ref.assert_called_once_with(self.org, "repo", "heads/main")
        self.api.git.create_ref.assert_called_once_with(self.org, "repo", "refs/heads/feature", "deadbeef")

    def test_orphan_branch_commit_has_no_parents(self) -> None:
        """An orphan branch's commit has no parents, so it carries no history."""
        self.api.git.create_blob.return_value = {"sha": "blob1"}
        self.api.git.create_tree.return_value = {"sha": "tree1"}
        self.api.git.create_commit.return_value = {"sha": "commit1"}

        self.client.create_orphan_branch("repo", "gh-pages", {"index.html": "<html/>"}, message="init")

        _, commit_kwargs = self.api.git.create_commit.call_args
        self.assertEqual(commit_kwargs["parents"], [])
        self.assertEqual(commit_kwargs["tree"], "tree1")
        self.api.git.create_ref.assert_called_once_with(self.org, "repo", "refs/heads/gh-pages", "commit1")

    def test_orphan_branch_creates_a_blob_per_file(self) -> None:
        """Each file becomes a blob entry in the tree."""
        self.api.git.create_blob.return_value = {"sha": "blob"}
        self.api.git.create_tree.return_value = {"sha": "tree"}
        self.api.git.create_commit.return_value = {"sha": "commit"}

        self.client.create_orphan_branch("repo", "gh-pages", {"a.html": "a", "b.html": "b"})

        self.assertEqual(self.api.git.create_blob.call_count, 2)
        _, tree_kwargs = self.api.git.create_tree.call_args
        self.assertEqual(sorted(entry["path"] for entry in tree_kwargs["tree"]), ["a.html", "b.html"])


class TestPages(GithubRepoClientTestCase):
    """GitHub Pages."""

    def test_enable_pages_reports_true_when_created(self) -> None:
        """Enabling Pages returns True and sends the source config."""
        self.assertTrue(self.client.enable_pages("repo", branch="gh-pages"))
        self.api.repos.create_pages_site.assert_called_once_with(
            self.org, "repo", source={"branch": "gh-pages", "path": "/"}
        )

    def test_already_enabled_reports_false(self) -> None:
        """An "already enabled" conflict is not an error."""
        self.api.repos.create_pages_site.side_effect = ValueError("Pages is already enabled")
        with patch.object(github_module, "HTTPError", ValueError):
            self.assertFalse(self.client.enable_pages("repo"))


class TestReleases(GithubRepoClientTestCase):
    """Release listing and lookup."""

    def _paged(self, releases: list[dict]) -> None:
        with_paged = patch.object(github_module, "paged", return_value=[releases])
        self.addCleanup(with_paged.stop)
        with_paged.start()

    def test_drafts_are_always_excluded(self) -> None:
        """Draft releases never appear."""
        self._paged([{"tag_name": "v1", "draft": True}, {"tag_name": "v2", "draft": False}])
        self.assertEqual(self.client.get_available_versions("repo"), ["v2"])

    def test_prereleases_excluded_by_default(self) -> None:
        """Prereleases are opt-in."""
        self._paged([{"tag_name": "v2rc", "prerelease": True}, {"tag_name": "v1", "prerelease": False}])
        self.assertEqual(self.client.get_available_versions("repo"), ["v1"])

    def test_prereleases_included_on_request(self) -> None:
        """Prereleases appear when asked for."""
        self._paged([{"tag_name": "v2rc", "prerelease": True}, {"tag_name": "v1", "prerelease": False}])
        self.assertEqual(self.client.get_available_versions("repo", include_prereleases=True), ["v2rc", "v1"])

    def test_missing_tag_returns_none(self) -> None:
        """A 404 on a tag lookup is reported as None."""
        self.api.repos.get_release_by_tag.side_effect = _not_found()
        self.assertIsNone(self.client.get_release_by_tag("repo", "v9"))

    def test_missing_latest_release_returns_none(self) -> None:
        """A repo with no releases reports None."""
        self.api.repos.get_latest_release.side_effect = _not_found()
        self.assertIsNone(self.client.get_latest_release("repo"))


class TestSearch(GithubRepoClientTestCase):
    """Repository search."""

    def test_query_is_passed_through_and_items_returned(self) -> None:
        """The query is forwarded verbatim and items unwrapped."""
        self.api.search.repos.return_value = {"items": [{"name": "a"}, {"name": "b"}]}
        result = self.client.search_repositories("org:acme topic:recipe")
        self.api.search.repos.assert_called_once_with(q="org:acme topic:recipe")
        self.assertEqual([r["name"] for r in result], ["a", "b"])

    def test_no_items_returns_empty_list(self) -> None:
        """A response without items yields an empty list."""
        self.api.search.repos.return_value = {}
        self.assertEqual(self.client.search_repositories("q"), [])


class TestRulesetMethods(GithubRepoClientTestCase):
    """Ruleset create/list/update/delete."""

    def test_create_sends_rendered_payload_and_returns_id(self) -> None:
        """The composed ruleset is rendered and the new ID returned."""
        self.api.repos.create_repo_ruleset.return_value = {"id": 77}
        ruleset = Ruleset(name="Protect main").block_deletion()
        self.assertEqual(self.client.create_ruleset("repo", ruleset), 77)
        _, kwargs = self.api.repos.create_repo_ruleset.call_args
        self.assertEqual(kwargs["name"], "Protect main")
        self.assertEqual(kwargs["rules"], [{"type": "deletion"}])

    def test_list_fetches_each_ruleset_in_full(self) -> None:
        """The summary list is expanded, because summaries omit rules."""
        self.api.repos.get_repo_rulesets.return_value = [{"id": 1}]
        self.api.repos.get_repo_ruleset.return_value = {
            "id": 1,
            "name": "Protect main",
            "enforcement": "active",
            "rules": [{"type": "deletion"}],
        }
        rulesets = self.client.list_rulesets("repo")
        self.assertEqual(len(rulesets), 1)
        self.assertEqual(rulesets[0].id, 1)
        self.assertEqual([r.type for r in rulesets[0].rules], ["deletion"])

    def test_list_returns_empty_when_absent(self) -> None:
        """A 404 yields an empty list."""
        self.api.repos.get_repo_rulesets.side_effect = _not_found()
        self.assertEqual(self.client.list_rulesets("repo"), [])

    def test_update_forwards_changes(self) -> None:
        """Enforcement changes are forwarded."""
        self.client.update_ruleset("repo", 5, enforcement=Enforcement.disabled.value)
        self.api.repos.update_repo_ruleset.assert_called_once_with(self.org, "repo", 5, enforcement="disabled")

    def test_delete_forwards_id(self) -> None:
        """Deletion targets the given ruleset ID."""
        self.client.delete_ruleset("repo", 9)
        self.api.repos.delete_repo_ruleset.assert_called_once_with(self.org, "repo", 9)


class TestGhCliToken(unittest.TestCase):
    """The gh CLI token source."""

    def test_returns_token_on_success(self) -> None:
        """A successful gh call yields the trimmed token."""
        completed = MagicMock(returncode=0, stdout="gho_abc123\n")
        with patch.object(github_module.subprocess, "run", return_value=completed):
            self.assertEqual(github_module.gh_cli_token(), "gho_abc123")

    def test_returns_none_when_gh_missing(self) -> None:
        """A missing gh binary yields None rather than raising."""
        with patch.object(github_module.subprocess, "run", side_effect=FileNotFoundError):
            self.assertIsNone(github_module.gh_cli_token())

    def test_returns_none_when_not_authenticated(self) -> None:
        """A non-zero exit yields None."""
        completed = MagicMock(returncode=1, stdout="")
        with patch.object(github_module.subprocess, "run", return_value=completed):
            self.assertIsNone(github_module.gh_cli_token())

    def test_not_used_unless_opted_in(self) -> None:
        """Settings do not consult the gh CLI unless use_gh_cli is set.

        Ambient credentials must not be picked up silently by a caller that
        supplied no token: with no token and no opted-in fallback, settings
        validation fails rather than quietly finding one.
        """
        with patch.object(github_module, "gh_cli_token") as token:
            with self.assertRaises(ValidationError):
                GithubSettings(organisation="acme", use_gh_cli=False)
            token.assert_not_called()

    def test_used_when_opted_in(self) -> None:
        """With use_gh_cli set, a gh token satisfies settings validation."""
        with patch.object(github_module, "gh_cli_token", return_value="gho_from_cli") as token:
            settings = GithubSettings(organisation="acme", use_gh_cli=True)
            token.assert_called_once()
            self.assertEqual(settings.token.get_secret_value(), "gho_from_cli")


if __name__ == "__main__":
    unittest.main()
