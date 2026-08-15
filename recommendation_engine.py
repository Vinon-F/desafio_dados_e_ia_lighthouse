import os

import numpy as np
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "port": int(os.getenv("DB_PORT")),
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
}

REQUIRED_ENV_VARS = ["DB_NAME", "DB_USER", "DB_PASSWORD"]


def validate_db_config(db_config: dict = DB_CONFIG) -> None:
    missing = [
        var for var, key in zip(
            REQUIRED_ENV_VARS, ["dbname", "user", "password"]
        )
        if not db_config.get(key)
    ]
    if missing:
        raise EnvironmentError(
            f"Variáveis de ambiente ausentes: {', '.join(missing)}. "
            f"Verifique seu arquivo .env."
        )

QUERY = """
    SELECT DISTINCT
        o.customer_id,
        p.id   AS product_id,
        p.name AS product_name
    FROM orders o
    JOIN order_items oi      ON oi.order_id = o.id
    JOIN product_variants pv ON pv.id = oi.product_variant_id
    JOIN products p          ON p.id = pv.product_id
    WHERE o.status IN ('paid', 'confirmed');
"""

def load_purchase_data(db_config: dict = DB_CONFIG, query: str = QUERY) -> pd.DataFrame:
    validate_db_config(db_config)
    with psycopg2.connect(**db_config) as conn:
        df = pd.read_sql(query, conn)
    return df

# MATRIZ USUÁRIO x PRODUTO

def build_user_item_matrix(df: pd.DataFrame) -> pd.DataFrame:

    matrix = pd.crosstab(df["customer_id"], df["product_id"])
    matrix = (matrix > 0).astype(int)
    return matrix

# SIMILARIDADE DE COSSENO ENTRE PRODUTOS

def compute_product_similarity(user_item_matrix: pd.DataFrame) -> pd.DataFrame:
    # Transpõe: cada linha vira um produto, cada coluna um cliente
    product_vectors = user_item_matrix.T

    sim_values = cosine_similarity(product_vectors.values)

    sim_df = pd.DataFrame(
        sim_values,
        index=product_vectors.index,
        columns=product_vectors.index,
    )
    return sim_df

# RANKING DE PRODUTOS SIMILARES

def get_top_similar_products(
    similarity_df: pd.DataFrame,
    product_id_to_name: dict,
    reference_product_id: int,
    top_n: int = 5,
) -> pd.DataFrame:
    """Retorna os top_n produtos mais similares ao produto de referência,
    excluindo o próprio produto do ranking.
    """
    if reference_product_id not in similarity_df.index:
        raise ValueError(f"Produto {reference_product_id} não encontrado na matriz de similaridade.")

    scores = similarity_df.loc[reference_product_id].drop(reference_product_id)
    top = scores.sort_values(ascending=False).head(top_n)

    ranking = pd.DataFrame({
        "product_id": top.index,
        "product_name": [product_id_to_name.get(pid, "?") for pid in top.index],
        "cosine_similarity": top.values.round(4),
    }).reset_index(drop=True)
    ranking.index += 1  # ranking começando em 1

    return ranking

# EXECUÇÃO

def main():
    REFERENCE_PRODUCT_NAME = "Motor de Popa 1949"
    TOP_N = 5

    df = load_purchase_data()

    product_id_to_name = (
        df.drop_duplicates("product_id")
        .set_index("product_id")["product_name"]
        .to_dict()
    )

    ref_matches = df.loc[df["product_name"] == REFERENCE_PRODUCT_NAME, "product_id"]
    if ref_matches.empty:
        raise ValueError(f"Produto de referência '{REFERENCE_PRODUCT_NAME}' não encontrado nos dados.")
    reference_product_id = int(ref_matches.iloc[0])

    user_item_matrix = build_user_item_matrix(df)
    print(f"Matriz Usuário x Produto: {user_item_matrix.shape[0]} clientes x {user_item_matrix.shape[1]} produtos\n")

    similarity_df = compute_product_similarity(user_item_matrix)

    ranking = get_top_similar_products(
        similarity_df,
        product_id_to_name,
        reference_product_id,
        top_n=TOP_N,
    )

    print(f"Top {TOP_N} produtos mais similares a '{REFERENCE_PRODUCT_NAME}':\n")
    print(ranking.to_string(index=True))

    return ranking


if __name__ == "__main__":
    main()