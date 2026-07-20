#!/usr/bin/env python3
"""
Validate Minimal Origin-Derivative Reasoning Protocol examples.

Supported protocol records:

v0.1
    Minimal Origin Knowledge Record

v0.2
    Knowledge Retention Decision

Validation stages:

1. JSON Schema validation
2. Protocol-specific semantic validation

Pass examples must pass both stages.
Fail examples must fail at least one stage.

Dependencies:
    pip install -r requirements.txt
"""

from __future__ import annotations

import json
import sys
from collections import Counter
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
    """Defines one schema and its associated examples."""

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
            f"Invalid JSON in {path}: "
            f"line {exc.lineno}, column {exc.colno}: {exc.msg}"
        ) from exc
    except OSError as exc:
        raise ValidationFailure(
            f"Could not read {path}: {exc}"
        ) from exc

    if not isinstance(value, Mapping):
        raise ValidationFailure(
            f"Expected an object at the root of {path}"
        )

    return value


def load_example(path: Path) -> Mapping[str, Any]:
    """Load a YAML or JSON example object."""

    try:
        with path.open("r", encoding="utf-8") as file:
            if path.suffix.lower() == ".json":
                value = json.load(file)
            else:
                value = yaml.safe_load(file)
    except FileNotFoundError as exc:
        raise ValidationFailure(f"File not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValidationFailure(
            f"Invalid JSON in {path}: "
            f"line {exc.lineno}, column {exc.colno}: {exc.msg}"
        ) from exc
    except yaml.YAMLError as exc:
        raise ValidationFailure(
            f"Invalid YAML in {path}: {exc}"
        ) from exc
    except OSError as exc:
        raise ValidationFailure(
            f"Could not read {path}: {exc}"
        ) from exc

    if not isinstance(value, Mapping):
        raise ValidationFailure(
            f"Expected an object at the root of {path}"
        )

    return value


def build_validator(
    schema: Mapping[str, Any],
) -> Draft202012Validator:
    """Validate a schema definition and create its validator."""

    try:
        Draft202012Validator.check_schema(schema)
    except SchemaError as exc:
        raise ValidationFailure(
            f"Invalid JSON Schema: {exc.message}"
        ) from exc

    return Draft202012Validator(
        schema,
        format_checker=FormatChecker(),
    )


def format_instance_path(path_parts: Iterable[Any]) -> str:
    """Convert a jsonschema path into readable dotted notation."""

    result = ""

    for part in path_parts:
        if isinstance(part, int):
            result += f"[{part}]"
        else:
            if result:
                result += "."
            result += str(part)

    return result or "<root>"


def validate_schema(
    instance: Mapping[str, Any],
    validator: Draft202012Validator,
) -> list[str]:
    """Return all JSON Schema errors for an instance."""

    errors: list[str] = []

    sorted_errors = sorted(
        validator.iter_errors(instance),
        key=lambda error: (
            format_instance_path(error.absolute_path),
            error.message,
        ),
    )

    for error in sorted_errors:
        location = format_instance_path(error.absolute_path)
        errors.append(f"{location}: {error.message}")

    return errors


def duplicate_values(values: Sequence[str]) -> list[str]:
    """Return duplicate values in deterministic order."""

    counts = Counter(values)

    return sorted(
        value
        for value, count in counts.items()
        if count > 1
    )


def parse_datetime(value: str) -> datetime:
    """Parse an ISO-8601 datetime string."""

    normalized = value

    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"

    return datetime.fromisoformat(normalized)


def validate_minimal_origin_knowledge_record(
    instance: Mapping[str, Any],
) -> list[str]:
    """Apply v0.1 semantic validation rules."""

    errors: list[str] = []

    record_id = instance["record_id"]
    origin_kernel = instance["origin_kernel"]
    partition = instance["knowledge_partition"]
    derivation_policy = instance["derivation_policy"]
    audit_policy = instance["audit_policy"]
    trace = instance["trace"]

    principles = origin_kernel["principles"]
    definitions = origin_kernel["definitions"]

    retained = partition["retained"]
    archived = partition["archived"]
    discarded = partition["discarded"]

    required_definitions = {
        "origin",
        "derivative",
        "residue",
    }

    missing_definitions = sorted(
        required_definitions.difference(definitions.keys())
    )

    for definition_name in missing_definitions:
        errors.append(
            "origin_kernel.definitions: "
            f"missing required semantic definition "
            f"'{definition_name}'"
        )

    principle_ids = [
        principle["id"]
        for principle in principles
    ]

    for duplicate_id in duplicate_values(principle_ids):
        errors.append(
            "origin_kernel.principles: "
            f"duplicate principle id '{duplicate_id}'"
        )

    retained_ids = [
        item["knowledge_id"]
        for item in retained
    ]

    archived_ids = [
        item["knowledge_id"]
        for item in archived
    ]

    for duplicate_id in duplicate_values(
        retained_ids + archived_ids
    ):
        errors.append(
            "knowledge_partition: "
            f"duplicate knowledge id '{duplicate_id}'"
        )

    discarded_hashes = [
        item["knowledge_hash"]
        for item in discarded
    ]

    for duplicate_hash in duplicate_values(discarded_hashes):
        errors.append(
            "knowledge_partition.discarded: "
            f"duplicate knowledge hash '{duplicate_hash}'"
        )

    if not derivation_policy["require_origin_binding"]:
        errors.append(
            "derivation_policy.require_origin_binding: "
            "must be true; derivative conclusions may not exist "
            "without retained origin bindings"
        )

    if not derivation_policy["require_context_declaration"]:
        errors.append(
            "derivation_policy.require_context_declaration: "
            "must be true to preserve contextual traceability"
        )

    if (
        derivation_policy["permit_external_retrieval"]
        and not archived
    ):
        errors.append(
            "knowledge_partition.archived: "
            "must contain at least one item when external retrieval "
            "is permitted"
        )

    safe_actions = set(
        derivation_policy.get(
            "allowed_insufficient_knowledge_actions",
            [],
        )
    )

    if not safe_actions:
        errors.append(
            "derivation_policy."
            "allowed_insufficient_knowledge_actions: "
            "at least one safe fallback action is required"
        )

    if {
        "retrieve",
        "defer",
        "ask",
        "abstain",
    }.isdisjoint(safe_actions):
        errors.append(
            "derivation_policy."
            "allowed_insufficient_knowledge_actions: "
            "must include retrieve, defer, ask, or abstain"
        )

    mandatory_audit_flags = {
        "verify_origin_integrity":
            "origin integrity verification must be enabled",
        "verify_derivation_trace":
            "derivation trace verification must be enabled",
        "record_retrieval_sources":
            "retrieval source recording must be enabled",
        "prohibit_unsupported_certainty":
            "unsupported certainty must be prohibited",
    }

    for field_name, message in mandatory_audit_flags.items():
        if not audit_policy[field_name]:
            errors.append(
                f"audit_policy.{field_name}: {message}"
            )

    for index, item in enumerate(discarded):
        reversible = item["reversible"]
        recovery_method = item["recovery_method"]
        replacement_locator = item.get("replacement_locator")

        if reversible and recovery_method == "none":
            errors.append(
                f"knowledge_partition.discarded[{index}]."
                "recovery_method: reversible residue cannot use "
                "'none'"
            )

        if (
            recovery_method == "archive"
            and not replacement_locator
        ):
            errors.append(
                f"knowledge_partition.discarded[{index}]."
                "replacement_locator: required when "
                "recovery_method is 'archive'"
            )

        if (
            not reversible
            and recovery_method != "none"
        ):
            errors.append(
                f"knowledge_partition.discarded[{index}]."
                "recovery_method: irreversible residue must use "
                "'none'"
            )

    if record_id in trace["parent_record_ids"]:
        errors.append(
            "trace.parent_record_ids: "
            "a record cannot reference itself as a parent"
        )

    archive_locators = [
        item["locator"]
        for item in archived
    ]

    for duplicate_locator in duplicate_values(
        archive_locators
    ):
        errors.append(
            "knowledge_partition.archived: "
            f"duplicate archive locator '{duplicate_locator}'"
        )

    return errors


def validate_knowledge_retention_decision(
    instance: Mapping[str, Any],
) -> list[str]:
    """Apply v0.2 semantic validation rules."""

    errors: list[str] = []

    decision_id = instance["decision_id"]
    evidence = instance["source_evidence"]
    origin_bindings = instance["origin_bindings"]
    evaluation = instance["evaluation"]
    decision = instance["decision"]
    policy = instance["policy_snapshot"]
    trace = instance["trace"]

    classification = decision["classification"]
    reversible = decision["reversible"]
    review_required = decision["review_required"]
    approval_ids = decision["approval_ids"]

    evidence_ids = [
        item["evidence_id"]
        for item in evidence
    ]

    for duplicate_id in duplicate_values(evidence_ids):
        errors.append(
            "source_evidence: "
            f"duplicate evidence id '{duplicate_id}'"
        )

    if not origin_bindings:
        errors.append(
            "origin_bindings: "
            "at least one retained origin binding is required "
            "for every retention decision"
        )

    if len(set(origin_bindings)) != len(origin_bindings):
        errors.append(
            "origin_bindings: "
            "duplicate origin bindings are not permitted"
        )

    minimum_provenance = policy[
        "minimum_provenance_quality"
    ]

    if evaluation["provenance_quality"] < minimum_provenance:
        errors.append(
            "evaluation.provenance_quality: "
            f"value {evaluation['provenance_quality']} is below "
            f"the policy minimum {minimum_provenance}"
        )

    essentiality_threshold = policy[
        "retain_if_essentiality_at_or_above"
    ]

    if (
        evaluation["essentiality"] >= essentiality_threshold
        and classification != "retain"
    ):
        errors.append(
            "decision.classification: "
            "knowledge meeting the essentiality retention threshold "
            "must be classified as 'retain'"
        )

    discard_threshold = policy[
        "discard_if_redundancy_at_or_above"
    ]

    if (
        classification == "discard"
        and evaluation["redundancy"] < discard_threshold
    ):
        errors.append(
            "evaluation.redundancy: "
            f"discard requires redundancy at or above "
            f"{discard_threshold}"
        )

    if classification == "archive":
        if not reversible:
            errors.append(
                "decision.reversible: "
                "archive decisions must be reversible"
            )

        if not decision.get("target_locator"):
            errors.append(
                "decision.target_locator: "
                "archive decisions require a target locator"
            )

        if decision.get("recovery_method") == "none":
            errors.append(
                "decision.recovery_method: "
                "archive decisions cannot use 'none'"
            )

    if classification == "discard":
        recovery_method = decision.get("recovery_method")

        if reversible and recovery_method == "none":
            errors.append(
                "decision.recovery_method: "
                "reversible discard cannot use 'none'"
            )

        if (
            not reversible
            and recovery_method != "none"
        ):
            errors.append(
                "decision.recovery_method: "
                "irreversible discard must use 'none'"
            )

        if (
            not reversible
            and policy[
                "prohibit_irreversible_discard_without_approval"
            ]
            and not approval_ids
        ):
            errors.append(
                "decision.approval_ids: "
                "irreversible discard requires at least one "
                "approval under the active policy"
            )

        if (
            evaluation["safety_critical"]
            and policy["prohibit_safety_critical_discard"]
        ):
            errors.append(
                "decision.classification: "
                "safety-critical knowledge cannot be discarded "
                "under the active policy"
            )

    if classification == "retain":
        if decision.get("disposal_method") is not None:
            errors.append(
                "decision.disposal_method: "
                "retained knowledge cannot define a disposal method"
            )

        if decision.get("recovery_method") == "none":
            errors.append(
                "decision.recovery_method: "
                "retained knowledge must not be marked "
                "unrecoverable"
            )

    if classification == "quarantine":
        if (
            policy["require_review_for_quarantine"]
            and not review_required
        ):
            errors.append(
                "decision.review_required: "
                "quarantine requires review under the active policy"
            )

        if not decision.get("target_locator"):
            errors.append(
                "decision.target_locator: "
                "quarantine requires an isolation locator"
            )

        if not decision.get("review_at"):
            errors.append(
                "decision.review_at: "
                "quarantine requires a scheduled review time"
            )

    if review_required and not decision.get("review_at"):
        errors.append(
            "decision.review_at: "
            "review_at is required when review_required is true"
        )

    if decision.get("review_at"):
        decided_at = parse_datetime(decision["decided_at"])
        review_at = parse_datetime(decision["review_at"])

        if review_at <= decided_at:
            errors.append(
                "decision.review_at: "
                "review time must occur after the decision time"
            )

    if decision_id in trace["parent_record_ids"]:
        errors.append(
            "trace.parent_record_ids: "
            "a decision cannot reference itself as a parent"
        )

    return errors


TARGETS: tuple[ValidationTarget, ...] = (
    ValidationTarget(
        name="Minimal Origin Knowledge Record",
        schema_path=(
            REPO_ROOT
            / "schemas"
            / "minimal-origin-knowledge-record.schema.json"
        ),
        pass_examples=(
            REPO_ROOT
            / "examples"
            / "pass"
            / "minimal-origin-knowledge-record.example.yaml",
        ),
        fail_examples=(
            REPO_ROOT
            / "examples"
            / "fail"
            / "missing-origin-binding.example.yaml",
            REPO_ROOT
            / "examples"
            / "fail"
            / "unsupported-certainty.example.yaml",
        ),
        semantic_validator=(
            validate_minimal_origin_knowledge_record
        ),
    ),
    ValidationTarget(
        name="Knowledge Retention Decision",
        schema_path=(
            REPO_ROOT
            / "schemas"
            / "knowledge-retention-decision.schema.json"
        ),
        pass_examples=(
            REPO_ROOT
            / "examples"
            / "pass"
            / "knowledge-retention-decision.example.yaml",
        ),
        fail_examples=(
            REPO_ROOT
            / "examples"
            / "fail"
            / "missing-origin-binding-decision.example.yaml",
            REPO_ROOT
            / "examples"
            / "fail"
            / "irreversible-discard-without-approval.example.yaml",
        ),
        semantic_validator=(
            validate_knowledge_retention_decision
        ),
    ),
)


def validate_instance(
    path: Path,
    validator: Draft202012Validator,
    semantic_validator: SemanticValidator,
) -> tuple[list[str], list[str]]:
    """Run schema and semantic validation for one instance."""

    instance = load_example(path)

    schema_errors = validate_schema(
        instance,
        validator,
    )

    if schema_errors:
        return schema_errors, []

    semantic_errors = semantic_validator(instance)

    return schema_errors, semantic_errors


def print_errors(
    error_type: str,
    errors: Sequence[str],
) -> None:
    """Print validation errors."""

    for error in errors:
        print(f"[{error_type}] {error}")


def validate_pass_example(
    path: Path,
    validator: Draft202012Validator,
    semantic_validator: SemanticValidator,
) -> bool:
    """Return True when a pass example behaves correctly."""

    relative_path = path.relative_to(REPO_ROOT)

    print()
    print(f"[validate-pass] {relative_path}")

    schema_errors, semantic_errors = validate_instance(
        path,
        validator,
        semantic_validator,
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
    """Return True when a fail example fails as expected."""

    relative_path = path.relative_to(REPO_ROOT)

    print()
    print(f"[validate-fail] {relative_path}")

    schema_errors, semantic_errors = validate_instance(
        path,
        validator,
        semantic_validator,
    )

    if schema_errors:
        print_errors(
            "expected-schema-error",
            schema_errors,
        )
        print("[expected-failure-ok]")
        return True

    print("[schema-ok]")

    if semantic_errors:
        print_errors(
            "expected-semantic-error",
            semantic_errors,
        )
        print("[expected-failure-ok]")
        return True

    print(
        "[unexpected-pass] "
        "The fail example passed schema and semantic validation."
    )

    return False


def validate_target(
    target: ValidationTarget,
) -> tuple[int, int, int, int]:
    """
    Validate one protocol target.

    Returns:
        pass_count
        fail_count
        unexpected_failures
        unexpected_passes
    """

    print()
    print("=" * 72)
    print(f"[target] {target.name}")
    print(
        f"[schema] "
        f"{target.schema_path.relative_to(REPO_ROOT)}"
    )

    schema = load_json(target.schema_path)
    validator = build_validator(schema)

    print("[schema-definition-ok]")

    unexpected_failures = 0
    unexpected_passes = 0

    for path in target.pass_examples:
        if not validate_pass_example(
            path,
            validator,
            target.semantic_validator,
        ):
            unexpected_failures += 1

    for path in target.fail_examples:
        if not validate_fail_example(
            path,
            validator,
            target.semantic_validator,
        ):
            unexpected_passes += 1

    return (
        len(target.pass_examples),
        len(target.fail_examples),
        unexpected_failures,
        unexpected_passes,
    )


def main() -> int:
    """Run all protocol validation targets."""

    print(
        "=== Minimal Origin-Derivative Reasoning "
        "Protocol Validation ==="
    )

    total_pass_examples = 0
    total_fail_examples = 0
    total_unexpected_failures = 0
    total_unexpected_passes = 0

    try:
        for target in TARGETS:
            (
                pass_count,
                fail_count,
                unexpected_failures,
                unexpected_passes,
            ) = validate_target(target)

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
        print(
            f"[fatal] Unexpected error: "
            f"{type(exc).__name__}: {exc}"
        )
        return 1

    print()
    print("=" * 72)
    print("=== Validation Summary ===")
    print(
        f"Targets checked       : {len(TARGETS)}"
    )
    print(
        f"Pass examples checked : {total_pass_examples}"
    )
    print(
        f"Fail examples checked : {total_fail_examples}"
    )
    print(
        f"Unexpected failures   : "
        f"{total_unexpected_failures}"
    )
    print(
        f"Unexpected passes     : "
        f"{total_unexpected_passes}"
    )

    if (
        total_unexpected_failures
        or total_unexpected_passes
    ):
        print()
        print("Validation failed.")
        return 1

    print()
    print("All validation checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
