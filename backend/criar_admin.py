"""Cria o primeiro administrador da API HidroWize (banco PostgreSQL `ygape`).

Exemplo:
  python criar_admin.py --nome "Administrador" --email admin@hidrowize.local
"""
from __future__ import annotations

import argparse
import getpass

from db import connection, ensure_schema
from main import password_hash


def main() -> None:
    parser = argparse.ArgumentParser(description="Cria ou atualiza um administrador da API")
    parser.add_argument("--nome", required=True)
    parser.add_argument("--email", required=True)
    parser.add_argument("--senha", help="Evite usar em shell compartilhado; sem ela a senha é solicitada.")
    args = parser.parse_args()
    senha = args.senha or getpass.getpass("Senha do administrador: ")
    if len(senha) < 8:
        parser.error("A senha deve ter ao menos 8 caracteres.")

    ensure_schema()
    with connection() as con:
        with con.cursor() as cur:
            cur.execute(
                """INSERT INTO usuarios(nome,email,senha_hash,papel,ativo) VALUES (%s,%s,%s,'admin',TRUE)
                ON CONFLICT (email) DO UPDATE SET nome=EXCLUDED.nome, senha_hash=EXCLUDED.senha_hash,
                papel='admin', ativo=TRUE""",
                (args.nome.strip(), args.email.strip().lower(), password_hash(senha)),
            )
    print(f"Administrador '{args.email.strip().lower()}' disponível.")


if __name__ == "__main__":
    main()
