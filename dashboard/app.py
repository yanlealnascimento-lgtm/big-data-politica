import os
import pandas as pd
import streamlit as st
import plotly.express as px
from sqlalchemy import create_engine
from sqlalchemy.engine.url import make_url

TABELA = "financiamento_representatividade"
BANCO = "tse_dados"

st.set_page_config(page_title="Representatividade & Financiamento - TSE 2022",
                   page_icon="🗳️", layout="wide")


def pega_url():
    try:
        if "DATABASE_URL" in st.secrets:
            return st.secrets["DATABASE_URL"]
    except Exception:
        pass
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env"))
    load_dotenv()
    return os.environ.get("DATABASE_URL")


@st.cache_resource
def conecta():
    uri = pega_url()
    if not uri:
        st.error("faltou configurar o DATABASE_URL")
        st.stop()
    url = make_url(uri).set(drivername="postgresql+psycopg", database=BANCO)
    q = dict(url.query)
    q.setdefault("sslmode", "require")
    return create_engine(url.set(query=q))


@st.cache_data(ttl=600)
def carrega():
    return pd.read_sql(f"SELECT * FROM {TABELA}", conecta())


df = carrega()

st.title("Representatividade Política e Financiamento Eleitoral")
st.markdown("#### Mulheres e pessoas negras recebem menos dinheiro de campanha e se elegem menos?")
st.caption("Eleições Gerais de 2022 · Fonte: TSE · Gênero × Cor/Raça")

st.sidebar.header("Filtros")

def filtro(label, col, excluir=None):
    opcoes = sorted(df[col].dropna().unique().tolist())
    excluir = excluir or []
    marcados = [o for o in opcoes if o not in excluir]
    return st.sidebar.multiselect(label, opcoes, default=marcados)

suplentes = [c for c in df.ds_cargo.unique() if "SUPLENTE" in str(c).upper()]
raca_fora = [r for r in df.ds_cor_raca.unique()
             if str(r).upper() in ("NÃO INFORMADO", "NAO INFORMADO", "NÃO DIVULGÁVEL", "NAO DIVULGAVEL")]
gen_fora = [g for g in df.ds_genero.unique() if str(g).upper() in ("NÃO DIVULGÁVEL", "NAO DIVULGAVEL")]

f_ano = filtro("Ano", "ano_eleicao")
f_uf = filtro("Estado (UF)", "sg_uf")
cargos = sorted(df.ds_cargo.dropna().unique().tolist())
padrao_cargo = ["DEPUTADO FEDERAL"] if "DEPUTADO FEDERAL" in cargos else [c for c in cargos if c not in suplentes]
f_cargo = st.sidebar.multiselect("Cargo", cargos, default=padrao_cargo)
f_gen = filtro("Gênero", "ds_genero", excluir=gen_fora)
f_raca = filtro("Cor/Raça", "ds_cor_raca", excluir=raca_fora)

tem_faixa = "faixa_etaria" in df.columns
ORDEM_FAIXA = ["ATE 24", "25-34", "35-44", "45-59", "60+", "NAO INFORMADO"]
NOME_FAIXA = {"ATE 24": "Até 24", "NAO INFORMADO": "Não informado"}
if tem_faixa:
    existentes = set(df.faixa_etaria.dropna())
    faixas = [f for f in ORDEM_FAIXA if f in existentes] + sorted(existentes - set(ORDEM_FAIXA))
    f_faixa = st.sidebar.multiselect("Faixa etária", faixas,
                                     default=[f for f in faixas if f != "NAO INFORMADO"],
                                     format_func=lambda f: NOME_FAIXA.get(f, f))
st.sidebar.caption("O painel abre em Deputado Federal, o cargo com mais candidaturas. Os outros cargos, suplentes e categorias sem info podem ser marcados nos filtros.")

mascara = (df.ano_eleicao.isin(f_ano) & df.sg_uf.isin(f_uf) & df.ds_cargo.isin(f_cargo) &
           df.ds_genero.isin(f_gen) & df.ds_cor_raca.isin(f_raca))
if tem_faixa:
    mascara &= df.faixa_etaria.isin(f_faixa)
d = df[mascara]

if len(d) == 0:
    st.warning("Nenhum dado com esses filtros.")
    st.stop()

cand = int(d.qt_candidaturas.sum())
eleitos = int(d.qt_eleitos.sum())
taxa = 100 * eleitos / cand if cand else 0
rec_media = d.receita_soma.sum() / cand if cand else 0

c1, c2, c3, c4 = st.columns(4)
c1.metric("Candidaturas", f"{cand:,}".replace(",", "."))
c2.metric("Eleitos", f"{eleitos:,}".replace(",", "."))
c3.metric("Taxa de eleição", f"{taxa:.1f}%")
c4.metric("Receita média / candidatura", f"R$ {rec_media:,.0f}".replace(",", "."))

base = df[df.ano_eleicao.isin(f_ano) & df.sg_uf.isin(f_uf) & df.ds_cargo.isin(f_cargo)]
if tem_faixa:
    base = base[base.faixa_etaria.isin(f_faixa)]

def resumo(g):
    c = g.qt_candidaturas.sum()
    if c == 0:
        return None
    return g.receita_soma.sum() / c, 100 * g.qt_eleitos.sum() / c

hb = resumo(base[(base.ds_genero == "MASCULINO") & (base.ds_cor_raca == "BRANCA")])
mn = resumo(base[(base.ds_genero == "FEMININO") & base.ds_cor_raca.isin(["PRETA", "PARDA"])])

def reais(v):
    return f"R$ {v:,.0f}".replace(",", ".")

st.subheader("Homens brancos x mulheres negras")
if hb and mn:
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Receita média: homens brancos", reais(hb[0]))
    k2.metric("Receita média: mulheres negras", reais(mn[0]),
              f"{mn[0] / hb[0]:.1f}x a dos homens brancos" if hb[0] else None, delta_color="off")
    k3.metric("Eleitos: homens brancos", f"{hb[1]:.1f}%")
    k4.metric("Eleitas: mulheres negras", f"{mn[1]:.1f}%",
              f"{mn[1] / hb[1]:.1f}x a dos homens brancos" if hb[1] else None, delta_color="off")
    st.caption("Mulheres negras = pretas e pardas. Este bloco segue os filtros de ano, estado, cargo e faixa etária.")
else:
    st.info("Não há candidaturas dos dois grupos com esses filtros.")

st.divider()

st.subheader("Comparação por Gênero × Cor/Raça")
metrica = st.radio("Métrica:", ["Receita média", "Receita total", "Taxa de eleição (%)"], horizontal=True)

g = d.groupby(["ds_genero", "ds_cor_raca"], as_index=False).agg(
    cand=("qt_candidaturas", "sum"), eleitos=("qt_eleitos", "sum"), receita_soma=("receita_soma", "sum"))
g["Receita média"] = g.receita_soma / g.cand
g["Receita total"] = g.receita_soma
g["Taxa de eleição (%)"] = 100 * g.eleitos / g.cand

fig = px.bar(g, x="ds_cor_raca", y=metrica, color="ds_genero", barmode="group", text_auto=".2s",
             labels={"ds_cor_raca": "Cor/Raça", "ds_genero": "Gênero"},
             color_discrete_sequence=px.colors.qualitative.Set2)
fig.update_layout(legend_title_text="Gênero", height=430)
st.plotly_chart(fig, width="stretch")

st.subheader("Financiamento × Taxa de eleição")
g["Receita média/candidatura"] = g.receita_soma / g.cand
g["Taxa eleição %"] = 100 * g.eleitos / g.cand
g["grupo"] = g.ds_genero + " · " + g.ds_cor_raca
fig2 = px.scatter(g, x="Receita média/candidatura", y="Taxa eleição %",
                  size="cand", color="ds_genero", hover_name="grupo",
                  color_discrete_sequence=px.colors.qualitative.Set2)
fig2.update_layout(height=430, legend_title_text="Gênero")
st.plotly_chart(fig2, width="stretch")

if tem_faixa:
    st.subheader("Por faixa etária")
    fx = d.groupby(["faixa_etaria", "ds_genero"], as_index=False).agg(
        cand=("qt_candidaturas", "sum"), eleitos=("qt_eleitos", "sum"), receita_soma=("receita_soma", "sum"))
    fx["Receita média"] = fx.receita_soma / fx.cand
    fx["Receita total"] = fx.receita_soma
    fx["Taxa de eleição (%)"] = 100 * fx.eleitos / fx.cand
    fx["faixa_etaria"] = fx.faixa_etaria.map(lambda f: NOME_FAIXA.get(f, f))
    ordem = [NOME_FAIXA.get(f, f) for f in ORDEM_FAIXA]
    fig3 = px.bar(fx, x="faixa_etaria", y=metrica, color="ds_genero", barmode="group", text_auto=".2s",
                  category_orders={"faixa_etaria": ordem},
                  labels={"faixa_etaria": "Faixa etária", "ds_genero": "Gênero"},
                  color_discrete_sequence=px.colors.qualitative.Set2)
    fig3.update_layout(legend_title_text="Gênero", height=400)
    st.plotly_chart(fig3, width="stretch")

st.subheader("Detalhamento")
tab = d.sort_values("receita_soma", ascending=False).rename(columns={
    "ano_eleicao": "Ano", "sg_uf": "UF", "ds_cargo": "Cargo", "ds_genero": "Gênero", "ds_cor_raca": "Cor/Raça",
    "faixa_etaria": "Faixa etária",
    "qt_candidaturas": "Candidaturas", "qt_eleitos": "Eleitos",
    "receita_media": "Receita média", "receita_mediana": "Receita mediana",
    "receita_soma": "Receita total", "taxa_eleicao": "Taxa eleição"})
st.dataframe(tab, width="stretch", hide_index=True)

st.caption("Grupos pequenos têm médias mais instáveis. Categorias 'NÃO INFORMADO' vieram do dado bruto do TSE.")
