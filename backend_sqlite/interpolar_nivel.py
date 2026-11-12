"""RF036 — Interpolação de nível d'água com ML (vs IDW).

Compara a interpolação do nível d'água por Machine Learning (RandomForest, kNN, Gradient
Boosting) com o baseline IDW (inverse distance weighting) usado no RF031, sobre um mês de
observações das estações virtuais (satélite) da bacia amazônica.

Dependências: numpy, shapely, scikit-learn.

Uso:
    python interpolar_nivel.py                 # usa 2024-09
    python interpolar_nivel.py --mes 2025-03   # outro mês
"""

from __future__ import annotations

import argparse
import os
import sqlite3

import numpy as np

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(RAIZ, "data", "hidrowize.db")

LON0, LAT0 = -60.0, -6.0  # centro aproximado da bacia (projeção local)
M_PER_DEG = 111320.0


def _proj(lon: np.ndarray, lat: np.ndarray) -> np.ndarray:
    x = (lon - LON0) * M_PER_DEG * np.cos(np.deg2rad(LAT0))
    y = (lat - LAT0) * M_PER_DEG
    return np.column_stack([x, y])


def carregar_estacoes_mes(con: sqlite3.Connection, mes: str) -> np.ndarray:
    """Retorna (longitude, latitude, nivel_medio) das estações com dado no mês."""
    cur = con.execute(
        "SELECT e.longitude, e.latitude, AVG(s.nivel_m) "
        "FROM series_nivel_satelite s "
        "JOIN estacoes_virtuais e ON e.codigo = s.codigo "
        "WHERE substr(s.data,1,7)=? AND s.nivel_m IS NOT NULL "
        "GROUP BY s.codigo, e.longitude, e.latitude",
        (mes,),
    )
    rows = cur.fetchall()
    return np.array([(r[0], r[1], r[2]) for r in rows], dtype=float)


def carregar_elevacao_trechos(con: sqlite3.Connection) -> tuple[np.ndarray, np.ndarray]:
    cur = con.execute(
        "SELECT centroid_lon, centroid_lat, hig_drn_elevation_avg FROM trechos_navegaveis"
    )
    rows = np.array(cur.fetchall(), dtype=float)
    return rows[:, :2], rows[:, 2]


def join_elevacao(esta_xy: np.ndarray, tre_xy: np.ndarray, tre_elev: np.ndarray) -> np.ndarray:
    from sklearn.neighbors import NearestNeighbors
    nn = NearestNeighbors(n_neighbors=1, metric="haversine").fit(
        np.deg2rad(tre_xy[:, ::-1])
    )
    _, idx = nn.kneighbors(np.deg2rad(esta_xy[:, ::-1]))
    return tre_elev[idx[:, 0]]


def idw(x_train: np.ndarray, y_train: np.ndarray, x_test: np.ndarray, k: int = 12) -> np.ndarray:
    """Inverse distance weighting (1/d²) com os k vizinhos mais próximos."""
    from sklearn.neighbors import NearestNeighbors
    nn = NearestNeighbors(n_neighbors=k).fit(x_train)
    dist, idx = nn.kneighbors(x_test)
    dist = np.maximum(dist, 1.0)  # evita divisão por zero
    w = 1.0 / dist ** 2
    num = (y_train[idx] * w).sum(axis=1)
    den = w.sum(axis=1)
    return num / den


def _metricas(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    res = np.asarray(y_true) - np.asarray(y_pred)
    ss_res = float((res ** 2).sum())
    ss_tot = float(((y_true - y_true.mean()) ** 2).sum())
    return {
        "r2": float(1 - ss_res / ss_tot) if ss_tot > 0 else float("nan"),
        "mae_m": float(np.abs(res).mean()),
        "rmse_m": float(np.sqrt((res ** 2).mean())),
        "bias_m": float(res.mean()),
        "n": int(len(y_true)),
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="RF036 — interpolação de nível com ML vs IDW")
    ap.add_argument("--mes", default="2024-09", help="Mês (AAAA-MM) das observações")
    ap.add_argument("--teste", type=float, default=0.2, help="Fração de teste")
    args = ap.parse_args()

    con = sqlite3.connect(DB)
    try:
        esta = carregar_estacoes_mes(con, args.mes)
        tre_xy, tre_elev = carregar_elevacao_trechos(con)
    finally:
        con.close()

    lon, lat, y = esta[:, 0], esta[:, 1], esta[:, 2]
    elev = join_elevacao(np.column_stack([lon, lat]), tre_xy, tre_elev)
    xy = _proj(lon, lat)

    print(f"mes={args.mes} estações={len(y)} "
          f"nível min={y.min():.1f} max={y.max():.1f} m")

    # Split espacial por célula de ~0.5°.
    grupo = (np.floor(lat * 2) * 10000 + np.floor(lon * 2)).astype(int)
    from sklearn.model_selection import GroupShuffleSplit
    gss = GroupShuffleSplit(n_splits=1, test_size=args.teste, random_state=42)
    tr_idx, te_idx = next(gss.split(xy, y, groups=grupo))

    Xtr_xy, Xte_xy = xy[tr_idx], xy[te_idx]
    Xtr_elev, Xte_elev = elev[tr_idx], elev[te_idx]
    ytr, yte = y[tr_idx], y[te_idx]
    print(f"treino={len(ytr)} teste={len(yte)}")

    # Baseline: IDW (só distância).
    print("\n=== baseline IDW (só distância) ===")
    for k, v in _metricas(yte, idw(Xtr_xy, ytr, Xte_xy)).items():
        print(f"  {k}: {v:.3f}" if isinstance(v, float) else f"  {k}: {v}")

    from sklearn.ensemble import RandomForestRegressor, HistGradientBoostingRegressor
    from sklearn.neighbors import KNeighborsRegressor

    Xtr = np.column_stack([Xtr_xy, Xtr_elev])
    Xte = np.column_stack([Xte_xy, Xte_elev])

    modelos = {
        "knn": KNeighborsRegressor(n_neighbors=12, weights="distance"),
        "rf": RandomForestRegressor(n_estimators=300, n_jobs=-1, random_state=42),
        "hgb": HistGradientBoostingRegressor(max_iter=400, learning_rate=0.05,
                                              random_state=42),
    }
    for nome, mod in modelos.items():
        mod.fit(Xtr, ytr)
        print(f"\n=== {nome} (xy + elevação) ===")
        for k, v in _metricas(yte, mod.predict(Xte)).items():
            print(f"  {k}: {v:.3f}" if isinstance(v, float) else f"  {k}: {v}")

    # RF só com xy (sem elevação), para isolar o ganho da covariável.
    rf_xy = RandomForestRegressor(n_estimators=300, n_jobs=-1, random_state=42)
    rf_xy.fit(Xtr_xy, ytr)
    print("\n=== rf (só xy, sem elevação) ===")
    for k, v in _metricas(yte, rf_xy.predict(Xte_xy)).items():
        print(f"  {k}: {v:.3f}" if isinstance(v, float) else f"  {k}: {v}")

    imp = modelos["rf"].feature_importances_
    print("\n=== importância (RF: x, y, elevação) ===")
    for nome, v in zip(["x (m)", "y (m)", "elevação (m)"], imp):
        print(f"  {nome:14s} {v:.3f}")

    # Cenário esparso: subsample das estações de treino (simula cobertura limitada,
    # ex.: apenas as ~75 réguas ANA). Onde o ML com elevação deve superar o IDW.
    print("\n=== cenário esparso (IDW vs RF xy+elevação) ===")
    rng = np.random.RandomState(0)
    for N in (50, 100, 200, 400, 800):
        idx = rng.choice(len(ytr), N, replace=False)
        xa = Xtr_xy[idx]
        ya = ytr[idx]
        xb = np.column_stack([Xtr_xy[idx], Xtr_elev[idx]])
        idw_m = _metricas(yte, idw(xa, ya, Xte_xy))["mae_m"]
        rf = RandomForestRegressor(n_estimators=300, n_jobs=-1, random_state=42).fit(xb, ya)
        rf_m = _metricas(yte, rf.predict(Xte))["mae_m"]
        print(f"  treino={N:4d}: IDW MAE={idw_m:6.2f} m   RF(xy+elev) MAE={rf_m:6.2f} m")


if __name__ == "__main__":
    main()
