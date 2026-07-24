# ProofWeave（证明织网）

[繁體中文](README.md) | [简体中文](README.zh-CN.md) | [English](README.en.md) | [日本語](README.ja.md)

**把命题、证据与独立验证织成一套可审计的数学研究流程。**

[GitHub 仓库](https://github.com/f0909172434/proofweave-math-lab)

ProofWeave 是一个在本地运行、与模型供应商无关的数学研究工作区，适用于研究、论文写作与对抗式审查。它以持久化文件和确定性检查为核心，而不是依赖聊天记录。系统明确区分证明、文献结果、数值证据、猜想与尚未解决的缺口，并记录每一次模型路由决策，但不把多个模型意见一致当作真理。

## 已实现功能

- 具备循环防护和“仅允许 VERIFIED 形式依赖”的事实有向无环图；
- 冷启动、仅限独立验证者的状态晋升；
- 传递式撤销级联和影响范围元数据；
- 经过验证的来源登记表与修订问题台账；
- 实验、参考文献、LaTeX 命题映射与敏感信息检查；
- 被动检测主机、供应商与模型，并分类为 MODE A–E；
- 确定性的任务、推理、模型、后备与预算路由；
- 默认拒绝实时／付费调用与虚假排名的基准测试框架；
- 28 个标准角色、18 套工作流、14 份提示词、12 个结构纲要，以及指向标准文件的 Codex／Claude 原生适配器；
- 隔离的奇数和证明流程与六个干式路由演示；
- 仅依赖 Python 标准库的命令行工具与自动测试。

`VERIFIED` 只是项目内的工作流状态，不代表人工同行评审或形式上的绝对确定。Lean 支持是可选功能；只有在固定版本的构建中不存在被禁止的 `sorry`、`admit` 或非预期公理时，才能标记为机器检查，且仍须由人工确认形式陈述与原始定理一致。

## 快速开始

在仓库根目录使用 Python 3.11 或更高版本：

```powershell
python -m mathlab init
python -m mathlab status
python -m unittest discover -s tests -v
python -m mathlab release-check
```

在当前 Codex Windows 桌面环境中，已经验证的 Python 随 Codex 提供，而 Windows 的裸 `python` 别名未必可靠。等效命令如下：

```powershell
$py = 'C:\Users\user\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
& $py -m mathlab status
& $py -m unittest discover -s tests -v
& $py -m mathlab release-check
```

实验检查会把复现命令开头的 `python`、`python3` 或 `py` 解析为正在执行 ProofWeave 的解释器。

要开始第一个真实研究项目，请编辑 `state/problem.md`、`state/assumptions.md`、`state/notation.md` 与 `state/research_plan.md`，然后把以下提示交给代理：

> 阅读 AGENTS.md 和 workflows/00_project_intake.md。将 state/problem.md 中的研究问题形式化，但先不要尝试证明。明确写出定义域、量词、假设、记号、完成定义和初始风险清单。分别标明定理目标、猜想、数值问题与文献问题；只更新研究受理阶段的状态文件，并把所有歧义记录为 OPEN GAP 或待人工决策事项。

## 研究流程

1. 问题受理与形式化。
2. 可复现的来源搜索，并打开原文核对精确支持范围。
3. 提出三至五条不同策略，涵盖有界证明、障碍分析与玩具模型路线。
4. 建立局部 `PROPOSED` 命题并尝试寻找反例。
5. 通过命令行关卡进行独立定理验证。
6. 按需进行可复现实验，并始终标记为证据而非证明。
7. 根据冻结的 `VERIFIED` 图与完整命题映射表规划和撰写论文。
8. 完整数学／审稿人审查、修订与发布检查。
9. 交接工作阶段，保存状态、缺口、失败路线与决策。

详见 `docs/operator_guide.md`、`docs/workflow_guide.md` 与 `docs/design/architecture.md`。

## 命令行工具

研究状态：

```powershell
python -m mathlab add-source --file source.json
python -m mathlab add-claim --file claim.json
python -m mathlab verify FACT_ID --outcome ACCEPT --verifier NAME --report report.json
python -m mathlab revoke FACT_ID --reason "reason" --actor NAME
python -m mathlab graph-check
python -m mathlab experiment-check
python -m mathlab paper-check
python -m mathlab review --mode blind-referee
python -m mathlab release-check
```

能力与路由：

```powershell
python -m mathlab models detect
python -m mathlab models list
python -m mathlab models show MODEL_ID
python -m mathlab models doctor
python -m mathlab models refresh
python -m mathlab models benchmark
python -m mathlab route classify TASK_FILE
python -m mathlab route recommend TASK_FILE
python -m mathlab route explain ROUTING_ID
python -m mathlab route run TASK_FILE
python -m mathlab route history
python -m mathlab budget status
python -m mathlab budget estimate TASK_FILE
python -m mathlab providers status
```

在原生模式中，`route run` 只会记录干式交接，不会暗中调用外部供应商。除非操作者明确修改 `config/runtime_policy.json`，并接受配额、隐私与费用后果，否则 CLI、API 与网关执行都保持禁用。

## 演示

```powershell
python -m scripts.run_toy_workflow
python -m scripts.run_routing_demo
python -m scripts.compile_paper
```

玩具流程会接受正确的归纳证明、拒绝近似造成的缺口、把已接受事实映射到 LaTeX，并在系统具备 `pdflatex` 时编译。每次成功发布都会写入 `state/release_report.json` 和内容寻址的 `state/release_manifest.json`，生成精确的文件哈希快照。

## 原生代理与技能

- `agents/` 是标准策略来源。
- `.codex/agents/` 和 `.claude/agents/` 是自动生成的轻量适配器。
- `.agents/skills/` 和 `.claude/skills/` 提供工作流入口。
- 角色或工作流变更后，执行 `python -m scripts.generate_native_adapters` 重新生成适配器。
- `.claude/settings.example.json` 是可选挂钩示例；启用前请先查阅最新 Claude Code 文档。

## 安全与费用默认值

项目不会创建真实的 `.env`。状态与日志禁止包含密钥、Cookie 或令牌。除非获得明确授权，付费探测、供应商 API、CLI 子进程代理、发布、推送、上传与传讯都保持禁用。并行代理和升级循环均有边界。预算失败会返回 `BLOCKED_BY_BUDGET` 或 `NEEDS_HUMAN_DECISION`，绝不降低验证标准。

来源与许可决策记录在 `docs/design/source_basis.md` 和 `state/source_registry.jsonl` 中。项目曾研究 Danus，但没有复制或安装其内容。
