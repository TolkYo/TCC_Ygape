"""Cliente SOAP publico de telemetria da ANA (sem autenticacao).

Base: https://telemetriaws1.ana.gov.br/ServiceANA.asmx
Namespace: http://MRCS/

Fornece a serie historica de cotas/vazoes/chuvas por estacao, que nao esta
disponivel na API REST (os endpoints REST /HidroSerieCotas/v1 estao inoperantes).

Uso:
    python -m ana_soap 14990000
"""

from __future__ import annotations

import calendar
import sys
from typing import Any
from xml.etree import ElementTree as ET

import requests

URL_BASE = "https://telemetriaws1.ana.gov.br/ServiceANA.asmx"

TIPO_COTA = "1"   # 1-Cotas, 2-Chuvas, 3-Vazoes
NIVEL_BRUTO = "1"
NIVEL_CONSISTIDO = "2"


def serie_historica(
    cod_estacao: str,
    data_inicio: str,
    data_fim: str = "",
    tipo_dados: str = TIPO_COTA,
    nivel_consistencia: str = NIVEL_CONSISTIDO,
    timeout: int = 180,
) -> list[dict[str, str]]:
    """Consulta HidroSerieHistorica e devolve lista de registros mensais.

    data_inicio/data_fim no formato dd/MM/yyyy. data_fim vazio = ate o dado
    mais recente. Retorna [] quando a estacao nao possui dados no periodo.
    """
    payload = {
        "codEstacao": str(cod_estacao),
        "dataInicio": data_inicio,
        "dataFim": data_fim,
        "tipoDados": tipo_dados,
        "nivelConsistencia": nivel_consistencia,
    }
    resp = requests.post(f"{URL_BASE}/HidroSerieHistorica", data=payload, timeout=timeout)
    resp.raise_for_status()

    root = ET.fromstring(resp.text)
    rows: list[dict[str, str]] = []
    for el in root.iter():
        tag = el.tag.split("}")[-1]
        if tag == "ErrorTable":
            return []  # "Sem dados para esta estacao..."
        if tag == "SerieHistorica":
            rows.append({c.tag.split("}")[-1]: (c.text or "") for c in el})
    return rows


def _cota_diaria_valida(valor: str | None) -> float | None:
    """Converte uma cota diaria (CotaNN) em float, descartando leituras invalidas.

    Cotas sao registradas em centimetros; valores ausentes, nao numericos ou
    fora do intervalo (0, 100000) sao considerados invalidos (ex.: -74).
    """
    if valor in (None, ""):
        return None
    try:
        v = float(valor)
    except (TypeError, ValueError):
        return None
    return v if 0 < v < 100000 else None


def _ano_mes(data_hora: str) -> tuple[int, int] | None:
    """Extrai (ano, mes) de um DataHora no formato 'YYYY-MM-DD HH:MM:SS'."""
    if len(data_hora) < 7 or data_hora[4] != "-":
        return None
    try:
        return int(data_hora[:4]), int(data_hora[5:7])
    except ValueError:
        return None


def serie_diaria(
    cod_estacao: str,
    data_inicio: str,
    data_fim: str = "",
    tipo_dados: str = TIPO_COTA,
    nivel_consistencia: str = NIVEL_CONSISTIDO,
    timeout: int = 180,
) -> list[dict[str, Any]]:
    """Consulta HidroSerieHistorica e devolve uma cota por dia.

    O SOAP retorna um registro por mes com os campos diarios ``Cota01..Cota31``
    (o resumo apenas usa Minima/Maxima/Media). Esta funcao:
      1. deduplica meses com mais de um registro (revisoes), mantendo o de
         ``DataHora`` mais recente;
      2. expande cada mes em leituras diarias;
      3. descarta dias sem leitura e valores invalidos.

    Cada linha: ``codigo_estacao``, ``data`` (YYYY-MM-DD), ``cota_cm``,
    ``status``, ``nivel_consistencia``.
    """
    rows = serie_historica(
        cod_estacao, data_inicio, data_fim, tipo_dados, nivel_consistencia, timeout
    )
    return _expandir_diaria(cod_estacao, rows, nivel_consistencia)


def _expandir_diaria(
    cod_estacao: str,
    rows: list[dict[str, str]],
    nivel_consistencia: str,
) -> list[dict[str, Any]]:
    melhor: dict[tuple[int, int], dict[str, str]] = {}
    for r in rows:
        ym = _ano_mes(r.get("DataHora", ""))
        if ym is None:
            continue
        atual = melhor.get(ym)
        if atual is None or r.get("DataHora", "") > atual.get("DataHora", ""):
            melhor[ym] = r

    saida: list[dict[str, Any]] = []
    for (ano, mes), r in sorted(melhor.items()):
        ultimo_dia = calendar.monthrange(ano, mes)[1]
        for dia in range(1, ultimo_dia + 1):
            cota = _cota_diaria_valida(r.get(f"Cota{dia:02d}"))
            if cota is None:
                continue
            status = r.get(f"Cota{dia:02d}Status") or ""
            saida.append(
                {
                    "codigo_estacao": cod_estacao,
                    "data": f"{ano:04d}-{mes:02d}-{dia:02d}",
                    "cota_cm": cota,
                    "status": status,
                    "nivel_consistencia": nivel_consistencia,
                }
            )
    return saida


def resumo_cotas(
    cod_estacao: str,
    anos: int = 5,
    timeout: int = 180,
) -> dict[str, Any] | None:
    """Resumo estatistico da serie de cotas de uma estacao (min/max/media).

    Consulta os niveis consistido (2) e bruto (1) e mescla os registros
    (o consistido cobre periodos antigos, o bruto os recentes), filtrando
    leituras com status de qualidade diferente de 0 (ok) e valores invalidos.
    Retorna None se nao houver dados em nenhum nivel.
    """
    ano_atual = 2026
    data_inicio = f"01/01/{ano_atual - anos + 1}"

    registros: list[dict] = []
    niveis_ok: list[str] = []
    for nivel in (NIVEL_CONSISTIDO, NIVEL_BRUTO):
        try:
            rows = serie_historica(
                cod_estacao, data_inicio, tipo_dados=TIPO_COTA,
                nivel_consistencia=nivel,
            )
        except requests.RequestException:
            rows = []
        if rows:
            registros.extend(rows)
            niveis_ok.append(nivel)
    if not registros:
        return None
    return _estatisticas(cod_estacao, registros, "+".join(niveis_ok))


def _estatisticas(cod_estacao: str, rows: list[dict], nivel: str) -> dict[str, Any]:
    def _ok(valor: str, status: str) -> float | None:
        if status not in ("", "0"):
            return None
        try:
            v = float(valor)
        except (TypeError, ValueError):
            return None
        return v if 0 < v < 100000 else None

    minimos = [_ok(r.get("Minima"), r.get("MinimaStatus")) for r in rows]
    maximos = [_ok(r.get("Maxima"), r.get("MaximaStatus")) for r in rows]
    medias = [_ok(r.get("Media"), r.get("MediaStatus")) for r in rows]
    minimos = [m for m in minimos if m is not None]
    maximos = [m for m in maximos if m is not None]
    medias = [m for m in medias if m is not None]
    datas = [r.get("DataHora", "") for r in rows if r.get("DataHora")]

    return {
        "codigo_estacao": cod_estacao,
        "nivel_consistencia": nivel,
        "registros": len(rows),
        "data_inicio_serie": min(datas) if datas else "",
        "data_fim_serie": max(datas) if datas else "",
        "cota_minima": min(minimos) if minimos else None,
        "cota_maxima": max(maximos) if maximos else None,
        "cota_media": round(sum(medias) / len(medias), 2) if medias else None,
    }


if __name__ == "__main__":
    codigo = sys.argv[1] if len(sys.argv) > 1 else "15400000"
    res = resumo_cotas(codigo, anos=5)
    if res:
        for k, v in res.items():
            print(f"{k}: {v}")
    else:
        print(f"Sem dados de cota para {codigo}")
