#!/usr/bin/env python3
"""
Validate Minimal Origin Knowledge Record examples.

Validation is performed in two stages:

1. JSON Schema validation
2. Protocol-specific semantic validation

Files under examples/pass/ must pass both stages.
Files under examples/fail/ must fail at least one stage.

Dependencies:
    pip install jsonschema PyYAML
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import yaml
from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import SchemaError


REPO_ROOT = Path(__file__).resolve().parents[1]

SCHEMA_PATH = (
    REPO_ROOT
    / "schemas"
    / "minimal-origin-knowledge-record.schema.json"
)

PASS_DIR = REPO_ROOT / "examples" / "pass"
FAIL_DIR = REPO_ROOT / "examples" / "fail"

SUPPORTED_EXAMPLE_SUFFIXES = {".yaml", ".yml", ".json"}


class ValidationFailure(Exception):
    """Raised when the validation suite cannot continue safely."""


def load_json(path: Path) -> Mapping[str, Any]:
    """Load and return a JSON object."""

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
        raise ValidationFailure(
            f"Expected a JSON object at the root of {path}"
        )

    return value


def load_example(path: Path) -> Mapping[str, Any]:
    """Load a YAML or JSON example file."""

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
            f"Invalid JSON in {path}: line {exc.lineno}, "
            f"column {exc.colno}: {exc.msg}"
        ) from exc
    except yaml.YAMLError as exc:
        raise ValidationFailure(f"Invalid YAML in {path}: {exc}") from exc
    except OSError as exc:
        raise ValidationFailure(f"Could not read {path}: {exc}") from exc

    if not isinstance(value, Mapping):
        raise ValidationFailure(
            f"Expected an object at the root of {path}"
        )

    return value


def format_instance_path(path_parts: Iterable[Any]) -> str:
    """
    Convert a jsonschema path into a readable dotted path.

    Example:
        ["origin_kernel", "principles", 0, "id"]
        -> origin_kernel.principles[0].id
    """

    result = ""

    for part in path_parts:
        if isinstance(part, int):
            result += f"[{part}]"
        else:
            if result:
                result += "."
            result += str(part)

    return result or "<root>"


def collect_example_files(directory: Path) -> list[Path]:
    """Return supported example files in deterministic order."""

    if not directory.exists():
        raise ValidationFailure(
            f"Example directory does not exist: {directory}"
        )

    if not directory.is_dir():
        raise ValidationFailure(
            f"Expected an example directory: {directory}"
        )

    files = sorted(
        path
        for path in directory.iterdir()
        if path.is_file()
        and path.suffix.lower() in SUPPORTED_EXAMPLE_SUFFIXES
    )

    if not files:
        raise ValidationFailure(
            f"No YAML or JSON examples found in: {directory}"
        )

    return files


def build_validator(
    schema: Mapping[str, Any],
) -> Draft202012Validator:
    """Validate the schema itself and construct a validator."""

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


def validate_schema(
    instance: Mapping[str, Any],
    validator: Draft202012Validator,
) -> list[str]:
    """Return all JSON Schema validation errors."""

    errors: list[str] = []

    sorted_errors = sorted(
        validator.iter_errors(instance),
        key=lambda error: (
            list(error.absolute_path),
            error.message,
        ),
    )

    for error in sorted_errors:
        location = format_instance_path(error.absolute_path)
        errors.append(f"{location}: {error.message}")

    return errors


def duplicate_values(values: Sequence[str]) -> list[str]:
    """Return sorted duplicate string values."""

    counts = Counter(values)
    return sorted(
        value
        for value, count in counts.items()
        if count > 1
    )


def validate_semantics(
    instance: Mapping[str, Any],
) -> list[str]:
    """
    Apply protocol-specific semantic rules.

    This function assumes JSON Schema validation has already succeeded.
    """

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

    # Rule 1:
    # The core vocabulary must remain explicitly defined.
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

    # Rule 2:
    # Principle identifiers must be unique.
    principle_ids = [
        principle["id"]
        for principle in principles
    ]

    for duplicate_id in duplicate_values(principle_ids):
        errors.append(
            "origin_kernel.principles: "
            f"duplicate principle id '{duplicate_id}'"
        )

    # Rule 3:
    # Retained and archived knowledge identifiers must be unique
    # across the complete active and recallable knowledge space.
    retained_ids = [
        item["knowledge_id"]
        for item in retained
    ]

    archived_ids = [
        item["knowledge_id"]
        for item in archived
    ]

    all_knowledge_ids = retained_ids + archived_ids

    for duplicate_id in duplicate_values(all_knowledge_ids):
        errors.append(
            "knowledge_partition: "
            f"duplicate knowledge id '{duplicate_id}'"
        )

    # Rule 4:
    # Discarded hashes must not be duplicated.
    discarded_hashes = [
        item["knowledge_hash"]
        for item in discarded
    ]

    for duplicate_hash in duplicate_values(discarded_hashes):
        errors.append(
            "knowledge_partition.discarded: "
            f"duplicate knowledge hash '{duplicate_hash}'"
        )

    # Rule 5:
    # Origin binding is mandatory for derivative reasoning.
    if not derivation_policy["require_origin_binding"]:
        errors.append(
            "derivation_policy.require_origin_binding: "
            "must be true; derivative conclusions may not exist "
            "without retained origin bindings"
        )

    # Rule 6:
    # Reasoning context must be declared.
    if not derivation_policy["require_context_declaration"]:
        errors.append(
            "derivation_policy.require_context_declaration: "
            "must be true to preserve contextual traceability"
        )

    # Rule 7:
    # External retrieval requires at least one recallable archive entry.
    if (
        derivation_policy["permit_external_retrieval"]
        and not archived
    ):
        errors.append(
            "knowledge_partition.archived: "
            "must contain at least one item when external retrieval "
            "is permitted"
        )

    # Rule 8:
    # Safe fallback actions must be defined.
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

    dangerous_absence = {
        "retrieve",
        "defer",
        "ask",
        "abstain",
    }.isdisjoint(safe_actions)

    if dangerous_absence:
        errors.append(
            "derivation_policy."
            "allowed_insufficient_knowledge_actions: "
            "must include retrieve, defer, ask, or abstain"
        )

    # Rule 9:
    # All audit protections are mandatory in v0.1.
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

    # Rule 10:
    # Reversible deletion must have a valid recovery path.
    for index, item in enumerate(discarded):
        reversible = item["reversible"]
        recovery_method = item["recovery_method"]
        replacement_locator = item.get("replacement_locator")

        if reversible and recovery_method == "none":
            errors.append(
                f"knowledge_partition.discarded[{index}]."
                "recovery_method: reversible residue cannot use "
                "'none' as its recovery method"
            )

        if (
            recovery_method == "archive"
            and not replacement_locator
        ):
            errors.append(
                f"knowledge_partition.discarded[{index}]."
                "replacement_locator: required when recovery_method "
                "is 'archive'"
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

    # Rule 11:
    # The record must not list itself as its own parent.
    parent_record_ids = trace["parent_record_ids"]

    if record_id in parent_record_ids:
        errors.append(
            "trace.parent_record_ids: "
            "a record cannot reference itself as a parent"
        )

    # Rule 12:
    # Archived locators should be unique to avoid ambiguous retrieval.
    archive_locators = [
        item["locator"]
        for item in archived
    ]

    for duplicate_locator in duplicate_values(archive_locators):
        errors.append(
            "knowledge_partition.archived: "
            f"duplicate archive locator '{duplicate_locator}'"
        )

    return errors


def validate_instance(
    path: Path,
    validator: Draft202012Validator,
) -> tuple[list[str], list[str]]:
    """Run schema and semantic validation for one file."""

    instance = load_example(path)

    schema_errors = validate_schema(instance, validator)

    if schema_errors:
        return schema_errors, []

    semantic_errors = validate_semantics(instance)

    return schema_errors, semantic_errors


def print_errors(
    error_type: str,
    errors: Sequence[str],
) -> None:
    """Print a formatted validation error list."""

    for error in errors:
        print(f"[{error_type}] {error}")


def validate_pass_examples(
    paths: Sequence[Path],
    validator: Draft202012Validator,
) -> int:
    """
    Validate examples expected to pass.

    Returns the number of unexpected failures.
    """

    unexpected_failures = 0

    for path in paths:
        relative_path = path.relative_to(REPO_ROOT)

        print()
        print(f"[validate-pass] {relative_path}")

        schema_errors, semantic_errors = validate_instance(
            path,
            validator,
        )

        if schema_errors:
            print_errors("schema-error", schema_errors)
            unexpected_failures += 1
            continue

        print("[schema-ok]")

        if semantic_errors:
            print_errors("semantic-error", semantic_errors)
            unexpected_failures += 1
            continue

        print("[semantic-ok]")
        print("[pass-ok]")

    return unexpected_failures


def validate_fail_examples(
    paths: Sequence[Path],
    validator: Draft202012Validator,
) -> int:
    """
    Validate examples expected to fail.

    Returns the number of examples that unexpectedly passed.
    """

    unexpected_passes = 0

    for path in paths:
        relative_path = path.relative_to(REPO_ROOT)

        print()
        print(f"[validate-fail] {relative_path}")

        schema_errors, semantic_errors = validate_instance(
            path,
            validator,
        )

        if schema_errors:
            print_errors("expected-schema-error", schema_errors)
            print("[expected-failure-ok]")
            continue

        print("[schema-ok]")

        if semantic_errors:
            print_errors(
                "expected-semantic-error",
                semantic_errors,
            )
            print("[expected-failure-ok]")
            continue

        print(
            "[unexpected-pass] "
            "The fail example passed both schema and semantic "
            "validation."
        )
        unexpected_passes += 1

    return unexpected_passes


def main() -> int:
    """Run the complete validation suite."""

    print(
        "=== Minimal Origin-Derivative Reasoning "
        "Protocol Validation ==="
    )

    try:
        schema = load_json(SCHEMA_PATH)
        validator = build_validator(schema)

        pass_examples = collect_example_files(PASS_DIR)
        fail_examples = collect_example_files(FAIL_DIR)

        print()
        print(f"[schema] {SCHEMA_PATH.relative_to(REPO_ROOT)}")
        print("[schema-definition-ok]")

        pass_failures = validate_pass_examples(
            pass_examples,
            validator,
        )

        fail_unexpected_passes = validate_fail_examples(
            fail_examples,
            validator,
        )

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
    print("=== Validation Summary ===")
    print(f"Pass examples checked : {len(pass_examples)}")
    print(f"Fail examples checked : {len(fail_examples)}")
    print(f"Unexpected failures   : {pass_failures}")
    print(
        "Unexpected passes     : "
        f"{fail_unexpected_passes}"
    )

    if pass_failures or fail_unexpected_passes:
        print()
        print("Validation failed.")
        return 1

    print()
    print("All validation checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
