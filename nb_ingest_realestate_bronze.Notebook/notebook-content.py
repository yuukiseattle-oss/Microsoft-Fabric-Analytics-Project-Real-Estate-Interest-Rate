# Fabric notebook source

# METADATA ********************

# META {
# META   "kernel_info": {
# META     "name": "synapse_pyspark"
# META   },
# META   "dependencies": {
# META     "lakehouse": {
# META       "default_lakehouse": "daafb4a7-f64d-4a0d-b5b6-a3f7d2e6f3ab",
# META       "default_lakehouse_name": "lh_bronze",
# META       "default_lakehouse_workspace_id": "a0023aa2-9b7b-419b-bec4-ad2bc8e7db13",
# META       "known_lakehouses": [
# META         {
# META           "id": "daafb4a7-f64d-4a0d-b5b6-a3f7d2e6f3ab"
# META         }
# META       ]
# META     }
# META   }
# META }

# CELL ********************

# Welcome to your new notebook
# Type here in the cell editor to add code!


# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

import pandas as pd
import requests
from io import StringIO

url = "https://www.mof.go.jp/jgbs/reference/interest_rate/data/jgbcm_all.csv"
response = requests.get(url)
response.encoding = 'shift_jis'

df = pd.read_csv(StringIO(response.text), skiprows=1)
# 10年国債利回りを抽出

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************


# pandas DataFrame → Spark DataFrame に変換し、Delta table として書き込み
spark_df = spark.createDataFrame(df)

table_name = "bronze_interest_rate"
spark_df.write.format("delta").mode("overwrite").saveAsTable(f"dbo.{table_name}")

print(f"Delta table '{table_name}' に {spark_df.count()} 行を書き込みました")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************


# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }
