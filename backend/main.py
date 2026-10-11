"""API HTTP do HidroWize.

Executar (a partir de ``backend``):
    uvicorn main:app --reload

Persistência: PostgreSQL/PostGIS (container ``ygape-db``). Os dados hidrográficos
(estações, trechos, telemetria, satélite) e os dados da aplicação (usuários,
rotas, logs) vivem no mesmo banco, alimentado pelo ETL ``carregar_postgis.py``.
"""
from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import json
import os
import secrets
import threading
import time
from datetime import datetime
from decimal import Decimal
from typing import Literal

import psycopg2
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Request, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from psycopg2.extras import Json
from pydantic import BaseModel, Field

from db import connection, ensure_schema, pg_config
from routing_engine import RiverGraph

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(ROOT, ".env"))
TOKEN_TTL_SECONDS = int(os.getenv("HIDROWIZE_TOKEN_TTL_SECONDS", "28800"))
TOKEN_SECRET = os.getenv("HIDROWIZE_TOKEN_SECRET", "")
MONITOR_INTERVALO_MIN = int(os.getenv("HIDROWIZE_MONITOR_INTERVALO_MIN", "15"))
bearer = HTTPBearer(auto_error=False)
river_graph = RiverGraph(pg_config())


class EventBus:
    """Canal de eventos em memoria por usuario (para o WebSocket)."""

    def __init__(self) -> None:
        self._subs: dict[int, set[asyncio.Queue]] = {}
        self._lock = threading.Lock()
        self._loop: asyncio.AbstractEventLoop | None = None

    def set_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    def subscribe(self, user_id: int) -> asyncio.Queue:
        fila: asyncio.Queue = asyncio.Queue(maxsize=100)
        with self._lock:
            self._subs.setdefault(user_id, set()).add(fila)
        return fila

    def unsubscribe(self, user_id: int, fila: asyncio.Queue) -> None:
        with self._lock:
            subs = self._subs.get(user_id)
            if subs:
                subs.discard(fila)
                if not subs:
                    self._subs.pop(user_id, None)

    def publish(self, user_id: int, evento: dict) -> None:
        with self._lock:
            filas = list(self._subs.get(user_id, ()))
        for fila in filas:
            try:
                if self._loop is not None:
                    self._loop.call_soon_threadsafe(fila.put_nowait, evento)
                else:
                    fila.put_nowait(evento)
            except (asyncio.QueueFull, RuntimeError):
                pass


bus = EventBus()

ROTA_COLS = (
    "id, usuario_id, origem_nome, destino_nome, calado_m, margem_seguranca_m, "
    "velocidade_embarcacao_kmh, distancia_total_km, tempo_total_h, custo_total, "
    "trechos_criticos, profundidade_minima_m, rota_geojson, monitorar, created_at::text AS created_at"
)


class ApiProblem(Exception):
    def __init__(self, status_code: int, code: str, message: str):
        self.status_code, self.code, self.message = status_code, code, message


def ok(data: object, status_code: int = 200) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"success": True, "data": data})


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


def issue_token(user: dict) -> str:
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
    with connection() as con:
        with con.cursor() as cur:
            cur.execute("SELECT id,nome,email,papel,ativo FROM usuarios WHERE id=%s", (token["id"],))
            row = cur.fetchone()
    if not row or not row["ativo"]:
        raise ApiProblem(401, "invalid_token", "Usuário não está ativo.")
    return dict(row)


def admin_user(user: dict = Depends(current_user)) -> dict:
    if user["papel"] != "admin":
        raise ApiProblem(403, "forbidden", "Esta operação requer perfil de administrador.")
    return user


def registrar_evento(tipo: str, detalhe: str, usuario_id: int | None = None) -> None:
    try:
        with connection() as con:
            with con.cursor() as cur:
                cur.execute("INSERT INTO log_eventos (usuario_id,tipo,detalhe) VALUES (%s,%s,%s)", (usuario_id, tipo, detalhe))
    except psycopg2.Error:
        pass


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


class ProfileUpdate(BaseModel):
    nome: str | None = Field(default=None, min_length=2, max_length=120)
    senha: str | None = Field(default=None, min_length=8, max_length=256)


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


class RouteSaveInput(BaseModel):
    origem_nome: str = Field(min_length=2, max_length=120)
    destino_nome: str = Field(min_length=2, max_length=120)
    calado_m: float = Field(ge=0.5, le=6)
    margem_seguranca_m: float = Field(default=0.5, ge=0, le=3)
    velocidade_embarcacao_kmh: float = Field(ge=6, le=35)
    distancia_total_km: float = Field(ge=0)
    tempo_total_h: float = Field(ge=0)
    custo_total: float = Field(ge=0)
    trechos_criticos: int = Field(default=0, ge=0)
    profundidade_minima_m: float | None = None
    geojson: dict | None = None
    monitorar: bool = False


class MonitorInput(BaseModel):
    monitorar: bool = True


app = FastAPI(title="HidroWize API", version="0.1.0", openapi_url="/api/v1/openapi.json", docs_url="/api/v1/docs")
origins = [item.strip() for item in os.getenv("HIDROWIZE_CORS_ORIGINS", "http://localhost:8000,http://localhost:8080,http://127.0.0.1:8080").split(",")]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


@app.on_event("startup")
async def iniciar() -> None:
    try:
        ensure_schema()
    except psycopg2.Error as error:
        print(f"[startup] falha ao garantir o schema: {error}")
    asyncio.create_task(monitor_loop())


@app.exception_handler(ApiProblem)
async def api_problem_handler(_: Request, error: ApiProblem):
    return JSONResponse(status_code=error.status_code, content={"success": False, "error": {"code": error.code, "message": error.message}})


@app.get("/health")
def health():
    try:
        with connection() as con:
            with con.cursor() as cur:
                cur.execute("SELECT 1")
        db_ok = True
    except psycopg2.Error:
        db_ok = False
    return ok({"status": "ok" if db_ok else "degraded", "db": db_ok})


@app.post("/api/v1/auth/login")
def login(input: LoginInput):
    with connection() as con:
        with con.cursor() as cur:
            cur.execute("SELECT * FROM usuarios WHERE lower(email)=lower(%s)", (input.email.strip(),))
            user = cur.fetchone()
    if not user or not user["ativo"] or not verify_password(input.senha, user["senha_hash"]):
        raise ApiProblem(401, "invalid_credentials", "E-mail ou senha inválidos.")
    public = {key: user[key] for key in ("id", "nome", "email", "papel")}
    registrar_evento("login", f"Login de {public['email']}", user["id"])
    return ok({"access_token": issue_token(user), "token_type": "bearer", "expires_in": TOKEN_TTL_SECONDS, "usuario": public})


@app.get("/api/v1/auth/me")
def me(user: dict = Depends(current_user)):
    return ok({key: user[key] for key in ("id", "nome", "email", "papel")})


@app.put("/api/v1/auth/me")
def update_me(input: ProfileUpdate, user: dict = Depends(current_user)):
    fields = input.model_dump(exclude_none=True)
    if not fields:
        raise ApiProblem(422, "empty_update", "Informe ao menos um campo para atualizar.")
    if "senha" in fields:
        fields["senha_hash"] = password_hash(fields.pop("senha"))
    columns, values = zip(*fields.items())
    with connection() as con:
        with con.cursor() as cur:
            cur.execute("UPDATE usuarios SET " + ", ".join(f"{key}=%s" for key in columns) + " WHERE id=%s", (*values, user["id"]))
            cur.execute("SELECT id,nome,email,papel FROM usuarios WHERE id=%s", (user["id"],))
            row = cur.fetchone()
    registrar_evento("perfil_atualizado", f"Usuário {user['id']} atualizou o próprio perfil", user["id"])
    return ok(dict(row))


@app.get("/api/v1/usuarios")
def list_users(_: dict = Depends(admin_user)):
    with connection() as con:
        with con.cursor() as cur:
            cur.execute("SELECT id,nome,email,papel,ativo,criado_em::text AS criado_em FROM usuarios ORDER BY nome")
            rows = [dict(row) for row in cur.fetchall()]
    return ok({"items": rows, "total": len(rows)})


@app.post("/api/v1/usuarios", status_code=status.HTTP_201_CREATED)
def create_user(input: UserInput, admin: dict = Depends(admin_user)):
    try:
        with connection() as con:
            with con.cursor() as cur:
                cur.execute(
                    "INSERT INTO usuarios (nome,email,senha_hash,papel) VALUES (%s,%s,%s,%s) RETURNING id,nome,email,papel,ativo",
                    (input.nome.strip(), input.email.strip().lower(), password_hash(input.senha), input.papel),
                )
                row = cur.fetchone()
    except psycopg2.errors.UniqueViolation:
        raise ApiProblem(409, "email_exists", "Já existe um usuário com este e-mail.")
    registrar_evento("usuario_criado", f"Usuário {row['email']} criado (papel {row['papel']})", admin["id"])
    return ok(dict(row), 201)


@app.put("/api/v1/usuarios/{user_id}")
def update_user(user_id: int, input: UserUpdate, _: dict = Depends(admin_user)):
    fields = input.model_dump(exclude_none=True)
    if not fields:
        raise ApiProblem(422, "empty_update", "Informe ao menos um campo para atualizar.")
    if "senha" in fields:
        fields["senha_hash"] = password_hash(fields.pop("senha"))
    columns, values = zip(*fields.items())
    with connection() as con:
        with con.cursor() as cur:
            cur.execute("UPDATE usuarios SET " + ", ".join(f"{key}=%s" for key in columns) + " WHERE id=%s", (*values, user_id))
            atualizados = cur.rowcount
            cur.execute("SELECT id,nome,email,papel,ativo FROM usuarios WHERE id=%s", (user_id,))
            row = cur.fetchone()
    if not atualizados or not row:
        raise ApiProblem(404, "user_not_found", "Usuário não encontrado.")
    return ok(dict(row))


@app.delete("/api/v1/usuarios/{user_id}")
def disable_user(user_id: int, admin: dict = Depends(admin_user)):
    with connection() as con:
        with con.cursor() as cur:
            cur.execute("UPDATE usuarios SET ativo=FALSE WHERE id=%s", (user_id,))
            removidos = cur.rowcount
    if not removidos:
        raise ApiProblem(404, "user_not_found", "Usuário não encontrado.")
    registrar_evento("usuario_desativado", f"Usuário {user_id} desativado", admin["id"])
    return ok({"id": user_id, "ativo": False})


@app.get("/api/v1/estacoes")
def list_stations(rio: str | None = None, municipio: str | None = None, ativa: bool = True):
    clauses, params = ["1=1"], []
    if rio:
        clauses.append("e.nome_rio ILIKE %s"); params.append(f"%{rio}%")
    if municipio:
        clauses.append("e.municipio ILIKE %s"); params.append(f"%{municipio}%")
    if ativa:
        clauses.append("COALESCE(e.operando, 1)=1")
    query = f"""SELECT e.codigo_estacao,e.nome_estacao,e.nome_rio,e.municipio,e.latitude,e.longitude,
      h.cota_minima, t.cota_adotada,t.data_hora_medicao
      FROM estacoes e LEFT JOIN cotas_historicas h USING(codigo_estacao)
      LEFT JOIN telemetria t ON t.id=(SELECT id FROM telemetria WHERE codigo_estacao=e.codigo_estacao ORDER BY data_hora_medicao DESC,id DESC LIMIT 1)
      WHERE {' AND '.join(clauses)} ORDER BY e.nome_estacao"""
    with connection() as con:
        with con.cursor() as cur:
            cur.execute(query, params)
            items = [dict(row) for row in cur.fetchall()]
    for item in items:
        item["cota_minima_historica_m"] = item.pop("cota_minima", None)
        item["nivel_atual_cm"] = item.pop("cota_adotada", None)
        item["atualizado_em"] = item.pop("data_hora_medicao", None)
    return ok({"items": items, "total": len(items)})


@app.get("/api/v1/estacoes/{codigo}")
def station(codigo: str):
    with connection() as con:
        with con.cursor() as cur:
            cur.execute("SELECT codigo_estacao,nome_estacao,nome_rio,municipio,latitude,longitude FROM estacoes WHERE codigo_estacao=%s", (codigo,))
            row = cur.fetchone()
    if not row:
        raise ApiProblem(404, "station_not_found", "Estação não encontrada.")
    return ok(dict(row))


@app.get("/api/v1/niveis")
def levels(estacao: str, data_inicio: str, data_fim: str | None = None, _: dict = Depends(current_user)):
    with connection() as con:
        with con.cursor() as cur:
            cur.execute("SELECT 1 FROM estacoes WHERE codigo_estacao=%s", (estacao,))
            if not cur.fetchone():
                raise ApiProblem(404, "station_not_found", "Estação não encontrada.")
            query = "SELECT data_hora_medicao,cota_adotada,chuva_adotada,vazao_adotada FROM telemetria WHERE codigo_estacao=%s AND substr(data_hora_medicao,1,10)>=%s"
            params = [estacao, data_inicio]
            if data_fim:
                query += " AND substr(data_hora_medicao,1,10)<=%s"; params.append(data_fim)
            query += " ORDER BY data_hora_medicao"
            cur.execute(query, params)
            items = [dict(row) for row in cur.fetchall()]
    return ok({"estacao": estacao, "items": [{"data_hora": x["data_hora_medicao"], "nivel_cm": x["cota_adotada"], "chuva_mm": x["chuva_adotada"], "vazao": x["vazao_adotada"]} for x in items]})


@app.post("/api/v1/niveis/coletar", status_code=status.HTTP_501_NOT_IMPLEMENTED)
def collect_levels(_: CollectInput, __: dict = Depends(admin_user)):
    raise ApiProblem(501, "collector_not_queued", "O coletor ainda deve ser executado pelo serviço agendado; não há fila de tarefas na API.")


@app.get("/api/v1/grafo/status")
def graph_status():
    graph = river_graph.status()
    return ok({**graph, "area_ativa": "hidrovias_navegaveis_bhae", "ultima_reconstrucao": None, "pronto": True})


def station_code(identifier: str) -> str:
    with connection() as con:
        with con.cursor() as cur:
            cur.execute("""SELECT e.codigo_estacao FROM estacoes e
              JOIN estacoes_trechos et ON et.codigo_estacao=e.codigo_estacao
              WHERE e.codigo_estacao=%s OR upper(e.nome_estacao)=upper(%s)
              ORDER BY et.distancia_m ASC LIMIT 1""", (identifier, identifier))
            row = cur.fetchone()
    if not row:
        raise ApiProblem(404, "port_not_found", f"Porto ou estação não encontrado: {identifier}.")
    return str(row["codigo_estacao"])


def nivel_atual_cm(codigo: str | None) -> float | None:
    """Ultima cota registrada (cm) para uma estacao, ou None."""
    if not codigo:
        return None
    with connection() as con:
        with con.cursor() as cur:
            cur.execute(
                "SELECT cota_adotada FROM telemetria WHERE codigo_estacao=%s "
                "ORDER BY data_hora_medicao DESC, id DESC LIMIT 1",
                (codigo,),
            )
            row = cur.fetchone()
    return float(row["cota_adotada"]) if row and row["cota_adotada"] is not None else None


def _alteracao_publica(row) -> dict:
    item = dict(row)
    for chave, valor in list(item.items()):
        if isinstance(valor, Decimal):
            item[chave] = float(valor)
    geo = item.get("rota_geojson")
    if isinstance(geo, str):
        geo = json.loads(geo)
    item["rota_geojson"] = geo
    return item


def _atualizar_rota(rota_id: int, campos: dict) -> None:
    if not campos:
        return
    colunas = list(campos)
    with connection() as con:
        with con.cursor() as cur:
            cur.execute(
                "UPDATE rotas SET " + ", ".join(f"{c}=%s" for c in colunas) + " WHERE id=%s",
                (*[campos[c] for c in colunas], rota_id),
            )


def _montar_geojson(edges) -> dict:
    geometrias = river_graph.geometries([e.fid for e in edges])
    features = []
    for edge in edges:
        linhas = geometrias.get(edge.fid, [])
        geometry = {"type": "LineString", "coordinates": linhas[0]} if len(linhas) == 1 else {"type": "MultiLineString", "coordinates": linhas}
        features.append({
            "type": "Feature",
            "properties": {"fid": edge.fid, "distancia_km": round(edge.distance_km, 3), "profundidade_m": edge.depth_m},
            "geometry": geometry,
        })
    return {"type": "FeatureCollection", "features": features}


def _ultimas_leituras_ana(codigos: set[str]) -> dict[str, float]:
    """Pull dirigido: le da ANA apenas as estacoes informadas (cota atual em cm)."""
    if not codigos:
        return {}
    try:
        from ana_client import AnaClient

        cliente = AnaClient()
    except Exception as exc:  # credenciais ausentes ou biblioteca indisponivel
        print(f"[monitor] ANA indisponivel, usando telemetria do banco: {exc}")
        return {}
    data_busca = datetime.now().strftime("%Y-%m-%d")
    lista = sorted(codigos)
    brutas: dict[str, tuple[str, float]] = {}
    for i in range(0, len(lista), 10):
        lote = lista[i:i + 10]
        try:
            dados = cliente._get(
                "/EstacoesTelemetricas/HidroinfoanaSerieTelemetricaAdotada/v2",
                params={
                    "Codigos_Estacoes": ",".join(lote),
                    "Tipo Filtro Data": "DATA_LEITURA",
                    "Data de Busca": data_busca,
                    "Range Intervalo de busca": "DIAS_30",
                },
            )
        except Exception as exc:
            print(f"[monitor] ANA lote {i // 10 + 1}: {exc}")
            continue
        for item in dados.get("items") or []:
            codigo = item.get("codigoestacao")
            cota = item.get("Cota_Adotada")
            quando = item.get("Data_Hora_Medicao") or ""
            if codigo is None or cota is None:
                continue
            codigo = str(codigo)
            try:
                valor = float(cota)
            except (TypeError, ValueError):
                continue
            anterior = brutas.get(codigo)
            if anterior is None or quando > anterior[0]:
                brutas[codigo] = (quando, valor)
    return {codigo: valor for codigo, (_, valor) in brutas.items()}


def _verificar_rota(rota: dict, leituras: dict[str, float]) -> dict | None:
    codigo = rota["estacao_referencia"]
    if not codigo:
        return None
    nivel = leituras.get(codigo)
    if nivel is None:
        nivel = nivel_atual_cm(codigo)
    if nivel is None:
        return None
    baseline = float(rota["nivel_baseline_cm"]) if rota["nivel_baseline_cm"] is not None else None
    if baseline is None:
        _atualizar_rota(rota["id"], {"nivel_baseline_cm": nivel})
        return None
    variacao = abs(nivel - baseline)
    if variacao < float(rota["limiar_cm"]):
        return None
    extremo = variacao >= 100
    ultima = rota["ultima_recomputacao"]
    if ultima is not None and not extremo:
        if (datetime.now() - ultima).total_seconds() < int(rota["cooldown_min"]) * 60:
            return None

    origem = station_code(rota["origem_nome"])
    destino = station_code(rota["destino_nome"])
    edges = river_graph.route(origem, destino, float(rota["calado_m"]), float(rota["margem_seguranca_m"]))
    fids = [e.fid for e in edges]
    if fids == (rota["fids_rota"] or []):
        _atualizar_rota(rota["id"], {"nivel_baseline_cm": nivel, "fids_rota": Json(fids)})
        return None

    distancia = sum(e.distance_km for e in edges)
    depths = [e.depth_m for e in edges if e.depth_m is not None]
    custo = round(distancia / float(rota["velocidade_embarcacao_kmh"]), 3)
    geojson = _montar_geojson(edges)
    motivo = "evento_extremo" if extremo else "variacao_nivel"
    profundidade_min = min(depths) if depths else None
    requerido = float(rota["calado_m"]) + float(rota["margem_seguranca_m"])

    with connection() as con:
        with con.cursor() as cur:
            cur.execute(
                "INSERT INTO rota_alteracao (rota_id,motivo,variacao_nivel_cm,estacao_origem,distancia_total_km,custo_total,rota_geojson) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s)",
                (rota["id"], motivo, round(variacao, 1), codigo, round(distancia, 3), custo, Json(geojson)),
            )
    _atualizar_rota(rota["id"], {
        "nivel_baseline_cm": nivel,
        "fids_rota": Json(fids),
        "ultima_recomputacao": datetime.now(),
        "distancia_total_km": round(distancia, 3),
        "tempo_total_h": custo,
        "custo_total": custo,
        "profundidade_minima_m": profundidade_min,
        "trechos_criticos": sum(1 for e in edges if e.depth_m is not None and e.depth_m < requerido),
        "rota_geojson": Json(geojson),
    })
    return {
        "evento": "rota_alterada",
        "rota_id": rota["id"],
        "motivo": motivo,
        "variacao_nivel_cm": round(variacao, 1),
        "nova_distancia_km": round(distancia, 3),
    }


def verificar_rotas_monitoradas() -> list[tuple[int, dict]]:
    eventos: list[tuple[int, dict]] = []
    with connection() as con:
        with con.cursor() as cur:
            cur.execute(
                "SELECT id,usuario_id,origem_nome,destino_nome,calado_m,margem_seguranca_m,velocidade_embarcacao_kmh,"
                "estacao_referencia,nivel_baseline_cm,limiar_cm,cooldown_min,ultima_recomputacao,fids_rota "
                "FROM rotas WHERE monitorar=TRUE"
            )
            rotas = [dict(r) for r in cur.fetchall()]
    codigos = {r["estacao_referencia"] for r in rotas if r["estacao_referencia"]}
    leituras = _ultimas_leituras_ana(codigos)
    for rota in rotas:
        try:
            evento = _verificar_rota(rota, leituras)
            if evento:
                eventos.append((rota["usuario_id"], evento))
        except Exception as exc:  # uma rota com erro nao derruba as demais
            print(f"[monitor] rota {rota['id']}: {exc}")
    return eventos


async def monitor_loop() -> None:
    bus.set_loop(asyncio.get_running_loop())
    while True:
        try:
            eventos = await asyncio.to_thread(verificar_rotas_monitoradas)
            for usuario_id, evento in eventos:
                bus.publish(usuario_id, evento)
        except Exception as exc:
            print(f"[monitor] erro no ciclo: {exc}")
        await asyncio.sleep(MONITOR_INTERVALO_MIN * 60)


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
    geometrias = river_graph.geometries([edge.fid for edge in edges])
    features = []
    items = []
    for edge in edges:
        linhas = geometrias.get(edge.fid, [])
        geometry = {"type": "LineString", "coordinates": linhas[0]} if len(linhas) == 1 else {"type": "MultiLineString", "coordinates": linhas}
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


def _rota_publica(row) -> dict:
    item = dict(row)
    item["monitorar"] = bool(item["monitorar"])
    for chave, valor in list(item.items()):
        if isinstance(valor, Decimal):
            item[chave] = float(valor)
    geo = item.get("rota_geojson")
    if isinstance(geo, str):
        geo = json.loads(geo)
    item["rota_geojson"] = geo
    return item


@app.post("/api/v1/rotas", status_code=status.HTTP_201_CREATED)
def save_route(input: RouteSaveInput, user: dict = Depends(current_user)):
    with connection() as con:
        with con.cursor() as cur:
            cur.execute(
                """INSERT INTO rotas (usuario_id,origem_nome,destino_nome,calado_m,margem_seguranca_m,
                velocidade_embarcacao_kmh,distancia_total_km,tempo_total_h,custo_total,trechos_criticos,
                profundidade_minima_m,rota_geojson,monitorar) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                RETURNING id""",
                (user["id"], input.origem_nome.strip(), input.destino_nome.strip(), input.calado_m,
                 input.margem_seguranca_m, input.velocidade_embarcacao_kmh, input.distancia_total_km,
                 input.tempo_total_h, input.custo_total, input.trechos_criticos, input.profundidade_minima_m,
                 Json(input.geojson) if input.geojson is not None else None, bool(input.monitorar)),
            )
            novo_id = cur.fetchone()["id"]
            cur.execute(f"SELECT {ROTA_COLS} FROM rotas WHERE id=%s", (novo_id,))
            row = cur.fetchone()
    registrar_evento("rota_salva", f"Rota {input.origem_nome} → {input.destino_nome}", user["id"])
    return ok(_rota_publica(row), 201)


@app.get("/api/v1/rotas")
def list_routes(user: dict = Depends(current_user)):
    with connection() as con:
        with con.cursor() as cur:
            cur.execute(f"SELECT {ROTA_COLS} FROM rotas WHERE usuario_id=%s ORDER BY created_at DESC, id DESC", (user["id"],))
            rows = cur.fetchall()
    items = [_rota_publica(row) for row in rows]
    return ok({"items": items, "total": len(items)})


@app.get("/api/v1/rotas/{rota_id}")
def get_route(rota_id: int, user: dict = Depends(current_user)):
    with connection() as con:
        with con.cursor() as cur:
            cur.execute(f"SELECT {ROTA_COLS} FROM rotas WHERE id=%s AND usuario_id=%s", (rota_id, user["id"]))
            row = cur.fetchone()
    if not row:
        raise ApiProblem(404, "route_not_found", "Rota não encontrada.")
    return ok(_rota_publica(row))


@app.delete("/api/v1/rotas/{rota_id}")
def delete_route(rota_id: int, user: dict = Depends(current_user)):
    with connection() as con:
        with con.cursor() as cur:
            cur.execute("DELETE FROM rotas WHERE id=%s AND usuario_id=%s", (rota_id, user["id"]))
            removidas = cur.rowcount
    if not removidas:
        raise ApiProblem(404, "route_not_found", "Rota não encontrada.")
    return ok({"id": rota_id, "removida": True})


@app.post("/api/v1/rotas/{rota_id}/monitorar")
def monitor_route(rota_id: int, input: MonitorInput, user: dict = Depends(current_user)):
    codigo = None
    baseline = None
    with connection() as con:
        with con.cursor() as cur:
            cur.execute(
                "SELECT id,destino_nome,limiar_cm,cooldown_min FROM rotas WHERE id=%s AND usuario_id=%s",
                (rota_id, user["id"]),
            )
            row = cur.fetchone()
            if not row:
                raise ApiProblem(404, "route_not_found", "Rota não encontrada.")
            if input.monitorar:
                try:
                    codigo = station_code(row["destino_nome"])
                    baseline = nivel_atual_cm(codigo)
                except ApiProblem:
                    codigo = None
                cur.execute(
                    "UPDATE rotas SET monitorar=TRUE, estacao_referencia=%s, nivel_baseline_cm=%s, ultima_verificacao=now() WHERE id=%s",
                    (codigo, baseline, rota_id),
                )
            else:
                cur.execute("UPDATE rotas SET monitorar=FALSE WHERE id=%s", (rota_id,))
    return ok({
        "rota_id": rota_id,
        "monitorar": input.monitorar,
        "estacao_referencia": codigo,
        "nivel_baseline_cm": baseline,
        "limiar_variacao_cm": float(row["limiar_cm"]),
        "cooldown_min": row["cooldown_min"],
    })


@app.get("/api/v1/rotas/{rota_id}/alteracoes")
def route_changes(rota_id: int, user: dict = Depends(current_user)):
    with connection() as con:
        with con.cursor() as cur:
            cur.execute("SELECT id FROM rotas WHERE id=%s AND usuario_id=%s", (rota_id, user["id"]))
            if not cur.fetchone():
                raise ApiProblem(404, "route_not_found", "Rota não encontrada.")
            cur.execute(
                "SELECT id,data_alteracao::text AS data_alteracao,motivo,variacao_nivel_cm,"
                "estacao_origem,distancia_total_km,custo_total,rota_geojson "
                "FROM rota_alteracao WHERE rota_id=%s ORDER BY id DESC",
                (rota_id,),
            )
            rows = cur.fetchall()
    return ok({"items": [_alteracao_publica(r) for r in rows]})


@app.get("/api/v1/logs")
def list_logs(limite: int = 100, _: dict = Depends(admin_user)):
    limite = max(1, min(limite, 500))
    with connection() as con:
        with con.cursor() as cur:
            cur.execute("SELECT id,usuario_id,tipo,detalhe,data_hora::text AS data_hora FROM log_eventos ORDER BY id DESC LIMIT %s", (limite,))
            rows = cur.fetchall()
    items = [dict(row) for row in rows]
    return ok({"items": items, "total": len(items)})


@app.websocket("/api/v1/ws")
async def websocket_eventos(websocket: WebSocket, token: str | None = None):
    if not token:
        await websocket.close(code=4401)
        return
    try:
        dados = read_token(token)
    except ApiProblem:
        await websocket.close(code=4401)
        return
    await websocket.accept()
    fila = bus.subscribe(dados["id"])
    try:
        while True:
            evento = await fila.get()
            await websocket.send_json(evento)
    except WebSocketDisconnect:
        pass
    finally:
        bus.unsubscribe(dados["id"], fila)


@app.post("/api/v1/monitor/executar")
def monitor_executar(_: dict = Depends(admin_user)):
    """Executa um ciclo de verificacao manualmente (admin)."""
    eventos = verificar_rotas_monitoradas()
    for usuario_id, evento in eventos:
        bus.publish(usuario_id, evento)
    return ok({"eventos": len(eventos), "itens": [ev for _, ev in eventos]})
