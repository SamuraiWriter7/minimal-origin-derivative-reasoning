#!/usr/bin/env python3
"""Validate Minimal Origin-Derivative Reasoning Protocol examples."""

from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence

import yaml
from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import SchemaError


REPO_ROOT = Path(__file__).resolve().parents[1]
SemanticValidator = Callable[[Mapping[str, Any]], list[str]]


class ValidationFailure(Exception):
    """Raised when the validation suite cannot continue safely."""


@dataclass(frozen=True)
class ValidationTarget:
    """A schema, its pass/fail examples, and semantic validator."""

    name: str
    schema_path: Path
    pass_examples: tuple[Path, ...]
    fail_examples: tuple[Path, ...]
    semantic_validator: SemanticValidator


def load_json(path: Path) -> Mapping[str, Any]:
    """Load a JSON object."""

    try:
        with path.open("r", encoding="utf-8") as file:
            value = json.load(file)
    except FileNotFoundError as exc:
        raise ValidationFailure(f"File not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValidationFailure(
            f"Invalid JSON in {path}: line {exc.lineno}, "
            f"column {exc.colno}: {exc.msg}"
        ) from exc
    except OSError as exc:
        raise ValidationFailure(f"Could not read {path}: {exc}") from exc

    if not isinstance(value, Mapping):
        raise ValidationFailure(f"Expected an object at the root of {path}")

    return value


def load_example(path: Path) -> Mapping[str, Any]:
    """Load a YAML or JSON example."""

    try:
        with path.open("r", encoding="utf-8") as file:
            value = json.load(file) if path.suffix.lower() == ".json" else yaml.safe_load(file)
    except FileNotFoundError as exc:
        raise ValidationFailure(f"File not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValidationFailure(
            f"Invalid JSON in {path}: line {exc.lineno}, "
            f"column {exc.colno}: {exc.msg}"
        ) from exc
    except yaml.YAMLError as exc:
        raise ValidationFailure(f"Invalid YAML in {path}: {exc}") from exc
    except OSError as exc:
        raise ValidationFailure(f"Could not read {path}: {exc}") from exc

    if not isinstance(value, Mapping):
        raise ValidationFailure(f"Expected an object at the root of {path}")

    return value


def build_validator(schema: Mapping[str, Any]) -> Draft202012Validator:
    """Check a schema and create its validator."""

    try:
        Draft202012Validator.check_schema(schema)
    except SchemaError as exc:
        raise ValidationFailure(f"Invalid JSON Schema: {exc.message}") from exc

    return Draft202012Validator(schema, format_checker=FormatChecker())


def format_instance_path(path_parts: Iterable[Any]) -> str:
    """Convert a jsonschema path into dotted notation."""

    result = ""
    for part in path_parts:
        if isinstance(part, int):
            result += f"[{part}]"
        else:
            result += ("." if result else "") + str(part)
    return result or "<root>"


def validate_schema(
    instance: Mapping[str, Any],
    validator: Draft202012Validator,
) -> list[str]:
    """Return all JSON Schema errors."""

    errors = sorted(
        validator.iter_errors(instance),
        key=lambda error: (
            format_instance_path(error.absolute_path),
            error.message,
        ),
    )
    return [
        f"{format_instance_path(error.absolute_path)}: {error.message}"
        for error in errors
    ]


def duplicate_values(values: Sequence[str]) -> list[str]:
    """Return duplicate values in deterministic order."""

    counts = Counter(values)
    return sorted(value for value, count in counts.items() if count > 1)


def parse_datetime(value: str) -> datetime:
    """Parse an ISO-8601 datetime string."""

    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    return datetime.fromisoformat(normalized)


def validate_minimal_origin_knowledge_record(
    instance: Mapping[str, Any],
) -> list[str]:
    """Apply v0.1 semantic rules."""

    errors: list[str] = []
    record_id = instance["record_id"]
    kernel = instance["origin_kernel"]
    partition = instance["knowledge_partition"]
    derivation = instance["derivation_policy"]
    audit = instance["audit_policy"]
    trace = instance["trace"]

    for name in sorted(
        {"origin", "derivative", "residue"}.difference(kernel["definitions"].keys())
    ):
        errors.append(
            "origin_kernel.definitions: "
            f"missing required semantic definition '{name}'"
        )

    for duplicate_id in duplicate_values([item["id"] for item in kernel["principles"]]):
        errors.append(
            "origin_kernel.principles: "
            f"duplicate principle id '{duplicate_id}'"
        )

    knowledge_ids = [item["knowledge_id"] for item in partition["retained"]]
    knowledge_ids += [item["knowledge_id"] for item in partition["archived"]]
    for duplicate_id in duplicate_values(knowledge_ids):
        errors.append(
            "knowledge_partition: "
            f"duplicate knowledge id '{duplicate_id}'"
        )

    for duplicate_hash in duplicate_values(
        [item["knowledge_hash"] for item in partition["discarded"]]
    ):
        errors.append(
            "knowledge_partition.discarded: "
            f"duplicate knowledge hash '{duplicate_hash}'"
        )

    if not derivation["require_origin_binding"]:
        errors.append(
            "derivation_policy.require_origin_binding: must be true; "
            "derivative conclusions may not exist without retained origins"
        )

    if not derivation["require_context_declaration"]:
        errors.append(
            "derivation_policy.require_context_declaration: must be true "
            "to preserve contextual traceability"
        )

    if derivation["permit_external_retrieval"] and not partition["archived"]:
        errors.append(
            "knowledge_partition.archived: must contain at least one item "
            "when external retrieval is permitted"
        )

    safe_actions = set(
        derivation.get("allowed_insufficient_knowledge_actions", [])
    )
    if not safe_actions:
        errors.append(
            "derivation_policy.allowed_insufficient_knowledge_actions: "
            "at least one safe fallback action is required"
        )
    elif {"retrieve", "defer", "ask", "abstain"}.isdisjoint(safe_actions):
        errors.append(
            "derivation_policy.allowed_insufficient_knowledge_actions: "
            "must include retrieve, defer, ask, or abstain"
        )

    mandatory_audit_flags = {
        "verify_origin_integrity": "origin integrity verification must be enabled",
        "verify_derivation_trace": "derivation trace verification must be enabled",
        "record_retrieval_sources": "retrieval source recording must be enabled",
        "prohibit_unsupported_certainty": "unsupported certainty must be prohibited",
    }
    for field_name, message in mandatory_audit_flags.items():
        if not audit[field_name]:
            errors.append(f"audit_policy.{field_name}: {message}")

    for index, item in enumerate(partition["discarded"]):
        reversible = item["reversible"]
        recovery_method = item["recovery_method"]
        if reversible and recovery_method == "none":
            errors.append(
                f"knowledge_partition.discarded[{index}].recovery_method: "
                "reversible residue cannot use 'none'"
            )
        if recovery_method == "archive" and not item.get("replacement_locator"):
            errors.append(
                f"knowledge_partition.discarded[{index}].replacement_locator: "
                "required when recovery_method is 'archive'"
            )
        if not reversible and recovery_method != "none":
            errors.append(
                f"knowledge_partition.discarded[{index}].recovery_method: "
                "irreversible residue must use 'none'"
            )

    if record_id in trace["parent_record_ids"]:
        errors.append(
            "trace.parent_record_ids: a record cannot reference itself as a parent"
        )

    for duplicate_locator in duplicate_values(
        [item["locator"] for item in partition["archived"]]
    ):
        errors.append(
            "knowledge_partition.archived: "
            f"duplicate archive locator '{duplicate_locator}'"
        )

    return errors


def validate_knowledge_retention_decision(
    instance: Mapping[str, Any],
) -> list[str]:
    """Apply v0.2 semantic rules."""

    errors: list[str] = []
    decision_id = instance["decision_id"]
    evidence = instance["source_evidence"]
    origin_bindings = instance["origin_bindings"]
    evaluation = instance["evaluation"]
    decision = instance["decision"]
    policy = instance["policy_snapshot"]
    trace = instance["trace"]

    for duplicate_id in duplicate_values([item["evidence_id"] for item in evidence]):
        errors.append(f"source_evidence: duplicate evidence id '{duplicate_id}'")

    if not origin_bindings:
        errors.append(
            "origin_bindings: at least one retained origin binding is required "
            "for every retention decision"
        )

    if len(set(origin_bindings)) != len(origin_bindings):
        errors.append("origin_bindings: duplicate origin bindings are not permitted")

    minimum_provenance = policy["minimum_provenance_quality"]
    if evaluation["provenance_quality"] < minimum_provenance:
        errors.append(
            "evaluation.provenance_quality: value "
            f"{evaluation['provenance_quality']} is below the policy minimum "
            f"{minimum_provenance}"
        )

    classification = decision["classification"]
    reversible = decision["reversible"]

    if (
        evaluation["essentiality"]
        >= policy["retain_if_essentiality_at_or_above"]
        and classification != "retain"
    ):
        errors.append(
            "decision.classification: knowledge meeting the essentiality "
            "threshold must be classified as 'retain'"
        )

    if (
        classification == "discard"
        and evaluation["redundancy"] < policy["discard_if_redundancy_at_or_above"]
    ):
        errors.append(
            "evaluation.redundancy: discard requires redundancy at or above "
            f"{policy['discard_if_redundancy_at_or_above']}"
        )

    if classification == "archive":
        if not reversible:
            errors.append("decision.reversible: archive decisions must be reversible")
        if not decision.get("target_locator"):
            errors.append("decision.target_locator: archive requires a target locator")
        if decision.get("recovery_method") == "none":
            errors.append("decision.recovery_method: archive cannot use 'none'")

    if classification == "discard":
        recovery_method = decision.get("recovery_method")
        if reversible and recovery_method == "none":
            errors.append(
                "decision.recovery_method: reversible discard cannot use 'none'"
            )
        if not reversible and recovery_method != "none":
            errors.append(
                "decision.recovery_method: irreversible discard must use 'none'"
            )
        if (
            not reversible
            and policy["prohibit_irreversible_discard_without_approval"]
            and not decision["approval_ids"]
        ):
            errors.append(
                "decision.approval_ids: irreversible discard requires at least "
                "one approval under the active policy"
            )
        if evaluation["safety_critical"] and policy["prohibit_safety_critical_discard"]:
            errors.append(
                "decision.classification: safety-critical knowledge cannot be discarded"
            )

    if classification == "retain" and decision.get("disposal_method") is not None:
        errors.append(
            "decision.disposal_method: retained knowledge cannot define a disposal method"
        )

    if classification == "quarantine":
        if policy["require_review_for_quarantine"] and not decision["review_required"]:
            errors.append(
                "decision.review_required: quarantine requires review under the policy"
            )
        if not decision.get("target_locator"):
            errors.append(
                "decision.target_locator: quarantine requires an isolation locator"
            )
        if not decision.get("review_at"):
            errors.append("decision.review_at: quarantine requires a review time")

    if decision["review_required"] and not decision.get("review_at"):
        errors.append(
            "decision.review_at: required when review_required is true"
        )

    if decision.get("review_at") and parse_datetime(decision["review_at"]) <= parse_datetime(
        decision["decided_at"]
    ):
        errors.append(
            "decision.review_at: review time must occur after the decision time"
        )

    if decision_id in trace["parent_record_ids"]:
        errors.append(
            "trace.parent_record_ids: a decision cannot reference itself as a parent"
        )

    return errors


def find_claim_cycle(
    claim_dependencies: Mapping[str, set[str]],
) -> list[str] | None:
    """Return one claim cycle, or None."""

    state: dict[str, int] = {}
    stack: list[str] = []

    def visit(claim_id: str) -> list[str] | None:
        current_state = state.get(claim_id, 0)
        if current_state == 1:
            start = stack.index(claim_id)
            return stack[start:] + [claim_id]
        if current_state == 2:
            return None

        state[claim_id] = 1
        stack.append(claim_id)
        for dependency in sorted(claim_dependencies.get(claim_id, set())):
            cycle = visit(dependency)
            if cycle:
                return cycle
        stack.pop()
        state[claim_id] = 2
        return None

    for claim_id in sorted(claim_dependencies):
        cycle = visit(claim_id)
        if cycle:
            return cycle
    return None


def validate_derivative_reasoning_trace(
    instance: Mapping[str, Any],
) -> list[str]:
    """Apply v0.3 semantic rules."""

    errors: list[str] = []
    trace_id = instance["trace_id"]
    context = instance["declared_context"]
    origins = instance["origin_bindings"]
    retrievals = instance["retrieval_inputs"]
    claims = instance["claims"]
    steps = instance["derivation_steps"]
    final_output = instance["final_output"]
    policy = instance["audit_policy"]
    trace = instance["trace"]

    assumption_ids = [item["assumption_id"] for item in context["assumptions"]]
    origin_ids = [item["binding_id"] for item in origins]
    retrieval_ids = [item["retrieval_id"] for item in retrievals]
    claim_ids = [item["claim_id"] for item in claims]
    step_ids = [item["step_id"] for item in steps]

    for duplicate_id in duplicate_values(
        assumption_ids + origin_ids + retrieval_ids + claim_ids + step_ids
    ):
        errors.append(
            "reference identifiers: identifier must be globally unique: "
            f"'{duplicate_id}'"
        )

    for duplicate_sequence in duplicate_values([str(item["sequence"]) for item in steps]):
        errors.append(
            "derivation_steps.sequence: duplicate sequence number "
            f"{duplicate_sequence}"
        )

    claim_by_id = {item["claim_id"]: item for item in claims}
    assumption_by_id = {
        item["assumption_id"]: item for item in context["assumptions"]
    }
    root_ids = set(assumption_ids) | set(origin_ids) | set(retrieval_ids)
    valid_input_ids = root_ids | set(claim_ids)

    for claim in claims:
        if claim["kind"] != "premise":
            continue
        for evidence_ref in claim["evidence_refs"]:
            if evidence_ref not in root_ids:
                errors.append(
                    f"claims.{claim['claim_id']}.evidence_refs: unresolved root "
                    f"reference '{evidence_ref}'"
                )
            assumption = assumption_by_id.get(evidence_ref)
            if assumption and assumption["status"] == "rejected":
                errors.append(
                    f"claims.{claim['claim_id']}.evidence_refs: rejected assumption "
                    f"'{evidence_ref}' cannot support a premise"
                )

    producers: dict[str, list[str]] = defaultdict(list)
    consumed_claim_ids: set[str] = set()
    claim_dependencies: dict[str, set[str]] = {
        claim_id: set() for claim_id in claim_ids
    }

    for step in steps:
        step_id = step["step_id"]
        output_claim_id = step["output_claim_id"]
        if output_claim_id not in claim_by_id:
            errors.append(
                f"derivation_steps.{step_id}.output_claim_id: unknown claim "
                f"'{output_claim_id}'"
            )
            continue

        if claim_by_id[output_claim_id]["kind"] == "premise":
            errors.append(
                f"derivation_steps.{step_id}.output_claim_id: a derivation step "
                "cannot produce a premise"
            )

        producers[output_claim_id].append(step_id)
        for input_ref in step["input_refs"]:
            if input_ref not in valid_input_ids:
                errors.append(
                    f"derivation_steps.{step_id}.input_refs: unresolved reference "
                    f"'{input_ref}'"
                )
                continue
            assumption = assumption_by_id.get(input_ref)
            if assumption and assumption["status"] == "rejected":
                errors.append(
                    f"derivation_steps.{step_id}.input_refs: rejected assumption "
                    f"'{input_ref}' cannot be used"
                )
            if input_ref in claim_by_id:
                consumed_claim_ids.add(input_ref)
                claim_dependencies[output_claim_id].add(input_ref)
                if input_ref == output_claim_id:
                    errors.append(
                        f"derivation_steps.{step_id}.input_refs: a claim cannot "
                        "directly derive itself"
                    )

    for claim in claims:
        claim_id = claim["claim_id"]
        producer_count = len(producers.get(claim_id, []))
        if claim["kind"] == "premise" and producer_count:
            errors.append(f"claims.{claim_id}: a premise must not have a producing step")
        if claim["kind"] != "premise" and producer_count != 1:
            errors.append(
                f"claims.{claim_id}: {claim['kind']} claims require exactly one "
                f"producing step; found {producer_count}"
            )

    final_ids = final_output["conclusion_claim_ids"]
    for conclusion_id in final_ids:
        claim = claim_by_id.get(conclusion_id)
        if claim is None:
            errors.append(
                "final_output.conclusion_claim_ids: unknown claim "
                f"'{conclusion_id}'"
            )
        elif claim["kind"] != "conclusion":
            errors.append(
                "final_output.conclusion_claim_ids: "
                f"'{conclusion_id}' is not a conclusion claim"
            )

    if policy["prohibit_orphan_claims"]:
        final_id_set = set(final_ids)
        for claim_id in claim_ids:
            if claim_id not in consumed_claim_ids and claim_id not in final_id_set:
                errors.append(
                    f"claims.{claim_id}: orphan claim is neither consumed by "
                    "another step nor declared as a final conclusion"
                )

    if policy["require_acyclic_trace"]:
        cycle = find_claim_cycle(claim_dependencies)
        if cycle:
            errors.append(
                "derivation_steps: cyclic claim dependency detected: "
                + " -> ".join(cycle)
            )

    step_by_output = {
        step["output_claim_id"]: step
        for step in steps
        if step["output_claim_id"] in claim_by_id
    }
    origin_id_set = set(origin_ids)
    reachability_memo: dict[str, bool] = {}

    def reaches_origin(claim_id: str, visiting: set[str]) -> bool:
        if claim_id in reachability_memo:
            return reachability_memo[claim_id]
        if claim_id in visiting:
            return False

        claim = claim_by_id[claim_id]
        next_visiting = set(visiting)
        next_visiting.add(claim_id)

        if claim["kind"] == "premise":
            result = any(ref in origin_id_set for ref in claim["evidence_refs"])
            reachability_memo[claim_id] = result
            return result

        step = step_by_output.get(claim_id)
        if step is None:
            reachability_memo[claim_id] = False
            return False

        for input_ref in step["input_refs"]:
            if input_ref in origin_id_set:
                reachability_memo[claim_id] = True
                return True
            if input_ref in claim_by_id and reaches_origin(input_ref, next_visiting):
                reachability_memo[claim_id] = True
                return True

        reachability_memo[claim_id] = False
        return False

    if policy["require_origin_reachability"]:
        for conclusion_id in final_ids:
            if conclusion_id in claim_by_id and not reaches_origin(conclusion_id, set()):
                errors.append(
                    "final_output.conclusion_claim_ids: conclusion "
                    f"'{conclusion_id}' is not reachable from a retained origin"
                )

    mandatory_flags = {
        "require_origin_reachability": "origin reachability must be enabled",
        "require_acyclic_trace": "acyclic trace validation must be enabled",
        "prohibit_orphan_claims": "orphan claim detection must be enabled",
        "require_declared_assumptions": "assumption declaration must be enabled",
    }
    for field_name, message in mandatory_flags.items():
        if not policy[field_name]:
            errors.append(f"audit_policy.{field_name}: {message}")

    threshold = policy["minimum_final_confidence"]
    low_confidence_final = any(
        claim_by_id[claim_id]["confidence"] < threshold
        for claim_id in final_ids
        if claim_id in claim_by_id
    )
    if (
        final_output["overall_confidence"] < threshold or low_confidence_final
    ) and final_output["insufficient_knowledge_action"] == "none":
        errors.append(
            "final_output.insufficient_knowledge_action: a safe action is required "
            "when final confidence is below the policy threshold"
        )

    if trace_id in trace["parent_record_ids"]:
        errors.append(
            "trace.parent_record_ids: a trace cannot reference itself as a parent"
        )

    return errors


def validate_knowledge_rehydration_record(
    instance: Mapping[str, Any],
) -> list[str]:
    """Apply v0.4 semantic rules."""

    errors: list[str] = []
    rehydration_id = instance["rehydration_id"]
    request = instance["request"]
    sources = instance["source_candidates"]
    checks = instance["integrity_checks"]
    integration = instance["integration"]
    policy = instance["audit_policy"]
    trace = instance["trace"]

    source_ids = [item["source_id"] for item in sources]
    for duplicate_id in duplicate_values(source_ids):
        errors.append(f"source_candidates: duplicate source id '{duplicate_id}'")

    if rehydration_id in trace["parent_record_ids"]:
        errors.append(
            "trace.parent_record_ids: a rehydration record cannot reference "
            "itself as a parent"
        )

    if request["parent_reasoning_trace_id"] not in trace["parent_record_ids"]:
        errors.append(
            "trace.parent_record_ids: must include "
            "request.parent_reasoning_trace_id"
        )

    selected_by_flag = {
        item["source_id"] for item in sources if item["selected"]
    }
    selected_by_integration = set(integration["selected_source_ids"])

    for source_id in sorted(selected_by_integration.difference(source_ids)):
        errors.append(
            "integration.selected_source_ids: unknown source "
            f"'{source_id}'"
        )

    if selected_by_flag != selected_by_integration:
        errors.append(
            "integration.selected_source_ids: must exactly match "
            "source_candidates marked selected"
        )

    mandatory_flags = {
        "require_verified_hash": "hash verification must be required",
        "require_provenance_verification": (
            "provenance verification must be required"
        ),
        "prohibit_disputed_sources": (
            "disputed source prohibition must be enabled"
        ),
        "require_expiry_for_temporary": (
            "temporary integration expiry must be required"
        ),
        "prohibit_permanent_integration_without_retention_decision": (
            "permanent integration must require a retention decision"
        ),
    }
    for field_name, message in mandatory_flags.items():
        if not policy[field_name]:
            errors.append(f"audit_policy.{field_name}: {message}")

    status = integration["status"]
    mode = integration["integration_mode"]

    if status == "integrated":
        if mode == "none":
            errors.append(
                "integration.integration_mode: integrated knowledge cannot use 'none'"
            )
        if not selected_by_integration:
            errors.append(
                "integration.selected_source_ids: integrated knowledge requires "
                "at least one selected source"
            )
        if not integration.get("integrated_knowledge_id"):
            errors.append(
                "integration.integrated_knowledge_id: required when status is "
                "'integrated'"
            )
        if not integration.get("integrated_at"):
            errors.append(
                "integration.integrated_at: required when status is 'integrated'"
            )
        if integration["isolation_scope"] == "none":
            errors.append(
                "integration.isolation_scope: integrated knowledge requires "
                "an isolation scope"
            )
        if integration["confidence"] < request["minimum_required_confidence"]:
            errors.append(
                "integration.confidence: below the request "
                "minimum_required_confidence"
            )

        if policy["require_verified_hash"] and not checks["hash_verified"]:
            errors.append(
                "integrity_checks.hash_verified: must be true before integration"
            )
        if (
            policy["require_provenance_verification"]
            and not checks["provenance_verified"]
        ):
            errors.append(
                "integrity_checks.provenance_verified: must be true before integration"
            )
        if not checks["schema_valid"]:
            errors.append(
                "integrity_checks.schema_valid: must be true before integration"
            )
        if checks["conflict_status"] == "unresolved":
            errors.append(
                "integrity_checks.conflict_status: unresolved conflicts prohibit integration"
            )
        if (
            checks["conflict_status"] == "resolved"
            and not integration["conflict_resolution_ids"]
        ):
            errors.append(
                "integration.conflict_resolution_ids: required when conflicts "
                "are resolved"
            )

        selected_sources = [
            item for item in sources if item["source_id"] in selected_by_integration
        ]
        for source in selected_sources:
            source_id = source["source_id"]
            if (
                policy["prohibit_disputed_sources"]
                and source["trust_level"] == "disputed"
            ):
                errors.append(
                    f"source_candidates.{source_id}.trust_level: disputed "
                    "sources cannot be integrated"
                )
            if (
                policy["require_provenance_verification"]
                and source["trust_level"] in {"unverified", "disputed"}
            ):
                errors.append(
                    f"source_candidates.{source_id}.trust_level: source must be "
                    "verified or supported before integration"
                )
            if source["relevance_score"] < policy["minimum_source_relevance"]:
                errors.append(
                    f"source_candidates.{source_id}.relevance_score: below "
                    "policy minimum"
                )
            if source["freshness_score"] < policy["minimum_source_freshness"]:
                errors.append(
                    f"source_candidates.{source_id}.freshness_score: below "
                    "policy minimum"
                )

        if mode == "temporary":
            if policy["require_expiry_for_temporary"] and not integration.get(
                "expires_at"
            ):
                errors.append(
                    "integration.expires_at: required for temporary integration"
                )
            if not integration.get("rollback_locator"):
                errors.append(
                    "integration.rollback_locator: required for temporary integration"
                )
            if integration.get("expires_at") and integration.get("integrated_at"):
                if parse_datetime(integration["expires_at"]) <= parse_datetime(
                    integration["integrated_at"]
                ):
                    errors.append(
                        "integration.expires_at: must occur after integrated_at"
                    )

        if mode == "permanent-candidate":
            if (
                policy[
                    "prohibit_permanent_integration_without_retention_decision"
                ]
                and not integration.get("retention_decision_id")
            ):
                errors.append(
                    "integration.retention_decision_id: required for "
                    "permanent-candidate integration"
                )
            if (
                integration.get("retention_decision_id")
                and integration["retention_decision_id"]
                not in trace["parent_record_ids"]
            ):
                errors.append(
                    "trace.parent_record_ids: must include "
                    "integration.retention_decision_id"
                )

    else:
        if mode != "none":
            errors.append(
                "integration.integration_mode: rejected or deferred records "
                "must use 'none'"
            )
        if selected_by_integration or selected_by_flag:
            errors.append(
                "integration.selected_source_ids: rejected or deferred records "
                "cannot select sources"
            )
        if integration["isolation_scope"] != "none":
            errors.append(
                "integration.isolation_scope: rejected or deferred records "
                "must use 'none'"
            )
        for field_name in (
            "integrated_knowledge_id",
            "integrated_at",
            "expires_at",
            "retention_decision_id",
            "rollback_locator",
        ):
            if integration.get(field_name) is not None:
                errors.append(
                    f"integration.{field_name}: must be absent when status "
                    "is not 'integrated'"
                )

    requested_at = parse_datetime(request["requested_at"])
    for source in sources:
        if parse_datetime(source["retrieved_at"]) < requested_at:
            errors.append(
                f"source_candidates.{source['source_id']}.retrieved_at: "
                "cannot precede request time"
            )

    checked_at = parse_datetime(checks["checked_at"])
    for source in sources:
        if (
            source["source_id"] in selected_by_integration
            and checked_at < parse_datetime(source["retrieved_at"])
        ):
            errors.append(
                "integrity_checks.checked_at: cannot precede retrieval "
                "of a selected source"
            )

    if integration.get("integrated_at") and parse_datetime(
        integration["integrated_at"]
    ) < checked_at:
        errors.append(
            "integration.integrated_at: cannot precede integrity checks"
        )

    if (
        integration.get("integrated_at")
        and parse_datetime(trace["created_at"])
        < parse_datetime(integration["integrated_at"])
    ):
        errors.append("trace.created_at: cannot precede integrated_at")

    return errors

def validate_knowledge_lifecycle_audit(
    instance: Mapping[str, Any],
) -> list[str]:
    """Apply v0.5 semantic rules."""

    errors: list[str] = []
    audit_id = instance["audit_id"]
    window = instance["audit_window"]
    bindings = instance["record_bindings"]
    events = instance["lifecycle_events"]
    controls = instance["control_results"]
    findings = instance["findings"]
    assessment = instance["assessment"]
    policy = instance["policy_snapshot"]
    trace = instance["trace"]

    binding_ids = [item["binding_id"] for item in bindings]
    record_ids = [item["record_id"] for item in bindings]
    event_ids = [item["event_id"] for item in events]
    control_ids = [item["control_id"] for item in controls]
    finding_ids = [item["finding_id"] for item in findings]

    for label, values in (
        ("record_bindings.binding_id", binding_ids),
        ("record_bindings.record_id", record_ids),
        ("lifecycle_events.event_id", event_ids),
        ("control_results.control_id", control_ids),
        ("findings.finding_id", finding_ids),
    ):
        for duplicate_id in duplicate_values(values):
            errors.append(f"{label}: duplicate identifier '{duplicate_id}'")

    all_ids = binding_ids + event_ids + control_ids + finding_ids
    for duplicate_id in duplicate_values(all_ids):
        errors.append(
            "audit identifiers: identifier must be globally unique: "
            f"'{duplicate_id}'"
        )

    if audit_id in trace["parent_record_ids"]:
        errors.append(
            "trace.parent_record_ids: an audit cannot reference itself as a parent"
        )

    bound_record_id_set = set(record_ids)
    parent_record_id_set = set(trace["parent_record_ids"])

    missing_parents = sorted(bound_record_id_set.difference(parent_record_id_set))
    for record_id in missing_parents:
        errors.append(
            "trace.parent_record_ids: must include bound record "
            f"'{record_id}'"
        )

    extra_parents = sorted(parent_record_id_set.difference(bound_record_id_set))
    for record_id in extra_parents:
        errors.append(
            "trace.parent_record_ids: unbound parent record "
            f"'{record_id}'"
        )

    record_types = [item["record_type"] for item in bindings]
    required_types = set(policy["required_record_types"])
    present_types = set(record_types)

    for record_type in sorted(required_types.difference(present_types)):
        errors.append(
            "record_bindings: missing required record type "
            f"'{record_type}'"
        )

    for duplicate_type in duplicate_values(record_types):
        errors.append(
            "record_bindings.record_type: duplicate lifecycle stage "
            f"'{duplicate_type}'"
        )

    expected_relationship = {
        "minimal-origin-knowledge-record": "origin-definition",
        "knowledge-retention-decision": "retention-decision",
        "derivative-reasoning-trace": "reasoning-use",
        "knowledge-rehydration-record": "rehydration-operation",
    }

    binding_by_id = {item["binding_id"]: item for item in bindings}

    for binding in bindings:
        binding_id = binding["binding_id"]
        expected = expected_relationship[binding["record_type"]]
        if binding["relationship"] != expected:
            errors.append(
                f"record_bindings.{binding_id}.relationship: expected "
                f"'{expected}' for record type '{binding['record_type']}'"
            )

        if policy["require_verified_record_bindings"] and not binding["verified"]:
            errors.append(
                f"record_bindings.{binding_id}.verified: must be true under "
                "the active policy"
            )

    mandatory_flags = {
        "require_verified_record_bindings": (
            "record binding verification must be required"
        ),
        "require_contiguous_event_chain": (
            "contiguous lifecycle event validation must be required"
        ),
        "require_acyclic_event_order": (
            "acyclic event ordering must be required"
        ),
        "require_closed_expired_temporary_integrations": (
            "expired temporary integrations must be closed"
        ),
        "prohibit_unapproved_irreversible_discard": (
            "unapproved irreversible discard must be prohibited"
        ),
        "require_terminal_state_consistency": (
            "terminal state consistency must be required"
        ),
    }

    for field_name, message in mandatory_flags.items():
        if not policy[field_name]:
            errors.append(f"policy_snapshot.{field_name}: {message}")

    started_at = parse_datetime(window["started_at"])
    ended_at = parse_datetime(window["ended_at"])

    if ended_at <= started_at:
        errors.append("audit_window.ended_at: must occur after started_at")

    sequences = [str(item["sequence"]) for item in events]
    for duplicate_sequence in duplicate_values(sequences):
        errors.append(
            "lifecycle_events.sequence: duplicate sequence number "
            f"{duplicate_sequence}"
        )

    ordered_events = sorted(events, key=lambda item: item["sequence"])
    actual_sequences = [item["sequence"] for item in ordered_events]
    expected_sequences = list(range(1, len(ordered_events) + 1))

    if policy["require_acyclic_event_order"] and actual_sequences != expected_sequences:
        errors.append(
            "lifecycle_events.sequence: sequence numbers must form the contiguous "
            f"range {expected_sequences}"
        )

    if ordered_events and ordered_events[0]["event_type"] != "origin-declared":
        errors.append(
            "lifecycle_events[0].event_type: lifecycle must begin with "
            "'origin-declared'"
        )

    allowed_record_types = {
        "origin-declared": {"minimal-origin-knowledge-record"},
        "retained": {"knowledge-retention-decision"},
        "archived": {"knowledge-retention-decision"},
        "discarded": {"knowledge-retention-decision"},
        "quarantined": {"knowledge-retention-decision"},
        "derivation-used": {"derivative-reasoning-trace"},
        "rehydration-requested": {"knowledge-rehydration-record"},
        "rehydrated": {"knowledge-rehydration-record"},
        "expired": {"knowledge-rehydration-record"},
        "rolled-back": {"knowledge-rehydration-record"},
        "promoted": {
            "knowledge-rehydration-record",
            "knowledge-retention-decision",
        },
    }

    allowed_transitions = {
        "origin-declared": {("absent", "active")},
        "retained": {("active", "active"), ("archived", "active")},
        "archived": {("active", "archived")},
        "discarded": {
            ("active", "discarded"),
            ("archived", "discarded"),
            ("quarantined", "discarded"),
        },
        "quarantined": {
            ("active", "quarantined"),
            ("archived", "quarantined"),
            ("temporary", "quarantined"),
        },
        "derivation-used": {
            ("active", "active"),
            ("archived", "archived"),
            ("temporary", "temporary"),
        },
        "rehydration-requested": {("archived", "archived")},
        "rehydrated": {("archived", "temporary")},
        "expired": {("temporary", "archived")},
        "rolled-back": {("temporary", "archived")},
        "promoted": {
            ("temporary", "active"),
            ("quarantined", "active"),
        },
    }

    evidence_id_set = set(binding_ids) | set(event_ids)
    previous_event: Mapping[str, Any] | None = None
    temporary_open_event: Mapping[str, Any] | None = None

    for event in ordered_events:
        event_id = event["event_id"]
        binding_id = event["record_binding_id"]
        binding = binding_by_id.get(binding_id)

        if binding is None:
            errors.append(
                f"lifecycle_events.{event_id}.record_binding_id: unknown binding "
                f"'{binding_id}'"
            )
        elif binding["record_type"] not in allowed_record_types[event["event_type"]]:
            errors.append(
                f"lifecycle_events.{event_id}.record_binding_id: event type "
                f"'{event['event_type']}' cannot be supported by record type "
                f"'{binding['record_type']}'"
            )

        transition = (event["state_before"], event["state_after"])
        if transition not in allowed_transitions[event["event_type"]]:
            errors.append(
                f"lifecycle_events.{event_id}: invalid transition "
                f"{event['state_before']} -> {event['state_after']} for "
                f"event type '{event['event_type']}'"
            )

        event_time = parse_datetime(event["occurred_at"])
        if event_time < started_at or event_time > ended_at:
            errors.append(
                f"lifecycle_events.{event_id}.occurred_at: outside the audit window"
            )

        if previous_event is not None:
            previous_time = parse_datetime(previous_event["occurred_at"])
            if event_time < previous_time:
                errors.append(
                    f"lifecycle_events.{event_id}.occurred_at: cannot precede "
                    f"event '{previous_event['event_id']}'"
                )

            if (
                policy["require_contiguous_event_chain"]
                and event["state_before"] != previous_event["state_after"]
            ):
                errors.append(
                    f"lifecycle_events.{event_id}.state_before: expected "
                    f"'{previous_event['state_after']}' from the previous event"
                )

        for evidence_ref in event["evidence_refs"]:
            if evidence_ref not in evidence_id_set:
                errors.append(
                    f"lifecycle_events.{event_id}.evidence_refs: unresolved "
                    f"reference '{evidence_ref}'"
                )

        if event["event_type"] == "rehydrated":
            expires_at_value = event.get("expires_at")
            if not expires_at_value:
                errors.append(
                    f"lifecycle_events.{event_id}.expires_at: required for "
                    "temporary rehydration"
                )
            else:
                expires_at = parse_datetime(expires_at_value)
                if expires_at <= event_time:
                    errors.append(
                        f"lifecycle_events.{event_id}.expires_at: must occur "
                        "after rehydration"
                    )
            temporary_open_event = event

        if event["event_type"] in {"expired", "rolled-back", "promoted"}:
            temporary_open_event = None

        if (
            event["event_type"] == "discarded"
            and not event["reversible"]
            and policy["prohibit_unapproved_irreversible_discard"]
            and not event.get("approval_ids", [])
        ):
            errors.append(
                f"lifecycle_events.{event_id}.approval_ids: irreversible discard "
                "requires approval"
            )

        previous_event = event

    if (
        temporary_open_event is not None
        and policy["require_closed_expired_temporary_integrations"]
    ):
        expires_at_value = temporary_open_event.get("expires_at")
        if expires_at_value and parse_datetime(expires_at_value) <= ended_at:
            errors.append(
                "lifecycle_events: temporary integration from event "
                f"'{temporary_open_event['event_id']}' expired within the audit "
                "window but was not expired, rolled back, or promoted"
            )

    required_control_types = {
        "origin-lineage",
        "retention-policy",
        "derivation-trace",
        "rehydration-safety",
        "temporal-order",
        "terminal-state",
    }
    control_types = [item["control_type"] for item in controls]

    for control_type in sorted(required_control_types.difference(control_types)):
        errors.append(
            "control_results: missing required control type "
            f"'{control_type}'"
        )

    for duplicate_type in duplicate_values(control_types):
        errors.append(
            "control_results.control_type: duplicate control type "
            f"'{duplicate_type}'"
        )

    for control in controls:
        for evidence_ref in control["evidence_refs"]:
            if evidence_ref not in evidence_id_set:
                errors.append(
                    f"control_results.{control['control_id']}.evidence_refs: "
                    f"unresolved reference '{evidence_ref}'"
                )

    event_id_set = set(event_ids)
    finding_by_id = {item["finding_id"]: item for item in findings}

    for finding in findings:
        finding_id = finding["finding_id"]
        for event_id in finding["related_event_ids"]:
            if event_id not in event_id_set:
                errors.append(
                    f"findings.{finding_id}.related_event_ids: unknown event "
                    f"'{event_id}'"
                )

        if finding["remediation_required"] and not finding.get("remediation_action"):
            errors.append(
                f"findings.{finding_id}.remediation_action: required when "
                "remediation_required is true"
            )

    actual_open_ids = {
        item["finding_id"] for item in findings if item["status"] == "open"
    }
    declared_open_ids = set(assessment["open_finding_ids"])

    for finding_id in sorted(declared_open_ids.difference(finding_by_id)):
        errors.append(
            "assessment.open_finding_ids: unknown finding "
            f"'{finding_id}'"
        )

    if actual_open_ids != declared_open_ids:
        errors.append(
            "assessment.open_finding_ids: must exactly match findings with "
            "status 'open'"
        )

    open_error_findings = [
        item
        for item in findings
        if item["status"] == "open" and item["severity"] in {"error", "critical"}
    ]
    open_warning_findings = [
        item
        for item in findings
        if item["status"] == "open" and item["severity"] == "warning"
    ]
    failed_controls = [item for item in controls if item["status"] == "fail"]
    warning_controls = [item for item in controls if item["status"] == "warning"]

    if len(open_error_findings) > policy["maximum_open_error_findings"]:
        errors.append(
            "findings: open error or critical findings exceed the policy maximum"
        )

    expected_status = "compliant"
    if open_error_findings or failed_controls:
        expected_status = "non-compliant"
    elif open_warning_findings or warning_controls:
        expected_status = "conditional"

    if assessment["overall_status"] != expected_status:
        errors.append(
            "assessment.overall_status: expected "
            f"'{expected_status}' from control and finding results"
        )

    if ordered_events:
        terminal_state = ordered_events[-1]["state_after"]
        if (
            policy["require_terminal_state_consistency"]
            and assessment["terminal_state"] != terminal_state
        ):
            errors.append(
                "assessment.terminal_state: must match the final lifecycle "
                f"state '{terminal_state}'"
            )

    issued_at = parse_datetime(assessment["issued_at"])
    if issued_at < ended_at:
        errors.append("assessment.issued_at: cannot precede audit_window.ended_at")

    if assessment.get("next_review_at") and parse_datetime(
        assessment["next_review_at"]
    ) <= issued_at:
        errors.append(
            "assessment.next_review_at: must occur after assessment.issued_at"
        )

    if parse_datetime(trace["created_at"]) < issued_at:
        errors.append("trace.created_at: cannot precede assessment.issued_at")

    return errors


TARGETS: tuple[ValidationTarget, ...] = (
    ValidationTarget(
        name="Minimal Origin Knowledge Record",
        schema_path=REPO_ROOT / "schemas" / "minimal-origin-knowledge-record.schema.json",
        pass_examples=(
            REPO_ROOT / "examples" / "pass" / "minimal-origin-knowledge-record.example.yaml",
        ),
        fail_examples=(
            REPO_ROOT / "examples" / "fail" / "missing-origin-binding.example.yaml",
            REPO_ROOT / "examples" / "fail" / "unsupported-certainty.example.yaml",
        ),
        semantic_validator=validate_minimal_origin_knowledge_record,
    ),
    ValidationTarget(
        name="Knowledge Retention Decision",
        schema_path=REPO_ROOT / "schemas" / "knowledge-retention-decision.schema.json",
        pass_examples=(
            REPO_ROOT / "examples" / "pass" / "knowledge-retention-decision.example.yaml",
        ),
        fail_examples=(
            REPO_ROOT / "examples" / "fail" / "missing-origin-binding-decision.example.yaml",
            REPO_ROOT / "examples" / "fail" / "irreversible-discard-without-approval.example.yaml",
        ),
        semantic_validator=validate_knowledge_retention_decision,
    ),
    ValidationTarget(
        name="Derivative Reasoning Trace",
        schema_path=REPO_ROOT / "schemas" / "derivative-reasoning-trace.schema.json",
        pass_examples=(
            REPO_ROOT / "examples" / "pass" / "derivative-reasoning-trace.example.yaml",
        ),
        fail_examples=(
            REPO_ROOT / "examples" / "fail" / "orphan-derived-claim.example.yaml",
            REPO_ROOT / "examples" / "fail" / "cyclic-derivation-trace.example.yaml",
        ),
        semantic_validator=validate_derivative_reasoning_trace,
    ),
    ValidationTarget(
        name="Knowledge Rehydration Record",
        schema_path=REPO_ROOT / "schemas" / "knowledge-rehydration-record.schema.json",
        pass_examples=(
            REPO_ROOT / "examples" / "pass" / "knowledge-rehydration-record.example.yaml",
        ),
        fail_examples=(
            REPO_ROOT / "examples" / "fail" / "unverified-source-integration.example.yaml",
            REPO_ROOT / "examples" / "fail" / "temporary-integration-without-expiry.example.yaml",
        ),
        semantic_validator=validate_knowledge_rehydration_record,
    ),
    ValidationTarget(
        name="Knowledge Lifecycle Audit",
        schema_path=REPO_ROOT / "schemas" / "knowledge-lifecycle-audit.schema.json",
        pass_examples=(
            REPO_ROOT / "examples" / "pass" / "knowledge-lifecycle-audit.example.yaml",
        ),
        fail_examples=(
            REPO_ROOT / "examples" / "fail" / "broken-lifecycle-lineage.example.yaml",
            REPO_ROOT / "examples" / "fail" / "unclosed-temporary-rehydration.example.yaml",
        ),
        semantic_validator=validate_knowledge_lifecycle_audit,
    ),
)


def validate_instance(
    path: Path,
    validator: Draft202012Validator,
    semantic_validator: SemanticValidator,
) -> tuple[list[str], list[str]]:
    """Run schema and semantic validation."""

    instance = load_example(path)
    schema_errors = validate_schema(instance, validator)
    if schema_errors:
        return schema_errors, []
    return [], semantic_validator(instance)


def print_errors(error_type: str, errors: Sequence[str]) -> None:
    """Print validation errors."""

    for error in errors:
        print(f"[{error_type}] {error}")


def validate_pass_example(
    path: Path,
    validator: Draft202012Validator,
    semantic_validator: SemanticValidator,
) -> bool:
    """Validate an example expected to pass."""

    print()
    print(f"[validate-pass] {path.relative_to(REPO_ROOT)}")
    schema_errors, semantic_errors = validate_instance(
        path, validator, semantic_validator
    )

    if schema_errors:
        print_errors("schema-error", schema_errors)
        return False

    print("[schema-ok]")
    if semantic_errors:
        print_errors("semantic-error", semantic_errors)
        return False

    print("[semantic-ok]")
    print("[pass-ok]")
    return True


def validate_fail_example(
    path: Path,
    validator: Draft202012Validator,
    semantic_validator: SemanticValidator,
) -> bool:
    """Validate an example expected to fail."""

    print()
    print(f"[validate-fail] {path.relative_to(REPO_ROOT)}")
    schema_errors, semantic_errors = validate_instance(
        path, validator, semantic_validator
    )

    if schema_errors:
        print_errors("expected-schema-error", schema_errors)
        print("[expected-failure-ok]")
        return True

    print("[schema-ok]")
    if semantic_errors:
        print_errors("expected-semantic-error", semantic_errors)
        print("[expected-failure-ok]")
        return True

    print(
        "[unexpected-pass] The fail example passed schema and semantic validation."
    )
    return False


def validate_target(target: ValidationTarget) -> tuple[int, int, int, int]:
    """Validate one protocol target."""

    print()
    print("=" * 72)
    print(f"[target] {target.name}")
    print(f"[schema] {target.schema_path.relative_to(REPO_ROOT)}")

    validator = build_validator(load_json(target.schema_path))
    print("[schema-definition-ok]")

    unexpected_failures = sum(
        not validate_pass_example(path, validator, target.semantic_validator)
        for path in target.pass_examples
    )
    unexpected_passes = sum(
        not validate_fail_example(path, validator, target.semantic_validator)
        for path in target.fail_examples
    )

    return (
        len(target.pass_examples),
        len(target.fail_examples),
        unexpected_failures,
        unexpected_passes,
    )


def main() -> int:
    """Run all protocol validation targets."""

    print("=== Minimal Origin-Derivative Reasoning Protocol Validation ===")

    total_pass_examples = 0
    total_fail_examples = 0
    total_unexpected_failures = 0
    total_unexpected_passes = 0

    try:
        for target in TARGETS:
            pass_count, fail_count, unexpected_failures, unexpected_passes = (
                validate_target(target)
            )
            total_pass_examples += pass_count
            total_fail_examples += fail_count
            total_unexpected_failures += unexpected_failures
            total_unexpected_passes += unexpected_passes
    except ValidationFailure as exc:
        print()
        print(f"[fatal] {exc}")
        return 1
    except Exception as exc:
        print()
        print(f"[fatal] Unexpected error: {type(exc).__name__}: {exc}")
        return 1

    print()
    print("=" * 72)
    print("=== Validation Summary ===")
    print(f"Targets checked       : {len(TARGETS)}")
    print(f"Pass examples checked : {total_pass_examples}")
    print(f"Fail examples checked : {total_fail_examples}")
    print(f"Unexpected failures   : {total_unexpected_failures}")
    print(f"Unexpected passes     : {total_unexpected_passes}")

    if total_unexpected_failures or total_unexpected_passes:
        print()
        print("Validation failed.")
        return 1

    print()
    print("All validation checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
