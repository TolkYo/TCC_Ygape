"""Cliente da API REST Hidro Webservice (ANA) — Agência Nacional de Águas.

Consome os endpoints documentados em docs/specs/mapeamento-ana-hidrowebservice.md.
Credenciais (ANA_IDENTIFICADOR / ANA_SENHA) lidas do .env na raiz do projeto.

Uso:
    python ana_client.py                # lista rios e imprime resumo
    python ana_client.py --csv rios.csv # salva o catálogo de rios em CSV
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

BASE_URL = "https://www.ana.gov.br/hidrowebservice"
RAIZ = Path(__file__).resolve().parent.parent
ARQUIVO_TOKEN = Path(__file__).resolve().parent / ".ana_token.json"
load_dotenv(RAIZ / ".env")

CAMPO_RIO = "Código do Rio"
CAMPO_ATU_INI = "Data Atualização Inicial"
CAMPO_ATU_FIM = "Data Atualização Final"
CAMPO_UF = "Unidade Federativa"
CAMPO_ESTACAO = "Código da Estação"
CAMPO_BACIA = "Código da Bacia"

VALIDADE_JWT_SEG = 3500  # token da ANA expira em ~1h


def _carregar_token() -> tuple[str | None, float]:
    if ARQUIVO_TOKEN.exists():
        try:
            dados = json.loads(ARQUIVO_TOKEN.read_text(encoding="utf-8"))
            return dados.get("token"), float(dados.get("expira_em", 0))
        except (ValueError, OSError):
            pass
    return None, 0.0


def _salvar_token(token: str, expira_em: float) -> None:
    try:
        ARQUIVO_TOKEN.write_text(
            json.dumps({"token": token, "expira_em": expira_em}), encoding="utf-8"
        )
    except OSError:
        pass


class AnaClient:
    """Cliente mínimo da API Hidro Webservice, com cache do token JWT."""

    def __init__(
        self,
        identificador: str | None = None,
        senha: str | None = None,
        base_url: str = BASE_URL,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self._identificador = identificador or os.getenv("ANA_IDENTIFICADOR")
        self._senha = senha or os.getenv("ANA_SENHA")
        if not self._identificador or not self._senha:
            raise ValueError(
                "Credenciais ausentes. Defina ANA_IDENTIFICADOR e ANA_SENHA no .env."
            )
        self.session = requests.Session()
        self._token, self._token_expira_em = _carregar_token()
        self._tentativas = 6

    def _requisitar(self, metodo: str, url: str, **kwargs) -> requests.Response:
        ultimo: requests.Response | None = None
        for tentativa in range(1, self._tentativas + 1):
            try:
                resp = self.session.request(metodo, url, **kwargs)
            except requests.RequestException as exc:
                ultimo = None
                if tentativa == self._tentativas:
                    raise
                time.sleep(5 * tentativa)
                continue
            if resp.status_code in (417, 429, 500, 502, 503, 504):
                ultimo = resp
                if tentativa == self._tentativas:
                    resp.raise_for_status()
                time.sleep(5 * tentativa)
                continue
            return resp
        if ultimo is not None:
            ultimo.raise_for_status()
        raise requests.ConnectionError("Falha na requisicao")

    def _autenticar(self) -> None:
        resp = self._requisitar(
            "GET",
            f"{self.base_url}/EstacoesTelemetricas/OAUth/v1",
            headers={"Identificador": self._identificador, "Senha": self._senha},
            timeout=60,
        )
        items = resp.json().get("items") or {}
        token = items.get("tokenautenticacao")
        if not token:
            raise RuntimeError(f"Falha na autenticacao ANA: {items}")
        self._token = token
        self._token_expira_em = time.time() + VALIDADE_JWT_SEG
        _salvar_token(token, self._token_expira_em)

    def _token_atual(self) -> str:
        if not self._token or time.time() >= self._token_expira_em:
            self._autenticar()
        return self._token

    def _get(self, rota: str, params: dict | None = None) -> dict:
        headers = {"Authorization": f"Bearer {self._token_atual()}"}
        resp = self._requisitar(
            "GET", f"{self.base_url}{rota}", headers=headers, params=params, timeout=120
        )
        if resp.status_code == 401:
            self._token = None
            self._token_expira_em = 0.0
            headers = {"Authorization": f"Bearer {self._token_atual()}"}
            resp = self._requisitar(
                "GET", f"{self.base_url}{rota}", headers=headers, params=params, timeout=120
            )
        return resp.json()

    def listar_rios(
        self,
        codigo_rio: int | None = None,
        data_ini: str | None = None,
        data_fim: str | None = None,
    ) -> list[dict]:
        params: dict = {}
        if codigo_rio is not None:
            params[CAMPO_RIO] = codigo_rio
        if data_ini:
            params[CAMPO_ATU_INI] = data_ini
        if data_fim:
            params[CAMPO_ATU_FIM] = data_fim
        data = self._get("/EstacoesTelemetricas/HidroRio/v1", params=params)
        return data.get("items") or []

    def listar_estacoes(
        self,
        codigo_estacao: int | None = None,
        uf: str | None = None,
        codigo_bacia: int | None = None,
        data_ini: str | None = None,
        data_fim: str | None = None,
    ) -> list[dict]:
        params: dict = {}
        if codigo_estacao is not None:
            params[CAMPO_ESTACAO] = codigo_estacao
        if uf:
            params[CAMPO_UF] = uf.upper()
        if codigo_bacia is not None:
            params[CAMPO_BACIA] = codigo_bacia
        if data_ini:
            params[CAMPO_ATU_INI] = data_ini
        if data_fim:
            params[CAMPO_ATU_FIM] = data_fim
        data = self._get(
            "/EstacoesTelemetricas/HidroInventarioEstacoes/v1", params=params
        )
        return data.get("items") or []


def normalizar_rio(rio: dict) -> dict:
    return {
        "codigo_rio": rio.get("codigorio"),
        "nome_rio": rio.get("Nome_Rio"),
        "bacia_codigo": rio.get("Bacia_Codigo"),
        "sub_bacia_codigo": rio.get("Sub_Bacia_Codigo"),
        "jurisdicao": rio.get("Rio_Jurisdicao"),
        "data_ultima_alteracao": rio.get("Data_Ultima_Alteracao"),
    }


def salvar_csv(rios: list[dict], caminho: str) -> None:
    with open(caminho, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(normalizar_rio(rios[0]).keys()))
        writer.writeheader()
        writer.writerows(normalizar_rio(r) for r in rios)


def main() -> None:
    parser = argparse.ArgumentParser(description="Coletor da API Hidro Webservice (ANA)")
    parser.add_argument("--csv", help="Salva o catálogo de rios em um arquivo CSV")
    parser.add_argument("--codigo", type=int, help="Filtra por código do rio")
    args = parser.parse_args()

    cliente = AnaClient()
    rios = cliente.listar_rios(codigo_rio=args.codigo)
    print(f"{len(rios)} rios retornados")

    if args.codigo is not None:
        for r in rios[:20]:
            print(normalizar_rio(r))

    if args.csv:
        salvar_csv(rios, args.csv)
        print(f"CSV salvo em {args.csv}")


if __name__ == "__main__":
    main()
