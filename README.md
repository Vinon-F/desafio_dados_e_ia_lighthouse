# Desafio Lighthouse — Indicium AI

desafio_dados_e_ia_lighthouse/
├── csv/                              # CSVs de origem (dados carregados no banco)
│
├── elt/                              # Extract-Load-Transform
│   ├── schema_generator.py           # Gera schema.sql a partir dos CSVs
│   ├── run_schema.py                 # Executa o schema.sql no PostgreSQL
│   ├── data_loader.py                # Carrega os CSVs nas tabelas
│   └── schema.sql                    # DDL gerado (CREATE TABLE ...)
│
├── modeling/                         # Modelagem preditiva e recomendação
│   ├── forecasting.py                # Previsão de demanda
│   └── recommendation_engine.py      # Similaridade de cosseno entre produtos
│
├── sql/
│   ├── analisys/                     # Consultas de análise de negócio
│   │   ├── 1_1_overview_orders.sql
│   │   ├── 3_2_sum_lines_validation.sql
│   │   ├── 4_1_clients_analysis.sql
│   │   └── 5_1_calendar_sales.sql
│   └── views/                        # Views que alimentam o dashboard de BI
│
├── .env.exemple                      # Modelo de variáveis de ambiente
├── .gitignore
├── docker-compose.yml                # Sobe o PostgreSQL local
└── requirements.txt                  # Dependências Python

## Como rodar o projeto

### 1. Pré-requisitos

- Docker e Docker Compose
- Python 3.10+
- `pip`

### 2. Clonar o repositório

```bash
git clone <https://github.com/Vinon-F/desafio_dados_e_ia_lighthouse>
cd desafio_dados_e_ia_lighthouse
```

Os CSVs de origem já estão inclusos na pasta `csv/`.

### 3. Configurar variáveis de ambiente

```bash
cp .env.exemple .env
```

Se quiser, edite o `.env` e ajuste `DB_USER`/`DB_PASSWORD`. Se alterar, replique os mesmos valores no `docker-compose.yml` (`POSTGRES_USER` e `POSTGRES_PASSWORD`).

### 4. Subir o banco de dados

```bash
docker compose up -d
```

Verifique se o container subiu corretamente:

```bash
docker compose ps
```

### 5. Instalar as dependências Python

```bash
python -m venv .venv
source .venv/bin/activate       # Linux/macOS
.venv\Scripts\activate          # Windows

pip install -r requirements.txt
```

### 6. Gerar o schema a partir dos CSVs

```bash
python schema_generator.py
```

Isso gera/atualiza o arquivo `schema.sql`.

### 7. Criar as tabelas no banco

```bash
python run_schema.py
```

### 8. Carregar os dados nas tabelas

```bash
python data_loader.py
```

### 9. Executar as análises SQL

As consultas estão na pasta `sql_questões/`. Execute com `psql` ou o cliente SQL de sua preferência:

```bash
psql "postgresql://seu_user_aqui:sua_senha_aqui@localhost:5432/db_lighthouse" -f sql_questões/4_1_clients_analysis.sql
```

Repita o comando trocando o nome do arquivo para as demais consultas (`1_1_overview_orders.sql`, `3_2_sum_lines_validation.sql`, `5_1_calendar_sales.sql`).

### 10. Rodar a previsão de demanda

```bash
python forecasting.py
```

### 11. Rodar o motor de recomendação

Requer que os passos 7 e 8 já tenham sido executados (banco populado).

```bash
python recommendation_engine.py
```