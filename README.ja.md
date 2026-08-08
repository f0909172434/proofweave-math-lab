# ProofWeave Core v2

[繁體中文](README.md) | [English](README.en.md) | [简体中文](README.zh-CN.md)

ProofWeave Core v2 は、AI が生成した数学命題と証明を読み、簡潔な論文用証明、proof spine／concept map、そして対応可能な場合は Lean 証明書と正確な deductive coverage を一度に出力します。

これはマルチエージェント統治基盤ではありません。runtime には agents、workflows、providers、model router、budget manager、paper review、reviewer loop、LLM 呼び出しがありません。

## クイックスタート

```powershell
py -3.14 -m pip install -e .
lake update mathlib
lake exe cache get
py -3.14 -m proofweave init
py -3.14 -m proofweave run examples/simple_ring/theorem.md --confirm-alignment
```

通常は `py -3.14 -m proofweave run theorem.md` だけを使います。他のコマンドは `init`、`status [CLAIM_ID]`、読み取り専用の `check` です。

入力は ID・仮定・量化・依存関係を TOML front matter に、本文を `## Statement` と `## Proof` に記述します。任意の `## Certificate` に固定形式の Lean 指定を置けます。長い証明では `### STEP_ID [semantic|bridge|computational|alias]` と `Depends:` を使います。

`CERTIFIED` は deterministic Lean result が 100% coverage に達した場合だけです。alignment は独立しており、`CERTIFIED + UNCONFIRMED` は Lean が formal target を証明しただけで、自然言語命題との同値性を意味しません。`run --confirm-alignment` は hash-bound な人間の確認を記録し、変更後は `STALE` になります。

Lean の allowlist は `ring`、`ring_nf`、`norm_num`、`linarith`、`nlinarith`、`positivity`、制限付き `exact` です。任意 command/import、`sorry`、`admit`、独自 axiom、unsafe meta、`run_tac`、`native_decide` は拒否します。Lean/Mathlib がなければ `PARTIAL/HOST_LIMITED` です。

global simplest proof を主張せず、自然言語と Lean target の意味的一致も自動証明しません。v1 は `py -3.14 -m tools.migrate_v1 OLD_FACT_GRAPH --root .` で一度だけ移行し、人手の `VERIFIED` は `UNVERIFIED` になります。
