"""Consolida todos os dados coletados do HidroWize em um único SQLite.

Gera `data/hidrowize.db` a partir dos CSVs em `planilhas/` e do GeoPackage de
trechos navegáveis (`data/hidrovias_navegaveis_bhae.gpkg`), com schema tipado,
índices e geometria armazenada em WKB (ISO) + centroide (para o IDW/RF002).

Tabelas:
- estacoes            (75)
- rios                (catálogo ANA)
- telemetria          (leituras de cota/vazão/chuva)
- cotas_historicas    (mín/máx/média por estação)
- navegabilidade      (regra de navegabilidade por estação)
- decretos            (Legisla.AM — validação qualitativa)
- trechos_navegaveis  (rede hidrográfica navegável, com geometria WKB)
- estacoes_trechos    (cruzamento estação × trecho mais próximo)
- estacoes_virtuais   (estações virtuais de nível — altimetria satelital)
- series_nivel_satelite (séries de nível d'água por satélite, altimetria)
- batimetria_sicflow  (seção transversal do leito por nó — SWOT L4 SICFLOW)
- series_vazao_satelite (séries de vazão por reach — SWOT L4 SOS Discharge)
- cotas_diarias       (série diária de cotas por estação — SOAP ANA)
- nivel_semanal       (agregação semanal de nível por estação — base semanal)

Uso:
    python gerar_sqlite.py [--out data/hidrowize.db]
    python gerar_sqlite.py --somente-diarias   # cria/popula só as tabelas diárias
"""

from __future__ import annotations

import argparse
import csv
import os
import sqlite3
import struct
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLANILHAS = os.path.join(RAIZ, "planilhas")
DATA = os.path.join(RAIZ, "data")
GPKG = os.path.join(DATA, "hidrovias_navegaveis_bhae.gpkg")

ENV_VALS = {0: 0, 1: 4, 2: 6, 3: 6, 4: 8}


# --------------------------------------------------------------------------- #
# GeoPackage Binary -> WKB + centroide
# --------------------------------------------------------------------------- #

def _gpb_wkb_off(blob: bytes) -> int:
    flags = blob[3]
    off = 4
    if flags & 0x01:
        off += 4  # srs_id
    off += ENV_VALS[(flags >> 1) & 0x07] * 8  # envelope
    return off


def _gpb_wkb(blob: bytes) -> bytes:
    return bytes(blob[_gpb_wkb_off(blob):])


def _parse_wkb(data: bytes, off: int) -> tuple[list[list[tuple[float, float]]], int]:
    e = data[off]
    end = "<" if e == 1 else ">"
    off += 1
    (gtype,) = struct.unpack_from(end + "I", data, off)
    off += 4
    lss: list[list[tuple[float, float]]] = []
    if gtype == 2:
        (n,) = struct.unpack_from(end + "I", data, off); off += 4
        lss.append([struct.unpack_from(end + "2d", data, off + i * 16) for i in range(n)])
    elif gtype == 5:
        (nls,) = struct.unpack_from(end + "I", data, off); off += 4
        for _ in range(nls):
            off += 5
            (n,) = struct.unpack_from(end + "I", data, off); off += 4
            pts = []
            for _ in range(n):
                x, y = struct.unpack_from(end + "2d", data, off); off += 16
                pts.append((x, y))
            lss.append(pts)
    return lss, off


def _gpb_centroid(blob: bytes) -> tuple[float, float]:
    off = _gpb_wkb_off(blob)
    lss, _ = _parse_wkb(blob, off)
    pts = [p for ls in lss for p in ls]
    if not pts:
        return 0.0, 0.0
    return sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)


# --------------------------------------------------------------------------- #
# Helpers de importação
# --------------------------------------------------------------------------- #

def _num(v: str) -> float | None:
    v = (v or "").strip()
    if v == "":
        return None
    try:
        return float(v)
    except ValueError:
        return None


def _int(v: str) -> int | None:
    x = _num(v)
    return int(x) if x is not None else None


def _ler_csv(caminho: str, delimitador: str) -> list[dict]:
    csv.field_size_limit(sys.maxsize)
    with open(caminho, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f, delimiter=delimitador))


LOTE_INSERCAO = 20000


def _iter_csv(caminho: str, delimitador: str):
    """Itera as linhas de um CSV sem carregar o arquivo inteiro na memoria."""
    csv.field_size_limit(sys.maxsize)
    with open(caminho, encoding="utf-8-sig", newline="") as f:
        yield from csv.DictReader(f, delimiter=delimitador)


def _inserir_em_lotes(con: sqlite3.Connection, sql: str, linhas) -> int:
    """Executa um iteravel de tuplas em lotes, devolvendo o total inserido."""
    lote: list[tuple] = []
    total = 0
    for linha in linhas:
        lote.append(linha)
        if len(lote) >= LOTE_INSERCAO:
            con.executemany(sql, lote)
            total += len(lote)
            lote = []
    if lote:
        con.executemany(sql, lote)
        total += len(lote)
    return total


# --------------------------------------------------------------------------- #
# Dados de satélite (hydroweb.next) — schema + upsert
# --------------------------------------------------------------------------- #

SATELITE = os.path.join(DATA, "satelite")

SQL_SATELITE = """
CREATE TABLE IF NOT EXISTS estacoes_virtuais (
    codigo      TEXT PRIMARY KEY,
    rio         TEXT,
    estacao     TEXT,
    km          TEXT,
    latitude    REAL,
    longitude   REAL,
    inicio      TEXT,
    fim         TEXT,
    fonte       TEXT
);

CREATE TABLE IF NOT EXISTS series_nivel_satelite (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo      TEXT NOT NULL,
    data        TEXT,
    nivel_m     REAL,
    incerteza_m REAL,
    fonte       TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_series_sat_cod ON series_nivel_satelite (codigo, data);
"""


def _real(v):
    if v is None or v == "":
        return None
    if isinstance(v, (int, float)):
        return float(v)
    return _num(v)


def criar_schema_satelite(con: sqlite3.Connection) -> None:
    con.executescript(SQL_SATELITE)


def upsert_estacoes_virtuais(con: sqlite3.Connection, linhas) -> int:
    def gerador():
        for l in linhas:
            yield (
                l["codigo"], l.get("rio"), l.get("estacao"), l.get("km"),
                _real(l.get("latitude")), _real(l.get("longitude")),
                l.get("inicio"), l.get("fim"), l.get("fonte"),
            )

    return _inserir_em_lotes(
        con,
        "INSERT OR REPLACE INTO estacoes_virtuais "
        "(codigo,rio,estacao,km,latitude,longitude,inicio,fim,fonte) "
        "VALUES (?,?,?,?,?,?,?,?,?)",
        gerador(),
    )


def upsert_series_nivel_satelite(con: sqlite3.Connection, linhas) -> int:
    def gerador():
        for l in linhas:
            yield (
                l["codigo"], l["data"], _real(l.get("nivel_m")),
                _real(l.get("incerteza_m")), l.get("fonte"),
            )

    return _inserir_em_lotes(
        con,
        "INSERT OR IGNORE INTO series_nivel_satelite "
        "(codigo,data,nivel_m,incerteza_m,fonte) VALUES (?,?,?,?,?)",
        gerador(),
    )


# --------------------------------------------------------------------------- #
# Batimetria (SWOT L4 SICFLOW) e vazão (SWOT L4 SOS Discharge) — schema + upsert
# --------------------------------------------------------------------------- #

AMAZON_BBOX = (-80.0, -21.0, -48.0, 6.0)

# Formato SWORD: node_id = CBBBBBRRRRNNNT; reach_id = CBBBBBRRRRT.
def _reach_de_node(node_id: int) -> int:
    return (node_id // 10000) * 10 + (node_id % 10)


def _batimetria_cols() -> str:
    elev = ", ".join(f"elev_{i:02d} REAL" for i in range(1, 13))
    larg = ", ".join(f"larg_{i:02d} REAL" for i in range(1, 13))
    met = ", ".join(f"metodo_{i:02d} INTEGER" for i in range(1, 13))
    return ", ".join([elev, larg, met])


def _batimetria_valores() -> list[str]:
    v: list[str] = []
    for p in ("elev", "larg", "metodo"):
        v += [f"{p}_{i:02d}" for i in range(1, 13)]
    return v


SQL_BATIMETRIA = f"""
CREATE TABLE IF NOT EXISTS batimetria_sicflow (
    node_id         INTEGER PRIMARY KEY,
    reach_id        INTEGER,
    longitude       REAL,
    latitude        REAL,
    h_interface     REAL,
    cota_fundo      REAL,
    cota_banco_max  REAL,
    largura_m       REAL,
    metodo_fundo    INTEGER,
    fonte           TEXT,
    {_batimetria_cols()}
);
CREATE INDEX IF NOT EXISTS idx_bat_reach ON batimetria_sicflow (reach_id);
CREATE INDEX IF NOT EXISTS idx_bat_latlon ON batimetria_sicflow (latitude, longitude);

CREATE TABLE IF NOT EXISTS series_vazao_satelite (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    reach_id    INTEGER,
    longitude   REAL,
    latitude    REAL,
    data        TEXT,
    vazao_m3s   REAL,
    fonte       TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_vazao_reach_data ON series_vazao_satelite (reach_id, data);
"""


def criar_schema_satelite(con: sqlite3.Connection) -> None:
    con.executescript(SQL_SATELITE)
    con.executescript(SQL_BATIMETRIA)


def upsert_batimetria_sicflow(con: sqlite3.Connection, linhas: list[tuple]) -> int:
    cols = ["node_id", "reach_id", "longitude", "latitude", "h_interface",
            "cota_fundo", "cota_banco_max", "largura_m", "metodo_fundo", "fonte"]
    cols += _batimetria_valores()
    placeholders = ", ".join("?" * len(cols))
    sql = f"INSERT OR REPLACE INTO batimetria_sicflow ({','.join(cols)}) VALUES ({placeholders})"
    con.executemany(sql, linhas)
    return len(linhas)


def upsert_series_vazao_satelite(con: sqlite3.Connection, linhas: list[tuple]) -> int:
    con.executemany(
        "INSERT OR IGNORE INTO series_vazao_satelite "
        "(reach_id,longitude,latitude,data,vazao_m3s,fonte) VALUES (?,?,?,?,?,?)",
        linhas)
    return len(linhas)


def _nc_satelite(pasta_coleta: str, prefixo: str) -> str | None:
    raiz = os.path.join(SATELITE, pasta_coleta)
    if not os.path.isdir(raiz):
        return None
    for dirpath, _dirs, files in os.walk(raiz):
        for nome in sorted(files):
            if nome.startswith(prefixo) and nome.endswith(".nc"):
                return os.path.join(dirpath, nome)
    return None


# --------------------------------------------------------------------------- #
# Importadores NetCDF (batimetria + vazão)
# --------------------------------------------------------------------------- #

BLOCO_NOS = 200_000  # nós lidos por vez do NetCDF (limita o pico de RAM)


def importar_batimetria_sicflow(con: sqlite3.Connection) -> int:
    nc = _nc_satelite("batimetria", "sa_")
    if nc is None:
        return 0
    try:
        import h5py
        import numpy as np
    except ImportError:
        print("  batimetria_sicflow: h5py indisponível, pulando")
        return 0

    FILL = -99999.0
    minlon, minlat, maxlon, maxlat = AMAZON_BBOX
    n = 0
    linhas: list[tuple] = []

    f = h5py.File(nc, "r")
    try:
        total = f["node_id"].shape[0]
        for i0 in range(0, total, BLOCO_NOS):
            i1 = min(i0 + BLOCO_NOS, total)
            node_id = f["node_id"][i0:i1]
            x = f["node_x"][i0:i1]
            y = f["node_y"][i0:i1]
            elev = f["SICFLOW/nodes/elevation"][i0:i1]
            larg = f["SICFLOW/nodes/width"][i0:i1]
            metodo = f["SICFLOW/nodes/method"][i0:i1]
            hi = f["SICFLOW/nodes/h_interface"][i0:i1]

            mask = (x >= minlon) & (x <= maxlon) & (y >= minlat) & (y <= maxlat)
            valid = elev > FILL
            mask &= valid.any(axis=1)
            if not mask.any():
                continue

            x = x[mask]
            y = y[mask]
            node_id = node_id[mask]
            elev = elev[mask]
            larg = larg[mask]
            metodo = metodo[mask]
            hi = hi[mask]
            valid = valid[mask]

            e = np.where(valid, elev, np.nan)
            w = np.where(valid, larg, np.nan)
            cota_fundo = np.nanmin(e, axis=1)
            cota_banco = np.nanmax(e, axis=1)
            largura = np.nanmax(w, axis=1)
            metodo_fundo = metodo[np.arange(metodo.shape[0]), np.nanargmin(e, axis=1)]
            h_interface = np.where(hi > FILL, hi, np.nan)

            n += int(mask.sum())
            for i in range(elev.shape[0]):
                row: list = [
                    int(node_id[i]),
                    _reach_de_node(int(node_id[i])),
                    float(x[i]), float(y[i]),
                    float(h_interface[i]) if not np.isnan(h_interface[i]) else None,
                    float(cota_fundo[i]), float(cota_banco[i]), float(largura[i]),
                    int(metodo_fundo[i]), "SWOT_L4_BATHY_SICFLOW",
                ]
                for k in range(12):
                    row.append(float(elev[i, k]) if valid[i, k] else None)
                for k in range(12):
                    row.append(float(larg[i, k]) if valid[i, k] else None)
                for k in range(12):
                    row.append(int(metodo[i, k]) if valid[i, k] else None)
                linhas.append(tuple(row))
                if len(linhas) >= 20000:
                    upsert_batimetria_sicflow(con, linhas)
                    linhas = []
    finally:
        f.close()

    if linhas:
        upsert_batimetria_sicflow(con, linhas)
    return n


def importar_series_vazao_satelite(con: sqlite3.Connection) -> int:
    nc = _nc_satelite("vazao", "sa_")
    if nc is None:
        return 0
    try:
        import h5py
        import numpy as np
    except ImportError:
        print("  series_vazao_satelite: h5py indisponível, pulando")
        return 0
    from datetime import datetime, timedelta

    f = h5py.File(nc, "r")
    try:
        reach_id = f["reaches/reach_id"][:]
        x = f["reaches/x"][:]
        y = f["reaches/y"][:]
        q = f["consensus/consensus_q"]
        t = f["consensus/time_int"]
        minlon, minlat, maxlon, maxlat = AMAZON_BBOX
        mask = (x >= minlon) & (x <= maxlon) & (y >= minlat) & (y <= maxlat)
        idx = np.nonzero(mask)[0]
        EPOCH = datetime(2000, 1, 1)
        linhas: list[tuple] = []
        total = 0
        for i in idx:
            qi = np.asarray(q[i], dtype=float)
            ti = np.asarray(t[i], dtype=float)
            ok = (qi > 0) & (ti > -1e12)
            for k in np.nonzero(ok)[0]:
                data = (EPOCH + timedelta(seconds=float(ti[k]))).isoformat()
                linhas.append((int(reach_id[i]), float(x[i]), float(y[i]),
                               data, float(qi[k]), "SWOT_L4_SOS_DISCHARGE"))
                total += 1
                if len(linhas) >= 20000:
                    upsert_series_vazao_satelite(con, linhas)
                    linhas = []
        if linhas:
            upsert_series_vazao_satelite(con, linhas)
    finally:
        f.close()
    return total


# --------------------------------------------------------------------------- #
# Série diária e agregação semanal (ANA SOAP) — schema
# --------------------------------------------------------------------------- #

SQL_DIARIAS = """
CREATE TABLE IF NOT EXISTS cotas_diarias (
    codigo_estacao     TEXT NOT NULL,
    data               TEXT NOT NULL,
    cota_cm            REAL,
    status             TEXT,
    nivel_consistencia TEXT,
    PRIMARY KEY (codigo_estacao, data)
);
CREATE INDEX IF NOT EXISTS idx_cotas_diarias_data ON cotas_diarias (data);

CREATE TABLE IF NOT EXISTS nivel_semanal (
    codigo_estacao TEXT NOT NULL,
    semana_inicio  TEXT NOT NULL,
    nivel_medio_cm REAL,
    nivel_min_cm   REAL,
    nivel_max_cm   REAL,
    n_dias         INTEGER,
    fonte          TEXT,
    incerteza_m    REAL,
    PRIMARY KEY (codigo_estacao, semana_inicio)
);
CREATE INDEX IF NOT EXISTS idx_nivel_semanal_data ON nivel_semanal (semana_inicio);
"""


def criar_schema_diarias(con: sqlite3.Connection) -> None:
    con.executescript(SQL_DIARIAS)


# --------------------------------------------------------------------------- #
# Criação do schema
# --------------------------------------------------------------------------- #

def criar_schema(con: sqlite3.Connection) -> None:
    con.executescript(
        """
        PRAGMA journal_mode = OFF;
        PRAGMA synchronous = OFF;

        CREATE TABLE IF NOT EXISTS estacoes (
            codigo_estacao  TEXT PRIMARY KEY,
            nome_estacao    TEXT,
            nome_rio        TEXT,
            municipio       TEXT,
            latitude        REAL,
            longitude       REAL,
            nome_ana        TEXT,
            tipo_estacao    TEXT,
            telemetrica     INTEGER,
            escala          INTEGER,
            operando        INTEGER,
            bacia           TEXT,
            sub_bacia       TEXT,
            altitude        REAL,
            area_drenagem   REAL,
            operadora       TEXT,
            responsavel     TEXT
        );

        CREATE TABLE IF NOT EXISTS rios (
            codigo_rio           INTEGER PRIMARY KEY,
            nome_rio             TEXT,
            bacia_codigo         INTEGER,
            sub_bacia_codigo     INTEGER,
            jurisdicao           INTEGER,
            data_ultima_alteracao TEXT
        );

        CREATE TABLE IF NOT EXISTS telemetria (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo_estacao    TEXT NOT NULL,
            data_hora_medicao TEXT,
            cota_adotada      REAL,
            cota_status       TEXT,
            vazao_adotada     REAL,
            vazao_status      TEXT,
            chuva_adotada     REAL,
            chuva_status      TEXT,
            data_atualizacao  TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_telemetria_est ON telemetria (codigo_estacao, data_hora_medicao);

        CREATE TABLE IF NOT EXISTS cotas_historicas (
            codigo_estacao      TEXT PRIMARY KEY,
            nome_estacao        TEXT,
            municipio           TEXT,
            nivel_consistencia  TEXT,
            registros           INTEGER,
            data_inicio_serie   TEXT,
            data_fim_serie      TEXT,
            cota_minima         REAL,
            cota_maxima         REAL,
            cota_media          REAL
        );

        CREATE TABLE IF NOT EXISTS navegabilidade (
            codigo_estacao          TEXT PRIMARY KEY,
            nome_estacao            TEXT,
            rio                     TEXT,
            municipio               TEXT,
            latitude                REAL,
            longitude               REAL,
            telemetrica             INTEGER,
            cota_atual              REAL,
            cota_minima_historica   REAL,
            fonte_minima            TEXT,
            status_navegabilidade   TEXT
        );

        CREATE TABLE IF NOT EXISTS decretos (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            numero       TEXT,
            data         TEXT,
            titulo       TEXT,
            ementa       TEXT,
            tipo         TEXT,
            municipio    TEXT,
            rio          TEXT,
            cobrade      TEXT,
            url          TEXT,
            corpo        TEXT,
            data_coleta  TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_decretos_tipo ON decretos (tipo);

        CREATE TABLE IF NOT EXISTS trechos_navegaveis (
            fid                INTEGER PRIMARY KEY,
            dominio            TEXT,
            rio                TEXT,
            cocursodag         TEXT,
            cotrecho           INTEGER,
            noorigem           INTEGER,
            nodestino          INTEGER,
            nustrahler         INTEGER,
            hig_drn_strahler   INTEGER,
            hig_drn_depth_m    REAL,
            hig_drn_width_m    REAL,
            hig_drn_annual_flow REAL,
            hig_drn_event_flow REAL,
            hig_drn_elevation_avg REAL,
            hig_drn_elevation_min REAL,
            hig_drn_elevation_max REAL,
            hig_drn_manning_n  REAL,
            hig_drn_velmann    REAL,
            hig_drn_sinuosity  REAL,
            hig_drn_slope_adim REAL,
            geom_wkb           BLOB,
            centroid_lon       REAL,
            centroid_lat       REAL
        );
        CREATE INDEX IF NOT EXISTS idx_trechos_dominio ON trechos_navegaveis (dominio);
        CREATE INDEX IF NOT EXISTS idx_trechos_strahler ON trechos_navegaveis (nustrahler);

        CREATE TABLE IF NOT EXISTS estacoes_trechos (
            codigo_estacao       TEXT,
            fid_trecho           INTEGER,
            dominio              TEXT,
            rio_bhae             TEXT,
            nustrahler           INTEGER,
            hig_drn_depth_m      REAL,
            hig_drn_width_m      REAL,
            hig_drn_annual_flow  REAL,
            hig_drn_elevation_avg REAL,
            distancia_m          REAL,
            status               TEXT,
            rio_confere          TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_est_trecho ON estacoes_trechos (codigo_estacao);
        """
    )
    criar_schema_satelite(con)
    criar_schema_diarias(con)


# --------------------------------------------------------------------------- #
# Importadores por tabela
# --------------------------------------------------------------------------- #

def importar_estacoes(con: sqlite3.Connection) -> int:
    caminho = os.path.join(PLANILHAS, "estacoes_am_enriquecidas.csv")

    def gerador():
        for r in _iter_csv(caminho, ";"):
            yield (
                r["codigo_estacao"], r["nome_estacao"], r["nome_rio"], r["municipio"],
                _num(r["latitude"]), _num(r["longitude"]), r["nome_ana"], r["tipo_estacao"],
                _int(r["telemetrica"]), _int(r["escala"]), _int(r["operando"]),
                r["bacia"], r["sub_bacia"], _num(r["altitude"]), _num(r["area_drenagem"]),
                r["operadora"], r["responsavel"],
            )

    return _inserir_em_lotes(
        con, "INSERT OR REPLACE INTO estacoes VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        gerador())


def importar_rios(con: sqlite3.Connection) -> int:
    caminho = os.path.join(PLANILHAS, "rios_ana.csv")

    def gerador():
        for r in _iter_csv(caminho, ","):
            yield (
                _int(r["codigo_rio"]), r["nome_rio"], _int(r["bacia_codigo"]),
                _int(r["sub_bacia_codigo"]), _int(r["jurisdicao"]),
                r["data_ultima_alteracao"],
            )

    return _inserir_em_lotes(
        con, "INSERT OR REPLACE INTO rios VALUES (?,?,?,?,?,?)", gerador())


def importar_telemetria(con: sqlite3.Connection) -> int:
    caminho = os.path.join(PLANILHAS, "telemetria_cotas_am.csv")

    def gerador():
        for r in _iter_csv(caminho, ";"):
            yield (
                r["codigo_estacao"], r["data_hora_medicao"], _num(r["cota_adotada"]),
                r["cota_status"], _num(r["vazao_adotada"]), r["vazao_status"],
                _num(r["chuva_adotada"]), r["chuva_status"], r["data_atualizacao"],
            )

    return _inserir_em_lotes(
        con,
        "INSERT INTO telemetria (codigo_estacao,data_hora_medicao,cota_adotada,cota_status,"
        "vazao_adotada,vazao_status,chuva_adotada,chuva_status,data_atualizacao) "
        "VALUES (?,?,?,?,?,?,?,?,?)",
        gerador())


def importar_cotas_historicas(con: sqlite3.Connection) -> int:
    caminho = os.path.join(PLANILHAS, "cotas_historicas_am.csv")

    def gerador():
        for r in _iter_csv(caminho, ";"):
            yield (
                r["codigo_estacao"], r["nome_estacao"], r["municipio"],
                r["nivel_consistencia"], _int(r["registros"]), r["data_inicio_serie"],
                r["data_fim_serie"], _num(r["cota_minima"]), _num(r["cota_maxima"]),
                _num(r["cota_media"]),
            )

    return _inserir_em_lotes(
        con, "INSERT OR REPLACE INTO cotas_historicas VALUES (?,?,?,?,?,?,?,?,?,?)",
        gerador())


def importar_navegabilidade(con: sqlite3.Connection) -> int:
    caminho = os.path.join(PLANILHAS, "estacoes_am_navegabilidade.csv")

    def gerador():
        for r in _iter_csv(caminho, ";"):
            yield (
                r["codigo_estacao"], r["nome_estacao"], r["rio"], r["municipio"],
                _num(r["latitude"]), _num(r["longitude"]), _int(r["telemetrica"]),
                _num(r["cota_atual"]), _num(r["cota_minima_historica"]),
                r["fonte_minima"], r["status_navegabilidade"],
            )

    return _inserir_em_lotes(
        con, "INSERT OR REPLACE INTO navegabilidade VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        gerador())


def importar_decretos(con: sqlite3.Connection) -> int:
    caminho = os.path.join(PLANILHAS, "decretos_legisla_am.csv")
    if not os.path.exists(caminho):
        return 0

    def gerador():
        for r in _iter_csv(caminho, ";"):
            yield (
                r["numero"], r["data"], r["titulo"], r["ementa"], r["tipo"],
                r["municipio"], r["rio"], r["cobrade"], r["url"], r["corpo"],
                r["data_coleta"],
            )

    return _inserir_em_lotes(
        con,
        "INSERT INTO decretos (numero,data,titulo,ementa,tipo,municipio,rio,cobrade,"
        "url,corpo,data_coleta) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        gerador())


def importar_estacoes_trechos(con: sqlite3.Connection) -> int:
    caminho = os.path.join(PLANILHAS, "estacoes_am_x_hidrovias_navegaveis.csv")

    def gerador():
        for r in _iter_csv(caminho, ";"):
            yield (
                r["codigo_estacao"], _int(r["fid_trecho"]), r["dominio"], r["rio_bhae"],
                _int(r["nustrahler"]), _num(r["hig_drn_depth_m"]),
                _num(r["hig_drn_width_m"]), _num(r["hig_drn_annual_flow"]),
                _num(r["hig_drn_elevation_avg"]), _num(r["distancia_m"]),
                r["status"], r["rio_confere"],
            )

    return _inserir_em_lotes(
        con, "INSERT INTO estacoes_trechos VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", gerador())


def importar_trechos(con: sqlite3.Connection) -> int:
    src = sqlite3.connect(GPKG)
    cur = src.execute(
        "SELECT fid, geom, dedominial, nooriginal, cocursodag, cotrecho, noorigem, nodestino, "
        "nustrahler, hig_drn_strahler, hig_drn_depth_m, hig_drn_width_m, "
        "hig_drn_annual_flow, hig_drn_event_flow, hig_drn_elevation_avg, "
        "hig_drn_elevation_min, hig_drn_elevation_max, hig_drn_manning_n, "
        "hig_drn_velmann, hig_drn_sinuosity, hig_drn_slope_adim "
        "FROM hidrovias_navegaveis_bhae"
    )
    n = 0
    for row in cur:
        (fid, geom, *attrs) = row
        if geom is None:
            continue
        wkb = _gpb_wkb(geom)
        clon, clat = _gpb_centroid(geom)
        con.execute(
            "INSERT INTO trechos_navegaveis VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (fid, attrs[0], attrs[1], attrs[2], attrs[3], attrs[4], attrs[5],
             attrs[6], attrs[7], attrs[8], attrs[9], attrs[10], attrs[11],
             attrs[12], attrs[13], attrs[14], attrs[15], attrs[16], attrs[17],
             attrs[18], wkb, clon, clat),
        )
        n += 1
        if n % 20000 == 0:
            print("  trechos:", n)
    src.close()
    return n


def importar_estacoes_virtuais(con: sqlite3.Connection) -> int:
    caminho = os.path.join(SATELITE, "estacoes_virtuais.csv")
    if not os.path.exists(caminho):
        return 0

    def gerador():
        for r in _iter_csv(caminho, ";"):
            r["fonte"] = "HYDROWEB_RIVERS_OPE"
            yield r

    return upsert_estacoes_virtuais(con, gerador())


def importar_series_nivel_satelite(con: sqlite3.Connection) -> int:
    caminho = os.path.join(SATELITE, "series_nivel_satelite.csv")
    if not os.path.exists(caminho):
        return 0

    def gerador():
        for r in _iter_csv(caminho, ";"):
            r["fonte"] = "HYDROWEB_RIVERS_OPE"
            yield r

    return upsert_series_nivel_satelite(con, gerador())


def importar_cotas_diarias(con: sqlite3.Connection) -> int:
    caminho = os.path.join(PLANILHAS, "cotas_diarias_am.csv")
    if not os.path.exists(caminho):
        return 0

    def gerador():
        for r in _iter_csv(caminho, ";"):
            yield (
                r["codigo_estacao"], r["data"], _num(r.get("cota_cm")),
                r.get("status", ""), r.get("nivel_consistencia", ""),
            )

    return _inserir_em_lotes(
        con,
        "INSERT OR REPLACE INTO cotas_diarias "
        "(codigo_estacao,data,cota_cm,status,nivel_consistencia) VALUES (?,?,?,?,?)",
        gerador())


def gerar_nivel_semanal(con: sqlite3.Connection) -> int:
    """Agrega cotas_diarias em uma linha por (estação, semana ISO).

    A semana é identificada pela segunda-feira (`semana_inicio`). A coluna
    `fonte` resume o nível de consistência do período: ANA_CONSISTIDO (2),
    ANA_BRUTO (1) ou ANA_MISTO.
    """
    from datetime import date, datetime

    grupos: dict[tuple[str, str], dict] = {}
    cur = con.execute(
        "SELECT codigo_estacao, data, cota_cm, nivel_consistencia FROM cotas_diarias"
    )
    for cod, d, cota, nivel in cur:
        if cota is None:
            continue
        try:
            dt = datetime.strptime(d, "%Y-%m-%d").date()
        except (TypeError, ValueError):
            continue
        iso = dt.isocalendar()
        segunda = date.fromisocalendar(iso[0], iso[1], 1).isoformat()
        g = grupos.setdefault((cod, segunda), {"vals": [], "niveis": set()})
        g["vals"].append(cota)
        if nivel:
            g["niveis"].add(str(nivel))

    linhas: list[tuple] = []
    for (cod, semana), g in grupos.items():
        vals = g["vals"]
        niveis = g["niveis"]
        if niveis == {"2"}:
            fonte = "ANA_CONSISTIDO"
        elif niveis == {"1"}:
            fonte = "ANA_BRUTO"
        elif niveis:
            fonte = "ANA_MISTO"
        else:
            fonte = ""
        linhas.append((
            cod, semana, round(sum(vals) / len(vals), 2), min(vals), max(vals),
            len(vals), fonte, None,
        ))
    con.executemany(
        "INSERT OR REPLACE INTO nivel_semanal "
        "(codigo_estacao,semana_inicio,nivel_medio_cm,nivel_min_cm,nivel_max_cm,"
        "n_dias,fonte,incerteza_m) VALUES (?,?,?,?,?,?,?,?)", linhas)
    return len(linhas)


def main() -> None:
    ap = argparse.ArgumentParser(description="Consolida os dados coletados em SQLite")
    ap.add_argument("--out", default=os.path.join(DATA, "hidrowize.db"))
    ap.add_argument(
        "--somente-diarias",
        action="store_true",
        help="Cria/popula apenas cotas_diarias e nivel_semanal (sem rebuild completo)",
    )
    args = ap.parse_args()

    if args.somente_diarias:
        con = sqlite3.connect(args.out)
        criar_schema_diarias(con)
        print("importando serie diaria...")
        print("  cotas_diarias:", importar_cotas_diarias(con))
        print("  nivel_semanal:", gerar_nivel_semanal(con))
        con.commit()
        con.close()
        return

    if os.path.exists(args.out):
        os.remove(args.out)
    con = sqlite3.connect(args.out)
    criar_schema(con)

    print("importando CSVs...")
    print("  estacoes:", importar_estacoes(con))
    print("  rios:", importar_rios(con))
    print("  telemetria:", importar_telemetria(con))
    print("  cotas_historicas:", importar_cotas_historicas(con))
    print("  navegabilidade:", importar_navegabilidade(con))
    print("  decretos:", importar_decretos(con))
    print("  estacoes_trechos:", importar_estacoes_trechos(con))
    print("  estacoes_virtuais:", importar_estacoes_virtuais(con))
    print("  series_nivel_satelite:", importar_series_nivel_satelite(con))

    print("importando trechos navegaveis (com geometria WKB)...")
    n_trechos = importar_trechos(con)

    print("importando dados satelitais (NetCDF)...")
    print("  batimetria_sicflow:", importar_batimetria_sicflow(con))
    print("  series_vazao_satelite:", importar_series_vazao_satelite(con))

    print("importando serie diaria e agregando semanal...")
    print("  cotas_diarias:", importar_cotas_diarias(con))
    print("  nivel_semanal:", gerar_nivel_semanal(con))

    con.commit()

    print("\n=== resumo ===")
    for t in ["estacoes", "rios", "telemetria", "cotas_historicas",
              "navegabilidade", "decretos", "trechos_navegaveis", "estacoes_trechos",
              "estacoes_virtuais", "series_nivel_satelite",
              "batimetria_sicflow", "series_vazao_satelite",
              "cotas_diarias", "nivel_semanal"]:
        c = con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        print(f"  {t}: {c}")

    tam = os.path.getsize(args.out)
    print(f"\nSQLite gerado: {args.out} ({tam/1e6:.1f} MB)")


if __name__ == "__main__":
    main()
