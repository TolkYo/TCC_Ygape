"""Coleta a cota minima/maxima/media historica das estacoes AM (SOAP ANA).

Gera cotas_historicas_am.csv na raiz do backend com as estatisticas por
estacao. Usa a SOAP HidroSerieHistorica (a REST HidroSerieCotas/v1 esta
inoperante). Uso:

    python coletar_cotas_historicas.py
    python coletar_cotas_historicas.py --anos 10 --saida cotas.csv
"""

from __future__ import annotations

import argparse
import csv
import sys
import time
from pathlib import Path

import ana_soap
from validar_estacoes import carregar_csv, salvar_csv

RAIZ = Path(__file__).resolve().parent.parent
CSV_ESTACOES = RAIZ / "estacoes_am.csv"


def main() -> None:
    parser = argparse.ArgumentParser(description="Coleta cota historica das estacoes AM")
    parser.add_argument("--anos", type=int, default=5, help="Janela historica em anos (default 5)")
    parser.add_argument("--saida", default="cotas_historicas_am.csv")
    parser.add_argument("--delay", type=float, default=0.5, help="Segundos entre chamadas")
    args = parser.parse_args()

    estacoes = carregar_csv(CSV_ESTACOES)
    print(f"{len(estacoes)} estacoes a processar (janela de {args.anos} anos)")

    resultados: list[dict] = []
    for i, est in enumerate(estacoes, 1):
        codigo = est["codigo_estacao"].strip()
        res = ana_soap.resumo_cotas(codigo, anos=args.anos)
        if res:
            res["nome_estacao"] = est.get("nome_estacao", "")
            res["municipio"] = est.get("municipio", "")
            status = "OK"
        else:
            res = {
                "codigo_estacao": codigo,
                "nome_estacao": est.get("nome_estacao", ""),
                "municipio": est.get("municipio", ""),
                "nivel_consistencia": "",
                "registros": 0,
                "data_inicio_serie": "",
                "data_fim_serie": "",
                "cota_minima": "",
                "cota_maxima": "",
                "cota_media": "",
            }
            status = "SEM DADOS"
        resultados.append(res)
        print(f"[{i:3d}/{len(estacoes)}] {codigo} {res.get('nome_estacao', ''):30s} -> {status}", flush=True)
        time.sleep(args.delay)

    if resultados:
        salvar_csv(resultados, Path(args.saida))
        print(f"\nCSV salvo em {args.saida}")


if __name__ == "__main__":
    sys.exit(main())
