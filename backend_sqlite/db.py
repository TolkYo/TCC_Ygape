"""Camada SQLite da cópia local da API Ygape."""
from __future__ import annotations

import json
import os
import re
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
DB_PATH = Path(os.getenv("HIDROWIZE_SQLITE_PATH", ROOT / "data" / "hidrowize.db"))


def pg_config() -> dict:
    """Compatibilidade com chamadas legadas; informa a base SQLite local."""
    return {"database": str(DB_PATH)}


def _sql(sql: str) -> str:
    sql = sql.replace("%s", "?")
    sql = re.sub(r"\bILIKE\b", "LIKE", sql, flags=re.IGNORECASE)
    sql = re.sub(r"\bTRUE\b", "1", sql, flags=re.IGNORECASE)
    sql = re.sub(r"\bFALSE\b", "0", sql, flags=re.IGNORECASE)
    sql = re.sub(r"([A-Za-z_][A-Za-z0-9_]*)::text", r"CAST(\1 AS TEXT)", sql)
    return sql.replace("now()", "CURRENT_TIMESTAMP")


def _value(value):
    if hasattr(value, "adapted"):
        value = value.adapted
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, bool):
        return int(value)
    return value


class Cursor:
    def __init__(self, cursor: sqlite3.Cursor):
        self._cursor = cursor

    def execute(self, sql: str, params=()):
        self._cursor.execute(_sql(sql), tuple(_value(value) for value in params))
        return self

    def fetchone(self):
        row = self._cursor.fetchone()
        return self._row(row) if row is not None else None

    def fetchall(self):
        return [self._row(row) for row in self._cursor.fetchall()]

    @staticmethod
    def _row(row):
        result = dict(row)
        for key in ("rota_geojson", "fids_rota"):
            if isinstance(result.get(key), str):
                try:
                    result[key] = json.loads(result[key])
                except json.JSONDecodeError:
                    pass
        return result

    @property
    def rowcount(self):
        return self._cursor.rowcount

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self._cursor.close()


class Connection:
    def __init__(self, connection: sqlite3.Connection):
        self._connection = connection

    def cursor(self):
        return Cursor(self._connection.cursor())

    def commit(self):
        self._connection.commit()

    def rollback(self):
        self._connection.rollback()

    def close(self):
        self._connection.close()


@contextmanager
def connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    raw = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False)
    raw.row_factory = sqlite3.Row
    raw.execute("PRAGMA foreign_keys = ON")
    con = Connection(raw)
    try:
        yield con
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


SCHEMA = """
CREATE TABLE IF NOT EXISTS usuarios (
  id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT NOT NULL, email TEXT NOT NULL UNIQUE,
  senha_hash TEXT NOT NULL, papel TEXT NOT NULL CHECK (papel IN ('admin','piloto')),
  ativo INTEGER NOT NULL DEFAULT 1, criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS rotas (
  id INTEGER PRIMARY KEY AUTOINCREMENT, usuario_id INTEGER REFERENCES usuarios(id),
  origem_nome TEXT NOT NULL, destino_nome TEXT NOT NULL,
  calado_m REAL NOT NULL, margem_seguranca_m REAL NOT NULL DEFAULT 0.5,
  velocidade_embarcacao_kmh REAL NOT NULL DEFAULT 20,
  distancia_total_km REAL NOT NULL, tempo_total_h REAL NOT NULL, custo_total REAL NOT NULL,
  trechos_criticos INTEGER NOT NULL DEFAULT 0, profundidade_minima_m REAL,
  rota_geojson TEXT, monitorar INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  limiar_cm REAL NOT NULL DEFAULT 30, cooldown_min INTEGER NOT NULL DEFAULT 30,
  estacao_referencia TEXT, nivel_baseline_cm REAL, ultima_verificacao TEXT,
  ultima_recomputacao TEXT, fids_rota TEXT
);
CREATE INDEX IF NOT EXISTS idx_rota_usuario ON rotas(usuario_id);
CREATE TABLE IF NOT EXISTS log_eventos (
  id INTEGER PRIMARY KEY AUTOINCREMENT, usuario_id INTEGER, tipo TEXT NOT NULL,
  detalhe TEXT, data_hora TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS rota_alteracao (
  id INTEGER PRIMARY KEY AUTOINCREMENT, rota_id INTEGER NOT NULL REFERENCES rotas(id) ON DELETE CASCADE,
  data_alteracao TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, motivo TEXT NOT NULL,
  variacao_nivel_cm REAL, estacao_origem TEXT, distancia_total_km REAL,
  custo_total REAL, rota_geojson TEXT
);
CREATE INDEX IF NOT EXISTS idx_rota_alteracao ON rota_alteracao(rota_id);
"""


def ensure_schema() -> None:
    with connection() as con:
        con._connection.executescript(SCHEMA)
