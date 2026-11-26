import argparse
import pandas as pd

SEP = ";"
ENCODING = "latin-1"  
CHUNKSIZE = 200000
ANO = 2022

COLS_CAND = [
    "SQ_CANDIDATO", "ANO_ELEICAO", "SG_UF", "DS_CARGO",
    "DS_GENERO", "DS_COR_RACA", "SG_PARTIDO",
    "DT_NASCIMENTO", "DS_SIT_TOT_TURNO",
]

DIMS = ["ANO_ELEICAO", "SG_UF", "DS_CARGO", "DS_GENERO", "DS_COR_RACA"]

COL_DESPESA = "VR_DESPESA_CONTRATADA"
COL_RECEITA = "VR_RECEITA"


def limpa_texto(serie):
    s = serie.astype("string").str.strip().str.upper()
    s = s.replace({"": pd.NA, "#NULO#": pd.NA, "#NE#": pd.NA})
    return s.fillna("NAO INFORMADO")


def faixa_etaria(dt):
    nasc = pd.to_datetime(dt, format="%d/%m/%Y", errors="coerce")
    idade = ANO - nasc.dt.year
    faixas = pd.cut(idade, bins=[0, 24, 34, 44, 59, 200],
                    labels=["ATE 24", "25-34", "35-44", "45-59", "60+"])
    return faixas.astype("object").fillna("NAO INFORMADO")


def eh_eleito(sit):
    s = sit.astype("string").str.upper().str.strip()
    ok = s.str.startswith("ELEITO", na=False) | s.str.contains("MEDIA", na=False)
    return ok.astype("int8")


def dinheiro(serie):
    # tira o ponto do milhar
    limpo = serie.astype("string").str.replace(".", "", regex=False).str.replace(",", ".", regex=False)
    return pd.to_numeric(limpo, errors="coerce")


def ler_candidatos(caminho):
    pedacos = []
    leitor = pd.read_csv(caminho, sep=SEP, encoding=ENCODING,
                         usecols=COLS_CAND, dtype=str, chunksize=CHUNKSIZE)
    i = 0
    for chunk in leitor:
        i += 1
        # aqui pega o ano de 2022
        chunk = chunk[chunk["ANO_ELEICAO"].astype(str).str.strip() == str(ANO)]
        if len(chunk) == 0:
            continue
        chunk["SQ_CANDIDATO"] = pd.to_numeric(chunk["SQ_CANDIDATO"], errors="coerce").astype("Int64")
        for col in ["SG_UF", "DS_CARGO", "DS_GENERO", "DS_COR_RACA", "SG_PARTIDO"]:
            chunk[col] = limpa_texto(chunk[col])
        chunk["ANO_ELEICAO"] = pd.to_numeric(chunk["ANO_ELEICAO"], errors="coerce").astype("Int16")
        chunk["FAIXA_ETARIA"] = faixa_etaria(chunk["DT_NASCIMENTO"])
        chunk["ELEITO"] = eh_eleito(chunk["DS_SIT_TOT_TURNO"])
        chunk = chunk.drop(columns=["DT_NASCIMENTO", "DS_SIT_TOT_TURNO"])
        pedacos.append(chunk)
        print(f"  chunk {i}: {len(chunk)} linhas")

    df = pd.concat(pedacos, ignore_index=True)
    df = df.dropna(subset=["SQ_CANDIDATO"]).drop_duplicates(subset=["SQ_CANDIDATO"])
    print(f"  total: {len(df)} candidatos")
    return df


def soma_dinheiro(caminho, col_valor, nome_saida):
    totais = {}
    n = 0
    leitor = pd.read_csv(caminho, sep=SEP, encoding=ENCODING,
                         usecols=["SQ_CANDIDATO", col_valor], dtype=str, chunksize=CHUNKSIZE)
    for chunk in leitor:
        chunk["SQ_CANDIDATO"] = pd.to_numeric(chunk["SQ_CANDIDATO"], errors="coerce").astype("Int64")
        chunk[col_valor] = dinheiro(chunk[col_valor])
        chunk = chunk.dropna(subset=["SQ_CANDIDATO"])
        for sq, val in chunk.groupby("SQ_CANDIDATO")[col_valor].sum().items():
            totais[sq] = totais.get(sq, 0.0) + float(val)
        n += len(chunk)
    print(f"  {nome_saida}: {n} lancamentos, {len(totais)} candidatos")
    return pd.DataFrame({"SQ_CANDIDATO": list(totais.keys()), nome_saida: list(totais.values())})


def agrega(cand, receitas, despesas):
    df = cand
    if receitas is not None:
        df = df.merge(receitas, on="SQ_CANDIDATO", how="left")
        df["RECEITA_TOTAL"] = df["RECEITA_TOTAL"].fillna(0.0)
    if despesas is not None:
        df = df.merge(despesas, on="SQ_CANDIDATO", how="left")
        df["DESPESA_TOTAL"] = df["DESPESA_TOTAL"].fillna(0.0)

    agg = {
        "QT_CANDIDATURAS": ("SQ_CANDIDATO", "count"),
        "QT_ELEITOS": ("ELEITO", "sum"),
    }
    if receitas is not None:
        agg["RECEITA_MEDIA"] = ("RECEITA_TOTAL", "mean")
        agg["RECEITA_MEDIANA"] = ("RECEITA_TOTAL", "median")
        agg["RECEITA_SOMA"] = ("RECEITA_TOTAL", "sum")
    if despesas is not None:
        agg["DESPESA_MEDIA"] = ("DESPESA_TOTAL", "mean")
        agg["DESPESA_MEDIANA"] = ("DESPESA_TOTAL", "median")

    res = df.groupby(DIMS, dropna=False).agg(**agg).reset_index()
    res["TAXA_ELEICAO"] = (res["QT_ELEITOS"] / res["QT_CANDIDATURAS"]).round(4)
    for c in res.columns:
        if res[c].dtype == "float64":
            res[c] = res[c].round(2)
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidatos", required=True)
    ap.add_argument("--receitas", default=None)
    ap.add_argument("--despesas", default=None)
    ap.add_argument("--col-receita", default=COL_RECEITA)
    ap.add_argument("--saida", default="saida_agregado.csv")
    args = ap.parse_args()

    print("lendo candidatos...")
    cand = ler_candidatos(args.candidatos)

    receitas = None
    despesas = None
    if args.receitas:
        print("lendo receitas...")
        receitas = soma_dinheiro(args.receitas, args.col_receita, "RECEITA_TOTAL")
    if args.despesas:
        print("lendo despesas...")
        despesas = soma_dinheiro(args.despesas, COL_DESPESA, "DESPESA_TOTAL")

    res = agrega(cand, receitas, despesas)
    res.to_csv(args.saida, sep=";", index=False, encoding="utf-8")
    print(f"\npronto -> {args.saida} ({len(res)} linhas)")
    print(res.head(12).to_string(index=False))


if __name__ == "__main__":
    main()