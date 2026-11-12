"""Coleta a serie DIARIA de cotas das estacoes do Amazonas (SOAP ANA).

Diferente de `coletar_cotas_historicas.py` (que persiste apenas min/max/media),
este coletor expande os campos diarios `Cota01..Cota31` do retorno mensal do
SOAP `HidroSerieHistorica` e grava uma linha por (estacao, dia). Serve de base
para o registro semanal de navegabilidade.

Mescla os dois niveis de consistencia:
  - 2 = consistido (controle de qualidade; periodos antigos)
  - 1 = bruto (recente)
Quando o mesmo dia existe nos dois, prevalece o consistido.

Uso:
    python coletar_cotas_diarias.py
    python coletar_cotas_diarias.py --anos 10 --saida planilhas/cotas_diarias_am.csv
    python coletar_cotas_diarias.py --codigo 15400000
"""

from __future__ import annotations

import argparse
import csv
import sys
import time
from pathlib import Path

import ana_soap

RAIZ = Path(__file__).resolve().parent.parent
PLANILHAS = RAIZ / "planilhas"

# Ordem de preferencia: consistido antes do bruto.
NIVEIS = (ana_soap.NIVEL_CONSISTIDO, ana_soap.NIVEL_BRUTO)

CANDIDATOS_ESTACOES = (
    PLANILHAS / "estacoes_am.csv",
    RAIZ / "estacoes_am.csv",
    PLANILHAS / "estacoes_am_enriquecidas.csv",
)

SAIDA = PLANILHAS / "cotas_diarias_am.csv"


def localizar_estacoes() -> Path:
    for caminho in CANDIDATOS_ESTACOES:
        if caminho.exists():
            return caminho
    raise SystemExit(
        "CSV de estacoes nao encontrado. Esperado em: "
        + ", ".join(str(c) for c in CANDIDATOS_ESTACOES)
    )


def carregar_csv(caminho: Path) -> list[dict]:
    with open(caminho, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f, delimiter=";"))


def salvar_csv(linhas: list[dict], caminho: Path) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    campos = ["codigo_estacao", "nome_estacao", "data", "cota_cm",
              "status", "nivel_consistencia"]
    with open(caminho, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=campos, delimiter=";")
        writer.writeheader()
        writer.writerows(linhas)


def coletar_estacao(codigo: str, anos: int, ano_atual: int) -> dict[str, dict]:
    """Retorna {data: linha} mesclando consistido (2) e bruto (1)."""
    data_inicio = f"01/01/{ano_atual - anos + 1}"
    por_data: dict[str, dict] = {}
    for nivel in NIVEIS:
        try:
            diarias = ana_soap.serie_diaria(
                codigo, data_inicio, nivel_consistencia=nivel
            )
        except Exception as exc:  # rede instavel: segue para o proximo nivel
            print(f"    nivel {nivel}: erro ({exc})", flush=True)
            continue
        for linha in diarias:
            por_data.setdefault(linha["data"], linha)
    return por_data


def main() -> None:
    parser = argparse.ArgumentParser(description="Coleta cotas diarias das estacoes AM")
    parser.add_argument("--anos", type=int, default=5, help="Janela historica (default 5)")
    parser.add_argument("--ano-atual", type=int, default=2026)
    parser.add_argument("--saida", default=str(SAIDA))
    parser.add_argument("--delay", type=float, default=0.5, help="Segundos entre chamadas")
    parser.add_argument("--codigo", help="Coleta apenas uma estacao (teste)")
    parser.add_argument("--limite", type=int, help="Limita o numero de estacoes (teste)")
    args = parser.parse_args()

    if args.codigo:
        estacoes = [{"codigo_estacao": args.codigo, "nome_estacao": ""}]
    else:
        caminho = localizar_estacoes()
        estacoes = carregar_csv(caminho)
        print(f"estacoes: {caminho} ({len(estacoes)})", flush=True)
        if args.limite:
            estacoes = estacoes[: args.limite]

    resultados: list[dict] = []
    resumo: list[tuple[str, int]] = []
    for i, est in enumerate(estacoes, 1):
        codigo = est["codigo_estacao"].strip()
        nome = est.get("nome_estacao", "")
        por_data = coletar_estacao(codigo, args.anos, args.ano_atual)
        for data in sorted(por_data):
            linha = dict(por_data[data])
            linha["nome_estacao"] = nome
            resultados.append(linha)
        resumo.append((codigo, len(por_data)))
        print(f"[{i:3d}/{len(estacoes)}] {codigo} {nome:30s} -> {len(por_data)} dias",
              flush=True)
        time.sleep(args.delay)

    if not resultados:
        print("Nenhuma leitura coletada.")
        return

    resultados.sort(key=lambda r: (r["codigo_estacao"], r["data"]))
    salvar_csv(resultados, Path(args.saida))

    vazias = [c for c, n in resumo if n == 0]
    datas = [r["data"] for r in resultados]
    print(f"\nCSV salvo: {args.saida}")
    print(f"estacoes: {len(resumo)} | linhas diarias: {len(resultados)}")
    print(f"periodo: {min(datas)} -> {max(datas)}")
    if vazias:
        print(f"estacoes sem dados ({len(vazias)}): {', '.join(vazias)}")


if __name__ == "__main__":
    sys.exit(main())
