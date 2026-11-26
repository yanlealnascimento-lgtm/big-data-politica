import os
import sys
import pandas as pd
from sqlalchemy import create_engine, types, text
from sqlalchemy.engine.url import make_url
from dotenv import load_dotenv

ARQUIVO = "saida_agregado.csv"
TABELA = "financiamento_representatividade"
BANCO = "tse_dados"

TIPOS = {
    "ano_eleicao": types.SmallInteger(),
    "sg_uf": types.String(2),
    "ds_cargo": types.String(60),
    "ds_genero": types.String(30),
    "ds_cor_raca": types.String(30),
    "qt_candidaturas": types.Integer(),
    "qt_eleitos": types.Integer(),
    "receita_media": types.Numeric(14, 2),
    "receita_mediana": types.Numeric(14, 2),
    "receita_soma": types.Numeric(16, 2),
    "despesa_media": types.Numeric(14, 2),
    "despesa_mediana": types.Numeric(14, 2),
    "taxa_eleicao": types.Numeric(6, 4),
}


def conecta():
    load_dotenv()
    uri = os.environ.get("DATABASE_URL")
    if not uri:
        sys.exit("faltou o DATABASE_URL no .env")
    url = make_url(uri).set(drivername="postgresql+psycopg", database=BANCO)
    q = dict(url.query)
    q.setdefault("sslmode", "require")
    return create_engine(url.set(query=q))


def main():
    if not os.path.exists(ARQUIVO):
        sys.exit(f"nao achei o {ARQUIVO}, roda o etl.py antes")

    print("lendo o csv...")
    df = pd.read_csv(ARQUIVO, sep=";", encoding="utf-8")
    df.columns = [c.lower() for c in df.columns]
    cols = [c for c in TIPOS if c in df.columns]
    df = df[cols]
    print(f"  {len(df)} linhas")

    print("conectando no banco...")
    eng = conecta()

    print("gravando a tabela...")
    df.to_sql(TABELA, eng, if_exists="replace", index=False,
              dtype={c: TIPOS[c] for c in cols}, method="multi", chunksize=500)

    with eng.connect() as con:
        total = con.execute(text(f"SELECT COUNT(*) FROM {TABELA}")).scalar()
    print(f"\npronto -> {total} linhas no banco")


if __name__ == "__main__":
    main()