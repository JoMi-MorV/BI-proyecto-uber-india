import pandas as pd
df = pd.read_csv("data/raw/uber_india_2024.csv")
print(df["Booking Status"].value_counts())
print(df["Date"].min(), df["Date"].max())
print(pd.crosstab(df["Booking Status"], df["Payment Method"].fillna("null")))