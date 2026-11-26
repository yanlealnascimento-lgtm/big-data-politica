# Representatividade Política e Financiamento Eleitoral

Projeto da disciplina Big Data e Analytics (UCSAL) - Marco 2.

A ideia do projeto é analisar, usando os dados abertos do TSE das eleições de 2022,
se existe desigualdade de representatividade e de financiamento de campanha quando a
gente cruza gênero com cor/raça. O tema está ligado aos ODS 5 (igualdade de gênero) e
ODS 18 (igualdade étnico-racial). Nesta etapa a gente deixou a camada de dados pronta:
baixou os dados, tratou, modelou e carregou num banco na nuvem provisionado por código.

## Dados utilizados

A fonte são os dados abertos do TSE (dadosabertos.tse.jus.br). Escolhemos as eleições
de 2022 porque é eleição geral, então tem vários cargos (deputado federal e estadual,
senador, governador, presidente) e o dinheiro de campanha é bem maior, o que faz sentido
pro nosso tema que fala de financiamento.

Usamos três arquivos, todos de 2022:

- `consulta_cand_2022` - perfil dos candidatos (gênero, cor/raça, cargo, partido, situação)
- `receitas_candidatos_2022` - o que cada candidato arrecadou
- `despesas_contratadas_candidatos_2022` - o que cada candidato gastou

Os três se ligam pela coluna `SQ_CANDIDATO`, que é o identificador de cada candidato.

Sobre as características da base: os arquivos vêm em CSV com separador ponto e vírgula e
codificação latin-1 (se abrir como UTF-8 os acentos quebram). A base de candidatos tem
mais ou menos 29 mil linhas e 50 colunas, a de receitas tem uns 675 mil lançamentos e a
de despesas passa de 2 milhões. Também tem dados pessoais (CPF, nome, email) que a gente
precisou tirar por causa da LGPD, e tem umas categorias próprias do TSE como "NÃO INFORMADO"
e "NÃO DIVULGÁVEL" pra quando a informação não está disponível.

## Tratamento realizado

O tratamento está no `etl.py`, feito em Python com Pandas.

Os principais problemas que a gente teve que resolver foram: os arquivos são grandes
demais pra abrir de uma vez, os valores de dinheiro vêm como texto no formato brasileiro
(tipo "1.234,56"), as datas vêm como texto, os textos estão despadronizados, e tem o
limite de 1 GB do banco gratuito que não ia caber se jogássemos tudo lá dentro.

O que a gente fez:

- Leu os arquivos em blocos (chunks) pra não estourar a memória
- Selecionou só as colunas que interessam, umas 10 das 50
- Tirou os dados pessoais (CPF, nome, email, título de eleitor) logo na leitura
- Converteu os valores de dinheiro pra número decimal
- Converteu as datas e tirou a faixa etária
- Padronizou os textos (tudo maiúsculo, nulos viram "NÃO INFORMADO")
- Criou uma marcação de eleito ou não a partir da situação final
- Somou receitas e despesas por candidato e juntou com o perfil
- No final, agrupou tudo por ano, estado, cargo, gênero e cor/raça

O resultado é o `saida_agregado.csv`, que ficou com 1.034 linhas e 13 colunas.

Algumas decisões que a gente tomou e por quê:

A agregação por grupo foi a forma de resolver o volume. Em vez de guardar milhões de
candidatos, guardamos só os grupos (1.034 linhas), o que cabe tranquilo no banco e ainda
ajuda na LGPD porque não fica dado individual.

Não usamos amostragem porque ela poderia bagunçar a contagem dos grupos menores, que são
justamente os que a gente quer olhar (mulheres negras, por exemplo).

Juntamos o financeiro antes de agregar de propósito. O `SQ_CANDIDATO` só existe na linha
de cada candidato, então se agrupássemos primeiro a gente perderia a ligação entre o
perfil e o quanto cada um arrecadou.

Guardamos média e mediana das receitas porque campanha tem muita diferença de valor (uns
poucos arrecadam muito), e aí a mediana mostra melhor o valor do candidato "comum".

## Modelagem

A gente usou uma tabela só, a `financiamento_representatividade`, com as 1.034 linhas.
Ela é desnormalizada, ou seja, as dimensões (ano, estado, cargo, gênero, cor/raça) e os
números (candidaturas, eleitos, receita, despesa, taxa de eleição) ficam todos juntos na
mesma tabela. Como as três bases já foram unidas lá no ETL pelo SQ_CANDIDATO, no banco não
tem relacionamento entre tabelas, o que deixa a consulta mais simples e rápida.

Os campos da tabela:

| Campo | Tipo | O que é |
|---|---|---|
| ano_eleicao | SMALLINT | ano da eleição (2022) |
| sg_uf | CHAR(2) | estado |
| ds_cargo | VARCHAR(60) | cargo |
| ds_genero | VARCHAR(30) | gênero |
| ds_cor_raca | VARCHAR(30) | cor/raça |
| qt_candidaturas | INTEGER | quantas candidaturas no grupo |
| qt_eleitos | INTEGER | quantos foram eleitos |
| receita_media | NUMERIC(14,2) | receita média por candidato |
| receita_mediana | NUMERIC(14,2) | receita mediana |
| receita_soma | NUMERIC(16,2) | receita total do grupo |
| despesa_media | NUMERIC(14,2) | despesa média |
| despesa_mediana | NUMERIC(14,2) | despesa mediana |
| taxa_eleicao | NUMERIC(6,4) | proporção de eleitos no grupo |

Sobre a escolha do banco: usamos PostgreSQL, que é relacional. Os dados são tabulares e as
consultas são todas em SQL, então faz sentido. A gente até pensou em usar OpenSearch, mas
não precisa, porque não tem busca de texto no projeto e a tabela única já resolve as
consultas que a gente quer fazer.

## Infraestrutura

O banco está hospedado na Aiven, no plano gratuito (free-1-1gb, com 1 CPU, 1 GB de RAM e
1 GB de disco). O serviço é o `pg-tse-2022` e dentro dele tem o banco `tse_dados`.

A infraestrutura toda foi criada por código com o Terraform (os arquivos estão na pasta
`terraform/`). Isso significa que em vez de criar o banco clicando no site da Aiven, a
gente escreveu o que queria num arquivo e rodou o Terraform pra criar.

As tecnologias usadas na etapa foram Terraform (infraestrutura), PostgreSQL (banco),
e Python com Pandas (tratamento e carga).

## Segurança

A gente tomou cuidado pra não deixar nenhuma senha, token ou chave no repositório.

O token da Aiven fica no `terraform.tfvars`, que não vai pro Git (no repo só tem o
`terraform.tfvars.example`, com o campo em branco pra pessoa preencher). A senha do banco
fica num arquivo `.env`, que também não vai pro Git, e o código lê de lá na hora de rodar.
O `variables.tf` só declara as variáveis como sensíveis, sem botar valor nenhum.

Tudo isso está bloqueado no `.gitignore`: o `.env`, o `terraform.tfvars`, os arquivos de
estado do Terraform (que guardam a senha) e a pasta de dados brutos.

Sobre a LGPD, como já falamos no tratamento, os dados pessoais (CPF, nome, email, título)
são jogados fora no ETL e nunca chegam no banco, já que a análise é por grupo e não por
pessoa.

## Como rodar

Precisa de Python 3 e do Terraform instalados, e de uma conta na Aiven com token.

Instalar as bibliotecas:

```
pip install pandas sqlalchemy "psycopg[binary]" python-dotenv
```

Os passos, mais ou menos nessa ordem:

1. Criar o banco com o Terraform:

```
cd terraform
cp terraform.tfvars.example terraform.tfvars
# preencher o token e o nome do projeto da Aiven no terraform.tfvars
terraform init
terraform apply
```

2. Baixar os dados de 2022 do site do TSE (candidatos, receitas e despesas contratadas)
e extrair numa pasta `dados/`. Esses arquivos não ficam no repositório porque são muito
grandes.

3. Rodar o ETL:

```
python etl.py --candidatos dados/consulta_cand_2022/consulta_cand_2022_BRASIL.csv --receitas dados/prestacao_de_contas_eleitorais_candidatos_2022/receitas_candidatos_2022_BRASIL.csv --despesas dados/prestacao_de_contas_eleitorais_candidatos_2022/despesas_contratadas_candidatos_2022_BRASIL.csv --saida saida_agregado.csv
```

4. Carregar no banco (antes disso, criar o `.env` com a DATABASE_URL, que sai do comando
`terraform output -raw pg_service_uri`):

```
python load.py
```

5. Pra conferir se carregou certo tem o `testa_banco.py`:

```
python testa_banco.py
```

## Arquivos do projeto

- `etl.py` - tratamento e agregação
- `load.py` - carga no banco
- `conferir.py` - script que a gente usou pra olhar as colunas no começo
- `testa_banco.py` - teste de leitura do banco
- `saida_agregado.csv` - a base já tratada
- `terraform/` - os arquivos de infraestrutura
- `.gitignore`
