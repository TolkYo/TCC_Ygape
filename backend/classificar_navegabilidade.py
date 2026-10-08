"""RF038 — Classificação de navegabilidade (ML vs regra RF018).

Avalia se um classificador ML (RandomForest) supera a regra de transitabilidade (RN010/RF018,
`profundidade = cota_atual - cota_minima_historica`) a partir dos rótulos disponíveis no projeto
(`navegabilidade.status_navegabilidade`, derivados da própria regra) e com features de geometria
AHGN + cota. O objetivo é evidenciar se há ganho do ML dado o rótulo disponível.

Dependências: numpy, scikit-learn.

Uso:
    python classificar_navegabilidade.py
"""

from __future__ import annotations

import os
import sqlite3

import numpy as np

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(RAIZ, "data", "hidrowize.db")

LIMIAR_CM = 50.0  # RN010/RF018: margem de 50 cm sobre a cota mínima


def main() -> None:
    con = sqlite3.connect(DB)
    try:
        cur = con.execute(
            "SELECT n.cota_atual, n.cota_minima_historica, n.status_navegabilidade, "
            "et.hig_drn_width_m, et.hig_drn_depth_m, et.hig_drn_annual_flow, "
            "et.nustrahler, et.hig_drn_elevation_avg "
            "FROM navegabilidade n "
            "JOIN estacoes_trechos et ON et.codigo_estacao = n.codigo_estacao "
            "WHERE n.status_navegabilidade IN ('NAVEGAVEL','RESTRITO') "
            "AND n.cota_atual IS NOT NULL AND n.cota_minima_historica IS NOT NULL"
        )
        rows = cur.fetchall()
    finally:
        con.close()

    cota_atual = np.array([r[0] for r in rows], dtype=float)
    cota_min = np.array([r[1] for r in rows], dtype=float)
    y = np.array([1 if r[2] == "RESTRITO" else 0 for r in rows], dtype=int)
    geom = np.array([r[3:] for r in rows], dtype=float)  # width, depth, annual_flow, strahler, elev

    diff = cota_atual - cota_min
    print(f"estações={len(y)} (RESTRITO={int(y.sum())}, NAVEGAVEL={int((y == 0).sum())})")
    print(f"diff (cota_atual - cota_min) cm: RESTRITO max={diff[y==1].max():.0f} "
          f"NAVEGAVEL min={diff[y==0].min():.0f}")

    # Baseline: regra RF018 (RESTRITO quando abaixo da margem).
    regra = (diff < LIMIAR_CM).astype(int)
    acc_regra = float((regra == y).mean())
    print(f"\n=== regra RF018 (diff >= {LIMIAR_CM:.0f} cm) ===")
    print(f"  acurácia={acc_regra:.3f}")

    from sklearn.ensemble import RandomForestClassifier
    from sklearn.model_selection import StratifiedKFold, cross_val_predict
    from sklearn.metrics import accuracy_score, f1_score, recall_score

    def avaliar(nome: str, X: np.ndarray) -> None:
        skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
        pred = cross_val_predict(
            RandomForestClassifier(n_estimators=400, class_weight="balanced",
                                   random_state=42),
            X, y, cv=skf,
        )
        acc = accuracy_score(y, pred)
        rec = recall_score(y, pred)  # recall da classe RESTRITO
        f1 = f1_score(y, pred)
        print(f"\n=== ML {nome} (CV estratificado) ===")
        print(f"  acurácia={acc:.3f}  recall(RESTRITO)={rec:.3f}  F1={f1:.3f}")

    avaliar("só geometria AHGN", geom)
    avaliar("geometria + cota_atual", np.column_stack([geom, cota_atual]))
    avaliar("geometria + cota_atual + cota_min", np.column_stack([geom, cota_atual, cota_min]))


if __name__ == "__main__":
    main()
