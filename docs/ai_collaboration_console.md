# 低 Token 與 AI Collaboration Console 操作規範

本工作區的唯一真理層是 `state/fact_graph.jsonl`。AI Collaboration
Console 只負責調度、用量紀錄與交叉審查；模型輸出、模型共識或 Console
reviewer 的 `ACCEPT` 都不能直接產生 `VERIFIED`。正式晉升仍須由獨立
`theorem_verifier` 依完整依賴閉包執行 ProofWeave promotion gate。

## Context packet

以 Fact ID 建立最小審查包：

```powershell
py -3.14 -m mathlab context build FACT_ID `
  --role theorem_verifier --profile max `
  --artifact research/formal/FACT_ID_proof.md
```

輸出固定寫入 `build/context-cache/<cache-key>.json`。`cache_key` 包含 task、
role、policy、fact graph、依賴、來源及指定工件的 digest；任一輸入改變即失效。
用下列命令驗證完整性或查看排除原因：

```powershell
py -3.14 -m mathlab context check build/context-cache/PACKET.json
py -3.14 -m mathlab context explain build/context-cache/PACKET.json
```

軟預算為 fast 8k、standard 16k、deep 24k、max 32k。超額或依賴閉包不完整時
回傳 `NEEDS_CONTEXT_REVIEW`，不會截斷證明或依賴。完整聊天、system prompt、
`state/STATUS.md`、秘密欄位與 raw chain-of-thought 一律排除。超過 32k 的摘要、
文獻或科學寫作資料只能按自然段落或章節切成每塊至多 12k、10% 重疊並附 digest；
數學證明與依賴鏈不得盲切，應縮小命題或進行人工 long-context handoff。

## Console 邊界工件

`mathlab collab prepare` 只建立 request JSON，不會自行提交外部工作：

```powershell
py -3.14 -m mathlab collab prepare FACT_ID `
  --role review --risk high --profile max `
  --artifact research/formal/FACT_ID_proof.md
```

request 必須記錄 context packet digest、risk、sensitivity、capability tags、
requested effort、最大 input/output/rounds、費用估計、費用上限及不同模型家族的
review 要求。v1 不接受 `workspace_id`，Console workspace 操作保持停用；不得從路徑
猜測 ID。

Console 回傳結果需整理成 `collab_job_result` 後才能匯入：

```powershell
py -3.14 -m mathlab collab ingest RESULT.json
py -3.14 -m mathlab collab audit
py -3.14 -m mathlab collab history
```

帳本 `state/collab_jobs.jsonl` 為 append-only。`completed` 只能留下
`PROPOSED` 或 `COMPUTATIONAL`；`needs_review` 正規化為 `OPEN`；
`awaiting_manual` 與 `needs_attention` 不產生研究結論；`COLLAB_UNAVAILABLE`
不得偽造 job ID。402、超出 USD 0.70/CNY 5、重試、秘密、raw chain-of-thought、
同家族 reviewer、unknown-family reviewer 或 `copilot-auto` 獨立 reviewer 都會被拒絕。

## 路由與 fallback

- 決定性雜湊、schema、編譯和資料比較使用本機程式。
- 低風險格式／摘要用 fast 單一 worker；一般研究用 standard/deep primary。
- 正式證明、漸近或出版審查用 max，並要求不同模型家族 reviewer。
- `restricted` 只能送至合格本機模型；沒有合格 lane 時回傳 `needs_attention`。
- Console 無法使用時記錄 `COLLAB_UNAVAILABLE` 並轉回原生 ProofWeave；若已提交後
  才收到 402 或 `needs_attention`，不得靜默換供應商。

模型名稱、家族、原生 effort 與 readiness 必須由目前主機及每次 Console 回傳確認，
不得把某次 inventory 快照寫成永久可用。抽象 `max` 只有在主機明確支援時才能映射；
外部模型也不能只憑名稱推斷 reviewer 獨立性。

## MCP 設定與驗證

全域 Codex 設定應把 Console 的 loopback MCP URL 設為非必要服務，並只允許
`submit_job`、`delegate_task`、`job_status`、`complete_job`、`workspace_read`、
`workspace_apply_patch`、`workspace_run_check` 七項工具。workspace 寫入與執行仍需
prompt 核准，而本專案 v1 不使用它們。

```powershell
codex mcp get ai-collab-console --json
```

若服務未註冊或停止，研究工作仍可在 ProofWeave 本機 truth layer 繼續。
