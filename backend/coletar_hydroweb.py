"""Coletor de dados hidrográficos de satélite — hydroweb.next (CNES/LEGOS).

Complementa os dados in situ (telemetria ANA) com produtos de altimetria espacial:

  1. Estações virtuais de nível d'água (altimetria)  -> HYDROWEB_RIVERS_OPE
  2. Batimetria de rio reconstruída via SWOT/SICFLOW  -> SWOT_L4_BATHY_SICFLOW
  3. Vazão (descarga) derivada do SWOT                -> SWOT_L4_SOS_DISCHARGE

O catálogo STAC é público (sem autenticação). O download exige uma API key
gratuita do hydroweb.next, lida do .env na raiz (HYDROWEB_API_KEY).

Uso:
    python coletar_hydroweb.py --listar       # lista estações virtuais na bacia
    python coletar_hydroweb.py --estacoes     # baixa e consolida as estações (CSV)
    python coletar_hydroweb.py --batimetria   # baixa a batimetria SICFLOW (NetCDF)
    python coletar_hydroweb.py --vazao        # baixa a vazão SWOT (NetCDF)
    python coletar_hydroweb.py --tudo         # executa todos os downloads
"""

from __future__ import annotations

import argparse
import csv
import os
import shutil
import sqlite3
import sys
import zipfile
from datetime import datetime
from pathlib import Path

import requests
from dotenv import load_dotenv

RAIZ = Path(__file__).resolve().parent.parent
load_dotenv(RAIZ / ".env")

STAC_URL = "https://hydroweb.next.theia-land.fr/api/catalog/stac"
COL_ESTACOES = "HYDROWEB_RIVERS_OPE"
COL_BATIMETRIA = "SWOT_L4_BATHY_SICFLOW"
COL_VAZAO = "SWOT_L4_SOS_DISCHARGE"

# Bacia amazônica completa (drenagem internacional): cabeceiras andinas a oeste,
# Bolívia ao sul, Guianas/Colômbia ao norte. ~4,7 mil estações virtuais.
AMAZON_BBOX = [-80.0, -21.0, -48.0, 6.0]

SAIDA = RAIZ / "data" / "satelite"
CSV_ESTACOES = SAIDA / "estacoes_virtuais.csv"
CSV_SERIES = SAIDA / "series_nivel_satelite.csv"
DB = RAIZ / "data" / "hidrowize.db"

CAMPOS_ESTACOES = [
    "codigo", "rio", "estacao", "km", "latitude", "longitude", "inicio", "fim",
]
CAMPOS_SERIES = [
    "codigo", "rio", "estacao", "km", "latitude", "longitude",
    "data", "nivel_m", "incerteza_m",
]

FORMATOS_DATA = [
    "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d", "%Y/%m/%d %H:%M:%S",
    "%Y/%m/%d", "%d/%m/%Y", "%d-%m-%Y",
]


def _get(url: str, params: dict | None = None) -> dict:
    resp = requests.get(url, params=params, timeout=120,
                        headers={"User-Agent": "hidrowize/0.1"})
    resp.raise_for_status()
    return resp.json()


def _api_key() -> str:
    chave = os.getenv("HYDROWEB_API_KEY")
    if not chave:
        raise RuntimeError(
            "HYDROWEB_API_KEY não definida. Crie a chave em hydroweb.next "
            "(conta > API key) e adicione 'HYDROWEB_API_KEY=...' ao .env da raiz."
        )
    return chave


def _extrair_meta(feature: dict) -> dict:
    codigo = feature["id"].split("@")[0]
    partes = codigo.split("_")
    rio = partes[1] if len(partes) > 1 else ""
    km = partes[-1][2:] if len(partes) > 1 and partes[-1].startswith("KM") else ""
    estacao = "_".join(partes[2:-1])
    lon, lat = (feature.get("geometry") or {}).get("coordinates", [None, None])
    props = feature.get("properties", {})
    return {
        "codigo": codigo,
        "rio": rio,
        "estacao": estacao,
        "km": km,
        "latitude": lat,
        "longitude": lon,
        "inicio": props.get("start_datetime"),
        "fim": props.get("end_datetime"),
    }


def listar_estacoes(bbox: list[float]) -> list[dict]:
    itens: list[dict] = []
    params: dict | None = {
        "collections": COL_ESTACOES,
        "bbox": ",".join(str(x) for x in bbox),
        "limit": 500,
    }
    url = STAC_URL + "/search"
    while url:
        dados = _get(url, params)
        itens.extend(dados.get("features", []))
        params = None
        url = next(
            (l["href"] for l in dados.get("links", []) if l.get("rel") == "next"),
            None,
        )
    return [_extrair_meta(f) for f in itens]


def _baixar_zip(collection_id: str, bbox: list[float], zip_nome: str, subpasta: str) -> Path:
    import py_hydroweb

    _api_key()
    cliente = py_hydroweb.Client()
    cesta = py_hydroweb.DownloadBasket(download_name=subpasta)
    cesta.add_collection(collection_id, bbox=bbox)
    pasta = SAIDA / subpasta
    pasta.mkdir(parents=True, exist_ok=True)
    print(f"Baixando {collection_id} (bbox={bbox})... isso pode levar alguns minutos.",
          flush=True)
    caminho = cliente.submit_and_download_zip(
        cesta, zip_filename=zip_nome, output_folder=str(pasta)
    )
    return Path(caminho)


def _extrair_zip(zip_path: Path, subpasta: str) -> Path:
    destino = SAIDA / subpasta
    with zipfile.ZipFile(zip_path) as z:
        z.extractall(destino)
    print(f"Extraído em {destino}")
    return destino


def _parse_data(valor: str) -> str | None:
    valor = valor.strip()
    for fmt in FORMATOS_DATA:
        try:
            return datetime.strptime(valor, fmt).isoformat()
        except ValueError:
            continue
    return None


def _parse_numero(valor: str) -> float | None:
    try:
        return float(valor.replace(",", "."))
    except ValueError:
        return None


def _delimitador(linha: str) -> str | None:
    for d in (";", "\t", ","):
        if d in linha:
            return d
    return None


def parsear_serie_txt(caminho: Path) -> list[dict]:
    """Converte um arquivo .txt de estação virtual em registros (data, nivel, incerteza)."""
    linhas = []
    with open(caminho, encoding="utf-8", errors="replace") as f:
        for raw in f:
            linha = raw.strip()
            if linha and not linha.startswith("#"):
                linhas.append(linha)

    if not linhas:
        return []

    delim = _delimitador(linhas[0])
    registros: list[dict] = []
    for linha in linhas:
        colunas = [c.strip() for c in linha.split(delim)] if delim else linha.split()
        if not colunas:
            continue
        data = _parse_data(colunas[0])
        if data is None:
            continue  # provável linha de cabeçalho
        numeros = [v for v in (_parse_numero(c) for c in colunas[1:]) if v is not None]
        registros.append({
            "data": data,
            "nivel_m": numeros[0] if numeros else None,
            "incerteza_m": numeros[1] if len(numeros) > 1 else None,
        })
    return registros


def _codigo_de_nome(nome: str) -> str:
    codigo = nome
    if codigo.startswith("hydroprd_"):
        codigo = codigo[len("hydroprd_"):]
    if codigo.endswith(".txt"):
        codigo = codigo[:-4]
    for sufixo in ("_exp", "_ope"):
        if codigo.endswith(sufixo):
            codigo = codigo[:-len(sufixo)]
            break
    return codigo


def _salvar_csv(linhas: list[dict], campos: list[str], caminho: Path) -> None:
    with open(caminho, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=campos, delimiter=";")
        writer.writeheader()
        writer.writerows(linhas)


def _persistir_satelite(estacoes: list[dict], series: list[dict], fonte: str) -> tuple[int, int]:
    from gerar_sqlite import (
        criar_schema_satelite,
        upsert_estacoes_virtuais,
        upsert_series_nivel_satelite,
    )

    DB.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB)
    try:
        criar_schema_satelite(con)
        n_est = upsert_estacoes_virtuais(con, [{**e, "fonte": fonte} for e in estacoes])
        n_ser = upsert_series_nivel_satelite(con, [{**s, "fonte": fonte} for s in series])
        con.commit()
    finally:
        con.close()
    return n_est, n_ser


def _persistir_netcdf(importador: str, rotulo: str) -> int:
    import importlib

    gs = importlib.import_module("gerar_sqlite")
    con = sqlite3.connect(DB)
    try:
        gs.criar_schema_satelite(con)
        n = getattr(gs, importador)(con)
        con.commit()
    finally:
        con.close()
    print(f"DB: {n} registros de {rotulo} persistidos em {DB}")
    return n


def _contar_tabela(tabela: str) -> int:
    if not DB.exists():
        return 0
    con = sqlite3.connect(DB)
    try:
        try:
            return con.execute(f"SELECT COUNT(*) FROM {tabela}").fetchone()[0]
        except sqlite3.OperationalError:
            return 0
    finally:
        con.close()


def _limpar_subpasta(subpasta: str) -> None:
    pasta = SAIDA / subpasta
    if pasta.exists():
        shutil.rmtree(pasta)
        print(f"Arquivos intermediários removidos: {pasta}")


def comando_listar(bbox: list[float]) -> None:
    estacoes = listar_estacoes(bbox)
    print(f"{len(estacoes)} estações virtuais no bbox {bbox}")
    for e in estacoes[:20]:
        print(f"  {e['codigo']:40s} lon {e['longitude']:>8} lat {e['latitude']:>8} "
              f"rio={e['rio']}")
    if len(estacoes) > 20:
        print(f"  ... e mais {len(estacoes) - 20}")
    SAIDA.mkdir(parents=True, exist_ok=True)
    _salvar_csv(estacoes, CAMPOS_ESTACOES, CSV_ESTACOES)
    print(f"CSV: {CSV_ESTACOES}")
    n_est, _ = _persistir_satelite(estacoes, [], COL_ESTACOES)
    print(f"DB: {n_est} estações persistidas em {DB}")


def _consolidar_series(pasta: Path, mapa: dict) -> tuple[int, int]:
    """Grava o CSV de séries e persiste no banco em streaming (baixa RAM).

    Em vez de acumular ~590 mil observações em uma lista, itera arquivo a
    arquivo, escreve no CSV e insere no SQLite em lotes de 20 mil. Retorna
    (total de observações, arquivos sem estação correspondente).
    """
    from gerar_sqlite import criar_schema_satelite, upsert_series_nivel_satelite

    DB.parent.mkdir(parents=True, exist_ok=True)
    total = 0
    nao_mapeadas = 0

    def iter_observacoes():
        nonlocal total, nao_mapeadas
        for arq in sorted(pasta.glob("**/*.txt")):
            meta = mapa.get(_codigo_de_nome(arq.name))
            if meta is None:
                nao_mapeadas += 1
                continue
            for obs in parsear_serie_txt(arq):
                total += 1
                yield {
                    "codigo": meta["codigo"],
                    "rio": meta["rio"],
                    "estacao": meta["estacao"],
                    "km": meta["km"],
                    "latitude": meta["latitude"],
                    "longitude": meta["longitude"],
                    "data": obs["data"],
                    "nivel_m": obs["nivel_m"],
                    "incerteza_m": obs["incerteza_m"],
                    "fonte": COL_ESTACOES,
                }

    con = sqlite3.connect(DB)
    try:
        criar_schema_satelite(con)
        with open(CSV_SERIES, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=CAMPOS_SERIES, delimiter=";")
            writer.writeheader()
            lote: list[dict] = []
            for obs in iter_observacoes():
                writer.writerow({campo: obs[campo] for campo in CAMPOS_SERIES})
                lote.append(obs)
                if len(lote) >= 20000:
                    upsert_series_nivel_satelite(con, lote)
                    lote = []
            if lote:
                upsert_series_nivel_satelite(con, lote)
        con.commit()
    finally:
        con.close()
    return total, nao_mapeadas


def comando_estacoes(bbox: list[float], forcar: bool = False) -> None:
    estacoes = listar_estacoes(bbox)
    mapa = {e["codigo"]: e for e in estacoes}
    SAIDA.mkdir(parents=True, exist_ok=True)
    _salvar_csv(estacoes, CAMPOS_ESTACOES, CSV_ESTACOES)

    if not forcar and _contar_tabela("series_nivel_satelite") > 0:
        print("series_nivel_satelite já populada — pulando download "
              "(use --forcar para rebaixar).")
        _persistir_satelite(estacoes, [], COL_ESTACOES)
        return

    zip_path = _baixar_zip(COL_ESTACOES, bbox, "estacoes_virtuais.zip", "estacoes_virtuais")
    pasta = _extrair_zip(zip_path, "estacoes_virtuais")

    n_obs, nao_mapeadas = _consolidar_series(pasta, mapa)
    n_est, _ = _persistir_satelite(estacoes, [], COL_ESTACOES)
    print(f"Consolidado {n_obs} observações de {len(estacoes)} estações "
          f"({nao_mapeadas} arquivos sem correspondência)")
    print(f"CSV: {CSV_SERIES}")
    print(f"DB: {n_est} estações e {n_obs} observações persistidas em {DB}")
    _limpar_subpasta("estacoes_virtuais")


def comando_batimetria(bbox: list[float], forcar: bool = False) -> None:
    if not forcar and _contar_tabela("batimetria_sicflow") > 0:
        print("batimetria_sicflow já populada — pulando download "
              "(use --forcar para rebaixar).")
        return
    print("Atenção: a batimetria SICFLOW é entregue num único NetCDF "
          "(América do Sul inteira); o download pode ser grande.")
    zip_path = _baixar_zip(COL_BATIMETRIA, bbox, "batimetria_sicflow.zip", "batimetria")
    _extrair_zip(zip_path, "batimetria")
    _persistir_netcdf("importar_batimetria_sicflow", "batimetria")
    _limpar_subpasta("batimetria")


def comando_vazao(bbox: list[float], forcar: bool = False) -> None:
    if not forcar and _contar_tabela("series_vazao_satelite") > 0:
        print("series_vazao_satelite já populada — pulando download "
              "(use --forcar para rebaixar).")
        return
    zip_path = _baixar_zip(COL_VAZAO, bbox, "vazao_swot.zip", "vazao")
    _extrair_zip(zip_path, "vazao")
    _persistir_netcdf("importar_series_vazao_satelite", "vazão")
    _limpar_subpasta("vazao")


def _parse_bbox(texto: str) -> list[float]:
    return [float(x) for x in texto.split(",")]


def main() -> None:
    parser = argparse.ArgumentParser(description="Coletor de dados satelitais hydroweb.next")
    parser.add_argument("--listar", action="store_true", help="Lista estações virtuais na bacia")
    parser.add_argument("--estacoes", action="store_true", help="Baixa e consolida estações virtuais")
    parser.add_argument("--batimetria", action="store_true", help="Baixa batimetria SICFLOW")
    parser.add_argument("--vazao", action="store_true", help="Baixa vazão SWOT")
    parser.add_argument("--tudo", action="store_true", help="Executa todos os downloads")
    parser.add_argument("--forcar", action="store_true",
                        help="Força o download mesmo que os dados já estejam no banco")
    parser.add_argument("--bbox", help="Bbox 'minLon,minLat,maxLon,maxLat' (default bacia amazônica)")
    args = parser.parse_args()

    bbox = _parse_bbox(args.bbox) if args.bbox else AMAZON_BBOX

    if not any([args.listar, args.estacoes, args.batimetria, args.vazao, args.tudo]):
        parser.print_help()
        return

    if args.listar:
        comando_listar(bbox)

    if args.estacoes or args.tudo:
        comando_estacoes(bbox, forcar=args.forcar)
    if args.batimetria or args.tudo:
        comando_batimetria(bbox, forcar=args.forcar)
    if args.vazao or args.tudo:
        comando_vazao(bbox, forcar=args.forcar)


if __name__ == "__main__":
    sys.exit(main())
