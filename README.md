# Minimal Origin–Derivative Reasoning Protocol

> Retain the minimum origin, derive what is needed, retrieve what is missing, and audit the entire knowledge lifecycle.

**Minimal Origin–Derivative Reasoning Protocol** は、知識を無制限に内部保持するのではなく、必要最小限の起源知識だけを保持し、文脈に応じて派生推論・外部取得・一時統合・破棄を行うための監査可能な仕様です。

本プロトコルは、次の問いを扱います。

* 何を恒常的に保持するべきか
* 何を外部アーカイブへ退避するべきか
* 何を破棄してよいか
* どのOriginから結論が派生したか
* 外部知識を安全に再取得できるか
* 一時統合された知識が期限後に回収されたか
* 知識の全ライフサイクルに矛盾がないか

---

## 1. Background

巨大な知識量をそのまま知能と見なす設計では、知識の重複、陳腐化、計算負荷、出典不明、推論経路の不透明化が蓄積します。

本プロトコルは、知能を次の構造として再定義します。

```text
Intelligence
  = Minimal Origin Kernel
  + Contextual Derivation
  + Selective Retrieval
  + Temporary Integration
  + Lifecycle Audit
  - Redundant Residue
```

重要なのは、すべてを覚えることではありません。

```text
何を残すか
何を外部へ置くか
何を忘れるか
何を再取得するか
どの起源から何を派生させたか
```

を制御し、説明できることが知能の基礎になります。

---

## 2. Core Principles

### Minimal Retention

恒常的に保持する知識を、意味・因果・制約・安全性を維持するために必要な最小限へ限定します。

### Origin Binding

派生した結論は、少なくとも一つの保持済みOriginへ遡れる必要があります。

### Selective Retrieval

詳細知識や更新頻度の高い情報は外部へ退避し、必要なときだけ取得します。

### Traceable Forgetting

知識の破棄を無記録で行いません。破棄理由、可逆性、復元方法、判断主体を記録します。

### Temporary Rehydration

再取得した知識は、検証後に期限付きで推論空間へ統合します。

### Lifecycle Audit

保持・退避・派生・再取得・昇格・回収・破棄までを、一つの知識ライフサイクルとして監査します。

---

## 3. Protocol Layers

本リポジトリは、v0.1からv0.5までの五つの記録仕様で構成されます。

| Version | Record                          | Purpose                      |
| ------- | ------------------------------- | ---------------------------- |
| v0.1    | Minimal Origin Knowledge Record | 恒常的に保持する最小Origin Kernelを定義する |
| v0.2    | Knowledge Retention Decision    | 保持・退避・破棄・隔離の判断根拠を記録する        |
| v0.3    | Derivative Reasoning Trace      | Originから結論までの派生経路を記録する       |
| v0.4    | Knowledge Rehydration Record    | 外部知識の取得・検証・一時統合を管理する         |
| v0.5    | Knowledge Lifecycle Audit       | 知識ライフサイクル全体を最終監査する           |

---

## 4. Architecture

```text
Knowledge Input
      │
      ▼
┌──────────────────────────────────────┐
│ v0.1 Minimal Origin Knowledge Record │
│ Origin Kernel / Archive / Residue    │
└──────────────────┬───────────────────┘
                   │
                   ▼
┌──────────────────────────────────────┐
│ v0.2 Knowledge Retention Decision    │
│ Retain / Archive / Discard /         │
│ Quarantine                           │
└──────────────────┬───────────────────┘
                   │
                   ▼
┌──────────────────────────────────────┐
│ v0.3 Derivative Reasoning Trace      │
│ Origin → Premise → Intermediate →    │
│ Conclusion                           │
└──────────────────┬───────────────────┘
                   │
            Missing knowledge
                   │
                   ▼
┌──────────────────────────────────────┐
│ v0.4 Knowledge Rehydration Record    │
│ Retrieve → Verify → Integrate →      │
│ Expire / Rollback / Promote          │
└──────────────────┬───────────────────┘
                   │
                   ▼
┌──────────────────────────────────────┐
│ v0.5 Knowledge Lifecycle Audit       │
│ Lineage / Transition / Closure /     │
│ Final Assessment                     │
└──────────────────────────────────────┘
```

---

## 5. Knowledge Partition

知識は、単純な保存・削除の二択ではなく、三つの領域へ分類されます。

### Origin Kernel

恒常的に保持する最小知識です。

例：

* 基本原則
* 定義
* 制約条件
* 安全規則
* 判断軸
* 起源識別子

### Recallable Archive

通常はアクティブな推論空間へ置かず、必要時に再取得する知識です。

例：

* 詳細な実装例
* 外部文書
* 過去の監査記録
* 更新頻度の高いデータ
* 特定状況でのみ必要な専門知識

### Disposable Residue

破棄または圧縮できる知識です。

例：

* 重複情報
* 古いキャッシュ
* 再生成可能な中間生成物
* 出典不明な断片
* 参照されない推論枝
* 置き換え済みの一時データ

---

## 6. Record Specifications

### v0.1 — Minimal Origin Knowledge Record

最小Origin Kernelと、知識の現在配置を記録します。

主な構造：

```text
subject
origin_kernel
  ├── principles
  ├── definitions
  └── constraints
knowledge_partition
  ├── retained
  ├── archived
  └── discarded
derivation_policy
audit_policy
trace
```

主な不変条件：

* `origin`、`derivative`、`residue`を定義する
* 派生推論にはOrigin紐付けを要求する
* 文脈宣言を必須にする
* 根拠なき断定を禁止する
* 可逆な破棄には復元方法を設定する
* レコード自身を親レコードに指定しない

---

### v0.2 — Knowledge Retention Decision

知識をどこへ配置するか、その判断過程を記録します。

判定分類：

```text
retain
archive
discard
quarantine
```

評価指標：

* Essentiality
* Recoverability
* Redundancy
* Freshness
* Provenance quality
* Safety criticality

主な不変条件：

* 判断にはOrigin紐付けが必要
* 来歴品質が方針値を下回る場合は拒否する
* 重要度が保持閾値以上なら`retain`とする
* 不可逆破棄には承認を要求する
* Safety-criticalな知識を無断破棄しない
* 隔離には再審査時刻を設定する

---

### v0.3 — Derivative Reasoning Trace

Originから結論までの派生経路を、有向非循環グラフとして記録します。

```text
Origin / Retrieved Source / Assumption
                  │
                  ▼
               Premise
                  │
                  ▼
             Intermediate
                  │
                  ▼
              Conclusion
```

主な不変条件：

* すべての参照IDを解決できる
* 参照IDをレコード内で重複させない
* Premiseには根拠参照が必要
* IntermediateとConclusionには生成ステップが必要
* 推論グラフに循環を作らない
* 未使用の孤立命題を残さない
* 最終結論を少なくとも一つのOriginへ接続する
* 信頼度不足時は安全なフォールバックを選択する

安全なフォールバック：

```text
retrieve
defer
ask
abstain
```

---

### v0.4 — Knowledge Rehydration Record

アーカイブまたは外部ソースから知識を再取得し、安全に一時統合する過程を記録します。

```text
Rehydration Request
        │
        ▼
Source Candidate Selection
        │
        ▼
Integrity Verification
        │
        ▼
Temporary Integration
        │
        ├── Expire
        ├── Rollback
        └── Promote
```

主な不変条件：

* 再取得要求を推論トレースへ接続する
* 選択されたソースIDと選択状態を一致させる
* ハッシュ・来歴・スキーマ検証後に統合する
* 未検証または係争中の情報を統合しない
* 関連度・鮮度の方針閾値を満たす
* 未解決の競合がある場合は統合しない
* 一時統合に有効期限を設定する
* ロールバック先を明示する
* 永続化候補をv0.2の保持判断へ接続する

---

### v0.5 — Knowledge Lifecycle Audit

v0.1〜v0.4のレコードを、一つの知識ライフサイクルとして監査します。

監査対象：

```text
Origin declaration
Retention decision
Derivative use
Rehydration
Temporary integration
Rollback
Promotion
Expiration
Discard
```

主な不変条件：

* 必須レコード種別をすべて確認する
* レコード系譜と親レコード参照を検証する
* 許可された状態遷移だけを認める
* イベント種別と根拠レコード種別を一致させる
* 期限切れの一時知識を閉鎖する
* 最終状態と監査評価を一致させる
* 未解決Findingと集計結果を一致させる
* Control failureがある状態で`compliant`と判定しない
* 監査レコード自身の自己矛盾を検出する

---

## 7. Lifecycle States

本プロトコルでは、知識状態を次のように扱います。

```text
absent
active
archived
temporary
quarantined
discarded
```

代表的な許可遷移：

```text
absent    → active
active    → archived
archived  → temporary
temporary → archived
temporary → active
active    → discarded
archived  → discarded
```

一時知識は、期限到来後に次のいずれかへ移行しなければなりません。

```text
expired
rolled-back
promoted
```

期限切れ後も`temporary`のまま残る状態は、ライフサイクル監査で拒否されます。

---

## 8. Repository Structure

```text
minimal-origin-derivative-reasoning/
├── README.md
├── CHANGELOG.md
├── requirements.txt
├── schemas/
│   ├── minimal-origin-knowledge-record.schema.json
│   ├── knowledge-retention-decision.schema.json
│   ├── derivative-reasoning-trace.schema.json
│   ├── knowledge-rehydration-record.schema.json
│   └── knowledge-lifecycle-audit.schema.json
├── examples/
│   ├── pass/
│   │   ├── minimal-origin-knowledge-record.example.yaml
│   │   ├── knowledge-retention-decision.example.yaml
│   │   ├── derivative-reasoning-trace.example.yaml
│   │   ├── knowledge-rehydration-record.example.yaml
│   │   └── knowledge-lifecycle-audit.example.yaml
│   └── fail/
│       ├── missing-origin-binding.example.yaml
│       ├── unsupported-certainty.example.yaml
│       ├── missing-origin-binding-decision.example.yaml
│       ├── irreversible-discard-without-approval.example.yaml
│       ├── orphan-derived-claim.example.yaml
│       ├── cyclic-derivation-trace.example.yaml
│       ├── unverified-source-integration.example.yaml
│       ├── temporary-integration-without-expiry.example.yaml
│       ├── broken-lifecycle-lineage.example.yaml
│       └── unclosed-temporary-rehydration.example.yaml
├── scripts/
│   └── validate_examples.py
└── .github/
    └── workflows/
        └── validate.yml
```

---

## 9. Requirements

* Python 3.11 or later
* `jsonschema`
* `PyYAML`

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

`requirements.txt`:

```text
jsonschema[format]>=4.20,<5
PyYAML>=6,<7
```

---

## 10. Validation

Run all schema and semantic validation:

```bash
python scripts/validate_examples.py
```

The validator performs two stages.

### Schema Validation

Checks:

* Required fields
* Data types
* Enumerations
* Identifier formats
* SHA-256 formats
* Date-time formats
* Conditional requirements
* Additional properties

### Semantic Validation

Checks relationships that cannot be fully represented by JSON Schema alone.

Examples:

* Origin reachability
* Duplicate identifiers
* Circular derivation
* Orphan claims
* Policy threshold compliance
* Approval requirements
* Temporary integration expiry
* Lifecycle state transitions
* Record lineage completeness
* Audit self-consistency

Expected summary:

```text
=== Validation Summary ===
Targets checked       : 5
Pass examples checked : 5
Fail examples checked : 10
Unexpected failures   : 0
Unexpected passes     : 0

All validation checks passed.
```

---

## 11. Pass and Fail Examples

Files under `examples/pass/` must pass both schema and semantic validation.

Files under `examples/fail/` must fail at least one validation stage.

This structure verifies not only that valid records are accepted, but also that dangerous or contradictory records are rejected.

```text
Pass example
  schema-ok
  semantic-ok
  pass-ok

Fail example
  schema-ok
  expected-semantic-error
  expected-failure-ok
```

A fail example that unexpectedly passes causes the validator to exit with a non-zero status.

---

## 12. GitHub Actions

The workflow runs validation automatically on:

* Pushes to `main` or `master`
* Pull requests
* Manual workflow execution

The validation matrix covers supported Python versions configured in:

```text
.github/workflows/validate.yml
```

Changes under the following paths trigger validation:

```text
schemas/**
examples/**
scripts/**
requirements.txt
.github/workflows/validate.yml
```

---

## 13. Adding a New Record Type

To extend the protocol:

1. Add a JSON Schema under `schemas/`
2. Add at least one valid example under `examples/pass/`
3. Add relevant invalid examples under `examples/fail/`
4. Implement a semantic validator in `scripts/validate_examples.py`
5. Register the record in `TARGETS`
6. Run local validation
7. Confirm GitHub Actions passes

Every new record type should define:

* Its role in the lifecycle
* Required parent records
* Allowed references
* Semantic invariants
* Failure examples
* Audit implications

---

## 14. Design Boundaries

This protocol does not attempt to define:

* A specific machine-learning model architecture
* A universal measure of knowledge importance
* A complete truth-verification system
* A replacement for source-specific access control
* A method for physically deleting data from every storage system

Instead, it defines a portable record and audit layer for systems that need to explain:

```text
why knowledge was retained
why knowledge was archived
why knowledge was discarded
how a conclusion was derived
how external knowledge was reintroduced
whether temporary knowledge was properly closed
```

---

## 15. Protocol Statement

> Intelligence is not the unlimited accumulation of knowledge.
> Intelligence is the ability to retain a minimal origin, derive what is needed, retrieve what is missing, discard what is redundant, and audit every transition.

日本語では、次のように表現できます。

> 知能とは、無限に知識を蓄積する能力ではない。
> 必要最小限の起源を保持し、必要な意味を派生させ、不足を再取得し、不要な残滓を手放し、その全過程を監査できる構造である。

---

## 16. Status

Current protocol milestone:

```text
v0.5 — Knowledge Lifecycle Audit
```

The v0.1–v0.5 foundational lifecycle is complete.

```text
Define
Decide
Derive
Rehydrate
Audit
```

This repository now provides a complete baseline for a traceable minimal-knowledge reasoning system.
