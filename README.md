# 不動産価格分析プロジェクト - Microsoft Fabric

## 📊 プロジェクト概要

金利変動がマンション価格に与える影響を分析するデータエンジニアリング・分析プロジェクト。
Microsoft Fabric上でメダリオンアーキテクチャ（Bronze/Silver/Gold）を実装し、Power BIで可視化します。

### 主要分析課題（Research Question）

**RQ1: 金利変動がマンション価格に与える影響度は？**
- 測定指標：金利1%上昇時の価格変動率
- 対象期間：2020年Q1〜2024年Q4
- 対象地域：東京都、大阪府、愛知県（主要3都府県）

## 🏗 アーキテクチャ

```
国交省API/日銀API
    ↓ (Fabric Notebook)
Bronze層 (Lakehouse - Delta Lake)
    ↓ (Data Pipeline)
Silver層 (Lakehouse - Delta Lake)
    ↓ (Data Pipeline + Notebook)
Gold層 (Warehouse - Star Schema)
    ↓ (Direct Lake)
Power BI Dashboard
```

### データソース
1. **国土交通省 不動産取引価格API** - 取引データ（~50万件）
2. **日本銀行 10年国債利回り** - 金利データ（~1,800件）

### 技術スタック
- **データレイヤー**: Microsoft Fabric (Lakehouse, Warehouse)
- **データ処理**: Spark (PySpark), SQL
- **オーケストレーション**: Fabric Data Pipeline
- **可視化**: Power BI (Direct Lake接続)
- **バージョン管理**: Git

## 📁 プロジェクト構造

```
fabric-realestate-analytics/
├── docs/                          # 設計ドキュメント
│   ├── 01_problem_definition.md
│   ├── 02_analysis_plan.md
│   ├── 03_technical_architecture.md
│   ├── 04_data_dictionary.md
│   ├── 05_transformation_logic.md
│   ├── 06_data_collection_plan.md
│   ├── 07_analysis_storyboard.md
│   ├── data_model_design.md      # スタースキーマ設計
│   └── day0_detailed_design.md   # Day 0詳細設計
├── notebooks/                     # Fabric Notebooks
├── pipelines/                     # Data Pipeline定義
├── warehouse/                     # SQL Scripts
└── powerbi/                       # Power BIレポート定義
```

## 🎯 データモデル（Star Schema）

### Fact Table
- **fact_transactions** - 取引トランザクション（~48万件）

### Dimension Tables
- **dim_date** - 日付マスタ（~1,800件）
- **dim_region** - 地域マスタ（~1,900件）
- **dim_property** - 物件種別マスタ（~15件）
- **dim_interest** - 金利マスタ（~60件）

詳細は [data_model_design.md](docs/data_model_design.md) を参照。

## 🚀 Getting Started

### 前提条件
- Microsoft Fabric ワークスペース（F64以上推奨）
- Lakehouse × 3（bronze, silver, gold）
- Warehouse × 1
- Power BI Premium Per User (PPU) またはPremium Capacity

### セットアップ手順

1. **Fabricワークスペース作成**
   ```
   Fabric Portal > Workspaces > New Workspace
   ```

2. **Lakehouse作成**
   ```
   bronze_lakehouse
   silver_lakehouse
   gold_lakehouse
   ```

3. **Warehouse作成**
   ```
   realestate_warehouse
   ```

4. **Git連携設定**（任意）
   ```
   Workspace Settings > Git integration
   ```

詳細は [day0_detailed_design.md](docs/day0_detailed_design.md) のDay 0セクションを参照。

## 📚 ドキュメント

| ドキュメント | 説明 |
|-------------|------|
| [Day 0詳細設計](docs/day0_detailed_design.md) | プロジェクト設計の全体像 |
| [データモデル設計](docs/data_model_design.md) | スタースキーマ・ERダイアグラム |
| [課題定義](docs/01_problem_definition.md) | Research Questions（準備中） |
| [分析計画](docs/02_analysis_plan.md) | 分析手法マッピング（準備中） |
| [技術アーキテクチャ](docs/03_technical_architecture.md) | 技術選定根拠（準備中） |

## 🔄 開発フェーズ

- [x] **Day 0**: 設計 & 環境構築
- [ ] **Day 1**: Bronze層実装（API取り込み）
- [ ] **Day 2-3**: Silver層実装（データクレンジング）
- [ ] **Day 4-5**: Gold層実装（スタースキーマ構築）
- [ ] **Day 6-7**: Power BI実装（ダッシュボード作成）

## 📊 期待される成果物

1. **データパイプライン**
   - 自動化されたデータ取り込み（API → Bronze）
   - データ品質保証（Bronze → Silver）
   - 分析用データマート（Silver → Gold）

2. **Power BIダッシュボード**
   - Executive Summary
   - 金利影響分析
   - 地域別Deep Dive
   - 価格帯別分析
   - 属性分析

3. **ドキュメント**
   - 技術設計書
   - データディクショナリ
   - 運用手順書

## 🤝 コントリビューション

このプロジェクトは学習・ポートフォリオ目的で作成されています。
フィードバックや改善提案は Issue または Pull Request でお願いします。

## 📄 ライセンス

このプロジェクトはMITライセンスの下で公開されています。

## 👤 作成者

学習プロジェクトとして作成。

---

**Status**: 🔨 設計フェーズ完了（Day 0） | 実装準備中
