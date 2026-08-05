"""Unit tests for the composable ruleset models."""

from __future__ import annotations

import unittest

from nskit.vcs.providers.rulesets import (
    ActorType,
    BypassActor,
    BypassMode,
    Deletion,
    Enforcement,
    MergeMethod,
    NonFastForward,
    PullRequest,
    RepositoryRole,
    RequiredStatusChecks,
    Ruleset,
    RulesetTarget,
    StatusCheck,
    protect_default_branch,
)


class TestRuleRendering(unittest.TestCase):
    """Individual rules render to the REST payload shape."""

    def test_parameterless_rule_omits_parameters(self) -> None:
        """A rule with no parameters emits only its type."""
        self.assertEqual(Deletion().to_api(), {"type": "deletion"})

    def test_unset_parameters_are_dropped(self) -> None:
        """Only explicitly-set parameters are sent, so GitHub defaults apply."""
        payload = PullRequest(require_code_owner_review=True).to_api()
        self.assertEqual(payload, {"type": "pull_request", "parameters": {"require_code_owner_review": True}})

    def test_enum_parameters_serialise_to_values(self) -> None:
        """Enum parameters render as their API string values."""
        payload = PullRequest(allowed_merge_methods=[MergeMethod.squash]).to_api()
        self.assertEqual(payload["parameters"]["allowed_merge_methods"], ["SQUASH"])

    def test_unset_values_are_dropped_inside_nested_objects(self) -> None:
        """``None`` is pruned at every depth, not just the top level.

        Regression test: a status check used to render as
        ``{"context": "ci", "integration_id": None}``, sending an explicit null
        for a field the caller never set.
        """
        payload = RequiredStatusChecks(required_status_checks=[StatusCheck(context="ci/test")]).to_api()
        self.assertEqual(payload["parameters"]["required_status_checks"], [{"context": "ci/test"}])

    def test_set_nested_values_are_kept(self) -> None:
        """Pruning nulls does not drop nested values that were set."""
        payload = RequiredStatusChecks(
            required_status_checks=[StatusCheck(context="ci/test", integration_id=42)]
        ).to_api()
        self.assertEqual(
            payload["parameters"]["required_status_checks"],
            [{"context": "ci/test", "integration_id": 42}],
        )

    def test_type_is_accessible_on_instances(self) -> None:
        """``type`` resolves to the subclass discriminator.

        Regression test: declaring ``type`` as a property on the base class made
        it a data descriptor, which shadowed the subclass field value.
        """
        self.assertEqual(Deletion().type, "deletion")
        self.assertEqual(NonFastForward().type, "non_fast_forward")


class TestBypassActors(unittest.TestCase):
    """Bypass actor construction and rendering."""

    def test_repository_admin_uses_verified_role_id(self) -> None:
        """The repository admin bypass uses RepositoryRole 5."""
        actor = BypassActor.repository_admin()
        self.assertEqual(actor.actor_id, 5)
        self.assertEqual(actor.actor_id, int(RepositoryRole.admin))
        self.assertEqual(actor.actor_type, ActorType.repository_role)

    def test_org_admin_omits_actor_id(self) -> None:
        """``OrganizationAdmin`` needs no actor_id, so none is sent."""
        payload = BypassActor.organization_admin().to_api()
        self.assertNotIn("actor_id", payload)
        self.assertEqual(payload["actor_type"], "OrganizationAdmin")

    def test_bypass_mode_is_configurable(self) -> None:
        """Bypass mode can be narrowed to pull requests."""
        actor = BypassActor.repository_admin(bypass_mode=BypassMode.pull_request)
        self.assertEqual(actor.to_api()["bypass_mode"], "pull_request")


class TestRulesetComposition(unittest.TestCase):
    """Composition semantics of the Ruleset builder."""

    def test_helpers_are_chainable(self) -> None:
        """The intent helpers chain into a single ruleset."""
        ruleset = (
            Ruleset(name="Protect main")
            .block_deletion()
            .block_force_push()
            .require_pull_request(reviews=2, code_owners=True)
            .require_merge_queue(MergeMethod.squash)
            .require_status_checks("ci/test", strict=True)
            .require_signed_commits()
            .require_linear_history()
            .allow_admin_bypass()
        )
        self.assertEqual(
            sorted(rule.type for rule in ruleset.rules),
            [
                "deletion",
                "merge_queue",
                "non_fast_forward",
                "pull_request",
                "required_linear_history",
                "required_signatures",
                "required_status_checks",
            ],
        )
        self.assertEqual(len(ruleset.bypass_actors), 1)

    def test_composition_does_not_mutate_the_original(self) -> None:
        """Each helper returns a new ruleset."""
        base = Ruleset(name="base").block_deletion()
        extended = base.block_force_push()
        self.assertEqual([r.type for r in base.rules], ["deletion"])
        self.assertEqual(len(extended.rules), 2)

    def test_same_type_rule_replaces_rather_than_duplicates(self) -> None:
        """Re-specifying a rule type overrides it instead of sending two."""
        ruleset = Ruleset(name="r").require_pull_request(reviews=0).require_pull_request(reviews=3)
        pull_requests = [r for r in ruleset.rules if r.type == "pull_request"]
        self.assertEqual(len(pull_requests), 1)
        self.assertEqual(pull_requests[0].required_approving_review_count, 3)

    def test_without_rules_removes_by_type(self) -> None:
        """Rules can be removed from a base policy."""
        ruleset = Ruleset(name="r").block_deletion().block_force_push().without_rules("deletion")
        self.assertEqual([r.type for r in ruleset.rules], ["non_fast_forward"])

    def test_require_status_checks_wraps_contexts(self) -> None:
        """Check names are wrapped into context objects."""
        ruleset = Ruleset(name="r").require_status_checks("ci/a", "ci/b")
        rule = ruleset.rules[0]
        self.assertEqual([c.context for c in rule.required_status_checks], ["ci/a", "ci/b"])

    def test_remaining_intent_helpers_emit_their_rule(self) -> None:
        """Every intent helper maps to the rule type it names.

        Each helper is a one-liner naming a rule class, so a mismatch would be
        invisible without asserting the emitted type.
        """
        cases = [
            (Ruleset(name="r").block_creation(), "creation"),
            (Ruleset(name="r").block_updates(), "update"),
            (Ruleset(name="r").require_deployments("prod"), "required_deployments"),
        ]
        for ruleset, expected_type in cases:
            with self.subTest(rule=expected_type):
                self.assertEqual([r.type for r in ruleset.rules], [expected_type])

    def test_require_deployments_carries_environments(self) -> None:
        """Deployment environments are passed through."""
        rule = Ruleset(name="r").require_deployments("staging", "prod").rules[0]
        self.assertEqual(rule.to_api()["parameters"]["required_deployment_environments"], ["staging", "prod"])

    def test_org_admin_bypass_helper(self) -> None:
        """The org-admin bypass helper adds an OrganizationAdmin actor."""
        ruleset = Ruleset(name="r").allow_org_admin_bypass()
        self.assertEqual(ruleset.bypass_actors[0].actor_type, ActorType.organization_admin)

    def test_for_refs_sets_conditions(self) -> None:
        """Ref targeting is configurable, defaulting to the default branch."""
        self.assertEqual(Ruleset(name="r").ref_name.include, ["~DEFAULT_BRANCH"])
        targeted = Ruleset(name="r").for_refs("refs/heads/release/*", exclude=["refs/heads/release/legacy"])
        payload = targeted.to_api()["conditions"]["ref_name"]
        self.assertEqual(payload["include"], ["refs/heads/release/*"])
        self.assertEqual(payload["exclude"], ["refs/heads/release/legacy"])

    def test_enforcement_toggle_returns_a_copy(self) -> None:
        """Enforcement can be changed without mutating the original."""
        base = Ruleset(name="r")
        disabled = base.with_enforcement(Enforcement.disabled)
        self.assertEqual(base.enforcement, Enforcement.active)
        self.assertEqual(disabled.enforcement, Enforcement.disabled)


class TestRulesetPayload(unittest.TestCase):
    """Full payload rendering and round-tripping."""

    def test_payload_shape(self) -> None:
        """The rendered payload carries the keys the REST endpoints expect."""
        payload = Ruleset(name="Protect main").block_deletion().to_api()
        self.assertEqual(payload["name"], "Protect main")
        self.assertEqual(payload["target"], RulesetTarget.branch.value)
        self.assertEqual(payload["enforcement"], Enforcement.active.value)
        self.assertEqual(payload["conditions"], {"ref_name": {"include": ["~DEFAULT_BRANCH"], "exclude": []}})
        self.assertEqual(payload["rules"], [{"type": "deletion"}])

    def test_id_is_never_sent(self) -> None:
        """A server-assigned id is not included in the payload."""
        ruleset = Ruleset(name="r", id=123).block_deletion()
        self.assertNotIn("id", ruleset.to_api())

    def test_round_trip_preserves_payload(self) -> None:
        """from_api(to_api(x)) renders the same payload."""
        original = protect_default_branch().require_copilot_review(on_push=True)
        self.assertEqual(Ruleset.from_api(original.to_api()).to_api(), original.to_api())

    def test_from_api_captures_id(self) -> None:
        """The server-assigned id is captured so it can be updated/deleted."""
        payload = {**Ruleset(name="r").block_deletion().to_api(), "id": 42}
        self.assertEqual(Ruleset.from_api(payload).id, 42)

    def test_from_api_skips_unknown_rule_types(self) -> None:
        """An unmodelled rule type is ignored rather than raising."""
        payload = Ruleset(name="r").block_deletion().to_api()
        payload["rules"].append({"type": "some_future_rule", "parameters": {"x": 1}})
        self.assertEqual([r.type for r in Ruleset.from_api(payload).rules], ["deletion"])


class TestProtectDefaultBranch(unittest.TestCase):
    """The convenience preset."""

    def test_preset_blocks_deletion_and_force_push(self) -> None:
        """The preset covers the conventional protections."""
        types = {rule.type for rule in protect_default_branch().rules}
        self.assertIn("deletion", types)
        self.assertIn("non_fast_forward", types)
        self.assertIn("pull_request", types)

    def test_preset_imposes_no_org_specific_policy(self) -> None:
        """The preset stays unopinionated beyond the basics.

        Merge methods and CODEOWNERS review are organisation conventions, not
        universal defaults, so a general-purpose library must not bake them in;
        callers add them by chaining.
        """
        pull_request = next(r for r in protect_default_branch().rules if r.type == "pull_request")
        self.assertIsNone(pull_request.allowed_merge_methods)
        self.assertIsNone(pull_request.require_code_owner_review)
        self.assertEqual(pull_request.to_api()["parameters"], {"required_approving_review_count": 1})

    def test_preset_is_specialisable(self) -> None:
        """The preset can be chained onto without re-specifying its rules."""
        ruleset = protect_default_branch(reviews=2).require_merge_queue(MergeMethod.squash)
        pull_request = next(r for r in ruleset.rules if r.type == "pull_request")
        self.assertEqual(pull_request.required_approving_review_count, 2)
        self.assertIn("merge_queue", {r.type for r in ruleset.rules})

    def test_admin_bypass_can_be_declined(self) -> None:
        """Admin bypass is opt-out."""
        self.assertEqual(protect_default_branch(admin_bypass=False).bypass_actors, [])


if __name__ == "__main__":
    unittest.main()
