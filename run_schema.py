import argparse
import os
import sys
from pathlib import Path

try:
    import psycopg2
except ImportError:
    sys.exit(
        "Erro: a biblioteca 'psycopg2-binary' não está instalada.\n"
        "Instale com: pip install psycopg2-binary python-dotenv"
    )

try:
    from dotenv import load_dotenv
except ImportError:
    sys.exit(
        "Erro: a biblioteca 'python-dotenv' não está instalada.\n"
        "Instale com: pip install psycopg2-binary python-dotenv"
    )


def carregar_configuracao(env_file: str) -> dict:
    """Carrega as variáveis do .env e valida se todas estão presentes."""
    if not Path(env_file).exists():
        sys.exit(f"Erro: arquivo de ambiente '{env_file}' não encontrado.")

    load_dotenv(dotenv_path=env_file)

    variaveis_obrigatorias = ["DB_HOST", "DB_PORT", "DB_NAME", "DB_USER", "DB_PASSWORD"]
    config = {var: os.getenv(var) for var in variaveis_obrigatorias}

    faltando = [var for var, valor in config.items() if not valor]
    if faltando:
        sys.exit(
            "Erro: as seguintes variáveis não foram encontradas no "
            f"'{env_file}': {', '.join(faltando)}"
        )

    return config


def executar_schema(config: dict, schema_path: str) -> None:
    """Conecta ao PostgreSQL e executa o conteúdo do arquivo schema.sql."""
    caminho = Path(schema_path)
    if not caminho.exists():
        sys.exit(f"Erro: arquivo de schema '{schema_path}' não encontrado.")

    sql = caminho.read_text(encoding="utf-8")
    if not sql.strip():
        sys.exit(f"Erro: o arquivo '{schema_path}' está vazio.")

    print(f"Conectando ao banco '{config['DB_NAME']}' em {config['DB_HOST']}:{config['DB_PORT']}...")

    conn = None
    try:
        conn = psycopg2.connect(
            host=config["DB_HOST"],
            port=config["DB_PORT"],
            dbname=config["DB_NAME"],
            user=config["DB_USER"],
            password=config["DB_PASSWORD"],
        )
        conn.autocommit = False

        with conn.cursor() as cur:
            print(f"Executando '{schema_path}'...")
            cur.execute(sql)

        conn.commit()
        print("Schema executado com sucesso! Tabelas criadas/atualizadas.")

    except psycopg2.Error as erro:
        if conn:
            conn.rollback()
        sys.exit(f"Erro ao executar o schema (rollback realizado): {erro}")

    finally:
        if conn:
            conn.close()


def main():
    parser = argparse.ArgumentParser(
        description="Executa um arquivo .sql para criar tabelas no PostgreSQL usando credenciais de um .env"
    )
    parser.add_argument(
        "--schema",
        default="schema.sql",
        help="Caminho do arquivo .sql a ser executado (padrão: schema.sql)",
    )
    parser.add_argument(
        "--env-file",
        default=".env",
        help="Caminho do arquivo .env com as credenciais (padrão: .env)",
    )
    args = parser.parse_args()

    config = carregar_configuracao(args.env_file)
    executar_schema(config, args.schema)


if __name__ == "__main__":
    main()