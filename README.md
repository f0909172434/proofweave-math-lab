# ProofWeave Core v2

[English](README.en.md) · [简体中文](README.zh-CN.md) · [日本語](README.ja.md)

[![Core CI](https://github.com/f0909172434/proofweave-math-lab/actions/workflows/ci.yml/badge.svg)](https://github.com/f0909172434/proofweave-math-lab/actions/workflows/ci.yml)
[![CodeQL](https://github.com/f0909172434/proofweave-math-lab/actions/workflows/codeql.yml/badge.svg)](https://github.com/f0909172434/proofweave-math-lab/actions/workflows/codeql.yml)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-3776AB.svg)](pyproject.toml)
[![Lean 4.32.2](https://img.shields.io/badge/Lean-4.32.2-4E64C4.svg)](lean-toolchain)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

**把一份結構化數學證明，轉成小而可檢視的認證紀錄。**

ProofWeave Core v2 讀取 UTF-8 Markdown 命題，輸出：

- 正規化後的 UTF-8 parsed input；原始輸入 bytes 另由 `source_hash` 綁定；
- 精簡論文證明與 Mermaid proof spine／concept map；
- 逐項 deductive coverage；
- 在受支援範圍內產生的 Lean 原始碼與 deterministic certificate；
- content-addressed run metadata、雜湊與明確的 claim revision 狀態。

Core 不會發現證明、不會把任意自然語言自動翻成 Lean，也不呼叫 LLM。
Runtime 沒有 agents、providers、prompts、model router、reviewer loop、託管服務或
telemetry。它只認證作者明確提供的 formal target；不支援的 obligation 會保留為
`PARTIAL`，不會被包裝成成功。

> **專案狀態：**實驗性研究基礎設施。目前 repository/evidence release 是
> `v0.1.0`，Core runtime 與 protocol version 是 `2.0.0`；兩者是不同版本軸。

## 先看結果

使用固定工具鏈執行內建環恆等式範例，會得到以下形式的結果（已省略路徑與雜湊）：

```json
{
  "claim_id": "square-successor",
  "proof_status": "CERTIFIED",
  "alignment": "UNCONFIRMED",
  "fast_path": true,
  "cache_hit": false,
  "coverage": {
    "deductive_total": 1,
    "certified": 1,
    "failed": 0,
    "unsupported": 0,
    "host_limited": 0,
    "percentage": 100.0,
    "dependencies_ready": true
  },
  "invocations": {
    "model": 0,
    "semantic_extraction": 0,
    "certifier": 1
  },
  "artifact_directory": ".../artifacts/square-successor/<run-id>"
}
```

`CERTIFIED + UNCONFIRMED` 是刻意的結果：Lean 證明了精確 formal target，
但 ProofWeave 沒有推論它與人類命題語義相同。相同輸入再次執行時，Core 會先核對
artifact hashes，然後回傳 `cache_hit: true`；model、semantic extraction 與
certifier invocation 都是 0。

## 適合與不適合的情境

適合用在：

- 以固定 Lean 工具鏈檢查代數或算術命題；
- 清楚顯示長證明中哪些步驟有 certificate、哪些仍 unsupported；
- 分開管理 assumptions、quantifiers、claim dependencies、revision 與 lifecycle；
- deterministic 地拒絕依賴循環、缺少 active dependency、過期 alignment、或遭竄改
  的 cache artifact；
- 在不改變 certificate obligations 的前提下輸出保守的 paper view 與 proof map；
- 為固定 corpus 或 theorem pack 產生可重現、帶 checksum 的 evaluation bundle。

不適合用在：

- 自動 proof search、自然語言 formalization、任意 Lean tactic/import、互動式證明 UI；
- 數學發現、文獻搜尋、新穎性判定、peer review 或現實世界語義保證；
- multi-agent orchestration、model routing、研究專案管理或託管協作資料庫；
- global soundness、completeness 或「最簡證明」保證。

## 從原始碼快速開始

### 1. 前置需求

- Python 3.11+；
- Git；
- [Elan](https://github.com/leanprover/elan)（Lean toolchain manager）。

Repository 以 [`lean-toolchain`](lean-toolchain) 固定 Lean，以
[`lakefile.toml`](lakefile.toml) 固定 Mathlib version，並由
[`lake-manifest.json`](lake-manifest.json) 固定完整 dependency revisions。
雖然 bootstrap 從 shell 呼叫 `lake`，實際認證會依專案 pin 從 Elan 管理目錄
（或 `ELAN_HOME`）解析 `lean`／`lake`；PATH-only shim 不算 frozen certifier。

### 2. 安裝並凍結 formal environment

```console
git clone https://github.com/f0909172434/proofweave-math-lab.git
cd proofweave-math-lab
python -m pip install --no-deps --editable .
lake update mathlib
lake exe cache get
```

Windows 可把每個 `python` 換成 `py -3.14`。第一次下載 Mathlib checkout/cache
可能需要數分鐘。Core 本身沒有 Python runtime dependency；真正認證才需要完整的
Lean/Mathlib。若環境不完整，Core 會 fail closed 為 `PARTIAL/HOST_LIMITED`，
不會捏造 certificate。

### 3. 初始化並認證範例

```console
python -m proofweave init
python -m proofweave run examples/simple_ring/theorem.md
python -m proofweave status square-successor
```

`init` 只建立缺少的 `workspace/claims/` 與 `artifacts/`；`run` 在終端輸出
JSON 並寫入完整 run；`status` 讀取 claim revision，並依三個獨立狀態軸統計。

不要機械式加入 `--confirm-alignment`。人類先比對精確的 `## Statement` 加
quantifiers 與 Lean `target`，並另外確認 assumptions/dependencies 符合預期 theorem，
再用以下命令建立本地 alignment attestation：

```console
python -m proofweave run examples/simple_ring/theorem.md --confirm-alignment
```

Alignment hash 把 `statement_hash`（statement 加 quantifiers）與 formal-target hash
綁在一起；stored source hash 會偵測其他 source edits。這個 flag 不驗證 reviewer
身分，也不代表 novelty、peer review 或 formal target 以外的真實性。Source 變動後，
stored alignment 會顯示 `STALE`，直到人類檢查並執行新 revision。

## 輸入契約

Claim 以 TOML front matter 開始，後接 `## Statement` 與 `## Proof`；whole-claim
certificate 放在可選的 `## Certificate`：

````markdown
+++
claim_id = "square-successor"
title = "Square of a successor"
assumptions = ["x is an integer"]
quantifiers = ["for every integer x"]
dependencies = []
+++

## Statement

For every integer x, (x + 1)^2 = x^2 + 2x + 1.

## Proof

Expand the square and collect like terms.

## Certificate

```proofweave-lean
target = "forall x : Int, (x + 1)^2 = x^2 + 2*x + 1"
tactic = "ring"
```
````

重要解析規則：

- `claim_id` 必須符合 `[A-Za-z0-9][A-Za-z0-9._-]{0,63}`。
- `assumptions` 必須明列；適用時使用 `["none"]`。
- `quantifiers` 與 `dependencies` 是陣列。每個 dependency 必須已在同一專案中有
  唯一一個 `ACTIVE` claim revision。
- Claim dependencies 與 proof-node dependencies 都必須是無環 DAG。
- 不明 front-matter/certificate fields 會 fail closed。
- 輸入 bytes 必須是 UTF-8。

### 較長、只有部分 formalization 的證明

若沒有 whole-claim `## Certificate`，Core 會建立一份 deterministic proof IR：

````markdown
### normalize [computational]

Normalize the polynomial endpoint.

```proofweave-lean
target = "(20 + 22 : Int) = 42"
tactic = "norm_num"
```

### interpret [semantic]
Depends: normalize

Explain why the certified endpoint establishes the intended mathematical step.
````

角色為 `semantic`、`bridge`、`computational`、`alias`。每個非 `alias` node
都是 deductive obligation。若 node 沒有受支援 certificate，就會原樣保留為
unsupported，整體 run 是 `PARTIAL`；Core 不會啟動 reviewer loop 來掩蓋缺口。
可直接查看內建 [`partial_proof`](examples/partial_proof/theorem.md) 範例。

## 四個命令與退出碼

| 命令 | 功能 | 是否寫入專案狀態 |
| --- | --- | --- |
| `proofweave init [--root DIR]` | 建立 `workspace/claims/` 與 `artifacts/` | 只建立缺少目錄 |
| `proofweave run INPUT [--root DIR] [--confirm-alignment]` | 解析、認證、render、hash 並記錄一個 claim revision | 是 |
| `proofweave status [CLAIM_ID] [--root DIR]` | 顯示 revisions 與各狀態軸統計 | 否 |
| `proofweave check [--root DIR]` | 核對 schemas、hashes、DAG、artifact integrity 與 Core budgets | 否 |

可使用已安裝的 `proofweave`，或 `python -m proofweave`。退出碼適合自動化：

| 呼叫 | Exit `0` | Exit `1` | Exit `2` |
| --- | --- | --- | --- |
| `run` | `CERTIFIED` | `FAILED` 或 input/runtime error | `PARTIAL`，包括 `HOST_LIMITED` |
| `check` | `PASS` | `FAIL` 或 error | — |
| `init`、`status` | 成功 | Error | — |

Exit `2` 代表證明尚未完成，不是可忽略的成功 warning。

## 判讀三個正交狀態軸

三者互相獨立，不可由其中之一推論另一個：

| 狀態軸 | 值 | 含義 |
| --- | --- | --- |
| `proof_status` | `UNVERIFIED`, `PARTIAL`, `CERTIFIED`, `FAILED` | 本 revision 的 machine-certificate 結果；`UNVERIFIED` 也保留給 v1 保守遷移等紀錄。 |
| `alignment` | `UNCONFIRMED`, `CONFIRMED`, `STALE` | 人類對 statement/formal-target 的 hash-bound 比對是否仍有效。 |
| `lifecycle` | `ACTIVE`, `SUPERSEDED`, `REVOKED` | Revision 治理，不會改寫 certificate truth。 |

常見組合：

- `CERTIFIED + UNCONFIRMED + ACTIVE`：Lean 證明 formal target；尚無 prose
  equivalence attestation。
- `CERTIFIED + CONFIRMED + ACTIVE`：formal target 通過且人類確認受綁定 pair；
  仍不代表 novelty 或 peer review。
- `CERTIFIED + STALE`：先前 certificate record 仍存在，但 alignment 後來因 source
  bytes 改變而過期；必須重讀並重跑。
- `PARTIAL + UNCONFIRMED`：至少一個 obligation unsupported，或 host 缺少 frozen
  Lean environment。
- `FAILED`：至少一個已提交 formal obligation 被 Lean 判定失敗。

Research-pack 的 `OPEN`、`PROPOSED`、`COMPUTATIONAL`、`VERIFIED` 是另一個
evidence layer，不是第四個 Core claim axis。現行 theorem-pack schema 不能綁定所有
獨立審查與 novelty evidence，因此會刻意拒絕每個 `VERIFIED` pack。

## Pipeline 與 artifact layout

```text
UTF-8 TOML + Markdown
        │
        ▼
preserving parser ──► revision/hash identity ──► claim + proof DAG checks
        │
        ▼
pinned-environment fingerprint ──► cache validation ──► allowlisted Lean batch
        │
        ▼
exact coverage/status ──► conservative rendering ──► hashed run + claim state
```

Fast-path run 會寫入：

```text
workspace/claims/
└── square-successor--<revision-prefix>.json

artifacts/square-successor/<run-id>/
├── input.md
├── paper_proof.md
├── concept_map.md
├── coverage.json
├── certificate.json
├── certificate.lean
├── run.json
└── run.sha256
```

Structured long proof 另有 `proof_ir.json`。`paper_proof.md` 與
`concept_map.md` 只是 presentation views，不提供額外 proof authority。
`run.json` 記錄每個 payload artifact hash，`run.sha256` 另行保護該 run record；
cache key 綁定 material claim、certificate、dependency、certifier 與 toolchain
inputs。缺少、移動、不一致或被修改的 artifact 不會被靜默重用。

## Certificate language 與信任邊界

產生的 Lean file 固定以 `import Mathlib` 開始，並停用 automatic implicit
parameters。Certificate block 只接受：

- `ring`、`ring_nf`、`norm_num`、`linarith`、`nlinarith`、`positivity`；
- 受限的 `exact`，只能引用同一 generated batch 中較早已認證的 node。

Core 拒絕任意 command/import、allowlist 外 tactic、`sorry`、`admit`、自訂 axiom、
unsafe/meta execution、`run_tac`、`native_decide`，以及嘗試定義 theorem/declaration
的 certificate syntax。

認證與 cache reuse 綁定：

- statement、assumptions、quantifiers、dependency certificate digests；
- 完整 certificate view 與 certifier version；
- `lean-toolchain`、`lakefile.toml`、`lake-manifest.json`；
- Elan 管理的 Lean/Lake executables 與 Lean library artifacts；
- 精確、乾淨的 dependency Git revisions 與 observed Lean-artifact digests。

Trusted computing base 仍包含 Python implementation、OS、Git executable、Elan
管理的 Lean toolchain、Lean kernel/compiler 與 pinned Mathlib dependency closure。
Hash 能偵測 bytes 改變，不會證明 host 未遭入侵。通過的 Lean result 只證明該環境
下的 generated formal target；它不建立：

- 自然語言 statement 的語義等價（除非另有人類 alignment）；
- informal assumptions 的真實性或 intended domain interpretation；
- novelty、openness、publication priority、peer review 或 expert consensus；
- tactic allowlist 的 completeness 或完全沒有 implementation bug；
- Lean／Mathlib／host 的 global soundness。

完整邊界見 [threat model](docs/design/threat_model.md) 與
[Core v2 architecture record](docs/v2_refactor.md)。

## Evaluation 與 theorem packs

安裝固定的 test-only dependencies，再跑本地 gate：

```console
python -m pip install -r requirements-test.txt
python -m coverage run -m unittest discover -s tests -v
python -m coverage report --fail-under=90 --show-missing
python -m proofweave check
python -m tools.check_workflow_security
```

若要產生真實 fixed-corpus evidence bundle，先按 quick start 完成 Lean environment，
再明確要求 Lean：

```powershell
$env:PROOFWEAVE_REQUIRE_LEAN = "1"
python -m tools.evaluate core --output artifacts/evaluation
```

POSIX shell 使用
`PROOFWEAVE_REQUIRE_LEAN=1 python -m tools.evaluate core --output artifacts/evaluation`。
Bundle 包含 `evaluation.json`、`summary.md`、`environment.txt`、保留的 Lean sources
與 `SHA256SUMS`。

固定 corpus 有 42 個 stable cases：14 positive、14 paired negative、8 escape
attempts、6 fail-closed state/integrity cases，另含 cold/warm replay。通過結果只是
finite-corpus `COMPUTATIONAL` evidence，不是 global soundness proof。Research pack、
attestation、release evidence 與 promotion limits 詳見
[evaluation protocol](docs/evaluation_protocol.md) 與
[claim–evidence matrix](docs/claim_evidence_matrix.md)。

CI 在 Ubuntu/Windows 的 Python 3.11/3.14 執行測試，並在兩平台使用 pinned Lean
做真實認證。Tag workflow 只建立並 attest candidate evidence 與 **draft** release；
publication 仍是獨立的人類動作。

## 與其他專案的關係

三個 repository 可互補，但沒有暗示 runtime dependency 或自動資料交換：

| 專案 | 窄責任範圍 |
| --- | --- |
| **ProofWeave Core** | 認證精確 formal target、暴露 partial obligations、保留 content-addressed proof runs。 |
| [RigorGraph](https://github.com/f0909172434/rigorgraph) | 稽核較廣的 claim–evidence traceability 與人類 workflow records；不是 theorem prover。 |
| [HonestCI](https://github.com/f0909172434/honest-ci) | 檢查預期測試 evidence 是否真的執行；不主張數學真實性。 |

## 開發與遷移

修改 Core 前先讀 [CONTRIBUTING.md](CONTRIBUTING.md)。Enforced design budget 是十個
production modules、三個 schemas、四個 commands、零 Python runtime dependencies、
零 model calls/reviewer loops、受支援 cold run 最多一個 Lean batch、unchanged warm
run 零額外工作。

Core v1 可從 Git history 取回；v2 不提供 compatibility runtime。一次性 formal-record
migration 必須明確呼叫工具：

```console
python -m tools.migrate_v1 OLD_FACT_GRAPH --root .
```

Migration 驗證後保留 formal statement fields 與 dependencies；non-formal evidence
會被列出並略過。所有 v1 人工 `VERIFIED` 都保守映射成
`UNVERIFIED + UNCONFIRMED`，絕不轉成 `CERTIFIED`。

## License 與安全性

ProofWeave Core 使用 [MIT License](LICENSE)。疑似 vulnerability 請依
[SECURITY.md](SECURITY.md) 私下通報，不要建立公開 issue。
