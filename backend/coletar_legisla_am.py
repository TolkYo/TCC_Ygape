"""Coletor do Legisla.AM — Diário Oficial do Amazonas (decretos hidrológicos).

Busca decretos por palavras-chave (emergência, calamidade, enchente, cheia,
estiagem...) no portal Legisla.AM, extrai número, data, ementa e corpo, e
classifica o evento (cheia/estiagem) com o município, rio e código COBRADE.

Fonte: https://legisla.imprensaoficial.am.gov.br/ (HTML server-rendered, sem JS).

Uso:
    python coletar_legisla_am.py
    python coletar_legisla_am.py --termos "emergência,estiagem" --paginas 3
    python coletar_legisla_am.py --sem-detalhe   # só a busca (mais rápido)

Notas:
- Sem robots.txt no site (verificado); ainda assim usa intervalo entre
  requisições (--atraso) para não sobrecarregar o servidor.
- O texto da ementa/COBRADE só sai completo na página de detalhe (a busca
  trunca o texto). Use --sem-detalhe apenas para um levantamento rápido.
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
import time
from datetime import datetime
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://legisla.imprensaoficial.am.gov.br"
URL_BUSCA = f"{BASE_URL}/diario_am/pesquisar"

TERMOS_PADRAO = [
    "emergência", "calamidade", "enchente", "estiagem", "cheia", "inundação",
]

HEADERS = {
    "User-Agent": "HidroWize/1.0 (coletor de pesquisa academica; contato: local)",
}

MESES = {
    "JANEIRO": 1, "FEVEREIRO": 2, "MARÇO": 3, "ABRIL": 4, "MAIO": 5, "JUNHO": 6,
    "JULHO": 7, "AGOSTO": 8, "SETEMBRO": 9, "OUTUBRO": 10, "NOVEMBRO": 11, "DEZEMBRO": 12,
}

KW_CHEIA = [
    "ELEVAÇÃO DAS ÁGUAS", "ELEVACAO DAS AGUAS", "INUNDAÇÃO", "INUNDACAO",
    "ENCHENTE", "CHEIA", "ALAGAMENTO", "ALAGADA", "SUBIDA DO RIO",
]
KW_ESTIAGEM = [
    "ESTIAGEM", "SECA", "VAZANTE", "ESCASSEZ", "BAIXO NÍVEL", "BAIXO NIVEL",
    "DEFICIÊNCIA HÍDRICA", "DEFICIENCIA HIDRICA",
]


def _get(session: requests.Session, url: str, params: dict | None = None) -> str:
    resp = session.get(url, params=params, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    resp.encoding = "utf-8"
    return resp.text


def buscar(session: requests.Session, termo: str, pagina: int) -> list[dict]:
    """Retorna os resultados (lista) de uma página de busca."""
    html = _get(session, URL_BUSCA, params={"q": termo, "page": pagina})
    soup = BeautifulSoup(html, "lxml")

    resultados: list[dict] = []
    for li in soup.select("li.item-li"):
        h4 = li.find("h4")
        titulo = h4.get_text(" ", strip=True) if h4 else ""
        p = li.select_one("p.mx-1")
        ementa = p.get_text(" ", strip=True) if p else ""
        a = li.find("a", href=True)
        url = a["href"].split("?")[0] if a else ""
        if not url:
            continue
        resultados.append({
            "titulo": titulo,
            "ementa_busca": ementa,
            "url": urljoin(BASE_URL, url),
        })
    return resultados


def extrair_detalhe(session: requests.Session, url: str) -> dict:
    """Extrai título, ementa e corpo completo da página de detalhe."""
    html = _get(session, url)
    soup = BeautifulSoup(html, "lxml")
    materia = soup.select_one("div.materia")
    if not materia:
        return {"titulo": "", "ementa": "", "corpo": ""}

    ps = [p.get_text(" ", strip=True) for p in materia.find_all("p")]
    ps = [p for p in ps if p]
    titulo = ps[0] if ps else ""
    ementa = ps[1] if len(ps) > 1 else ""
    corpo = " ".join(ps[2:]) if len(ps) > 2 else ""
    return {"titulo": titulo, "ementa": ementa, "corpo": corpo}


def parse_numero_data(titulo: str) -> tuple[str, str]:
    """Extrai (numero, data ISO) de um título tipo 'DECRETO Nº 54.712, DE 17 DE JULHO DE 2026'."""
    m = re.search(
        r'N\s*[º°]?\s*([\d.,]+)\s*,?\s*DE\s*(\d{1,2})\s+DE\s+([A-ZÇÃÕÂÊÔÁÉÍÓÚ]+)\s+DE\s+(\d{4})',
        titulo, re.I | re.S,
    )
    if not m:
        # tenta sem a vírgula e com formato compacto
        m = re.search(
            r'(\d{1,2})\s+DE\s+([A-ZÇÃÕÂÊÔÁÉÍÓÚ]+)\s+DE\s+(\d{4})', titulo, re.I,
        )
        if not m:
            return "", ""
        dia, mes, ano = m.group(1), m.group(2), m.group(3)
        numero = ""
    else:
        numero = m.group(1)
        dia, mes, ano = m.group(2), m.group(3), m.group(4)

    mes_num = MESES.get(mes.upper())
    if mes_num:
        data = f"{int(ano):04d}-{mes_num:02d}-{int(dia):02d}"
    else:
        data = ""
    return numero.strip(" ,."), data


def classificar(texto: str) -> dict:
    """Classifica o evento hidrológico e extrai município, rio e COBRADE."""
    t = texto.upper()
    if any(k in t for k in KW_CHEIA):
        tipo = "cheia"
    elif any(k in t for k in KW_ESTIAGEM):
        tipo = "estiagem"
    else:
        tipo = "outro"

    municipio = ""
    m = re.search(r'MUNIC[ÍI]PIO\s+DE\s+([A-ZÀ-Ú\s\'-]+?)(?:,|\s+NO\s+|\.|\s+na forma)', texto, re.I)
    if m:
        municipio = re.sub(r"\s+", " ", m.group(1)).strip(" ,.")

    rio = ""
    STOP_RIO = {"E", "O", "A", "DO", "DA", "DE", "SEU", "SEUS", "SUA", "SUAS",
                "AFLUENTES", "AFLUENTE", "E O", "E SEUS"}
    candidatos: list[str] = []
    for m in re.findall(r"\bRIO\s+([A-ZÀ-Ú]+(?:\s+[A-ZÀ-Ú]+)?)", texto, re.I):
        palavras = m.split()
        if not palavras:
            continue
        nome = palavras[0]
        if len(palavras) > 1 and palavras[1].upper() not in STOP_RIO:
            nome = " ".join(palavras[:2])
        candidatos.append(re.sub(r"\s+", " ", nome).strip())
    if candidatos:
        rio = candidatos[-1]

    cobrade = ""
    m = re.search(r'COBRADE[^\d]{0,20}(\d(?:\s*[\.\/]\s*\d){1,5})', texto, re.I)
    if m:
        cobrade = re.sub(r"\s+", "", m.group(1))
    else:
        m = re.search(r'\b(\d(?:\.\d){4})\b', texto)
        if m:
            cobrade = m.group(1)

    return {"tipo": tipo, "municipio": municipio, "rio": rio, "cobrade": cobrade}


def main() -> None:
    ap = argparse.ArgumentParser(description="Coletor de decretos do Legisla.AM")
    ap.add_argument("--termos", help="Palavras-chave separadas por vírgula")
    ap.add_argument("--paginas", type=int, default=5, help="Máx. de páginas por termo")
    ap.add_argument("--sem-detalhe", action="store_true", help="Não busca as páginas de detalhe")
    ap.add_argument("--atraso", type=float, default=1.0, help="Intervalo entre requisições (s)")
    ap.add_argument("--out", default="planilhas/decretos_legisla_am.csv")
    args = ap.parse_args()

    termos = [t.strip() for t in (args.termos or ",".join(TERMOS_PADRAO)).split(",") if t.strip()]

    session = requests.Session()
    vistos: dict[str, dict] = {}

    for termo in termos:
        for pagina in range(1, args.paginas + 1):
            try:
                resultados = buscar(session, termo, pagina)
            except requests.RequestException as exc:
                print(f"[aviso] falha na busca '{termo}' p.{pagina}: {exc}")
                break
            if not resultados:
                break
            for r in resultados:
                vistos.setdefault(r["url"], r)
            print(f"'{termo}' p.{pagina}: {len(resultados)} resultados")
            time.sleep(args.atraso)

    registros: list[dict] = []
    for url, r in vistos.items():
        if not args.sem_detalhe:
            try:
                det = extrair_detalhe(session, url)
            except requests.RequestException as exc:
                print(f"[aviso] falha no detalhe {url}: {exc}")
                det = {"titulo": r["titulo"], "ementa": r["ementa_busca"], "corpo": ""}
            time.sleep(args.atraso)
        else:
            det = {"titulo": r["titulo"], "ementa": r["ementa_busca"], "corpo": ""}

        titulo = det["titulo"] or r["titulo"]
        numero, data = parse_numero_data(titulo)
        texto_cls = " ".join([titulo, det["ementa"], det["corpo"]])
        cls = classificar(texto_cls)

        registros.append({
            "numero": numero,
            "data": data,
            "titulo": titulo,
            "ementa": det["ementa"],
            "tipo": cls["tipo"],
            "municipio": cls["municipio"],
            "rio": cls["rio"],
            "cobrade": cls["cobrade"],
            "url": url,
            "corpo": det["corpo"],
            "data_coleta": datetime.now().isoformat(timespec="seconds"),
        })

    # ordena por data desc
    registros.sort(key=lambda x: x["data"], reverse=True)

    campos = ["numero", "data", "titulo", "ementa", "tipo", "municipio",
              "rio", "cobrade", "url", "corpo", "data_coleta"]
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=campos, delimiter=";")
        w.writeheader()
        for r in registros:
            w.writerow(r)

    print(f"\n{len(registros)} decretos salvos em {args.out}")


if __name__ == "__main__":
    main()
