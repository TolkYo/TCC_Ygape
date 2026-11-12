"""Carrega as tabelas do SQLite (`hidrowize.db`) no PostgreSQL/PostGIS (`ygape-db`).

Estratégia hibrida (opcao C): a coleta continua gravando no SQLite; este ETL faz o
espelho dos dados no PostGIS. Como o SQLite e reconstruido pelo `gerar_sqlite.py`, cada
tabela e recarregada por inteiro (DROP + CREATE + COPY), o que e idempotente.

Uso:
    python carregar_postgis.py                              # tabelas principais
    python carregar_postgis.py --tabelas cotas_diarias,nivel_semanal
    python carregar_postgis.py --todas                      # inclui satelite/batimetria
    python carregar_postgis.py --limite 1000                # amostra (teste)

Credenciais lidas do `.env` (HIDROWIZE_PG_HOST/PORT/DB/USER/PASSWORD).
"""
from __future__ import annotations

import argparse
import csv
import os
import sqlite3
import sys
import tempfile
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

APP_DIR = Path(__file__).resolve().parent.parent
load_dotenv(APP_DIR / ".env")

SQLITE_PADRAO = APP_DIR / "data" / "hidrowize.db"

# Tabelas relevantes para o app/roteamento.
PRINCIPAIS = [
    "estacoes",
    "estacoes_trechos",
    "cotas_historicas",
    "cotas_diarias",
    "nivel_semanal",
    "telemetria",
    "trechos_navegaveis",
    "cota_fundo_trecho",
    "rios",
    "navegabilidade",
    "decretos",
    "estacoes_virtuais",
]
# Tabelas grandes de satelite/batimetria (so com --todas).
GRANDES = ["batimetria_sicflow", "series_nivel_satelite", "series_vazao_satelite"]

COL_GEOM = "geom_wkb"
SRID = 4326


def pg_type(tipo: str) -> str:
    u = (tipo or "").upper()
    if "INT" in u:
        return "bigint"
    if any(k in u for k in ("REAL", "FLOA", "DOUB")):
        return "double precision"
    if "BLOB" in u:
        return "bytea"
    if any(k in u for k in ("NUM", "DEC")):
        return "numeric"
    return "text"


def _quote(names: list[str]) -> str:
    return ", ".join('"' + n + '"' for n in names)


def conectar():
    return psycopg2.connect(
        host=os.getenv("HIDROWIZE_PG_HOST", "127.0.0.1"),
        port=os.getenv("HIDROWIZE_PG_PORT", "5432"),
        dbname=os.getenv("HIDROWIZE_PG_DB", "ygape"),
        user=os.getenv("HIDROWIZE_PG_USER", "ygape"),
        password=os.getenv("HIDROWIZE_PG_PASSWORD", ""),
    )


def carregar_tabela(sqlite_con, pg_cur, tabela: str, limite: int | None = None) -> int:
    info = sqlite_con.execute(f'PRAGMA table_info("{tabela}")').fetchall()
    if not info:
        raise SystemExit(f"Tabela inexistente no SQLite: {tabela}")

    tem_geom = any(c[1] == COL_GEOM for c in info)
    normal = [(c[1], pg_type(c[2])) for c in info if c[1] != COL_GEOM]
    pk = [c[1] for c in info if c[5]]

    pg_cur.execute(f'DROP TABLE IF EXISTS "{tabela}" CASCADE')
    ddl = [f'"{n}" {tp}' for n, tp in normal]
    if pk:
        ddl.append("PRIMARY KEY (" + _quote(pk) + ")")
    if tem_geom:
        ddl.append(f'"geom" geometry(Geometry,{SRID})')
        ddl.append('"_geom_hex" text')
    pg_cur.execute(f'CREATE TABLE "{tabela}" (' + ", ".join(ddl) + ")")

    cols = [n for n, _ in normal]
    select_cols = cols + ([COL_GEOM] if tem_geom else [])
    copy_cols = cols + (["_geom_hex"] if tem_geom else [])

    sql = f'SELECT {_quote(select_cols)} FROM "{tabela}"'
    if limite:
        sql += f" LIMIT {int(limite)}"

    total = 0
    with tempfile.TemporaryFile(mode="w+", newline="", encoding="utf-8") as tmp:
        writer = csv.writer(tmp, lineterminator="\n")
        for row in sqlite_con.execute(sql):
            valores = []
            for i, valor in enumerate(row):
                if tem_geom and select_cols[i] == COL_GEOM:
                    valores.append("" if valor is None else bytes(valor).hex())
                else:
                    valores.append("" if valor is None else valor)
            writer.writerow(valores)
            total += 1
        tmp.seek(0)
        pg_cur.copy_expert(
            f'COPY "{tabela}" ({_quote(copy_cols)}) FROM STDIN WITH (FORMAT csv, NULL \'\')',
            tmp,
        )

    if tem_geom:
        pg_cur.execute(
            f'UPDATE "{tabela}" SET "geom" = '
            f'ST_SetSRID(ST_GeomFromWKB(decode("_geom_hex", \'hex\')), {SRID}) '
            f'WHERE "_geom_hex" IS NOT NULL AND "_geom_hex" <> \'\''
        )
        pg_cur.execute(f'ALTER TABLE "{tabela}" DROP COLUMN "_geom_hex"')
        pg_cur.execute(f'CREATE INDEX "idx_{tabela}_geom" ON "{tabela}" USING GIST ("geom")')

    if tabela == "telemetria":
        pg_cur.execute(f'CREATE INDEX "idx_telemetria_estacao" ON "telemetria" ("codigo_estacao")')
    elif tabela == "trechos_navegaveis":
        pg_cur.execute(f'CREATE INDEX "idx_trechos_origem" ON "trechos_navegaveis" ("noorigem")')
        pg_cur.execute(f'CREATE INDEX "idx_trechos_destino" ON "trechos_navegaveis" ("nodestino")')
    elif tabela == "estacoes_trechos":
        pg_cur.execute(f'CREATE INDEX "idx_est_trechos_fid" ON "estacoes_trechos" ("fid_trecho")')

    return total


def main() -> int:
    parser = argparse.ArgumentParser(description="Espelha o hidrowize.db no PostGIS (ygape-db)")
    parser.add_argument("--tabelas", help="Lista separada por virgula (default: principais)")
    parser.add_argument("--todas", action="store_true", help="Inclui satelite/batimetria")
    parser.add_argument("--limite", type=int, help="Limita linhas por tabela (teste)")
    parser.add_argument("--sqlite", default=str(SQLITE_PADRAO), help="Caminho do SQLite")
    args = parser.parse_args()

    if args.tabelas:
        tabelas = [t.strip() for t in args.tabelas.split(",") if t.strip()]
    elif args.todas:
        tabelas = PRINCIPAIS + GRANDES
    else:
        tabelas = PRINCIPAIS

    sqlite_con = sqlite3.connect(f"file:{args.sqlite}?mode=ro", uri=True)
    pg = conectar()
    pg.autocommit = False
    cur = pg.cursor()
    cur.execute("CREATE EXTENSION IF NOT EXISTS postgis")

    for tabela in tabelas:
        n = carregar_tabela(sqlite_con, cur, tabela, args.limite)
        print(f"  -> {tabela}: {n} linhas carregadas", flush=True)

    pg.commit()
    print("--- verificacao no Postgres ---")
    for tabela in tabelas:
        cur.execute(f'SELECT count(*) FROM "{tabela}"')
        print(f"  [pg] {tabela}: {cur.fetchone()[0]}")

    cur.close()
    pg.close()
    sqlite_con.close()
    print("ETL_DONE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
