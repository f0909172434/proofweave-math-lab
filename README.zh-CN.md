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

## 测试与论文证据

开发测试使用锁定的 test-only dependencies，不会增加 runtime dependency：

```powershell
py -3.14 -m pip install -e . -r requirements-test.txt
py -3.14 -m coverage run -m unittest discover -s tests -v
py -3.14 -m coverage report --fail-under=90 --show-missing
py -3.14 -m proofweave check
py -3.14 -m tools.evaluate core --output artifacts/evaluation
py -3.14 -m tools.evaluate pack PACK.toml --output artifacts/evaluation
```

CI 在 Python 3.11/3.14 与 Ubuntu/Windows 上运行快速测试，并在两个平台使用锁定的 Lean/Mathlib 做真实认证。手动 workflow 产生候选证据；`v*.*.*` tag 只创建 draft release，不会自动发布。

有限 corpus 的结果只是 `COMPUTATIONAL`，coverage 也不是 soundness 证明。单一 Lean certificate 只证明它的 formal target；自然语言 alignment 需要 hash-bound 人工确认。文献搜索“未找到解答”不等于证明问题仍开放或具有新颖性。Evidence-pack schema v1 对 `VERIFIED` 一律 fail closed，直到未来 schema 能绑定冷启动重放、新颖性复查与独立审查证据。详见 [评估协议](docs/evaluation_protocol.md) 与 [claim–evidence matrix](docs/claim_evidence_matrix.md)。
