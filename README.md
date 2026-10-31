# Representatividade Política e Financiamento Eleitoral

Projeto da disciplina Big Data e Analytics (UCSAL) — Marco 2.

Neste projeto, usamos os dados das eleições de 2022 para investigar como a participação política e o financiamento de campanha variam entre os grupos de gênero e cor/raça. O tema se relaciona aos ODS 5, sobre igualdade de gênero, e 18, sobre igualdade étnico-racial.

O Marco 2 ficou concentrado na preparação dos dados: baixar as bases, tratar os arquivos e carregar o resultado em um banco na nuvem, com a infraestrutura definida em Terraform.

## Dados utilizados

Usamos os dados abertos do TSE referentes às eleições de 2022. A escolha de 2022 permite comparar vários cargos de uma mesma eleição geral e cruzar o perfil das candidaturas com os valores de campanha.

Foram utilizados três arquivos:

- `consulta_cand_2022` — informações sobre os candidatos, como gênero, cor/raça, cargo, partido e situação eleitoral;
- `receitas_candidatos_2022` — valores arrecadados por cada candidato;
- `despesas_contratadas_candidatos_2022` — gastos contratados por cada candidato.

Os arquivos são relacionados pela coluna `SQ_CANDIDATO`, que identifica cada candidatura. Os dados estão em CSV, usam ponto e vírgula como separador e a codificação `latin-1`, necessária para que os caracteres acentuados sejam lidos corretamente.

A base de candidatos tem cerca de 29 mil registros e 50 colunas. A base de receitas possui aproximadamente 675 mil lançamentos, enquanto a de despesas passa de 2 milhões. Como os arquivos incluem informações pessoais, como CPF, nome e e-mail, esses campos foram retirados durante o tratamento. Também mantivemos categorias do TSE como “NÃO INFORMADO” e “NÃO DIVULGÁVEL”, pois elas fazem parte dos dados originais.

## Tratamento dos dados

O tratamento está no arquivo `etl.py` e foi feito em Python com a biblioteca Pandas. Como os arquivos são grandes, não seria prático carregar tudo na memória de uma vez. Além disso, os valores monetários e as datas precisavam ser convertidos, e o banco gratuito tem limite de 1 GB.

O script faz a leitura em blocos e aproveita apenas as colunas usadas na análise. Os dados pessoais são descartados logo na leitura, os valores de dinheiro são convertidos para números decimais, as datas são tratadas e os textos são padronizados. Os valores ausentes são identificados como “NÃO INFORMADO”.

O processo também cria uma marcação para indicar se o candidato foi eleito, soma receitas e despesas por candidato e junta essas informações ao perfil de cada um. Por fim, os dados são agrupados por ano, estado, cargo, gênero e cor/raça.

O resultado é o arquivo `saida_agregado.csv`, com 1.034 linhas e 13 colunas. A agregação reduz bastante o tamanho da base e permite analisar os grupos sem manter os dados pessoais de cada candidato no resultado final.

Não usamos amostragem porque ela poderia alterar a representação dos grupos com menos candidaturas, que também são importantes para a análise, como o de mulheres negras. Também juntamos as informações financeiras ao perfil antes de agrupar os dados, para não perder a relação entre cada candidato e os valores que arrecadou e gastou.

Além da média, calculamos a mediana das receitas e despesas. Como alguns candidatos recebem ou gastam valores muito altos, a mediana ajuda a entender melhor o valor mais típico de cada grupo.

## Modelagem dos dados

No banco, usamos uma única tabela chamada `financiamento_representatividade`, com as 1.034 linhas agregadas. Ela reúne as informações de ano, estado, cargo, gênero e cor/raça, além dos totais de candidaturas, eleitos, receitas, despesas e taxa de eleição.

Como as três bases de origem foram unidas durante o ETL usando `SQ_CANDIDATO`, não foi necessário criar relacionamentos entre várias tabelas no banco. Com os dados já agregados, o painel pode consultar essa tabela diretamente.

Os principais campos da tabela são:

| Campo | Tipo | Descrição |
|---|---|---|
| `ano_eleicao` | `SMALLINT` | Ano da eleição (2022) |
| `sg_uf` | `CHAR(2)` | Estado |
| `ds_cargo` | `VARCHAR(60)` | Cargo disputado |
| `ds_genero` | `VARCHAR(30)` | Gênero do candidato |
| `ds_cor_raca` | `VARCHAR(30)` | Cor/raça declarada |
| `qt_candidaturas` | `INTEGER` | Quantidade de candidaturas no grupo |
| `qt_eleitos` | `INTEGER` | Quantidade de candidatos eleitos |
| `receita_media` | `NUMERIC(14,2)` | Receita média por candidato |
| `receita_mediana` | `NUMERIC(14,2)` | Mediana das receitas |
| `receita_soma` | `NUMERIC(16,2)` | Receita total do grupo |
| `despesa_media` | `NUMERIC(14,2)` | Despesa média por candidato |
| `despesa_mediana` | `NUMERIC(14,2)` | Mediana das despesas |
| `taxa_eleicao` | `NUMERIC(6,4)` | Proporção de candidatos eleitos no grupo |

Escolhemos o PostgreSQL porque os dados são organizados em tabelas e as consultas podem ser feitas em SQL. Consideramos o OpenSearch, mas ele não é necessário para este projeto, já que não precisamos de busca textual e a tabela única atende às consultas planejadas.

## Infraestrutura

O banco está hospedado na Aiven, no plano gratuito `free-1-1gb`, com 1 CPU, 1 GB de RAM e 1 GB de armazenamento. O serviço se chama `pg-tse-2022` e o banco utilizado é `tse_dados`.

Criamos a infraestrutura usando Terraform, com os arquivos que estão na pasta `terraform/`. Assim, em vez de configurar tudo manualmente pelo site da Aiven, descrevemos a configuração em arquivos e usamos o Terraform para criar os recursos.

As principais tecnologias utilizadas foram Terraform para a infraestrutura, PostgreSQL para armazenar os dados e Python com Pandas para o tratamento e a carga.

## Segurança e LGPD

As credenciais devem ficar fora do repositório. O token da Aiven fica no arquivo `terraform.tfvars`, que não deve ser enviado ao Git. O repositório contém apenas o exemplo `terraform.tfvars.example`, sem os valores reais.

A senha de acesso ao banco fica no arquivo `.env`, e o código lê essa informação quando precisa se conectar. O `.gitignore` lista esses arquivos, os estados do Terraform e os dados brutos para que não sejam adicionados ao Git por engano.

Para reduzir a exposição de dados pessoais, CPF, nome, e-mail e título de eleitor são removidos durante o ETL e não chegam à tabela final. Como a análise é feita por grupos, não precisamos manter esses dados pessoais.

## Como executar o projeto

Para executar o projeto, é necessário ter Python 3, Terraform e uma conta na Aiven com um token de acesso.

Primeiro, instale as bibliotecas usadas pelo projeto:

```bash
pip install pandas sqlalchemy "psycopg[binary]" python-dotenv
```

### 1. Criar o banco com Terraform

Entre na pasta `terraform`, copie o arquivo de exemplo e preencha as informações solicitadas:

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
```

Depois, execute os comandos:

```bash
terraform init
terraform apply
```

### 2. Baixar os dados do TSE

Baixe os arquivos de candidatos, receitas e despesas contratadas referentes a 2022 no site de dados abertos do TSE. Extraia os arquivos na pasta `dados/`. Eles não ficam no repositório porque ocupam bastante espaço.

### 3. Executar o ETL

Na pasta principal do projeto, rode o comando abaixo para tratar e agregar os dados:

```bash
python etl.py --candidatos dados/consulta_cand_2022/consulta_cand_2022_BRASIL.csv --receitas dados/prestacao_de_contas_eleitorais_candidatos_2022/receitas_candidatos_2022_BRASIL.csv --despesas dados/prestacao_de_contas_eleitorais_candidatos_2022/despesas_contratadas_candidatos_2022_BRASIL.csv --saida saida_agregado.csv
```

### 4. Carregar os dados no banco

Crie o arquivo `.env` com a variável `DATABASE_URL`. A URL de conexão pode ser obtida com o comando `terraform output -raw pg_service_uri`. Salve esse arquivo na raiz do projeto. Em seguida, execute:

```bash
python load.py
```

### 5. Conferir a carga

Para verificar se os dados foram carregados corretamente, execute:

```bash
python testa_banco.py
```

## Arquivos do projeto

- `etl.py` — faz o tratamento e a agregação dos dados;
- `load.py` — carrega os dados no banco;
- `conferir.py` — foi usado para verificar as colunas no início do projeto;
- `testa_banco.py` — testa a leitura dos dados no banco;
- `saida_agregado.csv` — contém a base tratada e agregada;
- `terraform/` — contém os arquivos usados para criar a infraestrutura;
- `.gitignore` — define quais arquivos não devem ser enviados ao repositório.
