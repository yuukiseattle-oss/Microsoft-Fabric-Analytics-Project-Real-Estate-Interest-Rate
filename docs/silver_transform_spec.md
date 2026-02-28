# Silver層 変換仕様書 - Dataflow Gen2 実装ガイド

## 概要

| 項目 | 内容 |
|------|------|
| 実装手段 | Dataflow Gen2（Microsoft Fabric） |
| ソース | Bronze Lakehouse（Delta Table） |
| シンク | Silver Lakehouse（Delta Table） |
| 対象テーブル | 2つ（不動産データ・金利データ） |
| スケジューリング | Data Pipeline `pl_bronze_to_silver` 経由 |

---

## Bronze層 スキーマ（確定）

### bronze_realestate_transactions

- **レコード数**: 231,810件（東京都、2018Q1〜2024Q4）
- **ほぼ全カラムが String型**（APIレスポンスをそのままDelta保存）
- **例外**: `year`（Int）・`quarter`（Int）・`ingested_at`（Timestamp）はNotebook取り込み時に付与
- **重要なカラム値サンプル**:

| カラム | サンプル値 | Silver層での変換 |
|--------|-----------|----------------|
| `transaction_period` | `"2024年第4四半期"` | → `DATE` 型 |
| `trade_price` | `"40000000"` | → `BIGINT`（円） |
| `area` | `"25"` | → `DOUBLE`（㎡） |
| `building_year` | `"2018年"` | → `INT`（西暦） |
| `property_type` | `"中古マンション等"` | フィルタキー |
| `municipality_code` | `"13101"` | そのまま |
| `DistrictCode` | `"131010030"` | `district_code` にリネーム |

- **物件種別内訳**:
  - 中古マンション等: 118,941件 ← Silver層でこれのみ抽出
  - 宅地(土地と建物): 77,415件
  - 宅地(土地): 35,093件
  - その他: 361件

### bronze_interest_rate

| カラム | 型 | サンプル値 |
|--------|-----|-----------|
| `date` | Date | `2020-01-06` |
| `yield_10y` | Double | `0.005` |
| `ingested_at` | Timestamp | `2026-02-22T...` |
| `year` | Int | `2020` |
| `month` | Int | `1` |

---

## Silver層 ターゲットスキーマ

### silver_realestate_cleaned

| カラム | 型 | 変換内容 | 備考 |
|--------|-----|---------|------|
| `transaction_id` | String | そのまま | PK |
| `transaction_date` | Date | `transaction_period` → Date変換 | 各四半期の初日 |
| `year_month` | String | `YYYY-MM` 形式 | Gold JOINキー |
| `year` | Int | `transaction_date` から抽出 | パーティションキー |
| `quarter` | Int | `transaction_date` から算出 | パーティションキー |
| `trade_price` | Int64 | String → BIGINT | 円 |
| `area` | Double | String → Double | ㎡ |
| `unit_price` | Double | `trade_price / area` | 万円/㎡ |
| `property_type` | String | そのまま | `中古マンション等` のみ |
| `prefecture` | String | そのまま | |
| `municipality_code` | String | そのまま | |
| `municipality` | String | そのまま | |
| `district` | String | そのまま | |
| `district_code` | String | `DistrictCode` からリネーム | |
| `building_year` | Int | `"2018年"` → `2018` | |
| `building_age` | Int | `2024 - building_year` | |
| `structure` | String | そのまま | RC, 木造等 |
| `floor_plan` | String | そのまま | 1K, 2LDK等 |
| `city_planning` | String | そのまま | |
| `renovation` | String | そのまま | |
| `ingested_at` | Timestamp | そのまま | Bronze取り込み時刻 |
| `transformed_at` | DateTimeZone | `DateTimeZone.UtcNow()` | Silver変換時刻 |

**パーティション**: `year` / `quarter`

### silver_interest_monthly

| カラム | 型 | 変換内容 | 備考 |
|--------|-----|---------|------|
| `year_month` | String | `YYYY-MM` 形式 | PK（Gold JOINキー） |
| `year` | Int | そのまま | パーティションキー |
| `month` | Int | そのまま | パーティションキー |
| `avg_yield` | Double | 月次平均 | % |
| `min_yield` | Double | 月次最小値 | |
| `max_yield` | Double | 月次最大値 | |
| `std_yield` | Double | 月次標準偏差 | |
| `mom_change_pct` | Double | 前月比変動率（%） | null許容（ゴールド層で補完も可） |
| `rate_trend` | String | `上昇` / `下降` / `横ばい` | `mom_change_pct` から判定 |
| `transformed_at` | DateTimeZone | `DateTimeZone.UtcNow()` | |

**パーティション**: `year` / `month`

---

## Dataflow Gen2 作成手順

### 共通手順

1. Fabricワークスペースを開く
2. **新しいアイテム** → **データフロー Gen2** を選択
3. Power Query エディターが開く

---

## df_realestate_bronze_to_silver

### ステップ1: Sourceに接続

1. **データの取得** → **OneLake データ ハブ** を選択
2. Bronze Lakehouse を選択
3. `bronze_realestate_transactions` テーブルを選択

### 変換ステップの設計方針

可読性を重視し、**「全データを変換してから、欲しいものを選ぶ」** 順序で構成します。

```
[型変換・異常値除外]  ← 依存関係により先行が必須
    ↓
[変換・計算列追加]    ← データを加工する
    ↓
[マンションフィルタ]  ← 何を残すかを決める
    ↓
[列の整形・削除]      ← 出力形を整える
```

> **なぜ型変換・異常値除外が先か？**
> `trade_price` が String のままでは `< 1,000,000,000` という数値比較ができないため、
> 型変換 → 異常値除外 の順序は変えられません。

### ステップ2〜14: Power Query 変換（M式）

Power Query エディターの **詳細エディター** を開き、以下のM式全体を貼り付ける:

```powerquery-m
let
    // ─────────────────────────────────────────
    // [フェーズ1] 型変換・異常値除外
    // 依存関係のため、変換・計算より先に実施
    // ─────────────────────────────────────────

    // Step 1: Bronze Lakehouseから読み込み
    // ※ 実際のLakehouseへの接続はGUI操作で設定
    Source    = Lakehouse.Tables(null, [Navigation.EnableCrossWorkspaceNavigation = true]),
    BronzeTable = Source{[Id = "bronze_realestate_transactions"]}[Data],

    // Step 2: trade_price, area を数値型に変換（全件対象）
    TypeConverted = Table.TransformColumnTypes(
        BronzeTable,
        {
            {"trade_price", Int64.Type},
            {"area",        Int64.Type}
        }
    ),

    // ─────────────────────────────────────────
    // [フェーズ2] 変換・計算列追加
    // 全物件種別のデータに対して変換を実施
    // ─────────────────────────────────────────

    // Step 3: transaction_period → transaction_date（Date型）
    // 例: "2024年第4四半期" → #date(2024, 10, 1)
    TransactionDateAdded = Table.AddColumn(
        TypeConverted,
        "transaction_date",
        each
            let
                period = [transaction_period],
                yr     = Number.From(Text.Start(period, 4)),
                month  = if Text.Contains(period, "第1四半期") then 1
                         else if Text.Contains(period, "第2四半期") then 4
                         else if Text.Contains(period, "第3四半期") then 7
                         else if Text.Contains(period, "第4四半期") then 10
                         else null
            in
                if month = null then null else #date(yr, month, 1),
        type nullable date
    ),

    // Step 5: year_month追加（YYYY-MM形式、Gold層JOINキー）
    // ※ year / quarter は Bronze取り込み時にNotebookで付与済みのためここでは不要
    YearMonthAdded = Table.AddColumn(
        TransactionDateAdded,
        "year_month",
        each
            if [transaction_date] = null then null
            else
                Text.From(Date.Year([transaction_date])) & "-" &
                Text.PadStart(Text.From(Date.Month([transaction_date])), 2, "0"),
        type nullable text
    ),

    // Step 6: building_year変換 "2018年" → 2018（Int）
    BuildingYearConverted = Table.TransformColumns(
        YearMonthAdded,
        {
            {
                "building_year",
                each if _ = null or _ = "" then null
                     else try Number.From(Text.Replace(_, "年", "")) otherwise null,
                type nullable number
            }
        }
    ),

    // Step 7: unit_price計算（円/㎡）
    UnitPriceAdded = Table.AddColumn(
        BuildingYearConverted,
        "unit_price",
        each
            if [area] = null or [area] = 0 then null
            else Number.Round([trade_price] / [area], 2),
        type nullable number
    ),

    // Step 8: building_age計算（2024年基準）
    BuildingAgeAdded = Table.AddColumn(
        UnitPriceAdded,
        "building_age",
        each
            if [building_year] = null then null
            else 2024 - Number.From([building_year]),
        type nullable number
    ),

    // Step 9: Silver変換時刻を追加
    TransformedAtAdded = Table.AddColumn(
        BuildingAgeAdded,
        "transformed_at",
        each DateTimeZone.UtcNow(),
        type datetimezone
    ),

    // ─────────────────────────────────────────
    // [フェーズ3] マンションフィルタ
    // 変換済みデータの中から分析対象物件を絞り込む
    // ─────────────────────────────────────────

    // Step 10: マンションのみ抽出（全変換完了後に絞り込む）
    FilteredManshon = Table.SelectRows(
        TransformedAtAdded,
        each [property_type] = "中古マンション等"
    ),

    // ─────────────────────────────────────────
    // [フェーズ4] 列の整形・削除
    // 出力スキーマを整える
    // ─────────────────────────────────────────

    // Step 11: DistrictCode → district_code にリネーム
    Renamed = Table.RenameColumns(
        FilteredManshon,
        {{"DistrictCode", "district_code"}}
    ),

    // Step 12: Silver層に必要な列のみ選択（不要列削除）
    FinalColumns = Table.SelectColumns(
        Renamed,
        {
            "transaction_id",
            "transaction_date",
            "year_month",
            "year",
            "quarter",
            "trade_price",
            "area",
            "unit_price",
            "property_type",
            "prefecture",
            "municipality_code",
            "municipality",
            "district",
            "district_code",
            "building_year",
            "building_age",
            "structure",
            "floor_plan",
            "city_planning",
            "renovation",
            "ingested_at",
            "transformed_at"
        }
    )
in
    FinalColumns
```

### ステップ3: Sink（出力先）設定

1. クエリ名 `silver_realestate_cleaned` をクリック（左下のクエリペイン）
2. 右下 **データの出力先を追加** → **Fabric Lakehouse（テーブル）** を選択
3. Silver Lakehouseを選択 → テーブル名: `silver_realestate_cleaned`
4. **更新方法**: `置換`（初回）または `追加`（増分時）
5. **パーティション列**: `year`, `quarter` を指定

---

## df_interest_bronze_to_silver

### M式（詳細エディターに貼り付け）

```powerquery-m
let
    // Step 1: Bronze Lakehouseから読み込み
    Source = Lakehouse.Tables(null, [Navigation.EnableCrossWorkspaceNavigation = true]),
    BronzeTable = Source{[Id = "bronze_interest_rate"]}[Data],

    // Step 2: 分析対象期間のみ抽出（2020〜2024年）
    Filtered = Table.SelectRows(
        BronzeTable,
        each [year] >= 2020 and [year] <= 2024
    ),

    // Step 3: yield_10yがnullの行を除外
    FilteredNotNull = Table.SelectRows(
        Filtered,
        each [yield_10y] <> null
    ),

    // Step 4: year_month列追加（YYYY-MM形式）
    YearMonthAdded = Table.AddColumn(
        FilteredNotNull,
        "year_month",
        each
            Text.PadStart(Text.From([year]), 4, "0") & "-" &
            Text.PadStart(Text.From([month]), 2, "0"),
        type text
    ),

    // Step 5: year_monthでグループ化して月次集計
    Grouped = Table.Group(
        YearMonthAdded,
        {"year_month", "year", "month"},
        {
            {"avg_yield", each List.Average([yield_10y]),           type nullable number},
            {"min_yield", each List.Min([yield_10y]),               type nullable number},
            {"max_yield", each List.Max([yield_10y]),               type nullable number},
            {"std_yield", each List.StandardDeviation([yield_10y]), type nullable number},
            {"record_count", each Table.RowCount(_),               type number}
        }
    ),

    // Step 6: 日付順にソート（前月比計算の準備）
    Sorted = Table.Sort(
        Grouped,
        {{"year", Order.Ascending}, {"month", Order.Ascending}}
    ),

    // Step 7: インデックス追加（前行参照用）
    Indexed = Table.AddIndexColumn(Sorted, "_idx", 0, 1, Int32.Type),

    // Step 8: 前月比変動率（mom_change_pct）計算
    // 前月のavg_yieldをインデックスで参照して計算
    MomChangeAdded = Table.AddColumn(
        Indexed,
        "mom_change_pct",
        each
            let
                currentIdx  = [_idx],
                currentYield = [avg_yield],
                prevRow     = Table.SelectRows(Indexed, each [_idx] = currentIdx - 1),
                prevYield   = if Table.IsEmpty(prevRow) then null
                              else Table.First(prevRow)[avg_yield]
            in
                if prevYield = null or prevYield = 0 then null
                else Number.Round((currentYield - prevYield) / prevYield * 100, 3),
        type nullable number
    ),

    // Step 9: rate_trend判定
    // mom_change_pct > 2% → "上昇" / < -2% → "下降" / その他 → "横ばい"
    RateTrendAdded = Table.AddColumn(
        MomChangeAdded,
        "rate_trend",
        each
            if [mom_change_pct] = null then null
            else if [mom_change_pct] > 2  then "上昇"
            else if [mom_change_pct] < -2 then "下降"
            else "横ばい",
        type nullable text
    ),

    // Step 10: transformed_at追加
    TransformedAtAdded = Table.AddColumn(
        RateTrendAdded,
        "transformed_at",
        each DateTimeZone.UtcNow(),
        type datetimezone
    ),

    // Step 11: 作業用列（_idx）を削除して最終列を選択
    FinalColumns = Table.SelectColumns(
        TransformedAtAdded,
        {
            "year_month",
            "year",
            "month",
            "avg_yield",
            "min_yield",
            "max_yield",
            "std_yield",
            "mom_change_pct",
            "rate_trend",
            "record_count",
            "transformed_at"
        }
    )
in
    FinalColumns
```

### Sink（出力先）設定

1. 右下 **データの出力先を追加** → **Fabric Lakehouse（テーブル）**
2. Silver Lakehouseを選択 → テーブル名: `silver_interest_monthly`
3. **更新方法**: `置換`
4. **パーティション列**: `year`, `month`

---

## Data Pipeline 設定（pl_bronze_to_silver）

Dataflow Gen2 単体でもスケジューリング可能だが、Bronze→Silver→Gold の連鎖実行を管理するため Data Pipeline でラップする。

```
pl_bronze_to_silver
├── アクティビティ1: Dataflow アクティビティ
│   └── df_realestate_bronze_to_silver
│
└── アクティビティ2: Dataflow アクティビティ（アクティビティ1成功後）
    └── df_interest_bronze_to_silver
```

**スケジュール設定**:
- 実行頻度: 四半期ごと（1月・4月・7月・10月の月初）
- タイムゾーン: Asia/Tokyo

---

## 動作確認クエリ（Warehouse SQL Endpoint経由）

Dataflow Gen2 実行後、Silver Lakehouseの SQL エンドポイントで以下を実行して品質確認。

### silver_realestate_cleaned 確認

```sql
-- 1. 件数・期間確認
SELECT
    year,
    quarter,
    COUNT(*)        AS record_count,
    MIN(trade_price) AS min_price,
    AVG(trade_price) AS avg_price,
    MAX(trade_price) AS max_price
FROM silver_realestate_cleaned
GROUP BY year, quarter
ORDER BY year, quarter;

-- 2. NULL値確認（重要カラムのみ）
SELECT
    COUNT(*)                                              AS total_count,
    COUNT(transaction_date)                              AS has_date,
    COUNT(trade_price)                                   AS has_price,
    COUNT(area)                                          AS has_area,
    COUNT(unit_price)                                    AS has_unit_price,
    COUNT(building_year)                                 AS has_building_year,
    ROUND(COUNT(building_year) * 100.0 / COUNT(*), 1)   AS building_year_fill_rate
FROM silver_realestate_cleaned;

-- 3. 異常値確認（除外後も念のため）
SELECT COUNT(*) AS anomaly_count
FROM silver_realestate_cleaned
WHERE trade_price <= 0
   OR trade_price >= 1000000000
   OR area <= 0
   OR area >= 1000;
```

### silver_interest_monthly 確認

```sql
-- 1. 月次データの連続性確認
SELECT
    year,
    month,
    avg_yield,
    mom_change_pct,
    rate_trend,
    record_count
FROM silver_interest_monthly
ORDER BY year, month;

-- 2. 期間確認（2020〜2024年の60ヶ月があるか）
SELECT COUNT(*) AS month_count FROM silver_interest_monthly;
-- 期待値: 60（2020年1月〜2024年12月）
```

---

## 異常値除外ルール（設計書より）

| カラム | 下限 | 上限 | 除外理由 |
|--------|------|------|---------|
| `trade_price` | 0円（除く） | 10億円未満 | データ入力ミス・異常高額取引 |
| `area` | 0㎡（除く） | 1,000㎡未満 | マンションとして非現実的 |

**除外件数の目安**: 231,810件 → 約225,000〜228,000件（約1〜3%の除外を想定）

---

## 設計判断記録

| 判断 | 採用 | 理由 |
|------|------|------|
| Silver変換の実装手段 | **Dataflow Gen2** | GUI変換フローの視覚化、Lakehouse→Lakehaouseのネイティブサポート、技術ブログ映え |
| property_typeフィルタ | `中古マンション等` のみ | RQ1（金利影響）の主分析対象、件数が最多(118,941件) |
| building_year基準年 | `2024年` | データ取得最終年（四半期ごとの更新時は動的に変更推奨） |
| mom_change_pct | Dataflow Gen2内で計算 | インデックス参照でM式実装可能、Silver層で完結 |
| transaction_dateの粒度 | 四半期初日（第1四半期=1/1等） | 取引は四半期単位で記録されており、月単位の精度は持たない |
