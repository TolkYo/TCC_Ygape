"""Gera a navegabilidade SEMANAL por trecho (camada 2) — fonte de nível: satélite.

Combina:
  - series_nivel_satelite  -> nível d'agua por estacao virtual (m, rel. geoide)
  - estacoes_virtuais      -> lat/lon das estacoes virtuais (HYDROWEB)
  - cota_fundo_trecho      -> cota de fundo por trecho (m, SICFLOW/AHGN)
  - trechos_navegaveis     -> centroide (associa o trecho as estacoes proximas)

Nivel por trecho: entre as `--vizinhos` estacoes virtuais mais proximas, usa a
primeira que tenha observacao na janela de +-`--janela-dias` em torno da semana
(media). Como o SWOT revisita ~21-27 dias, a janela evita buracos. A cota de
fundo e a do SICFLOW estao no mesmo referencial (m rel. geoide), entao
`profundidade = nivel_m - cota_fundo_m` e datum-consistente.

Regra (RN022 + RN029 + RN012):
  profundidade_m = nivel_m - cota_fundo_m
  folga_m        = profundidade_m - calado_ref_m
  status = NAVEGAVEL se profundidade_m >= calado + margem
           RESTRITO  se calado <= profundidade_m < calado + margem
           CRITICO   se profundidade_m < calado
           SEM_DADOS quando nao ha nivel dentro do raio/janela ou cota de fundo

RESSALVA: a janela agrega observacoes de +-N dias (nao e medicao semanal exata).
Para rios < ~100 m o SWOT nao alcanca (trecho fica SEM_DADOS).

Uso:
    python gerar_navegabilidade_semanal.py
    python gerar_navegabilidade_semanal.py --calado 10 --desde 2025-01-01
    python gerar_navegabilidade_semanal.py --tudo
"""

from __future__ import annotations

import argparse
import os
import sqlite3
import sys
import time
from datetime import date, datetime, timedelta

import numpy as np

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PADRAO = os.path.join(RAIZ, "data", "hidrowize.db")

RAIO_TERRA_M = 6371000.0
BLOCO_VIZINHOS = 1000
LOTE = 20000

SQL_TABELA = """
CREATE TABLE IF NOT EXISTS naveg_trecho_semanal (
    fid              INTEGER NOT NULL,
    semana_inicio    TEXT NOT NULL,
    codigo_estacao   TEXT,
    distancia_km     REAL,
    nivel_m          REAL,
    cota_fundo_m     REAL,
    fonte_cota_fundo TEXT,
    profundidade_m   REAL,
    calado_ref_m     REAL,
    folga_m          REAL,
    status           TEXT,
    fonte_nivel      TEXT,
    PRIMARY KEY (fid, semana_inicio)
);
CREATE INDEX IF NOT EXISTS idx_naveg_sem_data ON naveg_trecho_semanal (semana_inicio);
CREATE INDEX IF NOT EXISTS idx_naveg_sem_status ON naveg_trecho_semanal (status);
"""


def carregar_estacoes_virtuais(con: sqlite3.Connection):
    rows = con.execute(
        "SELECT codigo, latitude, longitude FROM estacoes_virtuais "
        "WHERE latitude IS NOT NULL AND longitude IS NOT NULL"
    ).fetchall()
    codigos = [r[0] for r in rows]
    lat = np.radians(np.array([r[1] for r in rows], dtype=float))
    lon = np.radians(np.array([r[2] for r in rows], dtype=float))
    return codigos, lat, lon, {c: i for i, c in enumerate(codigos)}


def carregar_trechos(con: sqlite3.Connection):
    rows = con.execute(
        "SELECT fid, centroid_lon, centroid_lat FROM trechos_navegaveis "
        "WHERE centroid_lon IS NOT NULL AND centroid_lat IS NOT NULL"
    ).fetchall()
    fids = np.array([r[0] for r in rows], dtype=np.int64)
    lon = np.radians(np.array([r[1] for r in rows], dtype=float))
    lat = np.radians(np.array([r[2] for r in rows], dtype=float))
    return fids, lat, lon


def carregar_cota_fundo(con: sqlite3.Connection, fids: np.ndarray):
    mapa: dict[int, tuple[float, str]] = {}
    for fid, obs, est in con.execute(
        "SELECT fid, cota_fundo_observada, cota_fundo_estimada FROM cota_fundo_trecho"
    ):
        if obs is not None:
            mapa[int(fid)] = (float(obs), "observada")
        elif est is not None:
            mapa[int(fid)] = (float(est), "estimada")
    cota = np.full(len(fids), np.nan)
    fonte = np.full(len(fids), "", dtype=object)
    for i, fid in enumerate(fids):
        v = mapa.get(int(fid))
        if v is not None:
            cota[i] = v[0]
            fonte[i] = v[1]
    return cota, fonte


def k_vizinhos(t_lat, t_lon, s_lat, s_lon, k: int):
    """k estacoes virtuais mais proximas (haversine) por trecho.

    Tudo em float32 e em blocos pequenos para caber numa VPS de 1 GB.
    """
    n = len(t_lat)
    idx = np.full((n, k), -1, dtype=np.int32)
    dist = np.full((n, k), np.nan, dtype=np.float32)
    s_lat32 = s_lat.astype(np.float32)
    s_lon32 = s_lon.astype(np.float32)
    cos_s = np.cos(s_lat32).astype(np.float32)
    for i0 in range(0, n, BLOCO_VIZINHOS):
        i1 = min(i0 + BLOCO_VIZINHOS, n)
        tla = t_lat[i0:i1].astype(np.float32)
        tlo = t_lon[i0:i1].astype(np.float32)
        cos_t = np.cos(tla).astype(np.float32)
        dlat = tla[:, None] - s_lat32[None, :]
        dlon = tlo[:, None] - s_lon32[None, :]
        a = np.sin(dlat / 2) ** 2 + cos_t[:, None] * cos_s[None, :] * np.sin(dlon / 2) ** 2
        d = (2 * RAIO_TERRA_M * np.arcsin(np.clip(np.sqrt(a), 0.0, 1.0)) / 1000.0).astype(np.float32)
        m = min(k, d.shape[1])
        part = np.argpartition(d, m - 1, axis=1)[:, :m]
        lin = np.arange(i1 - i0)[:, None]
        part = part[lin, np.argsort(d[lin, part], axis=1)]
        idx[i0:i1] = part
        dist[i0:i1] = d[lin, part]
    return idx, dist


def _segunda(data_iso: str) -> date | None:
    try:
        d = datetime.strptime(data_iso[:10], "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None
    return d - timedelta(days=d.weekday())


def montar_niveis(con: sqlite3.Connection, cod_idx: dict, janela_dias: int):
    """Matriz (semanas x estacoes) com nivel medio (m) na janela de +-N dias.

    Le as observacoes em streaming (sem carregar as 590 mil linhas de uma vez).
    """
    cur = con.execute(
        "SELECT codigo, data, nivel_m FROM series_nivel_satelite "
        "WHERE nivel_m IS NOT NULL AND data IS NOT NULL"
    )

    acumulado: dict[tuple[str, int], list[float]] = {}
    offsets = range(-2, 3)
    for cod, data_iso, nivel in cur:
        si = cod_idx.get(cod)
        if si is None:
            continue
        base = _segunda(data_iso)
        if base is None:
            continue
        d = datetime.strptime(data_iso[:10], "%Y-%m-%d").date()
        for off in offsets:
            segunda = base + timedelta(weeks=off)
            if abs((d - (segunda + timedelta(days=3))).days) > janela_dias:
                continue
            chave = (segunda.isoformat(), si)
            v = acumulado.setdefault(chave, [0.0, 0.0])
            v[0] += float(nivel)
            v[1] += 1

    semanas = sorted({k[0] for k in acumulado})
    matriz = np.full((len(semanas), len(cod_idx)), np.nan, dtype=np.float32)
    sem_idx = {s: i for i, s in enumerate(semanas)}
    for (semana, si), (soma, n) in acumulado.items():
        matriz[sem_idx[semana], si] = soma / n
    return semanas, matriz


def classificar(prof: np.ndarray, calado: float, margem: float) -> np.ndarray:
    status = np.full(prof.shape, "SEM_DADOS", dtype=object)
    valid = ~np.isnan(prof)
    naveg = valid & (prof >= calado + margem)
    restr = valid & (~naveg) & (prof >= calado)
    crit = valid & (~naveg) & (~restr)
    status[naveg] = "NAVEGAVEL"
    status[restr] = "RESTRITO"
    status[crit] = "CRITICO"
    return status


def main() -> None:
    ap = argparse.ArgumentParser(description="Navegabilidade semanal por trecho (nível satélite)")
    ap.add_argument("--db", default=DB_PADRAO)
    ap.add_argument("--calado", type=float, default=6.0,
                    help="Calado de referencia em metros (RN029; default 6 = Solimoes)")
    ap.add_argument("--margem", type=float, default=0.5, help="Margem de seguranca (RN012)")
    ap.add_argument("--raio-km", type=float, default=50.0, help="Raio maximo trecho-estacao")
    ap.add_argument("--vizinhos", type=int, default=5, help="Estacoes virtuais candidatas por trecho")
    ap.add_argument("--janela-dias", type=int, default=10, help="Janela (+-dias) para agregar nivel")
    ap.add_argument("--desde", default="2026-01-01",
                    help="Gera a partir desta semana (default recente; use --tudo p/ tudo)")
    ap.add_argument("--tudo", action="store_true", help="Todas as semanas")
    args = ap.parse_args()

    if not os.path.exists(args.db):
        raise SystemExit(f"Banco nao encontrado: {args.db}")

    con = sqlite3.connect(args.db)
    con.executescript(SQL_TABELA)

    codigos, s_lat, s_lon, cod_idx = carregar_estacoes_virtuais(con)
    if not codigos:
        raise SystemExit("Nenhuma estacao virtual com coordenadas.")
    fids, t_lat, t_lon = carregar_trechos(con)
    cota, fonte_cota = carregar_cota_fundo(con, fids)

    print(f"estacoes virtuais: {len(codigos)} | trechos: {len(fids)}")
    t0 = time.time()
    cand_idx, cand_dist = k_vizinhos(t_lat, t_lon, s_lat, s_lon, args.vizinhos)
    print(f"vizinhos calculados em {time.time()-t0:.0f}s")

    semanas, niveis = montar_niveis(con, cod_idx, args.janela_dias)
    if not args.tudo:
        semanas = [s for s in semanas if s >= args.desde]
    if not semanas:
        raise SystemExit("Sem dados de nivel no periodo pedido.")
    print(f"semanas: {len(semanas)} ({semanas[0]} a {semanas[-1]})")

    con.execute("DELETE FROM naveg_trecho_semanal" +
                ("" if args.tudo else " WHERE semana_inicio >= ?"),
                () if args.tudo else (args.desde,))

    pos_all = np.arange(len(fids))
    lote: list[tuple] = []
    total = 0
    t0 = time.time()
    for w, semana in enumerate(semanas):
        lvl = niveis[w]
        vals = lvl[cand_idx]                      # (T, k) com NaN
        dentro = cand_dist <= args.raio_km         # (T, k)
        mask = ~np.isnan(vals) & dentro
        tem = mask.any(axis=1)
        primeira = np.argmax(mask, axis=1)
        nivel_sel = vals[pos_all, primeira]
        dist_sel = cand_dist[pos_all, primeira]
        est_sel = cand_idx[pos_all, primeira]

        prof = np.where(np.isnan(cota) | ~tem, np.nan, nivel_sel - cota)
        folga = prof - args.calado
        st = classificar(prof, args.calado, args.margem)
        for j in range(len(fids)):
            if not tem[j]:
                continue  # sem nivel de satelite no raio/janela: nao grava
            lote.append((
                int(fids[j]), semana,
                codigos[int(est_sel[j])],
                float(dist_sel[j]),
                float(nivel_sel[j]),
                None if np.isnan(cota[j]) else float(cota[j]), str(fonte_cota[j]),
                None if np.isnan(prof[j]) else float(prof[j]), args.calado,
                None if np.isnan(folga[j]) else float(folga[j]), str(st[j]),
                "SATELITE_HYDROWEB",
            ))
            if len(lote) >= LOTE:
                con.executemany(
                    "INSERT OR REPLACE INTO naveg_trecho_semanal VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", lote)
                total += len(lote)
                lote = []
        if (w + 1) % 5 == 0:
            print(f"  {w+1}/{len(semanas)} semanas | {total + len(lote)} linhas", flush=True)
    if lote:
        con.executemany(
            "INSERT OR REPLACE INTO naveg_trecho_semanal VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", lote)
        total += len(lote)
    con.commit()

    contagem = dict(con.execute(
        "SELECT status, COUNT(*) FROM naveg_trecho_semanal GROUP BY status").fetchall())
    com_nivel = con.execute(
        "SELECT COUNT(*) FROM naveg_trecho_semanal WHERE fonte_nivel='SATELITE_HYDROWEB'").fetchone()[0]
    con.close()

    print(f"\nlinhas: {total} | com nivel: {com_nivel} | tempo: {time.time()-t0:.0f}s")
    print(f"periodo: {'tudo' if args.tudo else 'desde '+args.desde}")
    for s in ("NAVEGAVEL", "RESTRITO", "CRITICO", "SEM_DADOS"):
        print(f"  {s:12s}: {contagem.get(s, 0)}")


if __name__ == "__main__":
    sys.exit(main())
