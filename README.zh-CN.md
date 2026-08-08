# ProofWeave Core v2

[繁體中文](README.md) | [English](README.en.md) | [日本語](README.ja.md)

ProofWeave Core v2 读取 AI 生成的数学命题与证明，一次输出精简论文证明、proof spine／concept map，以及可用时的 Lean 证书与精确 deductive coverage。

它不再是多代理治理平台：runtime 没有 agents、workflows、providers、model router、budget manager、paper review、reviewer loop 或 LLM 调用。

## 快速开始

```powershell
py -3.14 -m pip install -e .
lake update mathlib
lake exe cache get
py -3.14 -m proofweave init
py -3.14 -m proofweave run examples/simple_ring/theorem.md --confirm-alignment
```

日常只需 `py -3.14 -m proofweave run theorem.md`；另外三个命令是 `init`、`status [CLAIM_ID]` 和只读的 `check`。

输入以 TOML front matter 记录 ID、假设、量词与依赖，正文使用 `## Statement`、`## Proof`，可选 `## Certificate`。长证明可使用 `### STEP_ID [semantic|bridge|computational|alias]` 与 `Depends:`。

只有 deterministic Lean result 达到 100% coverage 才能得到 `CERTIFIED`。`alignment` 独立存在：`CERTIFIED + UNCONFIRMED` 只表示 Lean 证明 formal target。`run --confirm-alignment` 记录绑定 hash 的人工确认，内容变化后变成 `STALE`。

Lean 只允许 `ring`、`ring_nf`、`norm_num`、`linarith`、`nlinarith`、`positivity` 和受限 `exact`；拒绝任意 command/import、`sorry`、`admit`、自定义 axiom、unsafe meta、`run_tac`、`native_decide`。缺少 Lean/Mathlib 时只能得到 `PARTIAL/HOST_LIMITED`。

系统不宣称找到 global simplest proof，也不会自动证明自然语言与 Lean target 的语义等价。v1 数据用 `py -3.14 -m tools.migrate_v1 OLD_FACT_GRAPH --root .` 一次性迁移；人工 `VERIFIED` 会映射为 `UNVERIFIED`。
