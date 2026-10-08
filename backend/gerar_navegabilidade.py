"""Gera estacoes_am_navegabilidade.csv cruzando as fontes de cota.

Fontes:
  - estacoes_am_enriquecidas.csv  -> cadastro (nome, rio, municipio, lat/lon)
  - cotas_historicas_am.csv       -> cota minima historica (SOAP)
  - telemetria_cotas_am.csv       -> cota atual + minima acumulada (REST v2)

Regra de navegabilidade (proposta em mapeamento_fontes.md):
  - NAVEGAVEL  se cota_atual - cota_minima_historica >= 50 cm
  - RESTRITO   se 0 <= cota_atual - cota_minima_historica < 50 cm
  - CRITICO    se cota_atual < cota_minima_historica
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
BACKEND = Path(__file__).resolve().parent

CSV_ENRIQUECIDO = BACKEND / "estacoes_am_enriquecidas.csv"
CSV_HISTORICO = BACKEND / "cotas_historicas_am.csv"
CSV_TELEMETRIA = BACKEND / "telemetria_cotas_am.csv"
SAIDA = BACKEND / "estacoes_am_navegabilidade.csv"

LIMIAR = 50.0  # cm de folga em relacao a cota minima historica


def carregar_csv(caminho: Path) -> list[dict]:
    if not caminho.exists():
        return []
    with open(caminho, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f, delimiter=";"))


def flutua(valor) -> float | None:
    try:
        return float(valor)
    except (TypeError, ValueError):
        return None


def estatisticas_telemetria() -> dict[str, dict]:
    """Por estacao: cota_atual (leitura mais recente) e cota_minima acumulada."""
    result: dict[str, dict] = {}
    por_estacao: dict[str, list[dict]] = {}
    for linha in carregar_csv(CSV_TELEMETRIA):
        por_estacao.setdefault(linha["codigo_estacao"], []).append(linha)

    for codigo, leituras in por_estacao.items():
        vals = [(flutua(l["cota_adotada"]), l["data_hora_medicao"]) for l in leituras]
        vals = [(v, d) for v, d in vals if v is not None and v > 0]
        if not vals:
            continue
        minimo = min(v for v, _ in vals)
        atual = max(vals, key=lambda x: x[1])[0]
        result[codigo] = {"cota_atual": atual, "cota_minima_tel": minimo}
    return result


def classificacao(cota_atual: float | None, cota_minima: float | None, limiar: float) -> str:
    if cota_atual is None or cota_minima is None:
        return "SEM DADOS"
    folga = cota_atual - cota_minima
    if folga >= limiar:
        return "NAVEGAVEL"
    if folga >= 0:
        return "RESTRITO"
    return "CRITICO"


def main() -> None:
    parser = argparse.ArgumentParser(description="Gera CSV de navegabilidade")
    parser.add_argument("--limiar", type=float, default=LIMIAR, help="Folga em cm (default 50)")
    parser.add_argument("--saida", default=str(SAIDA))
    args = parser.parse_args()

    limiar = args.limiar

    cadastro = {l["codigo_estacao"].strip(): l for l in carregar_csv(CSV_ENRIQUECIDO)}
    historico = {l["codigo_estacao"].strip(): l for l in carregar_csv(CSV_HISTORICO)}
    tel = estatisticas_telemetria()

    codigos = list(cadastro)
    linhas = []
    for codigo in codigos:
        hist = historico.get(codigo, {})
        tel_est = tel.get(codigo, {})

        cota_minima = flutua(hist.get("cota_minima"))
        cota_atual = tel_est.get("cota_atual")
        cota_minima_tel = tel_est.get("cota_minima_tel")

        # prefere o minimo do SOAP; completa com a telemetria acumulada
        cota_minima_final = cota_minima if cota_minima is not None else cota_minima_tel
        if cota_atual is None and hist.get("cota_media"):
            cota_atual = flutua(hist.get("cota_media"))

        est = cadastro[codigo]
        linhas.append(
            {
                "codigo_estacao": codigo,
                "nome_estacao": est.get("nome_estacao"),
                "rio": est.get("nome_rio") or hist.get("nome_estacao"),
                "municipio": est.get("municipio"),
                "latitude": est.get("latitude"),
                "longitude": est.get("longitude"),
                "telemetrica": est.get("telemetrica"),
                "cota_atual": f"{cota_atual:.2f}" if cota_atual is not None else "",
                "cota_minima_historica": f"{cota_minima_final:.2f}" if cota_minima_final is not None else "",
                "fonte_minima": "SOAP" if cota_minima is not None else ("TELEMETRIA" if cota_minima_tel is not None else ""),
                "status_navegabilidade": classificacao(cota_atual, cota_minima_final, limiar),
            }
        )

    campos = list(linhas[0].keys())
    with open(args.saida, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=campos, delimiter=";")
        writer.writeheader()
        writer.writerows(linhas)

    contagem: dict[str, int] = {}
    for l in linhas:
        contagem[l["status_navegabilidade"]] = contagem.get(l["status_navegabilidade"], 0) + 1
    print(f"CSV gerado: {args.saida} ({len(linhas)} estacoes)")
    for status, n in sorted(contagem.items()):
        print(f"  {status:12s}: {n}")


if __name__ == "__main__":
    sys.exit(main())
