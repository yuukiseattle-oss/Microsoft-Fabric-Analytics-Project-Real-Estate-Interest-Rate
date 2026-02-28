# CLAUDE.md - Microsoft Fabric 不動産価格分析プロジェクト

## プロジェクト概要
金利変動がマンション価格に与える影響を分析するデータエンジニアリングプロジェクト。
Microsoft Fabric 上でメダリオンアーキテクチャ（Bronze/Silver/Gold）を実装し、Power BI で可視化する。
詳細設計は `docs/day0_detailed_design.md`、進捗は `tasks/todo.md` を参照。

## コーディング規約

### PySpark / Notebook
- Fabric Notebook は Spark セッションが事前に初期化されている。`spark` 変数は自動で利用可能
- `SparkSession.builder` での明示的な初期化は不要
- Lakehouse への読み書きは `spark.read.format("delta")` / `df.write.format("delta")` を使用
- Fabric の Lakehouse パスは `Tables/テーブル名` または `abfss://` 形式
- notebookutils は Fabric 固有のユーティリティ（`notebookutils.lakehouse`, `notebookutils.credentials` 等）
- パーティションキーは year, quarter (不動産) / year, month (金利)

### SQL (Warehouse)
- Fabric Warehouse は T-SQL ベース（一部制約あり）
- IDENTITY 列、外部キー制約をサポート
- CLUSTERED COLUMNSTORE INDEX を Fact テーブルに適用

### Delta Lake
- MERGE を使った Upsert パターンを推奨（増分ロード時）
- OPTIMIZE / VACUUM で定期メンテナンス
- Z-ORDER BY で頻繁にフィルタするカラム（year_month, region_key）を最適化

## ドキュメント管理
- 設計ドキュメントは `docs/` 配下に Markdown で管理
- ユーザーとのやり取りで決定した設計判断は `docs/` 内の該当ドキュメントに反映すること
- 主要ドキュメント:
  - `docs/day0_detailed_design.md` - 全体設計（技術スタック・アーキテクチャ詳細）
  - `docs/data_model_design.md` - スタースキーマ設計
- 新しい設計判断があった場合は、該当ドキュメントを更新してから実装に進む

## コミュニケーション
- 日本語で応答すること
- 技術的な用語は英語のまま使用してよい（例: Lakehouse, Delta Lake, Star Schema）
- 外部発信（技術ブログ、ポートフォリオ）を意識した品質で設計・コーディングする
- 公式ドキュメントは Microsoft Learn MCP / WebSearch で都度参照すること

## Workflow Orchestration

### 1. Plan Node Default
- Enter plan mode for ANY non-trivial task (3+ steps or architectural decisions)
- If something goes sideways, STOP and re-plan immediately – don't keep pushing
- Use plan mode for verification steps, not just building
- Write detailed specs upfront to reduce ambiguity

### 2. Subagent Strategy
- Use subagents liberally to keep main context window clean
- Offload research, exploration, and parallel analysis to subagents
- For complex problems, throw more compute at it via subagents
- One task per subagent for focused execution

### 3. Self-Improvement Loop
- After ANY correction from the user: update `tasks/lessons.md` with the pattern
- Write rules for yourself that prevent the same mistake
- Ruthlessly iterate on these lessons until mistake rate drops
- Review lessons at session start for relevant project

### 4. Verification Before Done
- Never mark a task complete without proving it works
- Diff behavior between main and your changes when relevant
- Ask yourself: "Would a staff engineer approve this?"
- Run tests, check logs, demonstrate correctness

### 5. Demand Elegance (Balanced)
- For non-trivial changes: pause and ask "is there a more elegant way?"
- If a fix feels hacky: "Knowing everything I know now, implement the elegant solution"
- Skip this for simple, obvious fixes – don't over-engineer
- Challenge your own work before presenting it

### 6. Autonomous Bug Fixing
- When given a bug report: just fix it. Don't ask for hand-holding
- Point at logs, errors, failing tests – then resolve them
- Zero context switching required from the user
- Go fix failing CI tests without being told how

## Task Management

1. **Plan First**: Write plan to `tasks/todo.md` with checkable items
2. **Verify Plan**: Check in before starting implementation
3. **Track Progress**: Mark items complete as you go
4. **Explain Changes**: High-level summary at each step
5. **Document Results**: Add review section to `tasks/todo.md`
6. **Capture Lessons**: Update `tasks/lessons.md` after corrections

## Core Principles

- **Simplicity First**: Make every change as simple as possible. Impact minimal code.
- **No Laziness**: Find root causes. No temporary fixes. Senior developer standards.
- **Minimal Impact**: Changes should only touch what's necessary. Avoid introducing bugs.
