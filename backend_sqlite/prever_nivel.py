"""RF039 — Previsão de nível (cheia/estiagem) para planejamento de navegação.

Prevê o nível d'água a partir do ciclo sazonal (dia-do-ano) e tendência anual, usando a série
histórica de uma estação virtual de satélite. Compara um modelo ML (RandomForest) com o baseline
de climatologia mensal, com split temporal (treino no passado, teste no futuro).

Dependências: numpy, scikit-learn.

Uso:
    python prever_nivel.py                      # usa a estação com mais observações
    python prever_nivel.py --codigo R_AMAZONAS_AMAZONAS_KM1298 --ano_teste 2024
"""

from __future__ import annotations

import argparse
import os
import sqlite3
from datetime import datetime

import numpy as np

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(RAIZ, "data", "hidrowize.db")


def carregar_serie(con: sqlite3.Connection, codigo: str) -> tuple[np.ndarray, np.ndarray]:
    cur = con.execute(
        "SELECT data, nivel_m FROM series_nivel_satelite "
        "WHERE codigo=? AND nivel_m IS NOT NULL ORDER BY data",
        (codigo,),
    )
    datas, níveis = [], []
    for d, v in cur:
        datas.append(datetime.fromisoformat(d))
        níveis.append(v)
    return np.array(datas), np.array(níveis, dtype=float)


def _estacao_padrao(con: sqlite3.Connection) -> str:
    cur = con.execute(
        "SELECT codigo FROM series_nivel_satelite "
        "GROUP BY codigo ORDER BY COUNT(*) DESC LIMIT 1"
    )
    return cur.fetchone()[0]


def _metricas(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    res = np.asarray(y_true) - np.asarray(y_pred)
    ss_res = float((res ** 2).sum())
    ss_tot = float(((y_true - y_true.mean()) ** 2).sum())
    return {
        "r2": float(1 - ss_res / ss_tot) if ss_tot > 0 else float("nan"),
        "mae_m": float(np.abs(res).mean()),
        "rmse_m": float(np.sqrt((res ** 2).mean())),
        "n": int(len(y_true)),
    }


def _imprimir(rotulo: str, m: dict) -> None:
    print(f"=== {rotulo} ===")
    print(f"  MAE={m['mae_m']:.2f} m  RMSE={m['rmse_m']:.2f} m  R2={m['r2']:.3f}  n={m['n']}")


def main() -> None:
    ap = argparse.ArgumentParser(description="RF039 — previsão de nível (cheia/estiagem)")
    ap.add_argument("--codigo", help="Código da estação virtual")
    ap.add_argument("--ano_teste", type=int, default=2024, help="Primeiro ano do teste")
    args = ap.parse_args()

    con = sqlite3.connect(DB)
    try:
        codigo = args.codigo or _estacao_padrao(con)
        datas, níveis = carregar_serie(con, codigo)
    finally:
        con.close()

    doy = np.array([d.timetuple().tm_yday for d in datas], dtype=float)
    ano = np.array([d.year for d in datas], dtype=float)
    mes = np.array([d.month for d in datas], dtype=int)

    print(f"estação={codigo} observações={len(níveis)} "
          f"({datas.min().date()} -> {datas.max().date()})")

    tr = ano < args.ano_teste
    te = ~tr
    if te.sum() == 0 or tr.sum() == 0:
        print("sem dados suficientes nos dois períodos")
        return

    # Baseline: climatologia mensal (média por mês no treino).
    clima = np.array([níveis[tr & (mes == m)].mean() for m in range(1, 13)])
    pred_clima = clima[mes[te] - 1]
    _imprimir("baseline climatologia mensal", _metricas(níveis[te], pred_clima))

    # ML: features sazonais (dia-do-ano cíclico) + tendência anual.
    X = np.column_stack([
        np.sin(2 * np.pi * doy / 365.0),
        np.cos(2 * np.pi * doy / 365.0),
        ano,
    ])
    from sklearn.ensemble import RandomForestRegressor, HistGradientBoostingRegressor
    for nome, mod in [
        ("rf", RandomForestRegressor(n_estimators=400, random_state=42)),
        ("hgb", HistGradientBoostingRegressor(max_iter=400, learning_rate=0.05,
                                               random_state=42)),
    ]:
        mod.fit(X[tr], níveis[tr])
        _imprimir(f"ML {nome} (sazonal + tendência)", _metricas(níveis[te], mod.predict(X[te])))

    # Pico/baixa previstos vs observados no teste (cheia/estiagem).
    print("\n=== cheia/estiagem (mês de pico e baixa na climatologia) ===")
    pico = int(np.argmax(clima))
    baixa = int(np.argmin(clima))
    print(f"  pico ~mês {pico + 1} ({clima[pico]:.1f} m), "
          f"baixa ~mês {baixa + 1} ({clima[baixa]:.1f} m)")


if __name__ == "__main__":
    main()
