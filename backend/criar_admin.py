"""Cria o primeiro administrador local da API HidroWize.

Exemplo:
  python criar_admin.py --nome "Administrador" --email admin@hidrowize.local
"""
from __future__ import annotations

import argparse
import getpass
import os
import sqlite3
from pathlib import Path

from main import AUTH_DB, password_hash


def main() -> None:
    parser = argparse.ArgumentParser(description="Cria ou atualiza um administrador da API")
    parser.add_argument("--nome", required=True)
    parser.add_argument("--email", required=True)
    parser.add_argument("--senha", help="Evite usar em shell compartilhado; sem ela a senha é solicitada.")
    args = parser.parse_args()
    senha = args.senha or getpass.getpass("Senha do administrador: ")
    if len(senha) < 8:
        parser.error("A senha deve ter ao menos 8 caracteres.")

    AUTH_DB.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(AUTH_DB) as con:
        con.execute("""CREATE TABLE IF NOT EXISTS usuarios (
          id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT NOT NULL, email TEXT NOT NULL UNIQUE,
          senha_hash TEXT NOT NULL, papel TEXT NOT NULL CHECK(papel IN ('admin','piloto')),
          ativo INTEGER NOT NULL DEFAULT 1, criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )""")
        con.execute("""INSERT INTO usuarios(nome,email,senha_hash,papel,ativo) VALUES(?,?,?,?,1)
          ON CONFLICT(email) DO UPDATE SET nome=excluded.nome, senha_hash=excluded.senha_hash,
          papel='admin', ativo=1""", (args.nome.strip(), args.email.strip().lower(), password_hash(senha), "admin"))
    print(f"Administrador disponível em {AUTH_DB}")


if __name__ == "__main__":
    main()
