"""Extrai sondagens (profundidade) de uma carta náutica raster (GeoTIFF).

Uma carta náutica raster (RNC) codifica a profundidade em CORES — áreas de
profundidade (faixas) — e em números impressos (sondagens). Este script lê um
GeoTIFF georreferenciado, classifica os pixels conforme uma legenda
cor→profundidade (editável) e exporta pontos (lon, lat, profundidade) como
GeoJSON e CSV.

Uso:
    python extrair_sondagens_carta.py carta.tif
    python extrair_sondagens_carta.py carta.tif --legenda legenda.json --passo 10 --out sondagens.geojson
    python extrair_sondagens_carta.py carta.tif --areas          # também gera polígonos de faixas

Requisitos: pip install pillow numpy opencv-python

Observações:
- Se a Marinha entregar a carta em formato BSB (.kap), converta antes para
  GeoTIFF (ex.: gdal_translate -of GTiff carta.kap carta.tif, ou QGIS).
- A legenda de cores varia por carta. Ajuste o JSON de legenda conforme a
  legenda impressa na própria carta (tabela de profundidades × cores).
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

# --------------------------------------------------------------------------- #
# Georreferenciamento (GeoTIFF)
# --------------------------------------------------------------------------- #

TAG_PIXEL_SCALE = 33550   # ModelPixelScaleTag  -> (sx, sy, sz)
TAG_TIEPOINT = 33922      # ModelTiepointTag    -> (i, j, k, x, y, z)
TAG_TRANSFORM = 34264     # ModelTransformationTag -> 16 doubles


def _float(v) -> float:
    return float(v)


def ler_georef(im: Image.Image) -> tuple[float, float, float, float]:
    """Retorna (scale_x, scale_y, lon_origem, lat_origem) a partir das tags GeoTIFF.

    scale_x/scale_y: graus por pixel (scale_y costuma ser negativo — norte para cima).
    lon/lat_origem: coordenada do canto superior-esquerdo (pixel 0,0).
    """
    tags = getattr(im, "tag_v2", None)
    if tags is None:
        raise ValueError("A imagem não é um GeoTIFF (sem tags TIFF).")

    # 1) ModelTransformationTag (matriz affine 4x4, mais raro)
    m = tags.get(TAG_TRANSFORM)
    if m:
        m = [_float(x) for x in m]
        sx, sy = m[0], m[5]
        lon0, lat0 = m[3], m[7]
        return sx, sy, lon0, lat0

    # 2) ModelPixelScaleTag + ModelTiepointTag (padrão para RNC norte-acima)
    scale = tags.get(TAG_PIXEL_SCALE)
    tie = tags.get(TAG_TIEPOINT)
    if not scale or not tie:
        raise ValueError(
            "GeoTIFF sem georreferenciamento (tags 33550/33922 ausentes). "
            "A carta pode estar sem referência; use QGIS/GDAL para georreferenciar."
        )
    sx, sy = _float(scale[0]), _float(scale[1])
    # tie = (i, j, k, x, y, z) do pixel (i, j) = (0, 0)
    lon0, lat0 = _float(tie[3]), _float(tie[4])
    return sx, sy, lon0, lat0


def pixel_para_lonlat(col: int, row: int, georef) -> tuple[float, float]:
    sx, sy, lon0, lat0 = georef
    return lon0 + col * sx, lat0 + row * sy


# --------------------------------------------------------------------------- #
# Legenda cor → profundidade
# --------------------------------------------------------------------------- #

LEGENDA_PADRAO = [
    # Exemplo com as cores típicas de RNC (IHO S-4). AJUSTE os valores
    # conforme a legenda da sua carta (as faixas mudam de carta para carta).
    {"rotulo": "profundo",      "cor": [255, 255, 255], "prof_min": 30.0, "prof_max": 100.0},
    {"rotulo": "20-30m",        "cor": [170, 221, 255], "prof_min": 20.0, "prof_max": 30.0},
    {"rotulo": "10-20m",        "cor": [120, 195, 255], "prof_min": 10.0, "prof_max": 20.0},
    {"rotulo": "5-10m",         "cor": [80, 160, 235],  "prof_min": 5.0,  "prof_max": 10.0},
    {"rotulo": "0-5m (raso)",   "cor": [40, 110, 200],  "prof_min": 0.0,  "prof_max": 5.0},
    # Áreas de secagem (intertidal) e terra não geram profundidade:
    # {"rotulo": "seca", "cor": [190, 210, 160], "prof_min": None, "prof_max": None},
]


def carregar_legenda(caminho: str | None) -> list[dict]:
    if caminho:
        with open(caminho, encoding="utf-8") as f:
            return json.load(f)
    return LEGENDA_PADRAO


def cor_proxima(rgb, legenda: list[dict], tolerancia: float) -> dict | None:
    """Retorna a entrada da legenda cuja cor está mais próxima do pixel (dentro da tolerância)."""
    melhor, melhor_d = None, float("inf")
    for e in legenda:
        c = np.asarray(e["cor"], dtype=float)
        d = float(np.linalg.norm(np.asarray(rgb, dtype=float) - c))
        if d < melhor_d:
            melhor, melhor_d = e, d
    if melhor is not None and melhor_d <= tolerancia and melhor.get("prof_min") is not None:
        return melhor
    return None


# --------------------------------------------------------------------------- #
# Extração
# --------------------------------------------------------------------------- #

def amostrar_pontos(img_np: np.ndarray, legenda, tolerancia, passo, georef):
    h, w = img_np.shape[:2]
    pontos = []
    for row in range(0, h, passo):
        for col in range(0, w, passo):
            rgb = img_np[row, col][:3]
            e = cor_proxima(rgb, legenda, tolerancia)
            if e is None:
                continue
            lon, lat = pixel_para_lonlat(col, row, georef)
            prof = (e["prof_min"] + e["prof_max"]) / 2.0
            pontos.append({
                "lon": round(lon, 6), "lat": round(lat, 6),
                "profundidade_m": round(prof, 2),
                "profundidade_min_m": e["prof_min"],
                "profundidade_max_m": e["prof_max"],
                "rotulo": e["rotulo"],
                "cor": e["cor"],
            })
    return pontos


def gerar_areas(img_np: np.ndarray, legenda, tolerancia, georef, max_dim=2000):
    """Classifica a imagem inteira e extrai polígonos das faixas de profundidade."""
    import cv2

    h, w = img_np.shape[:2]
    fator = max(1.0, max(h, w) / max_dim)
    if fator > 1.0:
        img_np = cv2.resize(img_np, (int(w / fator), int(h / fator)),
                            interpolation=cv2.INTER_AREA)

    h, w = img_np.shape[:2]
    rotulo_map = np.zeros((h, w), dtype=np.int32)
    prof_map = np.full((h, w), np.nan, dtype=np.float64)

    cores = np.array([e["cor"] for e in legenda], dtype=float)
    for idx, e in enumerate(legenda):
        d = np.linalg.norm(img_np[:, :, :3].astype(float) - cores[idx], axis=2)
        mask = d <= tolerancia
        rotulo_map[mask] = idx + 1
        prof_map[mask] = (e["prof_min"] + e["prof_max"]) / 2.0

    areas = []
    sx, sy, lon0, lat0 = georef
    for idx, e in enumerate(legenda):
        binmask = (rotulo_map == idx + 1).astype(np.uint8)
        if binmask.sum() == 0:
            continue
        contornos, _ = cv2.findContours(binmask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for c in contornos:
            if cv2.contourArea(c) < 20:
                continue
            pts = [(float(px) * fator, float(py) * fator) for (px, py) in c.reshape(-1, 2)]
            if len(pts) < 4:
                continue
            coords = [[round(pixel_para_lonlat(px, py, georef)[0], 6),
                       round(pixel_para_lonlat(px, py, georef)[1], 6)] for (px, py) in pts]
            coords.append(coords[0])
            areas.append({
                "rotulo": e["rotulo"],
                "profundidade_m": round((e["prof_min"] + e["prof_max"]) / 2.0, 2),
                "coords": coords,
            })
    return areas


# --------------------------------------------------------------------------- #
# Saída
# --------------------------------------------------------------------------- #

def salvar_geojson(pontos: list[dict], areas: list[dict], saida: str) -> None:
    feats = []
    for p in pontos:
        feats.append({
            "type": "Feature",
            "properties": {
                "profundidade_m": p["profundidade_m"],
                "profundidade_min_m": p["profundidade_min_m"],
                "profundidade_max_m": p["profundidade_max_m"],
                "rotulo": p["rotulo"],
                "cor": p["cor"],
            },
            "geometry": {"type": "Point", "coordinates": [p["lon"], p["lat"]]},
        })
    for a in areas:
        feats.append({
            "type": "Feature",
            "properties": {
                "profundidade_m": a["profundidade_m"],
                "rotulo": a["rotulo"],
                "tipo": "area",
            },
            "geometry": {"type": "Polygon", "coordinates": [a["coords"]]},
        })
    with open(saida, "w", encoding="utf-8") as f:
        json.dump({"type": "FeatureCollection", "features": feats}, f, ensure_ascii=False)


def salvar_csv(pontos: list[dict], saida: str) -> None:
    with open(saida, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["longitude", "latitude", "profundidade_m", "profundidade_min_m",
                    "profundidade_max_m", "rotulo"])
        for p in pontos:
            w.writerow([p["lon"], p["lat"], p["profundidade_m"],
                        p["profundidade_min_m"], p["profundidade_max_m"], p["rotulo"]])


def main() -> None:
    ap = argparse.ArgumentParser(description="Extrai sondagens de carta náutica raster (GeoTIFF)")
    ap.add_argument("carta", help="Caminho do GeoTIFF da carta náutica")
    ap.add_argument("--legenda", help="JSON cor→profundidade (opcional; usa legenda de exemplo)")
    ap.add_argument("--passo", type=int, default=10, help="Passo da grade de amostragem em pixels")
    ap.add_argument("--tolerancia", type=float, default=40.0, help="Tolerância de cor (distância RGB)")
    ap.add_argument("--areas", action="store_true", help="Também gera polígonos das faixas de profundidade")
    ap.add_argument("--out", help="Saída GeoJSON (padrão: sondagens.geojson)")
    args = ap.parse_args()

    legenda = carregar_legenda(args.legenda)
    im = Image.open(args.carta)
    if im.mode not in ("RGB", "RGBA"):
        im = im.convert("RGB")

    georef = ler_georef(im)
    print(f"Georef: escala=({georef[0]:.7f}, {georef[1]:.7f}) graus/px | origem=({georef[2]:.5f}, {georef[3]:.5f})")

    img_np = np.asarray(im)
    pontos = amostrar_pontos(img_np, legenda, args.tolerancia, args.passo, georef)
    print(f"{len(pontos)} pontos de profundidade amostrados")

    areas = gerar_areas(img_np, legenda, args.tolerancia, georef) if args.areas else []

    base = Path(args.carta).stem
    out_geo = args.out or f"{base}_sondagens.geojson"
    out_csv = f"{base}_sondagens.csv"

    salvar_geojson(pontos, areas, out_geo)
    salvar_csv(pontos, out_csv)
    print(f"GeoJSON: {out_geo}  |  CSV: {out_csv}  |  áreas: {len(areas)}")


if __name__ == "__main__":
    main()
