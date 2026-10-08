"""Exporta dados agregados do `data/hidrowize.db` para o dashboard estático.

Gera `frontend/dashboard/dashboard.js` com `window.DASHBOARD = {...}` contendo
KPIs, estações (com navegabilidade, cotas históricas e última telemetria),
distribuições de trechos (domínio, profundidade, extensão em km) e decretos
recentes — consumido pelo dashboard em Vue 3 via CDN.

Uso:
    python gerar_dashboard_dados.py [--out frontend/dashboard/dashboard.js]
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sqlite3
import struct
from datetime import datetime

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(RAIZ, "data", "hidrowize.db")
DEFAULT_OUT = os.path.join(RAIZ, "frontend", "dashboard", "dashboard.js")

FAIXAS_PROF = [
    ("0–2 m (raso)", 0.0, 2.0),
    ("2–5 m", 2.0, 5.0),
    ("5–10 m", 5.0, 10.0),
    ("> 10 m (profundo)", 10.0, None),
]


def _extensao_km(blob: bytes) -> float:
    lss = _wkb_linestrings(blob)
    total = 0.0
    for pts in lss:
        for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
            dx = (x2 - x1) * 111320.0 * math.cos(math.radians((y1 + y2) / 2))
            dy = (y2 - y1) * 110540.0
            total += math.hypot(dx, dy)
    return total / 1000.0


def _wkb_linestrings(data: bytes) -> list[list[tuple[float, float]]]:
    end = "<" if data[0] == 1 else ">"
    (gtype,) = struct.unpack_from(end + "I", data, 1)
    off = 5
    lss: list[list[tuple[float, float]]] = []
    if gtype in (2, 3):
        (n,) = struct.unpack_from(end + "I", data, off)
        lss.append(_wkb_line(data, end, off + 4, n, gtype))
    elif gtype in (5, 7):
        (nls,) = struct.unpack_from(end + "I", data, off)
        off += 4
        for _ in range(nls):
            off += 1
            (lt,) = struct.unpack_from(end + "I", data, off)
            off += 4
            (n,) = struct.unpack_from(end + "I", data, off)
            off += 4
            lss.append(_wkb_line(data, end, off, n, lt))
            off += n * (24 if lt in (3, 13) else 16)
    return lss


def _wkb_line(data: bytes, end: str, off: int, n: int, gtype: int) -> list[tuple[float, float]]:
    pt = 24 if gtype in (3, 13) else 16
    return [struct.unpack_from(end + "2d", data, off + i * pt) for i in range(n)]


def _num(v):
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _arred(v, d=1):
    if v is None:
        return None
    return round(float(v), d)


def _cota_m(v):
    if v is None:
        return None
    try:
        return round(float(v) / 100.0, 2)
    except (TypeError, ValueError):
        return None


def _serie_data(v):
    if not v:
        return None
    try:
        return str(v).split("T")[0].split(" ")[0]
    except (AttributeError, ValueError):
        return None


def _data_hora(v):
    if not v:
        return None
    s = str(v)
    return s.replace(".0", "").replace("T", " ")


def resumo(con: sqlite3.Connection) -> dict:
    tabelas = [
        "estacoes", "rios", "telemetria", "cotas_historicas",
        "navegabilidade", "decretos", "trechos_navegaveis", "estacoes_trechos",
        "estacoes_virtuais", "series_nivel_satelite",
        "batimetria_sicflow", "series_vazao_satelite",
    ]
    return {t: con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in tabelas}


def navegabilidade(con: sqlite3.Connection) -> dict:
    return {
        r[0] or "SEM DADOS": r[1]
        for r in con.execute("SELECT status_navegabilidade, COUNT(*) FROM navegabilidade GROUP BY status_navegabilidade")
    }


def dominio(con: sqlite3.Connection) -> dict:
    return {
        r[0] or "Sem classificação": r[1]
        for r in con.execute("SELECT dominio, COUNT(*) FROM trechos_navegaveis GROUP BY dominio")
    }


def telemetria_stats(con: sqlite3.Connection) -> dict:
    total, com_cota, com_vazao, com_chuva = con.execute(
        "SELECT COUNT(*), COUNT(cota_adotada), COUNT(vazao_adotada), COUNT(chuva_adotada) FROM telemetria"
    ).fetchone()
    fim = _data_hora(con.execute("SELECT MAX(data_hora_medicao) FROM telemetria").fetchone()[0])
    inicio = _data_hora(con.execute("SELECT MIN(data_hora_medicao) FROM telemetria").fetchone()[0])

    recencia = {"com_telemetria": 0, "ate_24h": 0, "ate_7d": 0, "ate_30d": 0, "mais_30d": 0, "sem_telemetria": 0}
    ref = fim
    q = """
        SELECT MAX(data_hora_medicao)
        FROM telemetria
        GROUP BY codigo_estacao
    """
    for (ult,) in con.execute(q):
        if not ult:
            continue
        recencia["com_telemetria"] += 1
        try:
            dias = (datetime.fromisoformat(ref) - datetime.fromisoformat(str(ult).replace(".0", "").replace("T", " "))).days
        except ValueError:
            dias = 9999
        if dias <= 1:
            recencia["ate_24h"] += 1
        elif dias <= 7:
            recencia["ate_7d"] += 1
        elif dias <= 30:
            recencia["ate_30d"] += 1
        else:
            recencia["mais_30d"] += 1
    recencia["sem_telemetria"] = resumo(con)["estacoes"] - recencia["com_telemetria"]
    return {"total": total, "com_cota": com_cota, "com_vazao": com_vazao,
            "com_chuva": com_chuva, "inicio": _serie_data(inicio), "fim": _serie_data(fim),
            "recencia": recencia}


def estacoes(con: sqlite3.Connection) -> list[dict]:
    ultima = {}
    for codigo, data, cota, vazao, chuva in con.execute(
        "SELECT codigo_estacao, data_hora_medicao, cota_adotada, vazao_adotada, chuva_adotada "
        "FROM telemetria WHERE id IN (SELECT MAX(id) FROM telemetria GROUP BY codigo_estacao)"
    ):
        ultima[codigo] = (data, cota, vazao, chuva)

    nav = {}
    for r in con.execute(
        "SELECT codigo_estacao, cota_atual, cota_minima_historica, status_navegabilidade FROM navegabilidade"
    ):
        nav[r[0]] = (r[1], r[2], r[3])

    cotas = {}
    for r in con.execute(
        "SELECT codigo_estacao, cota_minima, cota_maxima, cota_media, registros, "
        "data_inicio_serie, data_fim_serie FROM cotas_historicas"
    ):
        cotas[r[0]] = r

    trecho = {}
    for r in con.execute(
        "SELECT codigo_estacao, rio_bhae, nustrahler, hig_drn_depth_m, hig_drn_width_m, "
        "hig_drn_annual_flow, distancia_m, status FROM estacoes_trechos"
    ):
        trecho[r[0]] = r

    out = []
    for r in con.execute(
        "SELECT codigo_estacao, nome_estacao, nome_rio, municipio, latitude, longitude, "
        "telemetrica, operando, bacia, sub_bacia, operadora, altitude, area_drenagem "
        "FROM estacoes"
    ):
        codigo = r[0]
        nome_rio = r[2] or ""
        c = cotas.get(codigo)
        n = nav.get(codigo)
        u = ultima.get(codigo)
        t = trecho.get(codigo)
        out.append({
            "codigo": codigo,
            "nome": r[1] or "",
            "rio": nome_rio,
            "municipio": r[3] or "",
            "lat": _arred(r[4], 5),
            "lon": _arred(r[5], 5),
            "telemetrica": bool(r[6]),
            "operando": bool(r[7]),
            "bacia": r[8] or "",
            "sub_bacia": r[9] or "",
            "operadora": r[10] or "",
            "altitude": _arred(r[11], 1),
            "area_drenagem": _arred(r[12], 0),
            "status_nav": n[2] if n else None,
            "cota_atual": _cota_m(n[0]) if n else None,
            "cota_min_hist": _cota_m(n[1]) if n else None,
            "cota_minima": _cota_m(c[1]) if c else None,
            "cota_maxima": _cota_m(c[2]) if c else None,
            "cota_media": _cota_m(c[3]) if c else None,
            "registros_cotas": c[4] if c else None,
            "serie_inicio": _serie_data(c[5]) if c else None,
            "serie_fim": _serie_data(c[6]) if c else None,
            "ult_leitura": _data_hora(u[0]) if u else None,
            "ult_cota": _cota_m(u[1]) if u else None,
            "ult_vazao": _arred(u[2], 1) if u else None,
            "ult_chuva": _arred(u[3], 1) if u else None,
            "rio_bhae": t[1] if t else None,
            "nustrahler": t[2] if t else None,
            "depth_m": _arred(t[3]) if t else None,
            "width_m": _arred(t[4], 0) if t else None,
            "flow_m3s": _arred(t[5], 0) if t else None,
            "distancia_m": _arred(t[6], 0) if t else None,
            "assoc_status": t[7] if t else None,
        })
    return out


def trechos_stats(con: sqlite3.Connection) -> dict:
    faixas = {nome: {"trechos": 0, "km": 0.0} for nome, _, _ in FAIXAS_PROF}
    total_km = 0.0
    km_com_prof = 0.0
    com_dado = 0
    sem_dado = 0
    soma_prof = 0.0
    for fid, geom, prof, lat in con.execute(
        "SELECT fid, geom_wkb, hig_drn_depth_m, centroid_lat FROM trechos_navegaveis"
    ):
        if geom is None:
            continue
        km = _extensao_km(geom)
        total_km += km
        if prof is None:
            sem_dado += 1
            continue
        com_dado += 1
        soma_prof += prof
        if lat is None or lat < -8.0 or lat > 5.0:
            continue
        km_com_prof += km
        for nome, lo, hi in FAIXAS_PROF:
            if (lo <= prof) and (hi is None or prof < hi):
                faixas[nome]["trechos"] += 1
                faixas[nome]["km"] += km
                break
    return {
        "total_km": round(total_km, 1),
        "km_com_prof": round(km_com_prof, 1),
        "com_dado": com_dado,
        "sem_dado": sem_dado,
        "prof_media": round(soma_prof / com_dado, 2) if com_dado else None,
        "faixas": [
            {"rotulo": nome, "trechos": v["trechos"], "km": round(v["km"], 1)}
            for nome, v in faixas.items()
        ],
    }


def rios_top(con: sqlite3.Connection, limite: int = 15) -> list[dict]:
    rows = con.execute(
        "SELECT rio, COUNT(*), AVG(hig_drn_depth_m) FROM trechos_navegaveis "
        "WHERE rio IS NOT NULL AND rio <> '' GROUP BY rio ORDER BY COUNT(*) DESC LIMIT ?",
        (limite,),
    )
    return [
        {"rio": r[0], "trechos": r[1], "prof_media": _arred(r[2], 2)}
        for r in rows
    ]


def decretos(con: sqlite3.Connection, limite: int = 60) -> list[dict]:
    rows = con.execute(
        "SELECT numero, data, titulo, ementa, tipo, municipio, rio, url "
        "FROM decretos ORDER BY COALESCE(data, '') DESC LIMIT ?",
        (limite,),
    )
    return [
        {"numero": r[0] or "", "data": _serie_data(r[1]), "titulo": r[2] or "",
         "ementa": r[3] or "", "tipo": r[4] or "", "municipio": r[5] or "",
         "rio": r[6] or "", "url": r[7] or ""}
        for r in rows
    ]


def series_stats(con: sqlite3.Connection) -> dict:
    nivel_inicio = _serie_data(con.execute("SELECT MIN(data) FROM series_nivel_satelite").fetchone()[0])
    nivel_fim = _serie_data(con.execute("SELECT MAX(data) FROM series_nivel_satelite").fetchone()[0])
    vazao_inicio = _serie_data(con.execute("SELECT MIN(data) FROM series_vazao_satelite").fetchone()[0])
    vazao_fim = _serie_data(con.execute("SELECT MAX(data) FROM series_vazao_satelite").fetchone()[0])
    reaches = con.execute("SELECT COUNT(DISTINCT reach_id) FROM batimetria_sicflow").fetchone()[0]
    return {
        "nivel": {"inicio": nivel_inicio, "fim": nivel_fim},
        "vazao": {"inicio": vazao_inicio, "fim": vazao_fim},
        "batimetria_reaches": reaches,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Exporta dados agregados para o dashboard")
    ap.add_argument("--out", default=DEFAULT_OUT)
    args = ap.parse_args()

    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row

    dados = {
        "gerado_em": datetime.now().isoformat(timespec="seconds"),
        "resumo": resumo(con),
        "navegabilidade": navegabilidade(con),
        "dominio": dominio(con),
        "telemetria": telemetria_stats(con),
        "estacoes": estacoes(con),
        "trechos": trechos_stats(con),
        "rios_top": rios_top(con),
        "decretos": decretos(con),
        "series": series_stats(con),
    }
    con.close()

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    payload = json.dumps(dados, ensure_ascii=False, separators=(",", ":"))
    with open(args.out, "w", encoding="utf-8") as f:
        f.write("// Gerado por backend/gerar_dashboard_dados.py — não editar manualmente.\n")
        f.write("window.DASHBOARD = " + payload + ";\n")

    print("OK — arquivo gerado:", args.out)
    print(f"  estações: {dados['resumo']['estacoes']} | trechos: {dados['resumo']['trechos_navegaveis']} "
          f"| extensão: {dados['trechos']['total_km']} km | telemetria: {dados['resumo']['telemetria']}")


if __name__ == "__main__":
    main()
