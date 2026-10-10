import pandas as pd

df = pd.read_csv(
    "dados/consulta_cand_2022/consulta_cand_2022_BA.csv",
    sep=";",
    encoding="latin-1",
    dtype=str,
    nrows=100
)

print(df.columns.tolist())   
print(df.head(10)) 
