"""Conexao PostgreSQL/PostGIS compartilhada (banco `ygape`).

As credenciais vem do `.env` (HIDROWIZE_PG_HOST/PORT/DB/USER/PASSWORD).
Usado pela API (`main.py`), pelo motor de roteamento (`routing_engine.py`) e
pelo criador de administrador (`criar_admin.py`).
"""
from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")


def pg_config() -> dict:
    return {
        "host": os.getenv("HIDROWIZE_PG_HOST", "127.0.0.1"),
        "port": os.getenv("HIDROWIZE_PG_PORT", "5432"),
        "dbname": os.getenv("HIDROWIZE_PG_DB", "ygape"),
        "user": os.getenv("HIDROWIZE_PG_USER", "ygape"),
        "password": os.getenv("HIDROWIZE_PG_PASSWORD", ""),
    }


@contextmanager
def connection():
    con = psycopg2.connect(**pg_config(), cursor_factory=psycopg2.extras.RealDictCursor)
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
  id SERIAL PRIMARY KEY, nome TEXT NOT NULL, email TEXT NOT NULL UNIQUE,
  senha_hash TEXT NOT NULL, papel TEXT NOT NULL CHECK (papel IN ('admin','piloto')),
  ativo BOOLEAN NOT NULL DEFAULT TRUE, criado_em TIMESTAMP NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS rotas (
  id SERIAL PRIMARY KEY, usuario_id INTEGER REFERENCES usuarios(id),
  origem_nome TEXT NOT NULL, destino_nome TEXT NOT NULL,
  calado_m NUMERIC NOT NULL, margem_seguranca_m NUMERIC NOT NULL DEFAULT 0.5,
  velocidade_embarcacao_kmh NUMERIC NOT NULL DEFAULT 20,
  distancia_total_km NUMERIC NOT NULL, tempo_total_h NUMERIC NOT NULL, custo_total NUMERIC NOT NULL,
  trechos_criticos INTEGER NOT NULL DEFAULT 0, profundidade_minima_m NUMERIC,
  rota_geojson JSONB, monitorar BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMP NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_rota_usuario ON rotas(usuario_id);
CREATE TABLE IF NOT EXISTS log_eventos (
  id SERIAL PRIMARY KEY, usuario_id INTEGER, tipo TEXT NOT NULL, detalhe TEXT,
  data_hora TIMESTAMP NOT NULL DEFAULT now()
);
-- Fase 5b: monitoramento de rota
ALTER TABLE rotas ADD COLUMN IF NOT EXISTS limiar_cm NUMERIC NOT NULL DEFAULT 30;
ALTER TABLE rotas ADD COLUMN IF NOT EXISTS cooldown_min INTEGER NOT NULL DEFAULT 30;
ALTER TABLE rotas ADD COLUMN IF NOT EXISTS estacao_referencia TEXT;
ALTER TABLE rotas ADD COLUMN IF NOT EXISTS nivel_baseline_cm NUMERIC;
ALTER TABLE rotas ADD COLUMN IF NOT EXISTS ultima_verificacao TIMESTAMP;
ALTER TABLE rotas ADD COLUMN IF NOT EXISTS ultima_recomputacao TIMESTAMP;
ALTER TABLE rotas ADD COLUMN IF NOT EXISTS fids_rota JSONB;
CREATE TABLE IF NOT EXISTS rota_alteracao (
  id SERIAL PRIMARY KEY,
  rota_id INTEGER NOT NULL REFERENCES rotas(id) ON DELETE CASCADE,
  data_alteracao TIMESTAMP NOT NULL DEFAULT now(),
  motivo TEXT NOT NULL,
  variacao_nivel_cm NUMERIC,
  estacao_origem TEXT,
  distancia_total_km NUMERIC,
  custo_total NUMERIC,
  rota_geojson JSONB
);
CREATE INDEX IF NOT EXISTS idx_rota_alteracao ON rota_alteracao(rota_id);
"""


def ensure_schema() -> None:
    with connection() as con:
        with con.cursor() as cur:
            cur.execute(SCHEMA)
