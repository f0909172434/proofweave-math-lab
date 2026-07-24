# ProofWeave（証明の織物）

[繁體中文](README.md) | [简体中文](README.zh-CN.md) | [English](README.en.md) | [日本語](README.ja.md)

**主張・証拠・独立検証を織り合わせた、監査可能な数学研究基盤。**

[GitHub リポジトリ](https://github.com/f0909172434/proofweave-math-lab)

ProofWeave は、数学研究・論文執筆・敵対的レビューのための、ローカルで動作するモデル非依存ワークスペースです。チャット履歴ではなく、永続ファイルと決定論的な検査を中核に据えています。証明、文献上の結果、数値的証拠、予想、未解決のギャップを明確に区別し、モデルの合意を真実とみなすことなく、すべてのモデルルーティング判断を記録します。

## 実装済みの機能

- 循環を防止し、形式的依存を `VERIFIED` に限定する事実 DAG；
- コールドスタートと独立検証者だけによる昇格；
- 推移的な取消し連鎖と影響メタデータ；
- 検証済みの情報源レジストリと改訂課題台帳；
- 実験、参考文献、LaTeX 主張マップ、機密情報の検査；
- ホスト／プロバイダー／モデルの受動検出と MODE A–E 分類；
- タスク、推論、モデル、フォールバック、予算の決定論的ルーティング；
- ライブ／有料呼び出しと偽のランキングを既定で拒否するベンチマーク基盤；
- 28 の標準ロール、18 のワークフロー、14 のプロンプト、12 のスキーマ、および標準ファイルを参照する Codex／Claude ネイティブアダプター；
- 独立した奇数和の証明ワークフローと 6 件のドライルーティング実演；
- Python 標準ライブラリだけを使う CLI と自動テスト。

`VERIFIED` はプロジェクト内のワークフロー状態であり、人間による査読や形式的な絶対確実性を意味しません。Lean 対応は任意です。固定されたビルドで、禁止された `sorry`、`admit`、予期しない公理が存在しない場合にのみ機械検証済みと扱い、それでも形式化された文が意図した定理と一致するかを人間が確認します。

## クイックスタート

リポジトリのルートで Python 3.11 以降を使用します：

```powershell
python -m mathlab init
python -m mathlab status
python -m unittest discover -s tests -v
python -m mathlab release-check
```

現在の Codex Windows デスクトップ環境では、検証済み Python は Codex に同梱されており、Windows の裸の `python` エイリアスは信頼できない場合があります。同等の検証済みコマンドは次のとおりです：

```powershell
$py = 'C:\Users\user\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
& $py -m mathlab status
& $py -m unittest discover -s tests -v
& $py -m mathlab release-check
```

実験ゲートは、記録された再現コマンドの先頭にある `python`、`python3`、`py` を、ProofWeave を実行中のインタープリターへ解決します。

最初の実研究プロジェクトを開始するには、`state/problem.md`、`state/assumptions.md`、`state/notation.md`、`state/research_plan.md` を編集し、次の指示をエージェントへ渡します：

> AGENTS.md と workflows/00_project_intake.md を読み、state/problem.md に記載された研究課題を形式化してください。まだ証明は試みないでください。定義域、量化子、仮定、記法、完了条件、初期リスク一覧を明示してください。定理目標、予想、数値的課題、文献上の課題を分離し、受付段階の状態ファイルだけを更新して、すべての曖昧さを OPEN GAP または人間による判断事項として報告してください。

## 研究フロー

1. 課題の受付と形式化。
2. 再現可能な情報源検索と、原文による厳密な裏付け確認。
3. 有界証明、障害分析、玩具モデルを含む 3～5 個の異なる戦略。
4. 局所的な `PROPOSED` 主張と反例探索。
5. CLI ゲートを通した独立定理検証。
6. 必要に応じた再現可能な実験（常に証拠として表示）。
7. 凍結した `VERIFIED` グラフと完全な主張マップに基づく論文設計・執筆。
8. 完全な数学的／査読者レビュー、改訂、リリース検査。
9. 状態、ギャップ、行き止まり、判断を保存するセッション引き継ぎ。

詳細は `docs/operator_guide.md`、`docs/workflow_guide.md`、`docs/design/architecture.md` を参照してください。

## CLI

研究状態：

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

機能とルーティング：

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

ネイティブモードの `route run` は記録されたドライ引き継ぎであり、外部プロバイダーを密かに呼び出しません。運用者が `config/runtime_policy.json` を明示的に変更し、クォータ・プライバシー・費用への影響を受け入れるまで、CLI／API／ゲートウェイ実行は無効のままです。

## デモ

```powershell
python -m scripts.run_toy_workflow
python -m scripts.run_routing_demo
python -m scripts.compile_paper
```

玩具ワークフローは、正しい帰納法の証明を受理し、近似によるギャップを拒否し、受理済みの事実を LaTeX に対応付け、`pdflatex` があればコンパイルします。リリース成功時には `state/release_report.json` とコンテンツアドレス方式の `state/release_manifest.json` を書き出し、正確なファイルハッシュのスナップショットを生成します。

## ネイティブエージェントとスキル

- `agents/` は標準ポリシーの情報源です。
- `.codex/agents/` と `.claude/agents/` は自動生成される薄いアダプターです。
- `.agents/skills/` と `.claude/skills/` はワークフローの入口を提供します。
- ロールまたはワークフローを変更した後は、`python -m scripts.generate_native_adapters` で再生成します。
- `.claude/settings.example.json` は任意のフック例です。有効化前に最新の Claude Code 文書を確認してください。

## 安全性と費用の既定値

実際の `.env` は作成しません。状態とログに秘密鍵、Cookie、トークンを含めることは禁止されています。明示的な許可がない限り、有料プローブ、プロバイダー API、CLI サブプロセスエージェント、公開、push、アップロード、メッセージ送信は無効です。並列エージェントとエスカレーションループには上限があります。予算不足時は `BLOCKED_BY_BUDGET` または `NEEDS_HUMAN_DECISION` を返し、検証基準を弱めることはありません。

情報源とライセンスの判断は `docs/design/source_basis.md` と `state/source_registry.jsonl` に記録されています。Danus は調査しましたが、コピーもインストールもしていません。
