# Changelog

All notable changes to the **Minimal Origin–Derivative Reasoning Protocol** are documented in this file.

The format is inspired by Keep a Changelog, and the project follows incremental protocol milestones.

---

## [Unreleased]

### Planned

* Cross-record reference validation using complete repository datasets
* Cryptographic signature support
* Policy profile separation
* Multi-agent knowledge custody records
* Knowledge conflict resolution records
* Royalty and attribution bindings for valuable Origin knowledge
* Machine-readable protocol registry

---

## [0.5.0] — 2026-07-20

### Added

* Added `Knowledge Lifecycle Audit`
* Added lifecycle-level validation covering v0.1 through v0.4 records
* Added record lineage requirements
* Added knowledge lifecycle event tracking
* Added terminal-state assessment
* Added control evaluation
* Added audit findings
* Added open-finding tracking
* Added lifecycle compliance assessment
* Added temporary integration closure checks
* Added event-to-record-type compatibility validation
* Added lifecycle state-transition validation

### Added Files

```text
schemas/knowledge-lifecycle-audit.schema.json
examples/pass/knowledge-lifecycle-audit.example.yaml
examples/fail/broken-lifecycle-lineage.example.yaml
examples/fail/unclosed-temporary-rehydration.example.yaml
```

### Validation

The v0.5 semantic validator checks:

* Required record types are present
* Required records appear in the audit lineage
* Record binding IDs are unique
* Lifecycle event IDs are unique
* Event sequence numbers are unique
* Event timestamps remain ordered
* Event states follow permitted transitions
* Event types are supported by the referenced record type
* Temporary integrations are closed after expiry
* Final lifecycle state matches the audit assessment
* Open findings match `open_finding_ids`
* Failed controls are not reported as compliant
* Error and critical findings remain within policy limits
* Audit issuance occurs after the audit period

### Negative Examples

* `broken-lifecycle-lineage.example.yaml`

  * Detects a missing v0.2 retention decision
  * Detects an archive event supported by an invalid record type

* `unclosed-temporary-rehydration.example.yaml`

  * Detects an expired temporary integration without rollback, expiry, or promotion

### Changed

* Updated `scripts/validate_examples.py` to support five protocol targets
* Expanded the validation summary to cover v0.1–v0.5
* Completed the initial knowledge lifecycle architecture

---

## [0.4.0] — 2026-07-20

### Added

* Added `Knowledge Rehydration Record`
* Added external and archived source candidate records
* Added source selection state
* Added integrity verification
* Added provenance verification
* Added schema compatibility checks
* Added relevance and freshness scoring
* Added conflict detection
* Added temporary integration controls
* Added expiry and rollback handling
* Added knowledge promotion support
* Added retention-decision linkage for persistent promotion

### Added Files

```text
schemas/knowledge-rehydration-record.schema.json
examples/pass/knowledge-rehydration-record.example.yaml
examples/fail/unverified-source-integration.example.yaml
examples/fail/temporary-integration-without-expiry.example.yaml
```

### Validation

The v0.4 semantic validator checks:

* Rehydration requests reference a reasoning trace
* Selected source IDs resolve correctly
* Exactly the declared source is marked as selected
* Hash verification is complete before integration
* Provenance verification is complete before integration
* Schema verification is complete before integration
* Selected sources have acceptable trust levels
* Source relevance meets policy thresholds
* Source freshness meets policy thresholds
* Unresolved conflicts block integration
* Temporary integration includes an expiry time
* Temporary integration includes a rollback target
* Expiry occurs after integration
* Persistent promotion references a retention decision
* Retrieval, verification, and integration timestamps remain ordered

### Negative Examples

* `unverified-source-integration.example.yaml`

  * Detects integration of a source without completed integrity verification
  * Detects integration of an unverified source

* `temporary-integration-without-expiry.example.yaml`

  * Detects temporary knowledge integration without an expiry time

### Changed

* Updated `scripts/validate_examples.py` to support four protocol targets
* Connected external retrieval to the derivative reasoning lifecycle

---

## [0.3.0] — 2026-07-20

### Added

* Added `Derivative Reasoning Trace`
* Added declared reasoning context
* Added assumptions
* Added Origin bindings
* Added retrieved knowledge inputs
* Added premise, intermediate, and conclusion claims
* Added derivation steps
* Added reasoning operations
* Added final-output records
* Added minimum final-confidence policies
* Added insufficient-knowledge actions

### Added Files

```text
schemas/derivative-reasoning-trace.schema.json
examples/pass/derivative-reasoning-trace.example.yaml
examples/fail/orphan-derived-claim.example.yaml
examples/fail/cyclic-derivation-trace.example.yaml
```

### Supported Reasoning Operations

```text
deduction
induction
abduction
analogy
aggregation
transformation
filter
comparison
```

### Validation

The v0.3 semantic validator checks:

* Reference identifiers are globally unique
* Derivation sequence numbers are unique
* Premise evidence references resolve
* Rejected assumptions are not used
* Derivation input references resolve
* A claim cannot directly derive itself
* Premises do not have producing steps
* Intermediate and conclusion claims have exactly one producing step
* Final output references conclusion claims
* Orphan claims are prohibited
* Circular claim dependencies are prohibited
* Final conclusions remain reachable from at least one Origin
* Low-confidence conclusions trigger a safe fallback action

### Negative Examples

* `orphan-derived-claim.example.yaml`

  * Detects a derived claim that is neither consumed nor finalized

* `cyclic-derivation-trace.example.yaml`

  * Detects circular dependency between derived claims

### Changed

* Updated `scripts/validate_examples.py` to support three protocol targets
* Replaced free-form reasoning logs with a machine-verifiable derivation graph

---

## [0.2.0] — 2026-07-20

### Added

* Added `Knowledge Retention Decision`
* Added knowledge subject metadata
* Added source evidence
* Added Origin bindings
* Added retention evaluation metrics
* Added policy snapshots
* Added approval requirements
* Added review scheduling
* Added quarantine decisions

### Added Files

```text
schemas/knowledge-retention-decision.schema.json
examples/pass/knowledge-retention-decision.example.yaml
examples/fail/missing-origin-binding-decision.example.yaml
examples/fail/irreversible-discard-without-approval.example.yaml
```

### Decision Classifications

```text
retain
archive
discard
quarantine
```

### Evaluation Metrics

```text
essentiality
recoverability
redundancy
freshness
provenance_quality
safety_critical
```

### Validation

The v0.2 semantic validator checks:

* Evidence IDs are unique
* At least one Origin binding exists
* Origin bindings are unique
* Provenance quality meets the active policy threshold
* Essential knowledge is retained
* Discard decisions meet the redundancy threshold
* Archives remain reversible
* Archives define a retrieval method and target
* Reversible discard defines a recovery method
* Irreversible discard requires approval
* Safety-critical knowledge is not discarded
* Quarantine decisions require review
* Review time occurs after the decision
* A decision cannot reference itself as a parent

### Negative Examples

* `missing-origin-binding-decision.example.yaml`

  * Detects retention decisions without an Origin relationship

* `irreversible-discard-without-approval.example.yaml`

  * Detects irreversible deletion without approval

### Changed

* Updated `scripts/validate_examples.py` to support v0.1 and v0.2
* Converted knowledge deletion from an implicit action into an auditable decision

---

## [0.1.0] — 2026-07-20

### Added

* Added `Minimal Origin Knowledge Record`
* Added the minimal Origin Kernel structure
* Added normative and informative principles
* Added protocol definitions
* Added reasoning constraints
* Added retained knowledge records
* Added recallable archive records
* Added disposable residue records
* Added derivation policy
* Added audit policy
* Added trace metadata
* Added schema and semantic validation
* Added pass and fail examples
* Added GitHub Actions validation workflow
* Added Python dependency management through `requirements.txt`

### Added Files

```text
schemas/minimal-origin-knowledge-record.schema.json
examples/pass/minimal-origin-knowledge-record.example.yaml
examples/fail/missing-origin-binding.example.yaml
examples/fail/unsupported-certainty.example.yaml
scripts/validate_examples.py
.github/workflows/validate.yml
requirements.txt
```

### Core Definitions

```text
Origin
A minimal knowledge unit required to preserve meaning,
causality, constraints, or identity.

Derivative
A contextual conclusion generated from one or more Origins
and the currently declared context.

Residue
Knowledge that is redundant, obsolete, reproducible,
untraceable, or unnecessary for stable reasoning.
```

### Knowledge Partitions

```text
Origin Kernel
Recallable Archive
Disposable Residue
```

### Validation

The v0.1 semantic validator checks:

* Required semantic definitions exist
* Principle identifiers are unique
* Knowledge identifiers are unique
* Discarded knowledge hashes are unique
* Origin binding is enabled
* Context declaration is enabled
* External retrieval has an archive source
* Safe insufficient-knowledge actions exist
* Mandatory audit controls are enabled
* Reversible residue has a recovery method
* Archived recovery defines a replacement locator
* Irreversible residue uses `none` as its recovery method
* Archive locators are unique
* A record cannot reference itself as a parent

### Negative Examples

* `missing-origin-binding.example.yaml`

  * Detects derivative reasoning without required Origin binding

* `unsupported-certainty.example.yaml`

  * Detects configurations that permit unsupported certainty

### Infrastructure

Added dependency definitions:

```text
jsonschema[format]>=4.20,<5
PyYAML>=6,<7
```

Added GitHub Actions validation for supported Python versions.

---

## Version Summary

```text
v0.1 Define the minimal Origin
v0.2 Decide where knowledge belongs
v0.3 Derive conclusions with traceable reasoning
v0.4 Rehydrate missing knowledge safely
v0.5 Audit the complete knowledge lifecycle
```

The v0.1–v0.5 foundation establishes the complete baseline:

```text
Define
Decide
Derive
Rehydrate
Audit
```
