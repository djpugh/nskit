"""Github provider using ghapi."""

from enum import Enum
from typing import Any, Optional

try:
    from fastcore.net import HTTP404NotFoundError
    from ghapi.all import GhApi, GhDeviceAuth, Scope, paged
    from ghapi.auth import _def_clientid
except ImportError:
    raise ImportError(
        "Github Provider requires installing extra dependencies (ghapi), use pip install nskit[github]"
    ) from None
from pydantic import Field, HttpUrl, SecretStr, ValidationInfo, field_validator

from nskit._logging import logger_factory
from nskit.common.configuration import BaseConfiguration, SettingsConfigDict
from nskit.vcs.providers.abstract import RepoClient, VCSProviderSettings

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


class GithubSettings(VCSProviderSettings):
    """Github settings.

    Uses PAT token for auth (set in environment variables as GITHUB_TOKEN)
    """

    model_config = SettingsConfigDict(env_prefix="GITHUB_", env_file=".env", dotenv_extra="ignore")

    interactive: bool = Field(False, description="Use Interactive Validation for token")
    url: HttpUrl = "https://api.github.com"
    organisation: Optional[str] = Field(
        None, description="Organisation to work in, otherwise uses the user for the token"
    )
    token: SecretStr = Field(
        None,
        validate_default=True,
        description="Token to use for authentication, falls back to interactive device authentication if not provided",
    )
    repo: GithubRepoSettings = Field(default_factory=GithubRepoSettings)

    @property
    def repo_client(self) -> "GithubRepoClient":
        """Get the instantiated repo client."""
        return GithubRepoClient(self)

    @field_validator("token", mode="before")
    @classmethod
    def _validate_token(cls, value, info: ValidationInfo):
        if value is None and info.data.get("interactive", False):
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
        self._github = GhApi(token=self._config.token.get_secret_value(), gh_host=str(self._config.url).rstrip("/"))
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
