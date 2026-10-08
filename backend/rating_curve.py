"""RF037 — Rating curve (nível → vazão) por ML.

Estima a vazão a partir do nível d'água e da geometria do canal (largura, profundidade,
vazão média AHGN, ordem de Strahler), treinada nas estações ANA com medição de vazão
(40 estações) e aplicável a trechos sem medição.

Dependências: numpy, scikit-learn.

Uso:
    python rating_curve.py
"""

from __future__ import annotations

import os
import sqlite3

import numpy as np

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(RAIZ, "data", "hidrowize.db")


def carregar_dados(con: sqlite3.Connection) -> dict:
    """Pares (nível, vazão) + geometria AHGN do trecho mais próximo da estação."""
    cur = con.execute(
        "SELECT t.codigo_estacao, t.cota_adotada, t.vazao_adotada, "
        "et.hig_drn_width_m, et.hig_drn_depth_m, et.hig_drn_annual_flow, "
        "et.nustrahler, et.hig_drn_elevation_avg "
        "FROM telemetria t "
        "JOIN estacoes_trechos et ON et.codigo_estacao = t.codigo_estacao "
        "WHERE t.cota_adotada IS NOT NULL AND t.vazao_adotada IS NOT NULL "
        "AND t.vazao_adotada > 0"
    )
    rows = np.array(cur.fetchall(), dtype=float)
    return {
        "codigo": rows[:, 0],
        "cota_m": rows[:, 1] / 100.0,  # cm -> m
        "q": rows[:, 2],
        "largura": rows[:, 3],
        "profundidade": rows[:, 4],
        "annual_flow": rows[:, 5],
        "strahler": rows[:, 6],
        "elev_avg": rows[:, 7],
    }


def _features(d: dict) -> np.ndarray:
    return np.column_stack([
        d["cota_m"], d["largura"], d["profundidade"],
        d["annual_flow"], d["strahler"], d["elev_avg"],
    ])


def _metricas(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    y_true = np.asarray(y_true)
    y_pred = np.asarray(y_pred)
    res = y_true - y_pred
    ss_res = float((res ** 2).sum())
    ss_tot = float(((y_true - y_true.mean()) ** 2).sum())
    pos = (y_true > 0) & (y_pred > 0)
    mlog = float(np.abs(np.log10(y_pred[pos]) - np.log10(y_true[pos])).mean())
    return {
        "r2": float(1 - ss_res / ss_tot) if ss_tot > 0 else float("nan"),
        "mae_m3s": float(np.abs(res).mean()),
        "rmse_m3s": float(np.sqrt((res ** 2).mean())),
        "mae_log10": mlog,
        "n": int(len(y_true)),
    }


def _imprimir(rotulo: str, m: dict) -> None:
    print(f"=== {rotulo} ===")
    print(f"  MAE={m['mae_m3s']:,.0f} m3/s  RMSE={m['rmse_m3s']:,.0f} m3/s  "
          f"R2={m['r2']:.3f}  MAE_log10={m['mae_log10']:.3f}  n={m['n']}")


def main() -> None:
    con = sqlite3.connect(DB)
    try:
        d = carregar_dados(con)
    finally:
        con.close()

    X = _features(d)
    y = d["q"]
    codigo = d["codigo"].astype(int)
    print(f"amostras={len(y)} estacoes={len(np.unique(codigo))} "
          f"vazao min={y.min():,.0f} max={y.max():,.0f} m3/s")

    # Baseline: vazão média anual AHGN (sem nível).
    _imprimir("baseline hig_drn_annual_flow", _metricas(y, d["annual_flow"]))

    from sklearn.ensemble import RandomForestRegressor, HistGradientBoostingRegressor
    from sklearn.model_selection import GroupKFold

    gkf = GroupKFold(n_splits=5)
    modelos = {
        "rf": RandomForestRegressor(n_estimators=300, n_jobs=-1, random_state=42),
        "hgb": HistGradientBoostingRegressor(max_iter=400, learning_rate=0.05,
                                              random_state=42),
    }

    for nome, mod in modelos.items():
        pred = np.zeros_like(y, dtype=float)
        for tr, te in gkf.split(X, y, groups=codigo):
            mod.fit(X[tr], y[tr])
            pred[te] = mod.predict(X[te])
        _imprimir(f"modelo {nome} (nível + geometria, CV por estação)", _metricas(y, pred))

    # In-station: split aleatório (as estações estão no treino) — rating curve própria.
    rng = np.random.RandomState(42)
    idx = rng.permutation(len(y))
    ntr = int(0.8 * len(y))
    rf_in = RandomForestRegressor(n_estimators=300, n_jobs=-1, random_state=42)
    rf_in.fit(X[idx[:ntr]], y[idx[:ntr]])
    pred_in = rf_in.predict(X[idx[ntr:]])
    _imprimir("modelo rf in-station (split aleatório)", _metricas(y[idx[ntr:]], pred_in))

    # Importâncias (RF, fold único para inspeção).
    rf = RandomForestRegressor(n_estimators=300, n_jobs=-1, random_state=42).fit(X, y)
    nomes = ["cota_m", "largura", "profundidade", "annual_flow", "strahler", "elev_avg"]
    print("\n=== importância (RF) ===")
    for nome, v in sorted(zip(nomes, rf.feature_importances_), key=lambda t: -t[1]):
        print(f"  {nome:14s} {v:.3f}")


if __name__ == "__main__":
    main()
