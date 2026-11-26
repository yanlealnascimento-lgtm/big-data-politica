import os
import sys
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.engine.url import make_url
from dotenv import load_dotenv

TABELA = "financiamento_representatividade"
BANCO = "tse_dados"

def monta_engine():
    load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env"))
    load_dotenv()
    raw = os.environ.get("DATABASE_URL")
    if not raw:
        sys.exit("ERRO")
    url = make_url(raw).set(drivername="postgresql+psycopg", database=BANCO)
    q = dict(url.query); q.setdefault("sslmode", "require")
    return create_engine(url.set(query=q))

def main():
    eng = monta_engine()

    total = pd.read_sql(f"SELECT COUNT(*) AS n FROM {TABELA}", eng)["n"][0]
    print(f"Total de linhas na tabela: {total}\n")

    for col in ["ano_eleicao", "sg_uf", "ds_cargo", "ds_genero", "ds_cor_raca", "faixa_etaria"]:
        n = pd.read_sql(f"SELECT COUNT(DISTINCT {col}) AS n FROM {TABELA}", eng)["n"][0]
        print(f"    {col:14s}: {n}")
    print()

    q = f"""
        SELECT ds_genero, ds_cor_raca,
               SUM(qt_candidaturas)                          AS candidaturas,
               SUM(qt_eleitos)                               AS eleitos,
               ROUND(SUM(receita_soma) / NULLIF(SUM(qt_candidaturas),0), 2) AS receita_media_grupo,
               ROUND(100.0 * SUM(qt_eleitos) / NULLIF(SUM(qt_candidaturas),0), 2) AS taxa_eleicao_pct
        FROM {TABELA}
        WHERE ds_cargo = 'DEPUTADO FEDERAL'
        GROUP BY ds_genero, ds_cor_raca
        ORDER BY receita_media_grupo DESC
    """
    df = pd.read_sql(q, eng)
    print("Financiamento e eleicao por genero x raca dos DP:")
    print(df.to_string(index=False))

if __name__ == "__main__":
    main()
