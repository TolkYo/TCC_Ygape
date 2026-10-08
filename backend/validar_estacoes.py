"""Valida as estacoes de estacoes_am.csv contra o inventario oficial da ANA.

Uso:
    python validar_estacoes.py               # valida e imprime resumo
    python validar_estacoes.py --relatorio relatorio.txt   # salva detalhes
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
from pathlib import Path

import ana_client

RAIZ = Path(__file__).resolve().parent.parent
CSV_ESTACOES = RAIZ / "estacoes_am.csv"


def normalizar_codigo(codigo: str | None) -> str:
    if not codigo:
        return ""
    return str(codigo).strip().lstrip("0")


def carregar_csv(caminho: Path) -> list[dict]:
    with open(caminho, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f, delimiter=";"))


def salvar_csv(linhas: list[dict], caminho: Path) -> None:
    campos = list(linhas[0].keys())
    with open(caminho, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=campos, delimiter=";")
        writer.writeheader()
        writer.writerows(linhas)


def main() -> None:
    parser = argparse.ArgumentParser(description="Valida estacoes AM na base da ANA")
    parser.add_argument("--relatorio", help="Salva relatorio detalhado em arquivo")
    parser.add_argument(
        "--enriquecido",
        metavar="CSV",
        help="Salva CSV enriquecido com dados do inventario da ANA",
    )
    args = parser.parse_args()

    linhas = carregar_csv(CSV_ESTACOES)
    cliente = ana_client.AnaClient()
    inventario = cliente.listar_estacoes(uf="AM")
    print(f"CSV: {len(linhas)} estacoes | Inventario ANA/AM: {len(inventario)}")

    inv = {
        normalizar_codigo(e.get("codigoestacao")): e
        for e in inventario
        if normalizar_codigo(e.get("codigoestacao"))
    }

    validas, invalidas, enriquecidas = [], [], []
    for linha in linhas:
        codigo_csv = linha["codigo_estacao"].strip()
        chave = normalizar_codigo(codigo_csv)
        if chave in inv:
            e = inv[chave]
            validas.append({**linha, "codigo_estacao": codigo_csv})
            enriquecidas.append(
                {
                    **linha,
                    "codigo_estacao": codigo_csv,
                    "nome_ana": e.get("Estacao_Nome"),
                    "tipo_estacao": e.get("Tipo_Estacao"),
                    "telemetrica": e.get("Tipo_Estacao_Telemetrica"),
                    "escala": e.get("Tipo_Estacao_Escala"),
                    "operando": e.get("Operando"),
                    "bacia": e.get("Bacia_Nome"),
                    "sub_bacia": e.get("Sub_Bacia_Nome"),
                    "altitude": e.get("Altitude"),
                    "area_drenagem": e.get("Area_Drenagem"),
                    "operadora": e.get("Operadora_Sigla"),
                    "responsavel": e.get("Responsavel_Sigla"),
                }
            )
        else:
            invalidas.append({**linha, "codigo_estacao": codigo_csv})

    print(f"\nValidas no inventario ANA: {len(validas)}")
    print(f"NAO encontradas: {len(invalidas)}")

    if invalidas:
        print("\n=== Estacoes nao encontradas ===")
        for i in invalidas:
            print(f"  {i['codigo_estacao']} | {i['nome_estacao']} | {i['nome_rio']}")

    if args.relatorio:
        with open(args.relatorio, "w", encoding="utf-8") as f:
            f.write("=== ESTACOES VALIDAS ===\n")
            for v in enriquecidas:
                f.write(
                    f"{v['codigo_estacao']}|{v['nome_estacao']}|{v['nome_ana']}|"
                    f"{v['nome_rio']}|{v['bacia']}|{v['municipio']}|{v['tipo_estacao']}|"
                    f"tele={v['telemetrica']}|escala={v['escala']}|op={v['operando']}\n"
                )
            f.write("\n=== ESTACOES NAO ENCONTRADAS ===\n")
            for i in invalidas:
                f.write(f"{i['codigo_estacao']}|{i['nome_estacao']}|{i['nome_rio']}\n")
        print(f"\nRelatorio salvo em {args.relatorio}")

    if args.enriquecido:
        salvar_csv(enriquecidas, Path(args.enriquecido))
        print(f"CSV enriquecido salvo em {args.enriquecido}")


if __name__ == "__main__":
    sys.exit(main())
