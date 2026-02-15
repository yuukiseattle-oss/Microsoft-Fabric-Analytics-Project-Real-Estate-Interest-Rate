# CLAUDE.md - Microsoft Fabric 不動産価格分析プロジェクト

## プロジェクト概要
金利変動がマンション価格に与える影響を分析するデータエンジニアリングプロジェクト。
Microsoft Fabric上でメダリオンアーキテクチャ（Bronze/Silver/Gold）を実装し、Power BIで可視化する。

## 技術スタック
- **プラットフォーム**: Microsoft Fabric (Lakehouse, Warehouse, Data Pipeline)
- **言語**: PySpark, Python, SQL, DAX
- **データフォーマット**: Delta Lake
- **可視化**: Power BI (Direct Lake接続)
- **Notebook**: Synapse Notebook (.ipynb)

## データソース
1. **国土交通省 不動産取引価格API** - 取引データ (~50万件)
2. **財務省 国債金利CSV** - 10年国債利回り (~1,800件)

## アーキテクチャ
```
国交省API / 財務省CSV
    ↓ (Fabric Notebook - PySpark)
Bronze層 (Lakehouse - Delta Lake) ← 生データ保存
    ↓ (Data Pipeline)
Silver層 (Lakehouse - Delta Lake) ← クレンジング・正規化
    ↓ (Data Pipeline + Notebook)
Gold層 (Warehouse - Star Schema) ← 分析用データマート
    ↓ (Direct Lake)
Power BI Dashboard
```

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
  - `docs/day0_detailed_design.md` - 全体設計
  - `docs/data_model_design.md` - スタースキーマ設計
- 新しい設計判断があった場合は、該当ドキュメントを更新してから実装に進む

## 参照すべき公式ドキュメント
コード記述やベストプラクティスの確認時、以下の公式ドキュメントを WebFetch/WebSearch で参照すること:
- Microsoft Fabric: https://learn.microsoft.com/ja-jp/fabric/
- Fabric Lakehouse: https://learn.microsoft.com/ja-jp/fabric/data-engineering/lakehouse-overview
- Fabric Notebook: https://learn.microsoft.com/ja-jp/fabric/data-engineering/how-to-use-notebook
- Delta Lake: https://docs.delta.io/latest/
- PySpark: https://spark.apache.org/docs/latest/api/python/

## コミュニケーション
- 日本語で応答すること
- 技術的な用語は英語のまま使用してよい（例: Lakehouse, Delta Lake, Star Schema）
- 外部発信（技術ブログ、ポートフォリオ）を意識した品質で設計・コーディングする

## 開発フェーズ
- [x] Day 0: 設計 & 環境構築
- [ ] Day 1: Bronze層実装（API取り込み） ← 現在
- [ ] Day 2-3: Silver層実装
- [ ] Day 4-5: Gold層実装
- [ ] Day 6-7: Power BI実装
