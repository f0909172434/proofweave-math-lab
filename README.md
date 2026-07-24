# ProofWeave（證明織網）

[繁體中文](README.md) | [简体中文](README.zh-CN.md) | [English](README.en.md) | [日本語](README.ja.md)

**把命題、證據與獨立驗證織成一套可稽核的數學研究流程。**

[GitHub 儲存庫](https://github.com/f0909172434/proofweave-math-lab)

ProofWeave 是一個在本機執行、與模型供應商無關的數學研究工作區，適用於研究、論文寫作與對抗式審查。它以持久化檔案與確定性檢查為核心，而不是依賴聊天紀錄。系統明確區分證明、文獻結果、數值證據、猜想與尚未解決的缺口，並記錄每一次模型路由決策，但不把多個模型意見一致當成真理。

## 已實作功能

- 具備循環防護與「僅允許 VERIFIED 形式依賴」的事實有向無環圖；
- 冷啟動、獨立驗證者限定的狀態晉升；
- 傳遞式撤銷連鎖與影響範圍中繼資料；
- 經驗證的來源登錄表與修訂問題帳冊；
- 實驗、參考文獻、LaTeX 命題對照與機密資訊檢查；
- 被動偵測主機、供應商與模型，並分類為 MODE A–E；
- 確定性的任務、推理、模型、備援與預算路由；
- 預設拒絕即時／付費呼叫與虛假排名的基準測試框架；
- 28 個標準角色、18 套工作流程、14 份提示詞、12 個結構綱要，以及指向標準檔案的 Codex／Claude 原生轉接器；
- 隔離的奇數和證明流程與六個乾式路由示範；
- 僅依賴 Python 標準函式庫的命令列工具與自動測試。

`VERIFIED` 只是專案內的工作流程狀態，不代表人類同儕審查或形式上的絕對確定。Lean 支援是選用功能；只有在固定版本的建置中不存在被禁止的 `sorry`、`admit` 或非預期公理時，才能標記為機器檢查，且仍須由人類確認形式陳述與原始定理一致。

## 快速開始

在儲存庫根目錄使用 Python 3.11 或更新版本：

```powershell
python -m mathlab init
python -m mathlab status
python -m unittest discover -s tests -v
python -m mathlab release-check
```

在目前的 Codex Windows 桌面環境中，已驗證的 Python 隨 Codex 提供，而 Windows 的裸 `python` 別名未必可靠。等效指令如下：

```powershell
$py = 'C:\Users\user\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
& $py -m mathlab status
& $py -m unittest discover -s tests -v
& $py -m mathlab release-check
```

實驗檢查會把重現指令開頭的 `python`、`python3` 或 `py` 解析為正在執行 ProofWeave 的直譯器。

要開始第一個真實研究專案，請編輯 `state/problem.md`、`state/assumptions.md`、`state/notation.md` 與 `state/research_plan.md`，然後把以下提示交給代理：

> 閱讀 AGENTS.md 與 workflows/00_project_intake.md。將 state/problem.md 中的研究問題形式化，但先不要嘗試證明。明確寫出定義域、量詞、假設、記號、完成定義與初始風險清單。分開標示定理目標、猜想、數值問題與文獻問題；只更新研究受理階段的狀態檔案，並把所有歧義記為 OPEN GAP 或待人類決策事項。

## 研究流程

1. 問題受理與形式化。
2. 可重現的來源搜尋，並開啟原文核對精確支持範圍。
3. 提出三至五條不同策略，涵蓋有界證明、障礙分析與玩具模型路線。
4. 建立局部 `PROPOSED` 命題並嘗試尋找反例。
5. 透過命令列閘門進行獨立定理驗證。
6. 視需要進行可重現實驗，且永遠標示為證據而非證明。
7. 依凍結的 `VERIFIED` 圖與完整命題對照表規劃及撰寫論文。
8. 完整數學／審稿人審查、修訂與發布檢查。
9. 交接工作階段，保存狀態、缺口、失敗路線與決策。

詳見 `docs/operator_guide.md`、`docs/workflow_guide.md` 與 `docs/design/architecture.md`。

## 命令列工具

研究狀態：

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

能力與路由：

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

在原生模式中，`route run` 只會記錄乾式交接，不會暗中呼叫外部供應商。除非操作者明確修改 `config/runtime_policy.json`，並接受額度、隱私與費用後果，否則 CLI、API 與閘道執行都保持停用。

## 示範

```powershell
python -m scripts.run_toy_workflow
python -m scripts.run_routing_demo
python -m scripts.compile_paper
```

玩具流程會接受正確的歸納證明、拒絕近似造成的缺口、把已接受事實對應至 LaTeX，並在系統具備 `pdflatex` 時編譯。每次成功發布都會寫入 `state/release_report.json` 與內容定址的 `state/release_manifest.json`，產生精確的檔案雜湊快照。

## 原生代理與技能

- `agents/` 是標準政策來源。
- `.codex/agents/` 與 `.claude/agents/` 是自動產生的輕量轉接器。
- `.agents/skills/` 與 `.claude/skills/` 提供工作流程入口。
- 角色或工作流程變更後，執行 `python -m scripts.generate_native_adapters` 重新產生轉接器。
- `.claude/settings.example.json` 是選用掛鉤範例；啟用前請先查閱最新 Claude Code 文件。

## 安全與費用預設值

專案不會建立真正的 `.env`。狀態與日誌禁止包含密鑰、Cookie 或權杖。除非得到明確授權，付費探測、供應商 API、CLI 子行程代理、發布、推送、上傳與傳訊都保持停用。平行代理與升級循環均有界限。預算失敗會回傳 `BLOCKED_BY_BUDGET` 或 `NEEDS_HUMAN_DECISION`，絕不降低驗證標準。

來源與授權決策記錄於 `docs/design/source_basis.md` 與 `state/source_registry.jsonl`。專案曾研究 Danus，但沒有複製或安裝其內容。
