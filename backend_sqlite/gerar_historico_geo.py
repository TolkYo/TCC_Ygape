"""Gera o histórico de cheias/vazantes e navegabilidade por período (satélite).

Consolida as estações virtuais (hydroweb.next) num GeoJSON temporal multi-frame,
amostrando apenas as estações associadas a trechos largos (largura >= LARGURA_MIN_M)
da rede navegável (BHAE), onde o sinal do satélite é confiável.

Para cada estação calcula os percentis do nível sobre toda a série e classifica o
nível mensal em VAZANTE / NORMAL / CHEIA (ou SEM_DADO). Complementarmente, associa
cada estação ao trecho navegável mais próximo (cota_fundo de SICFLOW/AHGN via
hidrowize.db) e estima a navegabilidade por mês pela regra RN010/RN012:

    profundidade = nivel_mensal - cota_fundo
    NAVEGAVEL se profundidade >= calado + margem (0,5 m)
    RESTRITO  se calado <= profundidade < calado + margem
    CRITICO   se profundidade < calado

O calado de referência é o da RN029 (Amazonas 10 m, Solimões 6 m, Madeira 13 m,
Negro irrestrito); rios fora da RN029 usam um proxy por largura (min 2 m, max 6 m).

O resultado é um arquivo único consumido pelo mapa
(frontend/mapa-hidrovias/index.html) com um slider.

Uso:
    python gerar_historico_geo.py [--raio-m 11000] [--largura-min-m 300] \
        [--saida ../frontend/mapa-hidrovias/historico_nivel.js]
"""

from __future__ import annotations

import argparse
import csv
import json
import sqlite3
import sys
import unicodedata
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parent.parent
CSV_ESTACOES = RAIZ / "data" / "satelite" / "estacoes_virtuais.csv"
CSV_SERIES = RAIZ / "data" / "satelite" / "series_nivel_satelite.csv"
DB = RAIZ / "data" / "hidrowize.db"
SAIDA_DEFAULT = RAIZ / "frontend" / "mapa-hidrovias" / "historico_nivel.js"

RAIO_M_DEFAULT = 11000.0
LARGURA_MIN_M_DEFAULT = 300.0
MARGEM_M = 0.5  # RN012

CLASSES = ("VAZANTE", "NORMAL", "CHEIA")
LIMIARES = (0.25, 0.75)

# Calado de projeto por tramo (RN029 — DNIT/ANTAQ). Correspondência por substring
# sobre o nome do rio da BHAE (normalizado, sem acentos).
CALADO_POR_RIO = {"AMAZONAS": 10.0, "SOLIMOES": 6.0, "MADEIRA": 13.0, "NEGRO": 0.0}


def normalizar_nome(nome: str | None) -> str:
    if not nome:
        return ""
    s = unicodedata.normalize("NFKD", nome)
    return "".join(c for c in s if not unicodedata.combining(c)).upper()


def calado_de_rio(nome_rio: str | None, largura_m: float | None,
                  longitude: float | None = None) -> float:
    """Calado de referência do trecho.

    RN029 segmenta os tramos por posição (Tabatinga lon ~ -69.9; Manaus ~ -59.9):
      - Amazonas a jusante de Manaus (lon >= -60.5): 10 m;
      - Solimões (Tabatinga–Manaus, -70.5 <= lon < -60.5): 6 m;
      - cabeceiras a montante (lon < -70.5) e rios fora da RN029: proxy por largura;
      - Madeira: 13 m; Negro: irrestrito (0 m).
    """
    norm = normalizar_nome(nome_rio)
    if "NEGRO" in norm:
        return 0.0
    if "MADEIRA" in norm:
        return 13.0
    if "SOLIMOES" in norm:
        return 6.0
    if "AMAZONAS" in norm:
        if longitude is not None and longitude >= -60.5:
            return 10.0
        if longitude is not None and longitude >= -70.5:
            return 6.0
    if largura_m:
        return min(6.0, max(2.0, round(largura_m / 100.0)))
    return 6.0


def carregar_estacoes() -> list[dict]:
    with open(CSV_ESTACOES, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f, delimiter=";")
        return [
            {
                "codigo": r["codigo"],
                "rio": r["rio"],
                "estacao": r["estacao"],
                "km": r["km"],
                "latitude": float(r["latitude"]),
                "longitude": float(r["longitude"]),
                "inicio": r["inicio"],
                "fim": r["fim"],
            }
            for r in reader
        ]


def carregar_trechos() -> dict:
    """Trechos navegáveis + cota de fundo (SICFLOW/AHGN) por fid, do hidrowize.db."""
    con = sqlite3.connect(DB)
    try:
        cur = con.execute(
            "SELECT t.fid, t.rio, t.hig_drn_width_m, t.geom_wkb, "
            "c.cota_fundo_observada, c.cota_fundo_estimada "
            "FROM trechos_navegaveis t "
            "LEFT JOIN cota_fundo_trecho c ON c.fid = t.fid"
        )
        linhas = cur.fetchall()
    finally:
        con.close()

    from shapely import from_wkb
    return {
        "fids": [r[0] for r in linhas],
        "rios": [r[1] for r in linhas],
        "larguras": [r[2] for r in linhas],
        "geoms": [from_wkb(r[3]) for r in linhas],
        "cota_fundo": [
            (r[4] if r[4] is not None else r[5]) for r in linhas
        ],
    }


def associar_trecho(estacoes: list[dict], raio_m: float, trechos: dict) -> dict[str, dict]:
    """Trecho navegável mais próximo de cada estação (largura, cota_fundo, rio)."""
    from shapely import STRtree, points

    tree = STRtree(trechos["geoms"])
    raio_deg = raio_m / 111320.0
    pts = points([(e["longitude"], e["latitude"]) for e in estacoes])
    candidatos = tree.query(pts, predicate="dwithin", distance=raio_deg)
    resultado: dict[str, dict | None] = {}
    for i, est in enumerate(estacoes):
        indices = candidatos[1][candidatos[0] == i]
        if not len(indices):
            resultado[est["codigo"]] = None
            continue
        alvo = pts[i]
        melhor = min(indices, key=lambda j: alvo.distance(trechos["geoms"][j]))
        resultado[est["codigo"]] = {
            "largura_m": trechos["larguras"][melhor],
            "cota_fundo_m": trechos["cota_fundo"][melhor],
            "rio_bhae": trechos["rios"][melhor],
        }
    return resultado


def classificar_navegabilidade(prof: float, calado: float) -> str:
    if prof < calado:
        return "CRITICO"
    if prof < calado + MARGEM_M:
        return "RESTRITO"
    return "NAVEGAVEL"


def ler_series() -> tuple[dict[str, list[float]], dict[str, dict[str, float]]]:
    """Retorna (niveis_por_estacao, media_mensal_por_estacao)."""
    niveis: dict[str, list[float]] = defaultdict(list)
    mensal: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    total = 0
    with open(CSV_SERIES, encoding="utf-8-sig") as f:
        for r in csv.DictReader(f, delimiter=";"):
            codigo = r["codigo"]
            nivel = r["nivel_m"]
            if not nivel:
                continue
            total += 1
            niveis[codigo].append(float(nivel))
            mes = r["data"][:7]
            mensal[codigo][mes].append(float(nivel))
    medias = {
        codigo: {mes: float(np.mean(v)) for mes, v in meses.items()}
        for codigo, meses in mensal.items()
    }
    print(f"Lidas {total} observações de {len(niveis)} estações.")
    return niveis, medias


def classificar(nivel: float, p25: float, p75: float) -> str:
    if nivel < p25:
        return "VAZANTE"
    if nivel > p75:
        return "CHEIA"
    return "NORMAL"


def gerar(features_out, estacoes, trechos_assoc, niveis, medias) -> None:
    todas_meses = sorted({mes for m in medias.values() for mes in m})
    for est in estacoes:
        codigo = est["codigo"]
        if codigo not in medias:
            continue
        assoc = trechos_assoc.get(codigo)
        if assoc is None:
            continue
        larg = assoc["largura_m"]
        if larg is None or larg < LARGURA_MIN_M_DEFAULT:
            continue
        calado = calado_de_rio(assoc["rio_bhae"], larg, est["longitude"])
        cota_fundo = assoc["cota_fundo_m"]
        obs = np.asarray(niveis[codigo])
        p25, p75 = np.percentile(obs, [25.0, 75.0])
        serie = []
        for mes in sorted(medias[codigo]):
            nivel = medias[codigo][mes]
            entrada = {
                "t": mes,
                "classe": classificar(nivel, float(p25), float(p75)),
                "nivel": round(nivel, 1),
            }
            if cota_fundo is not None:
                prof = nivel - cota_fundo
                entrada["prof"] = round(prof, 1)
                entrada["nav"] = classificar_navegabilidade(prof, calado)
            serie.append(entrada)
        features_out.append(
            {
                "type": "Feature",
                "properties": {
                    "codigo": codigo,
                    "rio": est["rio"],
                    "estacao": est["estacao"],
                    "km": est["km"],
                    "largura_m": round(larg, 0) if larg is not None else None,
                    "cota_fundo_m": round(cota_fundo, 1) if cota_fundo is not None else None,
                    "calado_m": calado,
                    "inicio": est["inicio"][:10],
                    "fim": est["fim"][:10],
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": [est["longitude"], est["latitude"]],
                },
                "serie": serie,
            }
        )
    return todas_meses


def salvar(features, meses, saida: Path) -> None:
    payload = {
        "meses": meses,
        "features": features,
    }
    texto = (
        "// Gerado por backend/gerar_historico_geo.py — histórico de cheias/vazantes\n"
        "// e navegabilidade por período. Fonte: hydroweb.next (altimetria satélite)\n"
        "// + BHAE/cota_fundo (hidrowize.db) + calado RN029.\n"
        "window.HISTORICO_NIVEL = "
        + json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        + ";\n"
    )
    saida.parent.mkdir(parents=True, exist_ok=True)
    saida.write_text(texto, encoding="utf-8")
    print(f"Escrito {saida} ({saida.stat().st_size / 1e6:.1f} MB)")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--raio-m", type=float, default=RAIO_M_DEFAULT,
                        help=f"Raio de associação ao trecho (default {RAIO_M_DEFAULT:g} m)")
    parser.add_argument("--largura-min-m", type=float, default=LARGURA_MIN_M_DEFAULT,
                        help=f"Largura mínima do trecho para manter (default {LARGURA_MIN_M_DEFAULT:g} m)")
    parser.add_argument("--saida", type=Path, default=SAIDA_DEFAULT,
                        help="Caminho de saída do arquivo JS")
    args = parser.parse_args()

    estacoes = carregar_estacoes()
    print(f"{len(estacoes)} estações virtuais.")
    trechos = carregar_trechos()
    trechos_assoc = associar_trecho(estacoes, args.raio_m, trechos)
    cobertas = sum(1 for v in trechos_assoc.values() if v is not None)
    largas = sum(
        1 for v in trechos_assoc.values()
        if v is not None and v["largura_m"] is not None and v["largura_m"] >= args.largura_min_m
    )
    print(f"{cobertas} com trecho no raio; {largas} com largura >= {args.largura_min_m:g} m.")

    niveis, medias = ler_series()

    features: list[dict] = []
    meses = gerar(features, estacoes, trechos_assoc, niveis, medias)
    salvar(features, meses, args.saida)
    print(f"Histórico com {len(features)} estações amostradas, "
          f"{len(meses)} meses ({meses[0]} -> {meses[-1]}).")


if __name__ == "__main__":
    sys.exit(main())
