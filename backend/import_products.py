import pandas as pd
from pathlib import Path
from sqlalchemy import create_engine

import os
from dotenv import load_dotenv
from sqlalchemy.engine import URL

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_PATH = BASE_DIR / "dataset" / "skincare_clustered.csv"

load_dotenv(BASE_DIR / "backend" / ".env")

DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", 5432))
DB_NAME = os.getenv("DB_NAME", "porefectly")

DATABASE_URL = URL.create(
    drivername="postgresql+psycopg2",
    username=DB_USER,
    password=DB_PASSWORD,
    host=DB_HOST,
    port=DB_PORT,
    database=DB_NAME
)

engine = create_engine(DATABASE_URL)

df = pd.read_csv(DATA_PATH)

needed_cols = [
    "brand",
    "name",
    "type",
    "ingridients",
    "cluster",
    "Oily",
    "Acne_Fighting",
    "Redness",
    "Large_Pores",
    "Skin_Texture",
    "Dark_Spots",
    "Scar",
    "Anti_Aging",
    "Brightening",
    "Hydrating",
    "Eczema",
    "Rosacea",
    "Irritating",
    "Drying",
    "Acne_Trigger",
    "Worsen_Oily"
]

needed_cols = [col for col in needed_cols if col in df.columns]

df_products = df[needed_cols].copy()

binary_cols = [
    "Oily",
    "Acne_Fighting",
    "Redness",
    "Large_Pores",
    "Skin_Texture",
    "Dark_Spots",
    "Scar",
    "Anti_Aging",
    "Brightening",
    "Hydrating",
    "Eczema",
    "Rosacea",
    "Irritating",
    "Drying",
    "Acne_Trigger",
    "Worsen_Oily"
]

for col in binary_cols:
    if col in df_products.columns:
        df_products[col] = df_products[col].fillna(0).astype(int)

df_products["cluster"] = df_products["cluster"].fillna(0).astype(int)

# Hapus isi tabel lama, lalu import ulang data terbaru
df_products.to_sql(
    name="products",
    con=engine,
    if_exists="replace",
    index=False
)

print("Import selesai.")
print("Jumlah produk masuk database:", len(df_products))
print("Kolom yang masuk:", df_products.columns.tolist())