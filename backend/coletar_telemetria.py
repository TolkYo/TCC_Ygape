"""Coletor incremental de cotas telemétricas (REST v2) para as estações AM.

Acumula as leituras dos últimos 30 dias (limite da API) em um CSV local,
evitando duplicatas a cada execução. Com o tempo (execuções periódicas),
gera a base histórica para estações sem dados no SOAP (ex.: Manaus, UHEs).

Uso:
    python coletar_telemetria.py                     # baixa/atualiza leituras
    python coletar_telemetria.py --resumo            # resumo min/max/media acumulado
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import ana_client

RAIZ = Path(__file__).resolve().parent.parent
CSV_ENRIQUECIDO = Path(__file__).resolve().parent / "estacoes_am_enriquecidas.csv"
CSV_BASE = RAIZ / "estacoes_am.csv"
SAIDA = Path(__file__).resolve().parent / "telemetria_cotas_am.csv"

CAMPOS = [
    "codigo_estacao",
    "data_hora_medicao",
    "cota_adotada",
    "cota_status",
    "vazao_adotada",
    "vazao_status",
    "chuva_adotada",
    "chuva_status",
    "data_atualizacao",
]


def carregar_csv(caminho: Path) -> list[dict]:
    if not caminho.exists():
        return []
    with open(caminho, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f, delimiter=";"))


def salvar_csv(linhas: list[dict], caminho: Path) -> None:
    with open(caminho, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=CAMPOS, delimiter=";")
        writer.writeheader()
        writer.writerows(linhas)


def estacoes_telemetricas() -> list[str]:
    if CSV_ENRIQUECIDO.exists():
        linhas = carregar_csv(CSV_ENRIQUECIDO)
        return [
            l["codigo_estacao"].strip()
            for l in linhas
            if l.get("telemetrica") == "1"
        ]
    return [l["codigo_estacao"].strip() for l in carregar_csv(CSV_BASE)]


def baixar_lote(cliente: ana_client.AnaClient, codigos: list[str], data_busca: str) -> list[dict]:
    dados = cliente._get(
        "/EstacoesTelemetricas/HidroinfoanaSerieTelemetricaAdotada/v2",
        params={
            "Codigos_Estacoes": ",".join(codigos),
            "Tipo Filtro Data": "DATA_LEITURA",
            "Data de Busca": data_busca,
            "Range Intervalo de busca": "DIAS_30",
        },
    )
    novos = []
    for item in dados.get("items") or []:
        novos.append(
            {
                "codigo_estacao": item.get("codigoestacao"),
                "data_hora_medicao": item.get("Data_Hora_Medicao"),
                "cota_adotada": item.get("Cota_Adotada"),
                "cota_status": item.get("Cota_Adotada_Status"),
                "vazao_adotada": item.get("Vazao_Adotada"),
                "vazao_status": item.get("Vazao_Adotada_Status"),
                "chuva_adotada": item.get("Chuva_Adotada"),
                "chuva_status": item.get("Chuva_Adotada_Status"),
                "data_atualizacao": item.get("Data_Atualizacao"),
            }
        )
    return novos


def resumo_telemetria() -> None:
    linhas = carregar_csv(SAIDA)
    if not linhas:
        print("Nenhum dado acumulado ainda. Rode sem --resumo primeiro.")
        return
    por_estacao: dict[str, list[float]] = {}
    for l in linhas:
        try:
            v = float(l["cota_adotada"])
        except (TypeError, ValueError):
            continue
        if v <= 0:
            continue
        por_estacao.setdefault(l["codigo_estacao"], []).append(v)

    print(f"Total de leituras acumuladas: {len(linhas)}")
    print(f"{'Estacao':12s} {'leituras':>8s} {'cota_min':>10s} {'cota_max':>10s} {'cota_med':>10s}")
    for codigo, vals in sorted(por_estacao.items()):
        print(
            f"{codigo:12s} {len(vals):8d} {min(vals):10.2f} {max(vals):10.2f} "
            f"{sum(vals)/len(vals):10.2f}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Coletor incremental de telemetria ANA")
    parser.add_argument("--resumo", action="store_true", help="Mostra resumo acumulado")
    parser.add_argument("--data-busca", help="Data de busca (yyyy-MM-dd); default hoje")
    args = parser.parse_args()

    if args.resumo:
        resumo_telemetria()
        return

    codigos = estacoes_telemetricas()
    print(f"{len(codigos)} estacoes telemetricas AM")

    cliente = ana_client.AnaClient()
    data_busca = args.data_busca or "2026-08-17"
    existentes = carregar_csv(SAIDA)
    chaves_existentes = {
        (l["codigo_estacao"], l["data_hora_medicao"]) for l in existentes
    }

    todas: list[dict] = list(existentes)
    inseridas = 0
    for i in range(0, len(codigos), 10):
        lote = codigos[i : i + 10]
        novos = baixar_lote(cliente, lote, data_busca)
        para_lote = [
            n
            for n in novos
            if (n["codigo_estacao"], n["data_hora_medicao"]) not in chaves_existentes
        ]
        for n in para_lote:
            chaves_existentes.add((n["codigo_estacao"], n["data_hora_medicao"]))
        todas.extend(para_lote)
        inseridas += len(para_lote)
        print(
            f"lote {i//10+1}: {len(lote)} estacoes -> {len(novos)} leituras "
            f"({len(para_lote)} novas)", flush=True
        )

    if inseridas:
        salvar_csv(todas, SAIDA)
    print(f"\nTotal acumulado: {len(todas)} leituras | inseridas agora: {inseridas}")
    print(f"CSV: {SAIDA}")


if __name__ == "__main__":
    sys.exit(main())
