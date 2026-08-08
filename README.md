# ProofWeave Core v2

[English](README.en.md) | [简体中文](README.zh-CN.md) | [日本語](README.ja.md)

ProofWeave Core v2 只做一件事：讀取 AI 產生的數學命題與證明，一次輸出精簡論文證明、proof spine／concept map，以及可用時的 Lean 證書與精確 coverage。

它不是多代理治理平台。Runtime 沒有 agents、workflows、providers、model router、budget manager、paper review 或 reviewer loop，也不會呼叫任何 LLM。

## 快速開始

需要 Python 3.11+、Lean 4.32.1 與 Mathlib 4.32.1：

```powershell
py -3.14 -m pip install -e .
lake update mathlib
lake exe cache get
py -3.14 -m proofweave init
py -3.14 -m proofweave run examples/simple_ring/theorem.md --confirm-alignment
```

日常操作只需要：

```powershell
py -3.14 -m proofweave run theorem.md
```

其他命令只有 `py -3.14 -m proofweave init`、`status [CLAIM_ID]` 與唯讀的 `check`。

## 輸入格式

檔案以 TOML front matter 開始，接著是 `## Statement` 與 `## Proof`。整體 Lean fast path 放在 `## Certificate` 的 `proofweave-lean` block：

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

Expand the square and collect terms.

## Certificate

```proofweave-lean
target = "forall x : Int, (x + 1)^2 = x^2 + 2*x + 1"
tactic = "ring"
```
````

長證明可使用 `### STEP_ID [semantic|bridge|computational|alias]` 與 `Depends:`。沒有支援證書的必要節點會得到 `PARTIAL`，不會啟動代理審查。

## 認證邊界

- `proof_status=CERTIFIED` 只來自 deterministic Lean result 與 100% deductive coverage。
- `alignment`、`proof_status`、`lifecycle` 是正交欄位。`CERTIFIED + UNCONFIRMED` 表示 Lean 證明 formal target，但尚未確認它等價於人類命題。
- 只有 `run --confirm-alignment` 建立 hash-bound 人工確認；內容改變後顯示 `STALE`。
- Lean allowlist：`ring`、`ring_nf`、`norm_num`、`linarith`、`nlinarith`、`positivity`、受限的 `exact`。
- 拒絕 `sorry`、`admit`、自訂 axiom、任意 import／command、unsafe meta、`run_tac`、`native_decide`。
- Lean/Mathlib 不可用時只回報 `PARTIAL/HOST_LIMITED`。
- ProofWeave 不宣稱產生 global simplest proof，也不證明自然語言命題與 Lean target 的語義等價。

v1 資料可用 `py -3.14 -m tools.migrate_v1 OLD_FACT_GRAPH --root .` 一次性搬運；v1 的人工 `VERIFIED` 一律遷移為 `UNVERIFIED`。

## 測試與論文證據

開發測試使用固定的 test-only dependencies，不會增加 runtime dependency：

```powershell
py -3.14 -m pip install -e . -r requirements-test.txt
py -3.14 -m coverage run -m unittest discover -s tests -v
py -3.14 -m coverage report --fail-under=90 --show-missing
py -3.14 -m proofweave check
py -3.14 -m tools.evaluate core --output artifacts/evaluation
py -3.14 -m tools.evaluate pack PACK.toml --output artifacts/evaluation
```

CI 在 Python 3.11/3.14 與 Ubuntu/Windows 上執行快速測試，並在兩個平台使用固定的 Lean/Mathlib 做真實認證。手動 workflow 產生候選證據；`v*.*.*` tag 只建立 draft release，不會自動發布。

有限 corpus 的結果只是 `COMPUTATIONAL`，coverage 也不是 soundness 證明。單一 Lean certificate 只證明它的 formal target；自然語言 alignment 需要 hash-bound 人工確認。文獻搜尋「未找到解答」不等於證明問題仍開放或具有新穎性。Evidence-pack schema v1 對 `VERIFIED` 一律 fail closed，直到未來 schema 能綁定冷啟動重播、新穎性複查與獨立審查證據。詳見 [評估協定](docs/evaluation_protocol.md) 與 [claim–evidence matrix](docs/claim_evidence_matrix.md)。
