"""Composable GitHub repository ruleset models.

Rulesets are GitHub's successor to classic branch protection. The REST payload
is a nested dict of loosely-typed rule objects, which is easy to get subtly
wrong, so this module models each rule as its own small class.

The usual way to build one is the chainable intent helpers, which read as policy
rather than as payload construction::

    ruleset = (
        Ruleset(name="Protect main")
        .block_deletion()
        .block_force_push()
        .require_pull_request(reviews=1, code_owners=True)
        .require_merge_queue(MergeMethod.squash)
        .require_status_checks("ci/test", strict=True)
        .allow_admin_bypass()
    )
    client.create_ruleset("my-repo", ruleset)

Every helper returns a new ``Ruleset``, so a base policy can be shared and
specialised without mutating it, and a rule of a type already present is
replaced rather than duplicated. Drop to :meth:`Ruleset.with_rules` with the
rule classes directly for anything the helpers do not cover.

Each rule renders itself via ``to_api()``, so adding a rule GitHub introduces
later means adding one class rather than editing a dict literal. Rules are a
discriminated union on ``type``, so a ruleset read back from the API can be
parsed into the same models (see :meth:`Ruleset.from_api`).

Only values that are explicitly set are sent, so GitHub's own defaults apply to
anything left alone.
"""

from __future__ import annotations

from enum import Enum, IntEnum
from typing import Annotated, Any, ClassVar, Literal, Optional, Union

from pydantic import BaseModel, Field


class RepositoryRole(IntEnum):
    """Built-in repository-role actor IDs for ruleset ``bypass_actors``.

    Only ``admin`` is encoded. GitHub does not publish a stable, complete
    mapping of role name to numeric ID for ruleset bypass actors, and guessing
    the others would be inventing an integration contract — pass a raw ``int``
    as ``actor_id`` if you need a role that is not listed here.

    ``admin = 5`` is corroborated by GitHub's own CLI issue tracker, which
    describes a repo admin as ``RepositoryRole=5``
    (https://github.com/cli/cli/issues/13388).
    """

    admin = 5


class ActorType(str, Enum):
    """Actor types accepted in ``bypass_actors``."""

    repository_role = "RepositoryRole"
    team = "Team"
    integration = "Integration"
    organization_admin = "OrganizationAdmin"
    deploy_key = "DeployKey"


class BypassMode(str, Enum):
    """When a bypass actor is allowed to bypass the ruleset.

    ``always`` bypasses everywhere; ``pull_request`` only for pull requests.
    """

    always = "always"
    pull_request = "pull_request"


class Enforcement(str, Enum):
    """Ruleset enforcement status."""

    active = "active"
    evaluate = "evaluate"
    disabled = "disabled"


class RulesetTarget(str, Enum):
    """What the ruleset applies to."""

    branch = "branch"
    tag = "tag"
    push = "push"


class MergeMethod(str, Enum):
    """Merge methods for the merge queue and pull-request rules."""

    merge = "MERGE"
    squash = "SQUASH"
    rebase = "REBASE"


class BypassActor(BaseModel):
    """An actor permitted to bypass a ruleset."""

    actor_id: Optional[int] = None
    actor_type: ActorType = ActorType.repository_role
    bypass_mode: BypassMode = BypassMode.always

    @classmethod
    def repository_admin(cls, bypass_mode: BypassMode = BypassMode.always) -> BypassActor:
        """Bypass for the repository ``admin`` role."""
        return cls(
            actor_id=int(RepositoryRole.admin),
            actor_type=ActorType.repository_role,
            bypass_mode=bypass_mode,
        )

    @classmethod
    def organization_admin(cls, bypass_mode: BypassMode = BypassMode.always) -> BypassActor:
        """Bypass for organisation admins.

        ``OrganizationAdmin`` needs no ``actor_id``.
        """
        return cls(actor_id=None, actor_type=ActorType.organization_admin, bypass_mode=bypass_mode)

    def to_api(self) -> dict[str, Any]:
        """Render to the REST payload shape, omitting an unset ``actor_id``."""
        payload: dict[str, Any] = {
            "actor_type": self.actor_type.value,
            "bypass_mode": self.bypass_mode.value,
        }
        if self.actor_id is not None:
            payload["actor_id"] = self.actor_id
        return payload


class Rule(BaseModel):
    """Base class for a single ruleset rule.

    Subclasses narrow ``type`` to a ``Literal`` discriminator and expose their
    configuration as ordinary fields; ``to_api`` folds those fields into the
    ``parameters`` object GitHub expects.

    ``type`` is a plain field rather than a property: a ``property`` is a data
    descriptor and would take precedence over the subclass field value, so
    ``rule.type`` would resolve to the base implementation.
    """

    type: str

    # Fields that are part of the model but not ruleset parameters.
    _non_parameter_fields: ClassVar[set[str]] = {"type"}

    def to_api(self) -> dict[str, Any]:
        """Render to ``{"type": ..., "parameters": {...}}``.

        ``parameters`` is omitted entirely when the rule takes none, and unset
        (``None``) parameters are dropped so GitHub's defaults apply.
        """
        parameters = {
            name: self._serialise(value)
            for name, value in self.model_dump(exclude=self._non_parameter_fields).items()
            if value is not None
        }
        payload: dict[str, Any] = {"type": self.type}
        if parameters:
            payload["parameters"] = parameters
        return payload

    @staticmethod
    def _serialise(value: Any) -> Any:
        """Render a parameter value, dropping unset entries at every depth.

        ``None`` must be pruned inside nested objects too, not just at the top
        level: a status check rendered as ``{"context": "ci", "integration_id":
        null}`` sends an explicit null for a field the caller never set.
        """
        if isinstance(value, Enum):
            return value.value
        if isinstance(value, list):
            return [Rule._serialise(item) for item in value]
        if isinstance(value, dict):
            return {k: Rule._serialise(v) for k, v in value.items() if v is not None}
        return value


# -- Parameterless rules ---------------------------------------------------
class Creation(Rule):
    """Only allow users with bypass permission to create matching refs."""

    type: Literal["creation"] = "creation"


class Update(Rule):
    """Only allow users with bypass permission to update matching refs."""

    type: Literal["update"] = "update"


class Deletion(Rule):
    """Only allow users with bypass permission to delete matching refs."""

    type: Literal["deletion"] = "deletion"


class NonFastForward(Rule):
    """Prevent force pushes to matching refs."""

    type: Literal["non_fast_forward"] = "non_fast_forward"


class RequiredLinearHistory(Rule):
    """Prevent merge commits being pushed to matching refs."""

    type: Literal["required_linear_history"] = "required_linear_history"


class RequiredSignatures(Rule):
    """Require commits to be signed."""

    type: Literal["required_signatures"] = "required_signatures"


# -- Parameterised rules ---------------------------------------------------
class PullRequest(Rule):
    """Require a pull request before merging."""

    type: Literal["pull_request"] = "pull_request"

    required_approving_review_count: Optional[int] = None
    dismiss_stale_reviews_on_push: Optional[bool] = None
    require_code_owner_review: Optional[bool] = None
    require_last_push_approval: Optional[bool] = None
    required_review_thread_resolution: Optional[bool] = None
    allowed_merge_methods: Optional[list[MergeMethod]] = None


class MergeQueue(Rule):
    """Require merges to go through a merge queue."""

    type: Literal["merge_queue"] = "merge_queue"

    merge_method: Optional[MergeMethod] = None
    max_entries_to_build: Optional[int] = None
    min_entries_to_merge: Optional[int] = None
    max_entries_to_merge: Optional[int] = None
    min_entries_to_merge_wait_minutes: Optional[int] = None
    grouping_strategy: Optional[str] = None
    check_response_timeout_minutes: Optional[int] = None


class StatusCheck(BaseModel):
    """A single required status check."""

    context: str
    integration_id: Optional[int] = None


class RequiredStatusChecks(Rule):
    """Require status checks to pass before merging."""

    type: Literal["required_status_checks"] = "required_status_checks"

    required_status_checks: list[StatusCheck] = Field(default_factory=list)
    strict_required_status_checks_policy: Optional[bool] = None
    do_not_enforce_on_create: Optional[bool] = None


class CopilotCodeReview(Rule):
    """Request a Copilot code review automatically."""

    type: Literal["copilot_code_review"] = "copilot_code_review"

    review_draft_pull_requests: Optional[bool] = None
    review_on_push: Optional[bool] = None


class RequiredDeployments(Rule):
    """Require successful deployments to named environments."""

    type: Literal["required_deployments"] = "required_deployments"

    required_deployment_environments: list[str] = Field(default_factory=list)


AnyRule = Annotated[
    Union[
        Creation,
        Update,
        Deletion,
        NonFastForward,
        RequiredLinearHistory,
        RequiredSignatures,
        PullRequest,
        MergeQueue,
        RequiredStatusChecks,
        CopilotCodeReview,
        RequiredDeployments,
    ],
    Field(discriminator="type"),
]


class RefNameCondition(BaseModel):
    """Which refs the ruleset applies to.

    Defaults to the repository's default branch via GitHub's ``~DEFAULT_BRANCH``
    alias, so the ruleset follows a renamed default branch.
    """

    include: list[str] = Field(default_factory=lambda: ["~DEFAULT_BRANCH"])
    exclude: list[str] = Field(default_factory=list)


class Ruleset(BaseModel):
    """A composable repository ruleset.

    Build one up with :meth:`with_rules` / :meth:`with_bypass`, both of which
    return a new instance so a base ruleset can be shared and specialised
    without mutating it.
    """

    name: str
    target: RulesetTarget = RulesetTarget.branch
    enforcement: Enforcement = Enforcement.active
    bypass_actors: list[BypassActor] = Field(default_factory=list)
    ref_name: RefNameCondition = Field(default_factory=RefNameCondition)
    rules: list[AnyRule] = Field(default_factory=list)
    id: Optional[int] = Field(
        None,
        description=(
            "Server-assigned ruleset ID. Populated by ``from_api`` so a ruleset "
            "read back can be updated or deleted; never sent in a payload."
        ),
    )

    def with_rules(self, *rules: Rule) -> Ruleset:
        """Return a copy with ``rules`` appended.

        A rule of a type already present replaces the existing one, so a base
        ruleset can be specialised (e.g. tightening ``PullRequest``) without
        sending GitHub two rules of the same type.
        """
        merged = {rule.type: rule for rule in self.rules}
        merged.update({rule.type: rule for rule in rules})
        return self.model_copy(update={"rules": list(merged.values())})

    def without_rules(self, *types: str) -> Ruleset:
        """Return a copy with rules of the given ``types`` removed."""
        excluded = set(types)
        return self.model_copy(update={"rules": [r for r in self.rules if r.type not in excluded]})

    def with_bypass(self, *actors: BypassActor) -> Ruleset:
        """Return a copy with ``actors`` appended to the bypass list."""
        return self.model_copy(update={"bypass_actors": [*self.bypass_actors, *actors]})

    def with_enforcement(self, enforcement: Enforcement) -> Ruleset:
        """Return a copy with a different enforcement status."""
        return self.model_copy(update={"enforcement": enforcement})

    def for_refs(self, *include: str, exclude: Optional[list[str]] = None) -> Ruleset:
        """Return a copy targeting the given refs (fnmatch patterns or aliases)."""
        return self.model_copy(update={"ref_name": RefNameCondition(include=list(include), exclude=exclude or [])})

    # -- Intent helpers ----------------------------------------------------
    # Thin, chainable wrappers over ``with_rules`` so the common policies read
    # as intent rather than as rule construction. Each returns a new Ruleset,
    # and each replaces any existing rule of the same type.
    def require_pull_request(
        self,
        reviews: Optional[int] = None,
        *,
        code_owners: Optional[bool] = None,
        dismiss_stale: Optional[bool] = None,
        last_push_approval: Optional[bool] = None,
        thread_resolution: Optional[bool] = None,
        merge_methods: Optional[list[MergeMethod]] = None,
    ) -> Ruleset:
        """Require a pull request before merging.

        Args:
            reviews: Number of approving reviews required.
            code_owners: Require review from a CODEOWNER.
            dismiss_stale: Dismiss approvals when new commits are pushed.
            last_push_approval: Require approval of the most recent push.
            thread_resolution: Require review threads to be resolved.
            merge_methods: Merge methods to permit.
        """
        return self.with_rules(
            PullRequest(
                required_approving_review_count=reviews,
                require_code_owner_review=code_owners,
                dismiss_stale_reviews_on_push=dismiss_stale,
                require_last_push_approval=last_push_approval,
                required_review_thread_resolution=thread_resolution,
                allowed_merge_methods=merge_methods,
            )
        )

    def require_merge_queue(
        self,
        merge_method: Optional[MergeMethod] = None,
        *,
        min_entries_to_merge: Optional[int] = None,
        max_entries_to_merge: Optional[int] = None,
        min_entries_to_merge_wait_minutes: Optional[int] = None,
        max_entries_to_build: Optional[int] = None,
        grouping_strategy: Optional[str] = None,
        check_response_timeout_minutes: Optional[int] = None,
    ) -> Ruleset:
        """Require merges to go through a merge queue."""
        return self.with_rules(
            MergeQueue(
                merge_method=merge_method,
                min_entries_to_merge=min_entries_to_merge,
                max_entries_to_merge=max_entries_to_merge,
                min_entries_to_merge_wait_minutes=min_entries_to_merge_wait_minutes,
                max_entries_to_build=max_entries_to_build,
                grouping_strategy=grouping_strategy,
                check_response_timeout_minutes=check_response_timeout_minutes,
            )
        )

    def require_status_checks(
        self,
        *contexts: str,
        strict: Optional[bool] = None,
        do_not_enforce_on_create: Optional[bool] = None,
    ) -> Ruleset:
        """Require the named status checks to pass.

        Args:
            contexts: Status check names (e.g. ``"ci/test"``).
            strict: Require the branch to be up to date before merging.
            do_not_enforce_on_create: Skip enforcement when a ref is created.
        """
        return self.with_rules(
            RequiredStatusChecks(
                required_status_checks=[StatusCheck(context=c) for c in contexts],
                strict_required_status_checks_policy=strict,
                do_not_enforce_on_create=do_not_enforce_on_create,
            )
        )

    def require_signed_commits(self) -> Ruleset:
        """Require commits to be signed."""
        return self.with_rules(RequiredSignatures())

    def require_linear_history(self) -> Ruleset:
        """Prevent merge commits (require a linear history)."""
        return self.with_rules(RequiredLinearHistory())

    def require_deployments(self, *environments: str) -> Ruleset:
        """Require successful deployments to the named environments."""
        return self.with_rules(RequiredDeployments(required_deployment_environments=list(environments)))

    def require_copilot_review(
        self,
        *,
        on_push: Optional[bool] = None,
        drafts: Optional[bool] = None,
    ) -> Ruleset:
        """Request a Copilot code review automatically."""
        return self.with_rules(CopilotCodeReview(review_on_push=on_push, review_draft_pull_requests=drafts))

    def block_deletion(self) -> Ruleset:
        """Prevent matching refs being deleted."""
        return self.with_rules(Deletion())

    def block_force_push(self) -> Ruleset:
        """Prevent force pushes to matching refs."""
        return self.with_rules(NonFastForward())

    def block_creation(self) -> Ruleset:
        """Prevent matching refs being created."""
        return self.with_rules(Creation())

    def block_updates(self) -> Ruleset:
        """Prevent matching refs being updated."""
        return self.with_rules(Update())

    def allow_admin_bypass(self, bypass_mode: BypassMode = BypassMode.always) -> Ruleset:
        """Let repository admins bypass this ruleset."""
        return self.with_bypass(BypassActor.repository_admin(bypass_mode=bypass_mode))

    def allow_org_admin_bypass(self, bypass_mode: BypassMode = BypassMode.always) -> Ruleset:
        """Let organisation admins bypass this ruleset."""
        return self.with_bypass(BypassActor.organization_admin(bypass_mode=bypass_mode))

    def to_api(self) -> dict[str, Any]:
        """Render the full REST payload for the ruleset endpoints."""
        return {
            "name": self.name,
            "target": self.target.value,
            "enforcement": self.enforcement.value,
            "bypass_actors": [actor.to_api() for actor in self.bypass_actors],
            "conditions": {"ref_name": self.ref_name.model_dump()},
            "rules": [rule.to_api() for rule in self.rules],
        }

    @classmethod
    def from_api(cls, payload: dict[str, Any]) -> Ruleset:
        """Parse a ruleset as returned by the REST API.

        Unknown rule types are skipped rather than raising, so a ruleset using a
        rule this module does not model yet can still be read (for example to
        toggle its enforcement).
        """
        known = {
            rule.model_fields["type"].default
            for rule in (
                Creation,
                Update,
                Deletion,
                NonFastForward,
                RequiredLinearHistory,
                RequiredSignatures,
                PullRequest,
                MergeQueue,
                RequiredStatusChecks,
                CopilotCodeReview,
                RequiredDeployments,
            )
        }
        rules: list[dict[str, Any]] = []
        for rule in payload.get("rules") or []:
            if rule.get("type") not in known:
                continue
            rules.append({"type": rule["type"], **(rule.get("parameters") or {})})

        conditions = payload.get("conditions") or {}
        ref_name = conditions.get("ref_name") or {}
        return cls.model_validate(
            {
                "id": payload.get("id"),
                "name": payload.get("name", ""),
                "target": payload.get("target", RulesetTarget.branch.value),
                "enforcement": payload.get("enforcement", Enforcement.active.value),
                "bypass_actors": payload.get("bypass_actors") or [],
                "ref_name": {
                    "include": ref_name.get("include") or ["~DEFAULT_BRANCH"],
                    "exclude": ref_name.get("exclude") or [],
                },
                "rules": rules,
            }
        )


def protect_default_branch(
    *,
    name: str = "Protect default branch",
    reviews: int = 1,
    code_owners: Optional[bool] = None,
    merge_methods: Optional[list[MergeMethod]] = None,
    admin_bypass: bool = True,
) -> Ruleset:
    """A minimal default-branch ruleset, as a starting point to specialise.

    Blocks deletion and force pushes and requires a pull request with ``reviews``
    approvals. Deliberately unopinionated beyond that: anything organisation
    specific — squash-only merges, CODEOWNERS review, required checks — is left
    unset so GitHub's defaults apply, and is added by chaining::

        (
            protect_default_branch(reviews=2, code_owners=True)
            .require_merge_queue(MergeMethod.squash)
            .require_status_checks("ci/test")
        )
    """
    ruleset = (
        Ruleset(name=name)
        .block_deletion()
        .block_force_push()
        .require_pull_request(reviews=reviews, code_owners=code_owners, merge_methods=merge_methods)
    )
    if admin_bypass:
        ruleset = ruleset.allow_admin_bypass()
    return ruleset
