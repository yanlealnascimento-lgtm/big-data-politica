# Representatividade Política e Financiamento Eleitoral

Neste projeto, usamos os dados das eleições de 2022 para investigar como a participação política e o financiamento de campanha variam entre os grupos de gênero e cor/raça. O tema se relaciona aos ODS 5, sobre igualdade de gênero, e 18, sobre igualdade étnico-racial.

**Link do painel online:** https://big-data-politica-ib6msrcjxts82spqy4yflm.streamlit.app/

## Arquitetura da solução

```
 Portal de Dados Abertos do TSE (CSV, eleições 2022)
   |  consulta_cand_2022        (perfil das candidaturas)
   |  receitas_candidatos_2022  (arrecadação)
   |  despesas_contratadas_2022 (gastos)
   v
 etl/etl.py  (Python + Pandas, leitura em blocos)
   |  seleção de colunas, remoção de dados pessoais,
   |  conversão de tipos, soma por candidato,
   |  junção por SQ_CANDIDATO, agregação por grupo
   v
 saida_agregado.csv  (base tratada, 2.560 linhas)
   |
   v  etl/load.py
 PostgreSQL na Aiven (plano gratuito)  <-- criado pelo Terraform (terraform/)
   |  tabela financiamento_representatividade
   v
 dashboard/app.py  (Streamlit)
      KPIs, filtros cruzados, seletor de métrica, detalhamento
```

## Dados utilizados

Usamos os dados abertos do TSE referentes às eleições de 2022. A escolha de 2022 permite comparar vários cargos de uma mesma eleição geral e cruzar o perfil das candidaturas com os valores de campanha.

Foram utilizados três arquivos:

- `consulta_cand_2022`: informações sobre os candidatos, como gênero, cor/raça, cargo, partido, data de nascimento e situação eleitoral;
- `receitas_candidatos_2022`: valores arrecadados por cada candidato;
- `despesas_contratadas_candidatos_2022`: gastos contratados por cada candidato.

Os arquivos são relacionados pela coluna `SQ_CANDIDATO`, que identifica cada candidatura. Os dados estão em CSV, usam ponto e vírgula como separador e a codificação `latin-1`, necessária para que os caracteres acentuados sejam lidos corretamente.

A base de candidatos tem cerca de 29 mil registros e 50 colunas. A base de receitas possui aproximadamente 675 mil lançamentos, enquanto a de despesas passa de 2 milhões. Como os arquivos incluem informações pessoais, como CPF, nome e e-mail, esses campos foram retirados durante o tratamento. Também mantivemos categorias do TSE como "NÃO INFORMADO" e "NÃO DIVULGÁVEL", pois elas fazem parte dos dados originais.

## Os 5 V's aplicados à base

**Volume.** Os três arquivos somam perto de 1,8 GB e quase 2,9 milhões de linhas, mais do que cabe no banco gratuito de 1 GB. Por isso o ETL lê os arquivos em blocos, usa só as colunas necessárias e agrega os dados antes da carga. O que vai para o banco são 2.560 linhas.

**Variedade.** A base principal é estruturada (tabelas em CSV com colunas fixas), mas vários campos chegam como texto e precisam de conversão: datas no formato `dd/mm/aaaa` e valores em reais no formato `1.234,56`. Os arquivos também trazem campos de texto livre, que não entraram na análise (ver a classificação abaixo).

**Velocidade.** O processamento é em lote (batch). Os dados de uma eleição mudam pouco depois que ela termina, então não faz sentido ingestão contínua: quando o TSE atualiza os arquivos, basta rodar o ETL e a carga de novo.

**Veracidade.** Lemos com a codificação correta, convertemos cada coluna para o tipo certo, padronizamos os textos, tratamos os nulos e removemos candidaturas duplicadas. Também não usamos amostragem, para não distorcer a contagem dos grupos menores, e mantivemos as categorias sem informação em vez de apagá-las.

**Valor.** A base permite medir desigualdades de gênero e raça em três pontos: quem consegue se candidatar, quem recebe dinheiro para a campanha e quem é eleito.

## Classificação dos tipos de dados

| Tipo | Onde aparece no projeto | Uso |
|---|---|---|
| Estruturado | Os três CSVs do TSE, com colunas fixas e separador `;` | Base de toda a análise |
| Semi-estruturado | Metadados dos conjuntos no portal de dados abertos (JSON da API do portal) | Consultados para localizar os arquivos, não entram no banco |
| Não estruturado | Textos livres como `DS_RECEITA` e `DS_DESPESA`, que descrevem cada lançamento | Descartados no ETL, não são necessários para os indicadores |

## Tratamento dos dados

O tratamento está no arquivo `etl/etl.py` e foi feito em Python com a biblioteca Pandas. Como os arquivos são grandes, não seria prático carregar tudo na memória de uma vez. Além disso, os valores monetários e as datas precisavam ser convertidos, e o banco gratuito tem limite de 1 GB.

O script faz a leitura em blocos e aproveita apenas as colunas usadas na análise. Os dados pessoais são descartados logo na leitura, os valores de dinheiro são convertidos para números decimais, as datas são tratadas e os textos são padronizados. Os valores ausentes são identificados como "NÃO INFORMADO".

O processo também cria uma marcação para indicar se o candidato foi eleito, calcula a faixa etária, soma receitas e despesas por candidato e junta essas informações ao perfil de cada um. Por fim, os dados são agrupados por ano, estado, cargo, gênero, cor/raça e faixa etária.

O resultado é o arquivo `saida_agregado.csv`, com 2.560 linhas e 14 colunas. A agregação reduz bastante o tamanho da base e permite analisar os grupos sem manter os dados pessoais de cada candidato no resultado final.

Não usamos amostragem porque ela poderia alterar a representação dos grupos com menos candidaturas, que também são importantes para a análise, como o de mulheres negras. Também juntamos as informações financeiras ao perfil antes de agrupar os dados, para não perder a relação entre cada candidato e os valores que arrecadou e gastou.

Além da média, calculamos a mediana das receitas e despesas. Como alguns candidatos recebem ou gastam valores muito altos, a mediana ajuda a entender melhor o valor mais típico de cada grupo.

## Regras de negócio

Estas são as regras que transformam os dados brutos nos indicadores do painel:

1. **Candidatura eleita.** Uma candidatura conta como eleita quando a situação final (`DS_SIT_TOT_TURNO`) começa com "ELEITO", o que inclui "ELEITO POR QP" e "ELEITO POR MÉDIA". Suplentes e não eleitos contam como não eleitos.
2. **Taxa de eleição.** Para cada grupo, é o número de eleitos dividido pelo número de candidaturas.
3. **Receita e despesa por candidato.** É a soma de todos os lançamentos com o mesmo `SQ_CANDIDATO`. Candidato sem nenhum lançamento fica com valor zero.
4. **Receita média.** No painel, a média de um conjunto de grupos é recalculada como receita total dividida pelo total de candidaturas. Não fazemos média das médias, porque isso daria o mesmo peso a um grupo de 3 pessoas e a um de 3 mil.
5. **Faixa etária.** É a idade no ano da eleição (2022 menos o ano de nascimento), separada em: até 24, 25 a 34, 35 a 44, 45 a 59 e 60 ou mais.
6. **Cada candidatura conta uma vez.** Quem disputou o segundo turno aparece duas vezes no arquivo do TSE, uma linha para cada turno. Nesses casos fica só a linha do último turno, que tem o resultado final. Sem essa regra, parte dos governadores eleitos no segundo turno seria contada como não eleita.
7. **Suplentes fora da análise padrão.** Suplentes não têm prestação de contas própria e entram com receita zero, o que puxaria as médias para baixo. Por isso vêm desmarcados no painel, mas continuam no banco e podem ser reativados no filtro.
8. **Categorias sem informação.** "NÃO INFORMADO" e "NÃO DIVULGÁVEL" ficam guardadas no banco, mas vêm desmarcadas nos gráficos para não aparecerem como se fossem um grupo de verdade.

## Modelagem dos dados

No banco, usamos uma única tabela chamada `financiamento_representatividade`, com as 2.560 linhas agregadas. Ela reúne as informações de ano, estado, cargo, gênero, cor/raça e faixa etária, além dos totais de candidaturas, eleitos, receitas, despesas e taxa de eleição.

Como as três bases de origem foram unidas durante o ETL usando `SQ_CANDIDATO`, não foi necessário criar relacionamentos entre várias tabelas no banco. Com os dados já agregados, o painel pode consultar essa tabela diretamente.

Chegamos a considerar um modelo estrela, com uma tabela fato e dimensões separadas para local, cargo e perfil. Mas como as dimensões têm poucos valores e a tabela é pequena, separar só acrescentaria JOINs em toda consulta, sem economia de espaço que fizesse diferença. A tabela única deixa a leitura do painel mais simples e rápida.

Os principais campos da tabela são:

| Campo | Tipo | Descrição |
|---|---|---|
| `ano_eleicao` | `SMALLINT` | Ano da eleição (2022) |
| `sg_uf` | `CHAR(2)` | Estado |
| `ds_cargo` | `VARCHAR(60)` | Cargo disputado |
| `ds_genero` | `VARCHAR(30)` | Gênero do candidato |
| `ds_cor_raca` | `VARCHAR(30)` | Cor/raça declarada |
| `faixa_etaria` | `VARCHAR(20)` | Faixa de idade no ano da eleição |
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

As principais tecnologias utilizadas foram Terraform para a infraestrutura, PostgreSQL para armazenar os dados, Python com Pandas para o tratamento e a carga, e Streamlit com Plotly para o painel.

## Dashboard

O painel está em `dashboard/app.py` e foi feito com Streamlit. Ele lê a tabela direto do PostgreSQL uma vez e guarda em cache por 10 minutos, então os filtros respondem na hora sem consultar o banco a cada clique.

O que o painel oferece:

- **Quatro indicadores no topo:** candidaturas, eleitos, taxa de eleição e receita média por candidatura, todos recalculados conforme os filtros;
- **Filtros cruzados na barra lateral:** ano, estado, cargo, gênero, cor/raça e faixa etária;
- **Seletor de métrica:** alterna os gráficos entre receita média, receita total e taxa de eleição;
- **Gráficos:** comparação por gênero e cor/raça, relação entre financiamento e taxa de eleição, e comparação por faixa etária;
- **Detalhamento:** tabela com cada grupo e todos os valores, para olhar um segmento específico.

## Segurança e LGPD

As credenciais devem ficar fora do repositório. O token da Aiven fica no arquivo `terraform.tfvars`, que não deve ser enviado ao Git. O repositório contém apenas o exemplo `terraform.tfvars.example`, sem os valores reais.

A senha de acesso ao banco fica no arquivo `.env`, e o código lê essa informação quando precisa se conectar. No Streamlit Cloud, a mesma informação vai nos Secrets da plataforma, e o repositório tem só o modelo `.streamlit/secrets.toml.example`. O `.gitignore` lista esses arquivos, os estados do Terraform e os dados brutos para que não sejam adicionados ao Git por engano.

Para reduzir a exposição de dados pessoais, CPF, nome, e-mail e título de eleitor são removidos durante o ETL e não chegam à tabela final. Como a análise é feita por grupos, não precisamos manter esses dados pessoais.

## Como executar o projeto

Para executar o projeto, é necessário ter Python 3, Terraform e uma conta na Aiven com um token de acesso. Todos os comandos abaixo são rodados a partir da pasta principal do projeto, exceto os do Terraform.

Primeiro, instale as bibliotecas usadas pelo projeto:

```bash
pip install -r requirements.txt
```

### 1. Criar o banco com Terraform

Entre na pasta `terraform`, copie o arquivo de exemplo e preencha as informações solicitadas:

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
```

Depois, execute os comandos e volte para a pasta principal:

```bash
terraform init
terraform apply
cd ..
```

### 2. Baixar os dados do TSE

Baixe os arquivos de candidatos, receitas e despesas contratadas referentes a 2022 no site de dados abertos do TSE. Extraia os arquivos na pasta `dados/`. Eles não ficam no repositório porque ocupam bastante espaço.

### 3. Executar o ETL

Rode o comando abaixo para tratar e agregar os dados. O `saida_agregado.csv` é gerado na pasta principal:

```bash
python etl/etl.py --candidatos dados/consulta_cand_2022/consulta_cand_2022_BRASIL.csv --receitas dados/prestacao_de_contas_eleitorais_candidatos_2022/receitas_candidatos_2022_BRASIL.csv --despesas dados/prestacao_de_contas_eleitorais_candidatos_2022/despesas_contratadas_candidatos_2022_BRASIL.csv
```

### 4. Carregar os dados no banco

Crie o arquivo `.env` na pasta principal com a variável `DATABASE_URL`. A URL de conexão pode ser obtida com o comando `terraform output -raw pg_service_uri`, rodado dentro da pasta `terraform`. Em seguida, execute:

```bash
python etl/load.py
```

### 5. Conferir a carga

Para verificar se os dados foram carregados corretamente, execute:

```bash
python etl/testa_banco.py
```

### 6. Abrir o painel

```bash
python -m streamlit run dashboard/app.py
```

O painel abre no navegador em `localhost:8501`.

### 7. Publicar no Streamlit Cloud

Com o repositório no GitHub, entre em share.streamlit.io, crie um app apontando para este repositório e use `dashboard/app.py` como arquivo principal. Em **Settings > Secrets**, cole a linha do `.streamlit/secrets.toml.example` trocando pela URL real do banco.

O banco gratuito da Aiven desliga depois de um tempo sem uso. Se o painel mostrar erro de conexão, ligue o serviço no console da Aiven e recarregue a página.

## Arquivos do projeto

```
etl/
  etl.py            tratamento e agregação dos dados
  load.py           carga da base tratada no banco
  testa_banco.py    confere a carga lendo o banco
  conferir.py       usado no começo para ver as colunas dos arquivos
dashboard/
  app.py            painel em Streamlit
terraform/          arquivos que criam o banco na Aiven
.streamlit/
  secrets.toml.example   modelo dos secrets para o Streamlit Cloud
saida_agregado.csv  base tratada e agregada
requirements.txt    bibliotecas do projeto
.gitignore          arquivos que não devem ir para o repositório
```
