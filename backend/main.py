"""API HTTP do HidroWize.

Executar (a partir de ``backend``):
    uvicorn main:app --reload

Os dados hidrográficos são lidos de ``data/hidrowize.db``. Usuários e sessões
da aplicação ficam em ``data/hidrowize_api.db`` para não alterar a base curada.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Literal

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field
from routing_engine import RiverGraph

ROOT = Path(__file__).resolve().parents[1]
DATA_DB = Path(os.getenv("HIDROWIZE_DATA_DB", ROOT / "data" / "hidrowize.db"))
AUTH_DB = Path(os.getenv("HIDROWIZE_AUTH_DB", ROOT / "data" / "hidrowize_api.db"))
TOKEN_TTL_SECONDS = int(os.getenv("HIDROWIZE_TOKEN_TTL_SECONDS", "28800"))
TOKEN_SECRET = os.getenv("HIDROWIZE_TOKEN_SECRET", "")
bearer = HTTPBearer(auto_error=False)
river_graph = RiverGraph(DATA_DB)


class ApiProblem(Exception):
    def __init__(self, status_code: int, code: str, message: str):
        self.status_code, self.code, self.message = status_code, code, message


def ok(data: object, status_code: int = 200) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"success": True, "data": data})


@contextmanager
def data_connection():
    if not DATA_DB.exists():
        raise ApiProblem(503, "data_unavailable", "Banco consolidado não encontrado.")
    con = sqlite3.connect(f"file:{DATA_DB}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    try:
        yield con
    finally:
        con.close()


@contextmanager
def auth_connection():
    AUTH_DB.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(AUTH_DB)
    con.row_factory = sqlite3.Row
    try:
        con.execute("""CREATE TABLE IF NOT EXISTS usuarios (
          id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT NOT NULL, email TEXT NOT NULL UNIQUE,
          senha_hash TEXT NOT NULL, papel TEXT NOT NULL CHECK(papel IN ('admin','piloto')),
          ativo INTEGER NOT NULL DEFAULT 1, criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )""")
        yield con
        con.commit()
    finally:
        con.close()


def password_hash(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1)
    return base64.urlsafe_b64encode(salt + digest).decode("ascii")


def verify_password(password: str, stored: str) -> bool:
    try:
        raw = base64.urlsafe_b64decode(stored.encode("ascii"))
        return hmac.compare_digest(password_hash(password, raw[:16]), stored)
    except (ValueError, TypeError):
        return False


def signing_secret() -> bytes:
    if not TOKEN_SECRET:
        raise ApiProblem(503, "auth_not_configured", "Defina HIDROWIZE_TOKEN_SECRET para habilitar autenticação.")
    return TOKEN_SECRET.encode("utf-8")


def issue_token(user: sqlite3.Row) -> str:
    payload = f"{user['id']}:{user['papel']}:{int(time.time()) + TOKEN_TTL_SECONDS}".encode("utf-8")
    signature = hmac.new(signing_secret(), payload, hashlib.sha256).digest()
    return base64.urlsafe_b64encode(payload + b"." + signature).decode("ascii")


def read_token(token: str) -> dict:
    try:
        raw = base64.urlsafe_b64decode(token.encode("ascii"))
        payload, signature = raw.rsplit(b".", 1)
        expected = hmac.new(signing_secret(), payload, hashlib.sha256).digest()
        if not hmac.compare_digest(signature, expected):
            raise ValueError
        user_id, role, expires = payload.decode("utf-8").split(":")
        if int(expires) < time.time() or role not in {"admin", "piloto"}:
            raise ValueError
        return {"id": int(user_id), "papel": role}
    except (ValueError, UnicodeDecodeError):
        raise ApiProblem(401, "invalid_token", "Token ausente, inválido ou expirado.")


def current_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)) -> dict:
    if not credentials or credentials.scheme.lower() != "bearer":
        raise ApiProblem(401, "missing_token", "Autenticação Bearer obrigatória.")
    token = read_token(credentials.credentials)
    with auth_connection() as con:
        row = con.execute("SELECT id,nome,email,papel,ativo FROM usuarios WHERE id=?", (token["id"],)).fetchone()
    if not row or not row["ativo"]:
        raise ApiProblem(401, "invalid_token", "Usuário não está ativo.")
    return dict(row)


def admin_user(user: dict = Depends(current_user)) -> dict:
    if user["papel"] != "admin":
        raise ApiProblem(403, "forbidden", "Esta operação requer perfil de administrador.")
    return user


class LoginInput(BaseModel):
    email: str
    senha: str


class UserInput(BaseModel):
    nome: str = Field(min_length=2, max_length=120)
    email: str
    senha: str = Field(min_length=8, max_length=256)
    papel: Literal["admin", "piloto"] = "piloto"


class UserUpdate(BaseModel):
    nome: str | None = Field(default=None, min_length=2, max_length=120)
    senha: str | None = Field(default=None, min_length=8, max_length=256)
    papel: Literal["admin", "piloto"] | None = None
    ativo: bool | None = None


class RouteInput(BaseModel):
    origem_nome: str = Field(min_length=2, max_length=120)
    destino_nome: str = Field(min_length=2, max_length=120)
    calado_m: float = Field(ge=0.5, le=6)
    margem_seguranca_m: float = Field(default=0.5, ge=0, le=3)
    velocidade_embarcacao_kmh: float = Field(ge=6, le=35)
    monitorar: bool = False


class CollectInput(BaseModel):
    estacoes: list[str] = []
    periodo_inicio: str | None = None
    periodo_fim: str | None = None


app = FastAPI(title="HidroWize API", version="0.1.0", openapi_url="/api/v1/openapi.json", docs_url="/api/v1/docs")
origins = [item.strip() for item in os.getenv("HIDROWIZE_CORS_ORIGINS", "http://localhost:8000,http://localhost:8080,http://127.0.0.1:8080").split(",")]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


@app.exception_handler(ApiProblem)
async def api_problem_handler(_: Request, error: ApiProblem):
    return JSONResponse(status_code=error.status_code, content={"success": False, "error": {"code": error.code, "message": error.message}})


@app.get("/health")
def health():
    return ok({"status": "ok", "data_db": DATA_DB.exists(), "auth_db": AUTH_DB.exists()})


@app.post("/api/v1/auth/login")
def login(input: LoginInput):
    with auth_connection() as con:
        user = con.execute("SELECT * FROM usuarios WHERE lower(email)=lower(?)", (input.email.strip(),)).fetchone()
    if not user or not user["ativo"] or not verify_password(input.senha, user["senha_hash"]):
        raise ApiProblem(401, "invalid_credentials", "E-mail ou senha inválidos.")
    public = {key: user[key] for key in ("id", "nome", "email", "papel")}
    return ok({"access_token": issue_token(user), "token_type": "bearer", "expires_in": TOKEN_TTL_SECONDS, "usuario": public})


@app.get("/api/v1/auth/me")
def me(user: dict = Depends(current_user)):
    return ok({key: user[key] for key in ("id", "nome", "email", "papel")})


@app.get("/api/v1/usuarios")
def list_users(_: dict = Depends(admin_user)):
    with auth_connection() as con:
        rows = [dict(row) for row in con.execute("SELECT id,nome,email,papel,ativo,criado_em FROM usuarios ORDER BY nome")]
    return ok({"items": rows, "total": len(rows)})


@app.post("/api/v1/usuarios", status_code=status.HTTP_201_CREATED)
def create_user(input: UserInput, _: dict = Depends(admin_user)):
    try:
        with auth_connection() as con:
            cursor = con.execute("INSERT INTO usuarios (nome,email,senha_hash,papel) VALUES (?,?,?,?)", (input.nome.strip(), input.email.strip().lower(), password_hash(input.senha), input.papel))
            row = con.execute("SELECT id,nome,email,papel,ativo FROM usuarios WHERE id=?", (cursor.lastrowid,)).fetchone()
    except sqlite3.IntegrityError:
        raise ApiProblem(409, "email_exists", "Já existe um usuário com este e-mail.")
    return ok(dict(row), 201)


@app.put("/api/v1/usuarios/{user_id}")
def update_user(user_id: int, input: UserUpdate, _: dict = Depends(admin_user)):
    fields = input.model_dump(exclude_none=True)
    if not fields:
        raise ApiProblem(422, "empty_update", "Informe ao menos um campo para atualizar.")
    if "senha" in fields:
        fields["senha_hash"] = password_hash(fields.pop("senha"))
    columns, values = zip(*fields.items())
    with auth_connection() as con:
        cursor = con.execute("UPDATE usuarios SET " + ", ".join(f"{key}=?" for key in columns) + " WHERE id=?", (*values, user_id))
        row = con.execute("SELECT id,nome,email,papel,ativo FROM usuarios WHERE id=?", (user_id,)).fetchone()
    if not cursor.rowcount or not row:
        raise ApiProblem(404, "user_not_found", "Usuário não encontrado.")
    return ok(dict(row))


@app.delete("/api/v1/usuarios/{user_id}")
def disable_user(user_id: int, _: dict = Depends(admin_user)):
    with auth_connection() as con:
        cursor = con.execute("UPDATE usuarios SET ativo=0 WHERE id=?", (user_id,))
    if not cursor.rowcount:
        raise ApiProblem(404, "user_not_found", "Usuário não encontrado.")
    return ok({"id": user_id, "ativo": False})


@app.get("/api/v1/estacoes")
def list_stations(rio: str | None = None, municipio: str | None = None, ativa: bool = True):
    clauses, params = ["1=1"], []
    if rio:
        clauses.append("e.nome_rio LIKE ?"); params.append(f"%{rio}%")
    if municipio:
        clauses.append("e.municipio LIKE ?"); params.append(f"%{municipio}%")
    if ativa:
        clauses.append("COALESCE(e.operando, 1)=1")
    query = f"""SELECT e.codigo_estacao,e.nome_estacao,e.nome_rio,e.municipio,e.latitude,e.longitude,
      h.cota_minima, t.cota_adotada,t.data_hora_medicao
      FROM estacoes e LEFT JOIN cotas_historicas h USING(codigo_estacao)
      LEFT JOIN telemetria t ON t.id=(SELECT id FROM telemetria WHERE codigo_estacao=e.codigo_estacao ORDER BY data_hora_medicao DESC,id DESC LIMIT 1)
      WHERE {' AND '.join(clauses)} ORDER BY e.nome_estacao"""
    with data_connection() as con:
        items = [dict(row) for row in con.execute(query, params)]
    for item in items:
        item["cota_minima_historica_m"] = item.pop("cota_minima", None)
        item["nivel_atual_cm"] = item.pop("cota_adotada", None)
        item["atualizado_em"] = item.pop("data_hora_medicao", None)
    return ok({"items": items, "total": len(items)})


@app.get("/api/v1/estacoes/{codigo}")
def station(codigo: str):
    with data_connection() as con:
        row = con.execute("SELECT codigo_estacao,nome_estacao,nome_rio,municipio,latitude,longitude FROM estacoes WHERE codigo_estacao=?", (codigo,)).fetchone()
    if not row:
        raise ApiProblem(404, "station_not_found", "Estação não encontrada.")
    return ok(dict(row))


@app.get("/api/v1/niveis")
def levels(estacao: str, data_inicio: str, data_fim: str | None = None, _: dict = Depends(current_user)):
    with data_connection() as con:
        exists = con.execute("SELECT 1 FROM estacoes WHERE codigo_estacao=?", (estacao,)).fetchone()
        if not exists:
            raise ApiProblem(404, "station_not_found", "Estação não encontrada.")
        query = "SELECT data_hora_medicao,cota_adotada,chuva_adotada,vazao_adotada FROM telemetria WHERE codigo_estacao=? AND substr(data_hora_medicao,1,10)>=?"
        params = [estacao, data_inicio]
        if data_fim:
            query += " AND substr(data_hora_medicao,1,10)<=?"; params.append(data_fim)
        query += " ORDER BY data_hora_medicao"
        items = [dict(row) for row in con.execute(query, params)]
    return ok({"estacao": estacao, "items": [{"data_hora": x["data_hora_medicao"], "nivel_cm": x["cota_adotada"], "chuva_mm": x["chuva_adotada"], "vazao": x["vazao_adotada"]} for x in items]})


@app.post("/api/v1/niveis/coletar", status_code=status.HTTP_501_NOT_IMPLEMENTED)
def collect_levels(_: CollectInput, __: dict = Depends(admin_user)):
    raise ApiProblem(501, "collector_not_queued", "O coletor ainda deve ser executado pelo serviço agendado; não há fila de tarefas na API.")


@app.get("/api/v1/grafo/status")
def graph_status():
    graph = river_graph.status()
    return ok({**graph, "area_ativa": "hidrovias_navegaveis_bhae", "ultima_reconstrucao": None, "pronto": True})


def station_code(identifier: str) -> str:
    with data_connection() as con:
        row = con.execute("""SELECT e.codigo_estacao FROM estacoes e
          JOIN estacoes_trechos et ON et.codigo_estacao=e.codigo_estacao
          WHERE e.codigo_estacao=? OR upper(e.nome_estacao)=upper(?)
          ORDER BY et.distancia_m ASC LIMIT 1""", (identifier, identifier)).fetchone()
    if not row:
        raise ApiProblem(404, "port_not_found", f"Porto ou estação não encontrado: {identifier}.")
    return str(row["codigo_estacao"])


@app.post("/api/v1/rotas/calcular")
def calculate_route(input: RouteInput):
    origin_code = station_code(input.origem_nome)
    destination_code = station_code(input.destino_nome)
    try:
        edges = river_graph.route(origin_code, destination_code, input.calado_m, input.margem_seguranca_m)
    except ValueError as error:
        raise ApiProblem(422, "port_without_segment", str(error))
    except LookupError as error:
        raise ApiProblem(404, "route_not_found", str(error))

    distance = sum(edge.distance_km for edge in edges)
    depths = [edge.depth_m for edge in edges if edge.depth_m is not None]
    features = []
    items = []
    for edge in edges:
        geometry = {"type": "LineString", "coordinates": edge.geometry[0]} if len(edge.geometry) == 1 else {"type": "MultiLineString", "coordinates": edge.geometry}
        transitavel = edge.depth_m is None or edge.depth_m >= input.calado_m + input.margem_seguranca_m
        props = {"fid": edge.fid, "distancia_km": round(edge.distance_km, 3), "profundidade_m": edge.depth_m, "transitavel": transitavel}
        features.append({"type": "Feature", "properties": props, "geometry": geometry})
        items.append({"no_origem": edge.source, "no_destino": edge.target, **props, "tempo_h": round(edge.distance_km / input.velocidade_embarcacao_kmh, 3)})
    return ok({
        "rota_id": None, "origem": input.origem_nome, "destino": input.destino_nome,
        "distancia_total_km": round(distance, 3), "tempo_total_h": round(distance / input.velocidade_embarcacao_kmh, 3),
        "custo_total": round(distance / input.velocidade_embarcacao_kmh, 3), "trechos_criticos": sum(not x["transitavel"] for x in items),
        "profundidade_minima_m": min(depths) if depths else None,
        "geojson": {"type": "FeatureCollection", "features": features}, "items": items
    })
