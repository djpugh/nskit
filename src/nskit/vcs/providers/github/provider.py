"""Github provider using ghapi."""

import base64
import subprocess  # nosec: B404
from enum import Enum
from typing import Any, Optional

try:
    from fastcore.net import HTTP404NotFoundError, HTTPError

    # GhApi and paged are not imported here: clients are constructed via
    # nskit.common.ghapi_compat.sync_ghapi and pagination goes through
    # ghapi_compat.paged, so the synchronous forms are selected on ghapi 2.x.
    # This import still serves as the availability check that produces the
    # "install nskit[github]" hint below.
    from ghapi.all import GhDeviceAuth, Scope
    from ghapi.auth import _def_clientid
except ImportError:
    raise ImportError(
        "Github Provider requires installing extra dependencies (ghapi), use pip install nskit[github]"
    ) from None
from pydantic import Field, HttpUrl, SecretStr, ValidationInfo, field_validator

from nskit._logging import logger_factory
from nskit.common.configuration import BaseConfiguration, SettingsConfigDict
from nskit.common.ghapi_compat import paged, sync_ghapi
from nskit.vcs.providers.abstract import RepoClient, VCSProviderSettings
from nskit.vcs.providers.github.rulesets import Ruleset

logger = logger_factory.get(__name__)


class GithubBranchProtectionSettings(BaseConfiguration):
    """Github default branch protection settings.

    Maps to the GitHub branch-protection API. Fields left as ``None`` are
    omitted so the provider only sends what is explicitly configured.
    """

    model_config = SettingsConfigDict(env_prefix="GITHUB_BRANCH_PROTECTION_", env_file=".env", dotenv_extra="ignore")

    enabled: bool = False
    required_approving_review_count: Optional[int] = None
    require_code_owner_reviews: Optional[bool] = None
    dismiss_stale_reviews: Optional[bool] = None
    require_conversation_resolution: Optional[bool] = None
    enforce_admins: Optional[bool] = None
    required_status_checks: Optional[list[str]] = None
    allow_force_pushes: Optional[bool] = None
    allow_deletions: Optional[bool] = None


class GithubRepoSettings(BaseConfiguration):
    """Github Repo settings."""

    model_config = SettingsConfigDict(env_prefix="GITHUB_REPO_", env_file=".env", dotenv_extra="ignore")

    private: bool = True
    has_issues: Optional[bool] = None
    has_wiki: Optional[bool] = None
    has_downloads: Optional[bool] = None
    has_projects: Optional[bool] = None
    allow_squash_merge: Optional[bool] = None
    allow_merge_commit: Optional[bool] = None
    allow_rebase_merge: Optional[bool] = None
    delete_branch_on_merge: Optional[bool] = None
    auto_init: bool = False
    branch_protection: GithubBranchProtectionSettings = Field(default_factory=GithubBranchProtectionSettings)


def gh_cli_token() -> Optional[str]:
    """Return a token from the GitHub CLI, or ``None`` if unavailable.

    Shells ``gh auth token``, which is how a developer machine that has already
    run ``gh auth login`` holds its credential. Returns ``None`` rather than
    raising when ``gh`` is absent or not authenticated, so this can be used as
    one link in a fallback chain.
    """
    try:
        result = subprocess.run(  # nosec B603, B607 - fixed argv, no shell
            ["gh", "auth", "token"],
            capture_output=True,
            text=True,
            check=False,
        )
    except (FileNotFoundError, OSError):
        logger.debug("gh CLI not available for token lookup")
        return None
    if result.returncode != 0:
        logger.debug("gh auth token failed; not authenticated?")
        return None
    return result.stdout.strip() or None


class GithubSettings(VCSProviderSettings):
    """Github settings.

    Token resolution order:

    1. an explicitly provided ``token`` (or ``GITHUB_TOKEN`` in the environment);
    2. the GitHub CLI (``gh auth token``), when ``use_gh_cli`` is set;
    3. interactive device authentication, when ``interactive`` is set.

    Both fallbacks are opt-in. In particular ``use_gh_cli`` defaults to
    ``False``: picking up whatever credential happens to be sitting in the
    developer's ``gh`` login would mean a caller that supplied no token silently
    acquires one, which hides misconfiguration and surprises anything that
    expects "no token" to mean "no access".
    """

    model_config = SettingsConfigDict(env_prefix="GITHUB_", env_file=".env", dotenv_extra="ignore")

    interactive: bool = Field(False, description="Use Interactive Validation for token")
    use_gh_cli: bool = Field(
        False,
        description="Fall back to the GitHub CLI (gh auth token) when no token is set",
    )
    url: HttpUrl = "https://api.github.com"
    organisation: Optional[str] = Field(
        None, description="Organisation to work in, otherwise uses the user for the token"
    )
    token: SecretStr = Field(
        None,
        validate_default=True,
        description="Token to use for authentication, falls back to the gh CLI then interactive device authentication",
    )
    repo: GithubRepoSettings = Field(default_factory=GithubRepoSettings)

    @property
    def repo_client(self) -> "GithubRepoClient":
        """Get the instantiated repo client."""
        return GithubRepoClient(self)

    @field_validator("token", mode="before")
    @classmethod
    def _validate_token(cls, value, info: ValidationInfo):
        if value is not None:
            return value
        # Try the local gh CLI before prompting: on a developer machine it is
        # usually already authenticated, which avoids an interactive detour.
        if info.data.get("use_gh_cli", True):
            value = gh_cli_token()
            if value:
                logger.info("Using GitHub token from the gh CLI")
                return value
        if info.data.get("interactive", False):
            ghauth = GhDeviceAuth(_def_clientid, Scope.repo, Scope.delete_repo)
            print(ghauth.url_docs())
            ghauth.open_browser()
            value = ghauth.wait()
        return value


class GithubOrgType(Enum):
    """Org type, user or org."""

    user = "User"
    org = "Org"


class GithubRepoClient(RepoClient):
    """Client for managing github repos."""

    def __init__(self, config: GithubSettings):
        """Initialise the client."""
        self._config = config
        self._github = sync_ghapi(
            token=self._config.token.get_secret_value(), gh_host=str(self._config.url).rstrip("/")
        )
        # If the organisation is set, we get it, and assume that the token is valid
        # Otherwise default to the user
        if self._config.organisation:
            try:
                self._github.orgs.get(self._config.organisation)
                self._org_type = GithubOrgType.org
            except HTTP404NotFoundError:
                self._github.users.get_by_username(self._config.organisation)
                self._org_type = GithubOrgType.user
        else:
            self._config.organisation = self._github.users.get_authenticated()["login"]
            self._org_type = GithubOrgType.user

    def create(self, repo_name: str):
        """Create the repo in the user/organisation."""
        kwargs = {
            "name": repo_name,
            "private": self._config.repo.private,
            "has_issues": self._config.repo.has_issues,
            "has_wiki": self._config.repo.has_wiki,
            "has_downloads": self._config.repo.has_downloads,
            "has_projects": self._config.repo.has_projects,
            "allow_squash_merge": self._config.repo.allow_squash_merge,
            "allow_merge_commit": self._config.repo.allow_merge_commit,
            "allow_rebase_merge": self._config.repo.allow_rebase_merge,
            "auto_init": self._config.repo.auto_init,
            "delete_branch_on_merge": self._config.repo.delete_branch_on_merge,
        }
        if self._org_type == GithubOrgType.org:
            self._github.repos.create_in_org(self._config.organisation, **kwargs)
        else:
            self._github.repos.create_for_authenticated_user(**kwargs)

    def get_remote_url(self, repo_name: str) -> HttpUrl:
        """Get the remote url for the repo."""
        if self.check_exists(repo_name):
            return self._github.repos.get(self._config.organisation, repo_name)["html_url"]

    def get_clone_url(self, repo_name: str) -> HttpUrl:
        """Get the clone url for the repo."""
        if self.check_exists(repo_name):
            return self._github.repos.get(self._config.organisation, repo_name)["clone_url"]

    def delete(self, repo_name: str):
        """Delete the repo if it exists in the organisation/user."""
        if self.check_exists(repo_name):
            return self._github.repos.delete(self._config.organisation, repo_name)

    def check_exists(self, repo_name: str) -> bool:
        """Check if the repo exists in the organisation/user."""
        try:
            self._github.repos.get(self._config.organisation, repo_name)
            return True
        except HTTP404NotFoundError:
            return False

    def list(self) -> list[str]:
        """List the repos in the project."""
        repos = []
        if self._org_type == GithubOrgType.org:
            get_method = self._github.repos.list_for_org
        else:
            get_method = self._github.repos.list_for_user
        for u in paged(get_method, self._config.organisation, per_page=100):
            repos += [x["name"] for x in u]
        return repos

    def configure(self, repo_name: str, settings: Optional[dict[str, Any]] = None) -> None:
        """Apply repository-level settings (merge options, features) to the repo.

        Uses the configured ``GithubRepoSettings`` as defaults, overridden by any
        explicit ``settings``. Only non-``None`` values are sent to the API.
        """
        defaults = self._config.repo.model_dump(
            include={
                "private",
                "has_issues",
                "has_wiki",
                "has_downloads",
                "has_projects",
                "allow_squash_merge",
                "allow_merge_commit",
                "allow_rebase_merge",
                "delete_branch_on_merge",
            },
        )
        defaults.update(settings or {})
        kwargs = {k: v for k, v in defaults.items() if v is not None}
        if not kwargs:
            return
        self._github.repos.update(self._config.organisation, repo_name, **kwargs)
        logger.info(f"Configured repository {repo_name}")

    def set_branch_protection(
        self,
        repo_name: str,
        branch: str,
        rules: Optional[dict[str, Any]] = None,
    ) -> None:
        """Apply branch protection to ``branch`` using the GitHub API.

        Uses the configured ``GithubBranchProtectionSettings`` as defaults,
        overridden by any explicit ``rules``. A no-op unless protection is
        enabled (either via config or an explicit ``rules`` payload).
        """
        config = self._config.repo.branch_protection
        enabled = config.enabled or bool(rules)
        if not enabled:
            return

        required_reviews = None
        if config.required_approving_review_count is not None or config.require_code_owner_reviews is not None:
            required_reviews = {}
            if config.required_approving_review_count is not None:
                required_reviews["required_approving_review_count"] = config.required_approving_review_count
            if config.require_code_owner_reviews is not None:
                required_reviews["require_code_owner_reviews"] = config.require_code_owner_reviews
            if config.dismiss_stale_reviews is not None:
                required_reviews["dismiss_stale_reviews"] = config.dismiss_stale_reviews

        status_checks = None
        if config.required_status_checks is not None:
            status_checks = {"strict": True, "contexts": config.required_status_checks}

        payload = {
            "required_status_checks": status_checks,
            "enforce_admins": config.enforce_admins,
            "required_pull_request_reviews": required_reviews,
            "restrictions": None,
            "required_conversation_resolution": config.require_conversation_resolution,
            "allow_force_pushes": config.allow_force_pushes,
            "allow_deletions": config.allow_deletions,
        }
        payload.update(rules or {})
        self._github.repos.update_branch_protection(self._config.organisation, repo_name, branch, **payload)
        logger.info(f"Applied branch protection to {repo_name}@{branch}")

    # -- Rulesets ----------------------------------------------------------
    # Rulesets are GitHub's successor to classic branch protection. See
    # nskit.vcs.providers.github.rulesets for the composable rule models.
    def create_ruleset(self, repo_name: str, ruleset: "Ruleset") -> Optional[int]:
        """Create ``ruleset`` on the repo and return its server-assigned ID.

        Note the ordering implication when populating a brand-new repo: apply
        rulesets *after* the initial push. Creating a protective ruleset first
        and then relaxing it to let the push through leaves a window in which
        the repo is unprotected, and a crash mid-way leaves it that way.
        """
        result = self._github.repos.create_repo_ruleset(self._config.organisation, repo_name, **ruleset.to_api())
        ruleset_id = result.get("id") if hasattr(result, "get") else None
        logger.info(f"Created ruleset '{ruleset.name}' on {repo_name}")
        return ruleset_id

    def list_rulesets(self, repo_name: str) -> "list[Ruleset]":
        """List the repo's rulesets, parsed into :class:`Ruleset` models.

        Returns an empty list when the repo has none. Each result carries its
        ``id`` so it can be updated or deleted.
        """
        from nskit.vcs.providers.github.rulesets import Ruleset

        try:
            response = self._github.repos.get_repo_rulesets(self._config.organisation, repo_name)
        except HTTP404NotFoundError:
            return []
        raw = response if isinstance(response, list) else []
        # The list endpoint returns summaries without ``rules``; fetch each in
        # full so the parsed model reflects the actual rule set.
        rulesets: list[Ruleset] = []
        for summary in raw:
            ruleset_id = summary.get("id") if hasattr(summary, "get") else None
            if ruleset_id is None:
                continue
            try:
                detail = self._github.repos.get_repo_ruleset(self._config.organisation, repo_name, ruleset_id)
            except HTTP404NotFoundError:  # pragma: no cover - race on delete
                continue
            rulesets.append(Ruleset.from_api(dict(detail)))
        return rulesets

    def update_ruleset(self, repo_name: str, ruleset_id: int, **changes: Any) -> None:
        """Update fields on an existing ruleset (e.g. ``enforcement="disabled"``)."""
        self._github.repos.update_repo_ruleset(self._config.organisation, repo_name, ruleset_id, **changes)
        logger.info(f"Updated ruleset {ruleset_id} on {repo_name}")

    def delete_ruleset(self, repo_name: str, ruleset_id: int) -> None:
        """Delete a ruleset from the repo."""
        self._github.repos.delete_repo_ruleset(self._config.organisation, repo_name, ruleset_id)
        logger.info(f"Deleted ruleset {ruleset_id} from {repo_name}")

    # -- Contents ----------------------------------------------------------
    def get_file_contents(self, repo_name: str, path: str, ref: Optional[str] = None) -> Optional[str]:
        """Return the decoded text of a file, or ``None`` if it does not exist.

        Args:
            repo_name: Repository name within the configured organisation.
            path: Path to the file within the repo.
            ref: Branch, tag or commit to read from. Defaults to the default branch.
        """
        kwargs = {"ref": ref} if ref else {}
        try:
            result = self._github.repos.get_content(self._config.organisation, repo_name, path, **kwargs)
        except HTTP404NotFoundError:
            return None
        content = result.get("content") if hasattr(result, "get") else None
        if content is None:
            return None
        return base64.b64decode(content).decode("utf-8")

    def create_or_update_file(
        self,
        repo_name: str,
        path: str,
        content: str,
        message: str,
        branch: Optional[str] = None,
    ) -> None:
        """Create or replace a single file, committing directly to ``branch``.

        Existing files are updated in place: their blob SHA is looked up first,
        because GitHub rejects an update that does not supply it.
        """
        kwargs: dict[str, Any] = {
            "message": message,
            "content": base64.b64encode(content.encode("utf-8")).decode("ascii"),
        }
        if branch:
            kwargs["branch"] = branch
        try:
            existing = self._github.repos.get_content(
                self._config.organisation, repo_name, path, **({"ref": branch} if branch else {})
            )
            if hasattr(existing, "get") and existing.get("sha"):
                kwargs["sha"] = existing["sha"]
        except HTTP404NotFoundError:
            pass
        self._github.repos.create_or_update_file_contents(self._config.organisation, repo_name, path, **kwargs)
        logger.info(f"Wrote {path} to {repo_name}" + (f"@{branch}" if branch else ""))

    # -- Branches ----------------------------------------------------------
    def create_branch(self, repo_name: str, branch: str, from_branch: str) -> None:
        """Create ``branch`` pointing at the head of ``from_branch``."""
        source = self._github.git.get_ref(self._config.organisation, repo_name, f"heads/{from_branch}")
        self._github.git.create_ref(
            self._config.organisation, repo_name, f"refs/heads/{branch}", source["object"]["sha"]
        )
        logger.info(f"Created branch {branch} from {from_branch} on {repo_name}")

    def create_orphan_branch(
        self,
        repo_name: str,
        branch: str,
        files: dict[str, str],
        message: str = "Initial commit",
    ) -> None:
        """Create a branch with no history, containing exactly ``files``.

        Builds the commit through the git data API (blob → tree → commit → ref)
        with no ``parents``, which is what makes the branch orphaned. Useful for
        a docs branch such as ``gh-pages`` that should not carry the main
        branch's history.

        Args:
            repo_name: Repository name within the configured organisation.
            branch: Branch to create.
            files: Mapping of path to text content.
            message: Commit message.
        """
        org = self._config.organisation
        tree = []
        for path, content in files.items():
            blob = self._github.git.create_blob(org, repo_name, content=content, encoding="utf-8")
            tree.append({"path": path, "mode": "100644", "type": "blob", "sha": blob["sha"]})
        tree_result = self._github.git.create_tree(org, repo_name, tree=tree)
        commit = self._github.git.create_commit(org, repo_name, message=message, tree=tree_result["sha"], parents=[])
        self._github.git.create_ref(org, repo_name, f"refs/heads/{branch}", commit["sha"])
        logger.info(f"Created orphan branch {branch} on {repo_name} with {len(files)} file(s)")

    # -- Pages -------------------------------------------------------------
    def enable_pages(self, repo_name: str, branch: str = "gh-pages", path: str = "/") -> bool:
        """Enable GitHub Pages for the repo, serving from ``branch``/``path``.

        Returns ``True`` when Pages was enabled by this call and ``False`` when
        it was already enabled, so callers can distinguish the two without
        treating "already enabled" as a failure.
        """
        try:
            self._github.repos.create_pages_site(
                self._config.organisation, repo_name, source={"branch": branch, "path": path}
            )
        except HTTPError as e:
            # 409 Conflict is GitHub's "already enabled" response.
            if getattr(e, "code", None) == 409 or "already" in str(e).lower():
                logger.info(f"Pages already enabled for {repo_name}")
                return False
            raise
        logger.info(f"Enabled Pages for {repo_name} from {branch}{path}")
        return True

    # -- Releases ----------------------------------------------------------
    def list_releases(self, repo_name: str, include_prereleases: bool = False) -> "list[dict[str, Any]]":
        """List the repo's releases, newest first.

        Drafts are always excluded; prereleases only when asked for.
        """
        releases: list[dict[str, Any]] = []
        for page in paged(self._github.repos.list_releases, self._config.organisation, repo_name, per_page=100):
            for release in page:
                if release.get("draft"):
                    continue
                if release.get("prerelease") and not include_prereleases:
                    continue
                releases.append(dict(release))
        return releases

    def get_release_by_tag(self, repo_name: str, tag: str) -> Optional[dict[str, Any]]:
        """Return the release for ``tag``, or ``None`` if there is not one."""
        try:
            return dict(self._github.repos.get_release_by_tag(self._config.organisation, repo_name, tag))
        except HTTP404NotFoundError:
            return None

    def get_latest_release(self, repo_name: str) -> Optional[dict[str, Any]]:
        """Return the latest non-prerelease release, or ``None``."""
        try:
            return dict(self._github.repos.get_latest_release(self._config.organisation, repo_name))
        except HTTP404NotFoundError:
            return None

    def get_available_versions(self, repo_name: str, include_prereleases: bool = False) -> "list[str]":
        """Return release tag names, newest first."""
        return [r["tag_name"] for r in self.list_releases(repo_name, include_prereleases) if r.get("tag_name")]

    # -- Search ------------------------------------------------------------
    def search_repositories(self, query: str) -> "list[dict[str, Any]]":
        """Search repositories with a GitHub search query.

        The query is passed through as given (e.g. ``"org:acme topic:recipe"``).
        """
        result = self._github.search.repos(q=query)
        items = result.get("items") if hasattr(result, "get") else None
        return [dict(item) for item in (items or [])]
