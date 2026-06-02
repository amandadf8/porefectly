from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from pathlib import Path
import pandas as pd
import joblib
from typing import List, Optional

from fastapi.middleware.cors import CORSMiddleware

from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL

import os
from dotenv import load_dotenv

# ============================================================
# PATH SETUP
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent
MODEL_DIR = BASE_DIR / "models" / "classification"


# ============================================================
# DATABASE SETUP
# ============================================================

load_dotenv(BASE_DIR / "backend" / ".env")

DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", 5432))
DB_NAME = os.getenv("DB_NAME", "porefectly")

if not DB_PASSWORD:
    raise ValueError("DB_PASSWORD belum diatur di file .env")

DATABASE_URL = URL.create(
    drivername="postgresql+psycopg2",
    username=DB_USER,
    password=DB_PASSWORD,
    host=DB_HOST,
    port=DB_PORT,
    database=DB_NAME
)

engine = create_engine(DATABASE_URL)

# ============================================================
# FASTAPI APP
# ============================================================

app = FastAPI(
    title="Skincare Recommendation API",
    description="API rekomendasi skincare berdasarkan tipe kulit dan permasalahan kulit",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# MAPPING INPUT USER
# ============================================================

skin_type_mapping = {
    "Normal": [],
    "Oily": ["Oily"],
    "Dry": ["Hydrating"],
    "Combination": ["Oily", "Hydrating"],
    "Sensitive": ["Redness", "Eczema", "Rosacea"]
}

skin_problem_mapping = {
    "Acne": ["Acne_Fighting"],
    "Aging": ["Anti_Aging"],
    "Dark Spots": ["Dark_Spots"],
    "Brightening": ["Brightening"],
    "Scar": ["Scar"],
    "Large Pores": ["Large_Pores"],
    "Skin Texture": ["Skin_Texture"]
}

type_list = [
    "Serum",
    "Moisturizer",
    "Face Cleanser",
    "Sunscreen",
    "Toner",
    "Exfoliator",
    "Makeup Remover"
]


# ============================================================
# REQUEST SCHEMA
# ============================================================

class RecommendationRequest(BaseModel):
    skin_type: str
    skin_problems: List[str]
    product_type: str
    top_n: Optional[int] = 5


class RecommendationAllRequest(BaseModel):
    skin_type: str
    skin_problems: List[str]
    top_n: Optional[int] = 5


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def safe_filename(text: str) -> str:
    return text.lower().replace(" ", "_").replace("/", "_")


def encode_user_input(
    skin_type: str,
    skin_problems: List[str],
    feature_cols: List[str]
) -> pd.DataFrame:
    user_vector = {col: 0 for col in feature_cols}

    for tag in skin_type_mapping.get(skin_type, []):
        if tag in user_vector:
            user_vector[tag] = 1

    for problem in skin_problems:
        for tag in skin_problem_mapping.get(problem, []):
            if tag in user_vector:
                user_vector[tag] = 1

    return pd.DataFrame([user_vector])


def load_classifier(product_type: str):
    model_path = MODEL_DIR / f"best_classifier_{safe_filename(product_type)}.pkl"

    if not model_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Model untuk product_type '{product_type}' tidak ditemukan."
        )

    return joblib.load(model_path)


def get_products_from_db(product_type: str, predicted_cluster: int) -> pd.DataFrame:
    query = text("""
        SELECT *
        FROM products
        WHERE type = :product_type
        AND cluster = :predicted_cluster
    """)

    with engine.connect() as conn:
        df_products = pd.read_sql(
            query,
            conn,
            params={
                "product_type": product_type,
                "predicted_cluster": int(predicted_cluster)
            }
        )

    return df_products


def save_recommendation_history(
    skin_type: str,
    skin_problems: List[str],
    product_type: str,
    predicted_cluster: int,
    top_n: int,
    recommendations: List[dict]
):
    skin_problems_text = ", ".join(skin_problems)

    with engine.begin() as conn:
        history_query = text("""
            INSERT INTO recommendation_history
            (skin_type, skin_problems, product_type, predicted_cluster, top_n)
            VALUES
            (:skin_type, :skin_problems, :product_type, :predicted_cluster, :top_n)
            RETURNING id
        """)

        history_id = conn.execute(
            history_query,
            {
                "skin_type": skin_type,
                "skin_problems": skin_problems_text,
                "product_type": product_type,
                "predicted_cluster": int(predicted_cluster),
                "top_n": int(top_n)
            }
        ).scalar()

        item_query = text("""
            INSERT INTO recommendation_items
            (
                history_id,
                brand,
                product_name,
                product_type,
                cluster_id,
                both_match,
                problem_score,
                skin_score,
                final_score,
                warning_score
            )
            VALUES
            (
                :history_id,
                :brand,
                :product_name,
                :product_type,
                :cluster_id,
                :both_match,
                :problem_score,
                :skin_score,
                :final_score,
                :warning_score
            )
        """)

        for item in recommendations:
            conn.execute(
                item_query,
                {
                    "history_id": history_id,
                    "brand": item.get("brand", ""),
                    "product_name": item.get("name", ""),
                    "product_type": item.get("type", product_type),
                    "cluster_id": int(item.get("cluster", predicted_cluster)),
                    "both_match": int(item.get("both_match", 0)),
                    "problem_score": float(item.get("problem_score", 0)),
                    "skin_score": float(item.get("skin_score", 0)),
                    "final_score": float(item.get("final_score", 0)),
                    "warning_score": float(item.get("warning_score", 0))
                }
            )

    return history_id


def recommend_products(
    skin_type: str,
    skin_problems: List[str],
    product_type: str,
    top_n: int = 5,
    save_history: bool = True
):
    classifier_package = load_classifier(product_type)

    clf = classifier_package["model"]
    used_features = classifier_package["features"]

    user_input = encode_user_input(
        skin_type=skin_type,
        skin_problems=skin_problems,
        feature_cols=used_features
    )

    predicted_cluster = clf.predict(user_input)[0]

    # Ambil kandidat produk dari PostgreSQL, bukan CSV
    candidates = get_products_from_db(product_type, predicted_cluster)

    if candidates.empty:
        return {
            "input": {
                "skin_type": skin_type,
                "skin_problems": skin_problems,
                "product_type": product_type,
                "top_n": top_n
            },
            "predicted_cluster": int(predicted_cluster),
            "skin_type_tags": [],
            "problem_tags": [],
            "total_candidates": 0,
            "recommendations": []
        }

    # Tag tipe kulit
    skin_type_tags = skin_type_mapping.get(skin_type, [])
    skin_type_tags = [tag for tag in skin_type_tags if tag in used_features]

    # Tag masalah kulit
    problem_tags = []
    for problem in skin_problems:
        problem_tags.extend(skin_problem_mapping.get(problem, []))

    problem_tags = [tag for tag in problem_tags if tag in used_features]

    # Hitung skor tipe kulit
    if skin_type_tags:
        candidates["skin_score"] = candidates[skin_type_tags].sum(axis=1)
    else:
        candidates["skin_score"] = 0

    # Hitung skor masalah kulit
    if problem_tags:
        candidates["problem_score"] = candidates[problem_tags].sum(axis=1)
    else:
        candidates["problem_score"] = 0

    # Produk yang cocok dengan tipe kulit dan masalah kulit
    candidates["has_skin_match"] = (candidates["skin_score"] > 0).astype(int)
    candidates["has_problem_match"] = (candidates["problem_score"] > 0).astype(int)

    candidates["both_match"] = (
        (candidates["has_skin_match"] == 1) &
        (candidates["has_problem_match"] == 1)
    ).astype(int)

    # Warning score
    warning_cols = ["Irritating", "Drying", "Acne_Trigger", "Worsen_Oily"]
    warning_cols = [col for col in warning_cols if col in candidates.columns]

    if warning_cols:
        candidates["warning_score"] = candidates[warning_cols].sum(axis=1)
    else:
        candidates["warning_score"] = 0

    # Final score
    candidates["final_score"] = (
        candidates["problem_score"] * 2 +
        candidates["skin_score"] * 1.5 +
        candidates["both_match"] * 3 -
        candidates["warning_score"] * 0.5
    )

    candidates = candidates.sort_values(
        by=[
            "both_match",
            "problem_score",
            "skin_score",
            "final_score",
            "warning_score"
        ],
        ascending=[
            False,
            False,
            False,
            False,
            True
        ]
    )

    output_cols = [
        "brand",
        "name",
        "type",
        "ingridients",
        "cluster",
        "both_match",
        "problem_score",
        "skin_score",
        "final_score",
        "warning_score",
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

    output_cols = [col for col in output_cols if col in candidates.columns]

    recommendations_df = candidates[output_cols].head(top_n)
    recommendations = recommendations_df.fillna("").to_dict(orient="records")

    history_id = None
    if save_history:
        history_id = save_recommendation_history(
            skin_type=skin_type,
            skin_problems=skin_problems,
            product_type=product_type,
            predicted_cluster=predicted_cluster,
            top_n=top_n,
            recommendations=recommendations
        )

    return {
        "input": {
            "skin_type": skin_type,
            "skin_problems": skin_problems,
            "product_type": product_type,
            "top_n": top_n
        },
        "skin_type_tags": skin_type_tags,
        "problem_tags": problem_tags,
        "predicted_cluster": int(predicted_cluster),
        "total_candidates": int(len(candidates)),
        "history_id": history_id,
        "recommendations": recommendations
    }


# ============================================================
# ROUTES
# ============================================================

@app.get("/")
def root():
    return {
        "message": "Skincare Recommendation API aktif",
        "available_endpoints": [
            "/recommend",
            "/recommend-all",
            "/options",
            "/health"
        ]
    }


@app.get("/health")
def health_check():
    try:
        with engine.connect() as conn:
            total_products = conn.execute(
                text("SELECT COUNT(*) FROM products")
            ).scalar()

        return {
            "status": "ok",
            "database": "connected",
            "total_products": int(total_products),
            "model_dir": str(MODEL_DIR)
        }

    except Exception as e:
        return {
            "status": "error",
            "database": "not connected",
            "detail": str(e)
        }


@app.get("/options")
def get_options():
    return {
        "skin_types": list(skin_type_mapping.keys()),
        "skin_problems": list(skin_problem_mapping.keys()),
        "product_types": type_list
    }


@app.post("/recommend")
def recommend(request: RecommendationRequest):
    if request.skin_type not in skin_type_mapping:
        raise HTTPException(
            status_code=400,
            detail=f"skin_type tidak valid. Pilihan: {list(skin_type_mapping.keys())}"
        )

    invalid_problems = [
        problem for problem in request.skin_problems
        if problem not in skin_problem_mapping
    ]

    if invalid_problems:
        raise HTTPException(
            status_code=400,
            detail=f"skin_problems tidak valid: {invalid_problems}. Pilihan: {list(skin_problem_mapping.keys())}"
        )

    if request.product_type not in type_list:
        raise HTTPException(
            status_code=400,
            detail=f"product_type tidak valid. Pilihan: {type_list}"
        )

    return recommend_products(
        skin_type=request.skin_type,
        skin_problems=request.skin_problems,
        product_type=request.product_type,
        top_n=request.top_n or 5,
        save_history=True
    )


@app.post("/recommend-all")
def recommend_all(request: RecommendationAllRequest):
    if request.skin_type not in skin_type_mapping:
        raise HTTPException(
            status_code=400,
            detail=f"skin_type tidak valid. Pilihan: {list(skin_type_mapping.keys())}"
        )

    invalid_problems = [
        problem for problem in request.skin_problems
        if problem not in skin_problem_mapping
    ]

    if invalid_problems:
        raise HTTPException(
            status_code=400,
            detail=f"skin_problems tidak valid: {invalid_problems}. Pilihan: {list(skin_problem_mapping.keys())}"
        )

    results = {}

    for product_type in type_list:
        results[product_type] = recommend_products(
            skin_type=request.skin_type,
            skin_problems=request.skin_problems,
            product_type=product_type,
            top_n=request.top_n or 5,
            save_history=True
        )

    return {
        "input": {
            "skin_type": request.skin_type,
            "skin_problems": request.skin_problems,
            "top_n": request.top_n or 5
        },
        "results": results
    }
