"""RF035 — Regressão de cota de fundo (batimetria SICFLOW → trechos sem batimetria).

Treina um modelo ``cota_fundo = f(atributos AHGN do trecho)`` usando como rótulo a cota
de fundo dos nós do SICFLOW espacialmente próximos a cada trecho navegável (mediana dos
nós num raio). O modelo estima a cota de fundo dos trechos sem cobertura SICFLOW,
preenchendo a lacuna de batimetria (seção 10 do mapeamento de fontes).

Dependências: numpy, shapely, scikit-learn.

Uso:
    python treinar_cota_fundo.py                  # treina, avalia e persiste
    python treinar_cota_fundo.py --raio 2000      # raio de associação em metros
    python treinar_cota_fundo.py --modelo rf      # rf | hgb | ambos
"""

from __future__ import annotations

import argparse
import os
import sqlite3

import numpy as np

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(RAIZ, "data", "hidrowize.db")

# Atributos AHGN usados como features (ordem deve bater com a query SQL).
FEATURES = [
    "nustrahler", "hig_drn_strahler", "hig_drn_depth_m", "hig_drn_width_m",
    "hig_drn_annual_flow", "hig_drn_event_flow", "hig_drn_elevation_avg",
    "hig_drn_elevation_min", "hig_drn_elevation_max", "hig_drn_manning_n",
    "hig_drn_velmann", "hig_drn_sinuosity", "hig_drn_slope_adim",
]

BASELINE_COL = "hig_drn_elevation_min"

SQL_FEATURES = ", ".join(FEATURES)


def carregar_trechos(con: sqlite3.Connection) -> dict:
    cur = con.execute(
        f"SELECT fid, {SQL_FEATURES}, geom_wkb, centroid_lon, centroid_lat "
        "FROM trechos_navegaveis"
    )
    from shapely import from_wkb
    fids, X, geoms, lon, lat = [], [], [], [], []
    for fid, *feat, wkb, clon, clat in cur:
        fids.append(fid)
        X.append(feat)
        geoms.append(from_wkb(wkb))
        lon.append(clon)
        lat.append(clat)
    return {
        "fids": np.array(fids, dtype=int),
        "X": np.array(X, dtype=float),
        "geoms": geoms,
        "lon": np.array(lon, dtype=float),
        "lat": np.array(lat, dtype=float),
    }


def carregar_nos(con: sqlite3.Connection) -> tuple[np.ndarray, np.ndarray]:
    cur = con.execute("SELECT longitude, latitude, cota_fundo FROM batimetria_sicflow")
    rows = np.array(cur.fetchall(), dtype=float)
    return rows[:, :2], rows[:, 2]


def associar_cota_fundo(geoms, nos_xy, nos_cf, raio_m: float) -> tuple[np.ndarray, np.ndarray]:
    """Para cada trecho, mediana da cota_fundo dos nós num raio (m)."""
    from shapely import STRtree, points
    tree = STRtree(points(nos_xy[:, 0], nos_xy[:, 1]))
    raio_deg = raio_m / 111320.0
    y = np.full(len(geoms), np.nan)
    n_nos = np.zeros(len(geoms), dtype=int)
    for i, g in enumerate(geoms):
        idx = tree.query(g, predicate="dwithin", distance=raio_deg)
        n_nos[i] = len(idx)
        if len(idx):
            y[i] = float(np.median(nos_cf[idx]))
    return y, n_nos


def _metricas(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    y_true = np.asarray(y_true)
    y_pred = np.asarray(y_pred)
    res = y_true - y_pred
    ss_res = float((res ** 2).sum())
    ss_tot = float(((y_true - y_true.mean()) ** 2).sum())
    return {
        "r2": float(1 - ss_res / ss_tot) if ss_tot > 0 else float("nan"),
        "mae_m": float(np.abs(res).mean()),
        "rmse_m": float(np.sqrt((res ** 2).mean())),
        "bias_m": float(res.mean()),
        "n": int(len(y_true)),
    }


def _modelos() -> dict:
    from sklearn.ensemble import RandomForestRegressor, HistGradientBoostingRegressor
    return {
        "rf": RandomForestRegressor(
            n_estimators=300, max_depth=None, min_samples_leaf=3,
            n_jobs=-1, random_state=42,
        ),
        "hgb": HistGradientBoostingRegressor(
            max_iter=400, learning_rate=0.05, max_leaf_nodes=31,
            l2_regularization=1.0, random_state=42,
        ),
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="RF035 — regressão de cota de fundo")
    ap.add_argument("--raio", type=float, default=1000.0, help="Raio de associação (m)")
    ap.add_argument("--modelo", default="ambos", help="rf | hgb | ambos")
    ap.add_argument("--nao-persistir", action="store_true",
                    help="Não grava as previsões no banco")
    args = ap.parse_args()

    con = sqlite3.connect(DB)
    try:
        trechos = carregar_trechos(con)
        nos_xy, nos_cf = carregar_nos(con)
    finally:
        con.close()

    X = trechos["X"]
    fids = trechos["fids"]
    print(f"trechos={len(fids)} nós={len(nos_xy)} raio={args.raio:.0f}m")

    y, n_nos = associar_cota_fundo(trechos["geoms"], nos_xy, nos_cf, args.raio)
    mask = ~np.isnan(y) & np.isfinite(X).all(axis=1)
    print(f"trechos associados (com rótulo): {int(mask.sum())} "
          f"({100 * mask.mean():.1f}%)")

    Xt = X[mask]
    yt = y[mask]

    # Split espacial: célula de ~0.5° como grupo (evita vazamento entre vizinhos).
    grupo = (np.floor(trechos["lat"] * 2) * 10000 + np.floor(trechos["lon"] * 2)).astype(int)
    from sklearn.model_selection import GroupShuffleSplit
    gss = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
    tr_idx, te_idx = next(gss.split(Xt, yt, groups=grupo[mask]))
    Xtr, Xte, ytr, yte = Xt[tr_idx], Xt[te_idx], yt[tr_idx], yt[te_idx]
    print(f"treino={len(Xtr)} teste={len(Xte)}")

    # Baseline: usar direto a feature de elevação mínima AHGN.
    base_col = FEATURES.index(BASELINE_COL)
    print("\n=== baseline (hig_drn_elevation_min) ===")
    for k, v in _metricas(yte, Xte[:, base_col]).items():
        print(f"  {k}: {v:.3f}" if isinstance(v, float) else f"  {k}: {v}")

    modelos = _modelos()
    if args.modelo != "ambos":
        modelos = {args.modelo: modelos[args.modelo]}

    val_mae: dict[str, float] = {}
    test_preds: dict[str, np.ndarray] = {}
    for nome, mod in modelos.items():
        mod.fit(Xtr, ytr)
        pred = mod.predict(Xte)
        val_mae[nome] = _metricas(yte, pred)["mae_m"]
        test_preds[nome] = pred
        print(f"\n=== modelo: {nome} ===")
        for k, v in _metricas(yte, pred).items():
            print(f"  {k}: {v:.3f}" if isinstance(v, float) else f"  {k}: {v}")

    # Importâncias do primeiro modelo treinado (RF).
    if "rf" in modelos:
        imp = modelos["rf"].feature_importances_
        ordem = np.argsort(imp)[::-1]
        print("\n=== importância (RandomForest) ===")
        for i in ordem[:8]:
            print(f"  {FEATURES[i]:24s} {imp[i]:.3f}")

    # Análise de erro: por largura de rio e relevância ao calado (RF).
    if "rf" in test_preds:
        e = test_preds["rf"] - yte
        abse = np.abs(e)
        print("\n=== análise de erro (RF, teste) ===")
        for p in (50, 90, 99):
            print(f"  |erro| p{p}: {np.percentile(abse, p):.2f} m")
        w = Xte[:, FEATURES.index("hig_drn_width_m")]
        faixas = [(0, 200), (200, 500), (500, 1000), (1000, 3000), (3000, float("inf"))]
        print("  MAE por largura do canal:")
        for a, b in faixas:
            m = (w >= a) & (w < b)
            if m.sum():
                rotulo = f"{a:>5}-{int(b) if b != float('inf') else '∞'}"
                print(f"    {rotulo:>8} m: n={m.sum():5d} "
                      f"MAE={np.abs(e[m]).mean():.2f} m  bias={e[m].mean():.2f} m")
        print("  P(|erro cota_fundo| > calado):")
        for c in (1, 2, 3, 4, 5):
            print(f"    calado {c} m: {(abse > c).mean() * 100:.1f}%")

    # Persistência: previsão para TODOS os trechos.
    if args.nao_persistir:
        print("\n(nao-persistir: previsões não gravadas)")
        return

    melhor = min(val_mae, key=val_mae.get)
    if "rf" in modelos:
        modelos["rf"].fit(Xt, yt)  # re-treina com todos os rótulos
    if "hgb" in modelos:
        modelos["hgb"].fit(Xt, yt)
    pred_todos = modelos[melhor].predict(X)

    con = sqlite3.connect(DB)
    try:
        con.execute(
            "CREATE TABLE IF NOT EXISTS cota_fundo_trecho ("
            "fid INTEGER PRIMARY KEY,"
            "cota_fundo_observada REAL,"
            "cota_fundo_estimada REAL,"
            "n_nos INTEGER,"
            "modelo TEXT,"
            "raio_m REAL,"
            "fonte TEXT"
            ")"
        )
        linhas = [
            (int(f), (float(y[i]) if not np.isnan(y[i]) else None),
             float(pred_todos[i]), int(n_nos[i]), melhor, args.raio,
             "RF035_SICFLOW")
            for i, f in enumerate(fids)
        ]
        con.executemany(
            "INSERT OR REPLACE INTO cota_fundo_trecho "
            "(fid,cota_fundo_observada,cota_fundo_estimada,n_nos,modelo,raio_m,fonte) "
            "VALUES (?,?,?,?,?,?,?)", linhas)
        con.commit()
    finally:
        con.close()
    print(f"\nprevisões persistidas em cota_fundo_trecho ({len(fids)} trechos, modelo={melhor})")


if __name__ == "__main__":
    main()
