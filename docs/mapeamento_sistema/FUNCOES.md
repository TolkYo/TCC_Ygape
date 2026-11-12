# FUNCOES — catálogo de funções próprias

> Fonte: código do repositório (verificado em 2026-10-20). IDs nunca são reciclados.
> Organização: linguagem → categoria → função.
> **Cobertura:** `backend/` (API FastAPI + PostGIS) e `frontend/src/` (aplicação Vue 3).
> **Fora de cobertura:** `backend_sqlite/` (legado pré-PostGIS) e `frontend/prototipos/` (protótipos declarados como legado no README). Cobertura incremental: funções aninhadas/geradores são descritas dentro da função hospedeira; clientes de endpoint em `frontend/src/services/endpoints.ts` são rastreados em `API-END.md`.
> Assinaturas refletem o código na data da auditoria. Não há anotação `@id` no código-fonte; a vinculação foi feita por arquivo + símbolo.

## PYTHON

### AUTH

#### FUN-PY-AUTH-001 — password_hash(password, salt=None)
- Status: Ativa
- Arquivo: `backend/main.py`
- Simbolo: `password_hash`
- Assinatura: `password_hash(password: str, salt: bytes | None = None) -> str`
- Objetivo: Gerar hash de senha com sal aleatório para armazenamento.
- Funcionamento: Usa `hashlib.scrypt` (n=2**14, r=8, p=1) e codifica `salt + digest` em base64 URL-safe.
- Entradas: Senha em texto puro e sal opcional de 16 bytes.
- Saidas: String base64 URL-safe contendo sal e digest.
- Erros e efeitos: Não trata exceções; sal é gerado com `secrets.token_bytes(16)` quando omitido.
- Dependencias: `hashlib`, `base64`, `secrets`.
- Consumidores: `backend/main.py` (criação/atualização de usuário, perfil), `backend/criar_admin.py` (FUN-PY-ADMIN-001).
- Testes: Sem teste automatizado identificado.

#### FUN-PY-AUTH-002 — verify_password(password, stored)
- Status: Ativa
- Arquivo: `backend/main.py`
- Simbolo: `verify_password`
- Assinatura: `verify_password(password: str, stored: str) -> bool`
- Objetivo: Comparar senha informada com hash armazenado.
- Funcionamento: Decodifica base64, separa os 16 bytes de sal, recalcula o hash e compara com `hmac.compare_digest`.
- Entradas: Senha em texto puro e hash armazenado.
- Saidas: `True` se confere; `False` em hash inválido ou divergência.
- Erros e efeitos: Captura `ValueError`/`TypeError` e devolve `False`.
- Dependencias: FUN-PY-AUTH-001.
- Consumidores: `backend/main.py` (`login`, FUN-PY-API-021).
- Testes: Sem teste automatizado identificado.

#### FUN-PY-AUTH-003 — signing_secret()
- Status: Ativa
- Arquivo: `backend/main.py`
- Simbolo: `signing_secret`
- Assinatura: `signing_secret() -> bytes`
- Objetivo: Obter o segredo HMAC dos tokens a partir do ambiente.
- Funcionamento: Lê `HIDROWIZE_TOKEN_SECRET` no carregamento do módulo; se vazio, levanta `ApiProblem`.
- Entradas: Nenhuma.
- Saidas: Segredo em bytes.
- Erros e efeitos: `ApiProblem(503, "auth_not_configured")` quando o segredo não está definido.
- Dependencias: `os`, `ApiProblem` (FUN-PY-API-044).
- Consumidores: FUN-PY-AUTH-004, FUN-PY-AUTH-005.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-AUTH-004 — issue_token(user)
- Status: Ativa
- Arquivo: `backend/main.py`
- Simbolo: `issue_token`
- Assinatura: `issue_token(user: dict) -> str`
- Objetivo: Emitir token de sessão assinado.
- Funcionamento: Monta payload `id:papel:expira_em` (epoch + `TOKEN_TTL_SECONDS`, padrão 28800 s), assina com HMAC-SHA256 e codifica em base64 URL-safe.
- Entradas: Dicionário com `id` e `papel`.
- Saidas: Token opaco.
- Erros e efeitos: `ApiProblem(503)` se o segredo não estiver configurado.
- Dependencias: FUN-PY-AUTH-003.
- Consumidores: `backend/main.py` (`login`, FUN-PY-API-021).
- Testes: Sem teste automatizado identificado.

#### FUN-PY-AUTH-005 — read_token(token)
- Status: Ativa
- Arquivo: `backend/main.py`
- Simbolo: `read_token`
- Assinatura: `read_token(token: str) -> dict`
- Objetivo: Validar assinatura/expiração e extrair identidade do token.
- Funcionamento: Decodifica base64, separa payload/assinatura, recalcula HMAC, valida expiração e papel em `{admin, piloto}`.
- Entradas: Token opaco.
- Saidas: `{"id": int, "papel": str}`.
- Erros e efeitos: `ApiProblem(401, "invalid_token")` em token ausente, inválido ou expirado.
- Dependencias: FUN-PY-AUTH-003.
- Consumidores: FUN-PY-AUTH-006, FUN-PY-API-041 (WebSocket).
- Testes: Sem teste automatizado identificado.

#### FUN-PY-AUTH-006 — current_user(credentials)
- Status: Ativa
- Arquivo: `backend/main.py`
- Simbolo: `current_user`
- Assinatura: `current_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)) -> dict`
- Objetivo: Dependência FastAPI que autentica o usuário em cada requisição.
- Funcionamento: Exige esquema Bearer, valida o token (FUN-PY-AUTH-005) e recarrega `id,nome,email,papel,ativo` do banco; rejeita usuário inativo.
- Entradas: Credencial HTTP Bearer.
- Saidas: Dicionário do usuário ativo.
- Erros e efeitos: `ApiProblem(401, "missing_token"|"invalid_token")`; consulta o PostgreSQL.
- Dependencias: FUN-PY-AUTH-005, FUN-PY-DATA-002.
- Consumidores: `me`, `update_me`, `levels`, rotas, logs e `sync_snapshot` (FUN-PY-API-022/023/030/034-043).
- Testes: Sem teste automatizado identificado.

#### FUN-PY-AUTH-007 — admin_user(user)
- Status: Ativa
- Arquivo: `backend/main.py`
- Simbolo: `admin_user`
- Assinatura: `admin_user(user: dict = Depends(current_user)) -> dict`
- Objetivo: Restringir operações ao papel `admin`.
- Funcionamento: Reutiliza `current_user` e compara `user["papel"]`.
- Entradas: Usuário autenticado.
- Saidas: O mesmo usuário, quando admin.
- Erros e efeitos: `ApiProblem(403, "forbidden")` para piloto.
- Dependencias: FUN-PY-AUTH-006.
- Consumidores: `list_users`, `create_user`, `update_user`, `disable_user`, `collect_levels`, `list_logs`, `monitor_executar` (FUN-PY-API-024/025/026/027/031/040/042).
- Testes: Sem teste automatizado identificado.

### API

#### FUN-PY-API-001 — ok(data, status_code=200)
- Status: Ativa
- Arquivo: `backend/main.py`
- Simbolo: `ok`
- Assinatura: `ok(data: object, status_code: int = 200) -> JSONResponse`
- Objetivo: Padronizar o envelope de sucesso `{"success": true, "data": ...}`.
- Funcionamento: Serializa o conteúdo em `JSONResponse` com o status informado.
- Entradas: Dados e status HTTP.
- Saidas: `JSONResponse`.
- Erros e efeitos: Pode falhar na serialização JSON de tipos não suportados (não tratado).
- Dependencias: `fastapi.responses.JSONResponse`.
- Consumidores: Todos os handlers HTTP de `backend/main.py`.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-API-002 — registrar_evento(tipo, detalhe, usuario_id=None)
- Status: Ativa
- Arquivo: `backend/main.py`
- Simbolo: `registrar_evento`
- Assinatura: `registrar_evento(tipo: str, detalhe: str, usuario_id: int | None = None) -> None`
- Objetivo: Gravar evento de auditoria em `log_eventos`.
- Funcionamento: Abre conexão e executa `INSERT`; erros de banco são silenciados.
- Entradas: Tipo, detalhe e usuário opcional.
- Saidas: Nenhuma.
- Erros e efeitos: Falhas `psycopg2.Error` são ignoradas; não há transação própria além do contexto.
- Dependencias: FUN-PY-DATA-002.
- Consumidores: `login`, `update_me`, `create_user`, `disable_user`, `save_route` (FUN-PY-API-021/023/025/027/034).
- Testes: Sem teste automatizado identificado.

#### FUN-PY-API-003 — station_code(identifier)
- Status: Ativa
- Arquivo: `backend/main.py`
- Simbolo: `station_code`
- Assinatura: `station_code(identifier: str) -> str`
- Objetivo: Resolver código de estação/porto a partir do código ou nome.
- Funcionamento: Consulta `estacoes` + `estacoes_trechos`, aceita código exato ou nome sem distinção de caixa e escolhe o trecho de menor `distancia_m`.
- Entradas: Código ou nome da estação.
- Saidas: `codigo_estacao` como string.
- Erros e efeitos: `ApiProblem(404, "port_not_found")` quando não encontra.
- Dependencias: FUN-PY-DATA-002.
- Consumidores: `calculate_route`, `monitor_route`, `_verificar_rota` (FUN-PY-API-033/038, FUN-PY-MON-002).
- Testes: Sem teste automatizado identificado.

#### FUN-PY-API-004 — nivel_atual_cm(codigo)
- Status: Ativa
- Arquivo: `backend/main.py`
- Simbolo: `nivel_atual_cm`
- Assinatura: `nivel_atual_cm(codigo: str | None) -> float | None`
- Objetivo: Obter a última cota adotada de uma estação.
- Funcionamento: Consulta `telemetria` ordenando por `data_hora_medicao DESC, id DESC LIMIT 1`.
- Entradas: Código da estação (ou `None`).
- Saidas: Cota em cm como float, ou `None`.
- Erros e efeitos: Consulta o banco quando o código é informado.
- Dependencias: FUN-PY-DATA-002.
- Consumidores: `monitor_route`, `_verificar_rota` (FUN-PY-API-038, FUN-PY-MON-002).
- Testes: Sem teste automatizado identificado.

#### FUN-PY-API-005 — _alteracao_publica(row)
- Status: Ativa
- Arquivo: `backend/main.py`
- Simbolo: `_alteracao_publica`
- Assinatura: `_alteracao_publica(row) -> dict`
- Objetivo: Converter registro de `rota_alteracao` para resposta pública.
- Funcionamento: Converte `Decimal` em `float` e desserializa `rota_geojson` quando string.
- Entradas: Linha de banco (mapeamento ou dict).
- Saidas: Dicionário serializável.
- Erros e efeitos: `json.loads` pode levantar erro se o campo textual for JSON inválido (não tratado).
- Dependencias: `json`, `Decimal`.
- Consumidores: `route_changes` (FUN-PY-API-039).
- Testes: Sem teste automatizado identificado.

#### FUN-PY-API-006 — _atualizar_rota(rota_id, campos)
- Status: Ativa
- Arquivo: `backend/main.py`
- Simbolo: `_atualizar_rota`
- Assinatura: `_atualizar_rota(rota_id: int, campos: dict) -> None`
- Objetivo: Atualizar colunas arbitrárias de uma rota.
- Funcionamento: Monta `UPDATE rotas SET ... WHERE id=%s` com os nomes de coluna informados.
- Entradas: ID da rota e mapa coluna→valor.
- Saidas: Nenhuma.
- Erros e efeitos: Retorna imediatamente se `campos` estiver vazio; nomes de coluna entram na SQL sem validação (uso interno controlado).
- Dependencias: FUN-PY-DATA-002.
- Consumidores: FUN-PY-MON-002.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-API-007 — _montar_geojson(edges)
- Status: Ativa
- Arquivo: `backend/main.py`
- Simbolo: `_montar_geojson`
- Assinatura: `_montar_geojson(edges) -> dict`
- Objetivo: Montar `FeatureCollection` com a geometria das arestas da rota.
- Funcionamento: Obtém geometrias via `RiverGraph.geometries` e emite `LineString` ou `MultiLineString` com `fid`, distância e profundidade.
- Entradas: Lista de `Edge`.
- Saidas: GeoJSON (`FeatureCollection`).
- Erros e efeitos: Consulta o PostGIS.
- Dependencias: FUN-PY-ROUTE-004.
- Consumidores: FUN-PY-MON-002.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-API-008 — _rota_publica(row)
- Status: Ativa
- Arquivo: `backend/main.py`
- Simbolo: `_rota_publica`
- Assinatura: `_rota_publica(row) -> dict`
- Objetivo: Normalizar rota persistida para resposta JSON.
- Funcionamento: Converte `monitorar` para bool, `Decimal` para float e desserializa `rota_geojson`.
- Entradas: Linha de `rotas`.
- Saidas: Dicionário serializável.
- Erros e efeitos: Pode falhar em JSON inválido (não tratado).
- Dependencias: `json`, `Decimal`.
- Consumidores: `save_route`, `list_routes`, `get_route` (FUN-PY-API-034/035/036).
- Testes: Sem teste automatizado identificado.

#### FUN-PY-API-009 — api_problem_handler(_, error)
- Status: Ativa
- Arquivo: `backend/main.py`
- Simbolo: `api_problem_handler`
- Assinatura: `api_problem_handler(_: Request, error: ApiProblem)`
- Objetivo: Serializar `ApiProblem` no envelope de erro.
- Funcionamento: Retorna `{"success": false, "error": {code, message}}` com o status da exceção.
- Entradas: Requisição e exceção.
- Saidas: `JSONResponse`.
- Erros e efeitos: Nenhum efeito colateral.
- Dependencias: FUN-PY-API-044.
- Consumidores: FastAPI (handler registrado em `app.exception_handler`).
- Testes: Sem teste automatizado identificado.

#### FUN-PY-API-010 — iniciar()
- Status: Ativa
- Arquivo: `backend/main.py`
- Simbolo: `iniciar`
- Assinatura: `iniciar() -> None`
- Objetivo: Inicializar schema e ciclo de monitoramento no startup.
- Funcionamento: Chama `ensure_schema()`; falhas de banco apenas imprimem aviso; agenda `monitor_loop()` como task.
- Entradas: Nenhuma.
- Saidas: Nenhuma.
- Erros e efeitos: Cria tarefa assíncrona permanente; erros de schema não interrompem o startup.
- Dependencias: FUN-PY-DATA-003, FUN-PY-MON-004.
- Consumidores: Evento `startup` do FastAPI.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-API-020 — health()
- Status: Ativa
- Arquivo: `backend/main.py`
- Simbolo: `health`
- Assinatura: `health()`
- Objetivo: Verificar disponibilidade da API e do banco.
- Funcionamento: Executa `SELECT 1`; retorna `status` `ok`/`degraded` e booleano `db`.
- Entradas: Nenhuma.
- Saidas: Envelope de sucesso.
- Erros e efeitos: Captura `psycopg2.Error`.
- Dependencias: FUN-PY-DATA-002.
- Consumidores: `API-SYSTEM-001`.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-API-021 — login(input)
- Status: Ativa
- Arquivo: `backend/main.py`
- Simbolo: `login`
- Assinatura: `login(input: LoginInput)`
- Objetivo: Autenticar usuário e emitir token.
- Funcionamento: Busca por e-mail case-insensitive, exige usuário ativo e senha válida; registra evento e devolve token, validade e dados públicos.
- Entradas: `email`, `senha`.
- Saidas: `access_token`, `token_type`, `expires_in`, `usuario`.
- Erros e efeitos: `ApiProblem(401, "invalid_credentials")`; grava log de login.
- Dependencias: FUN-PY-AUTH-002, FUN-PY-AUTH-004, FUN-PY-API-002, FUN-PY-DATA-002.
- Consumidores: `API-AUTH-001`; `frontend/src/stores/session.ts` → `api.login`.
- Testes: `frontend/src/stores/session.spec.ts` (fluxo de login no cliente).
- Observação: `backend/criar_admin.py` importa `password_hash` deste módulo, não `login`.

#### FUN-PY-API-022 — me(user)
- Status: Ativa
- Arquivo: `backend/main.py`
- Simbolo: `me`
- Assinatura: `me(user: dict = Depends(current_user))`
- Objetivo: Retornar o usuário autenticado.
- Funcionamento: Projeta `id,nome,email,papel` do usuário resolvido pela dependência.
- Entradas: Usuário autenticado.
- Saidas: Envelope com dados do usuário.
- Erros e efeitos: Herda os erros de autenticação.
- Dependencias: FUN-PY-AUTH-006.
- Consumidores: `API-AUTH-002`; `frontend/src/stores/session.ts` → `api.me`.
- Testes: `frontend/src/stores/session.spec.ts`.

#### FUN-PY-API-023 — update_me(input, user)
- Status: Ativa
- Arquivo: `backend/main.py`
- Simbolo: `update_me`
- Assinatura: `update_me(input: ProfileUpdate, user: dict = Depends(current_user))`
- Objetivo: Atualizar nome/senha do próprio usuário.
- Funcionamento: Remove campos nulos, converte `senha` em `senha_hash` e atualiza somente o usuário autenticado.
- Entradas: `nome` e/ou `senha`.
- Saidas: Dados públicos atualizados.
- Erros e efeitos: `ApiProblem(422, "empty_update")`; grava log.
- Dependencias: FUN-PY-AUTH-001, FUN-PY-API-002, FUN-PY-DATA-002.
- Consumidores: `API-AUTH-003`; `frontend/src/stores/session.ts` → `api.atualizarPerfil`.
- Testes: `frontend/src/stores/session.spec.ts`.

#### FUN-PY-API-024 — list_users(_)
- Status: Ativa
- Arquivo: `backend/main.py`
- Simbolo: `list_users`
- Assinatura: `list_users(_: dict = Depends(admin_user))`
- Objetivo: Listar usuários para administração.
- Funcionamento: Seleciona todos os campos públicos ordenados por nome.
- Entradas: Nenhuma (admin).
- Saidas: `{items, total}`.
- Erros e efeitos: `403` para não-admin.
- Dependencias: FUN-PY-AUTH-007, FUN-PY-DATA-002.
- Consumidores: `API-USER-001`; `frontend/src/views/admin/UsuariosView.vue`.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-API-025 — create_user(input, admin)
- Status: Ativa
- Arquivo: `backend/main.py`
- Simbolo: `create_user`
- Assinatura: `create_user(input: UserInput, admin: dict = Depends(admin_user))`
- Objetivo: Criar usuário (somente admin).
- Funcionamento: Insere `nome,email,senha_hash,papel`; e-mail é normalizado para minúsculas.
- Entradas: `nome`, `email`, `senha`, `papel`.
- Saidas: Usuário criado (201).
- Erros e efeitos: `ApiProblem(409, "email_exists")` em e-mail duplicado; grava log.
- Dependencias: FUN-PY-AUTH-001, FUN-PY-AUTH-007, FUN-PY-API-002.
- Consumidores: `API-USER-002`; `frontend/src/views/admin/UsuariosView.vue`.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-API-026 — update_user(user_id, input, _)
- Status: Ativa
- Arquivo: `backend/main.py`
- Simbolo: `update_user`
- Assinatura: `update_user(user_id: int, input: UserUpdate, _: dict = Depends(admin_user))`
- Objetivo: Atualizar qualquer usuário (admin).
- Funcionamento: Aceita `nome`, `senha`, `papel`, `ativo`; converte senha em hash.
- Entradas: ID e campos parciais.
- Saidas: Dados públicos atualizados.
- Erros e efeitos: `422` para payload vazio; `404` se usuário inexistente.
- Dependencias: FUN-PY-AUTH-001, FUN-PY-AUTH-007, FUN-PY-DATA-002.
- Consumidores: `API-USER-003`; `frontend/src/views/admin/UsuariosView.vue`.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-API-027 — disable_user(user_id, admin)
- Status: Ativa
- Arquivo: `backend/main.py`
- Simbolo: `disable_user`
- Assinatura: `disable_user(user_id: int, admin: dict = Depends(admin_user))`
- Objetivo: Desativar usuário sem removê-lo.
- Funcionamento: `UPDATE usuarios SET ativo=FALSE`; 404 se nenhuma linha afetada; grava log.
- Entradas: ID do usuário.
- Saidas: `{id, ativo: false}`.
- Erros e efeitos: `ApiProblem(404, "user_not_found")`.
- Dependencias: FUN-PY-AUTH-007, FUN-PY-API-002.
- Consumidores: `API-USER-004`; `frontend/src/views/admin/UsuariosView.vue`.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-API-028 — list_stations(rio, municipio, ativa)
- Status: Ativa
- Arquivo: `backend/main.py`
- Simbolo: `list_stations`
- Assinatura: `list_stations(rio: str | None = None, municipio: str | None = None, ativa: bool = True)`
- Objetivo: Listar estações com cota mínima e última telemetria.
- Funcionamento: Filtros `ILIKE` por rio/município e `COALESCE(operando,1)=1`; junta `cotas_historicas` e a leitura mais recente de `telemetria`.
- Entradas: Filtros opcionais.
- Saidas: `items` com `cota_minima_historica_m`, `nivel_atual_cm`, `atualizado_em`.
- Erros e efeitos: Consulta correlacionada por estação; sem paginação.
- Dependencias: FUN-PY-DATA-002.
- Consumidores: `API-DATA-001`; `frontend/src/stores/estacoes.ts`.
- Testes: `frontend/src/stores/estacoes.spec.ts` (cliente).

#### FUN-PY-API-029 — station(codigo)
- Status: Ativa
- Arquivo: `backend/main.py`
- Simbolo: `station`
- Assinatura: `station(codigo: str)`
- Objetivo: Consultar uma estação pelo código.
- Funcionamento: `SELECT` em `estacoes` por `codigo_estacao`.
- Entradas: Código da estação.
- Saidas: Dados cadastrais.
- Erros e efeitos: `ApiProblem(404, "station_not_found")`.
- Dependencias: FUN-PY-DATA-002.
- Consumidores: `API-DATA-002`.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-API-030 — levels(estacao, data_inicio, data_fim, _)
- Status: Ativa
- Arquivo: `backend/main.py`
- Simbolo: `levels`
- Assinatura: `levels(estacao: str, data_inicio: str, data_fim: str | None = None, _: dict = Depends(current_user))`
- Objetivo: Consultar a série de telemetria de uma estação.
- Funcionamento: Valida existência da estação e filtra por `substr(data_hora_medicao,1,10)` entre as datas; ordena cronologicamente.
- Entradas: Estação, data inicial e final opcional.
- Saidas: `estacao` e `items` (`data_hora`, `nivel_cm`, `chuva_mm`, `vazao`).
- Erros e efeitos: `404` para estação inexistente; exige autenticação.
- Dependencias: FUN-PY-AUTH-006, FUN-PY-DATA-002.
- Consumidores: `API-DATA-003`.
- Testes: Sem teste automatizado identificado.
- Observação: não aplica o limite de 90 dias previsto na regra RN-NIVEL-003.

#### FUN-PY-API-031 - collect_levels(input, admin)
- Status: Ativa
- Arquivo: `backend/main.py`
- Simbolo: `collect_levels`
- Assinatura: `collect_levels(input: CollectInput, admin: dict = Depends(admin_user)): JSONResponse`
- Objetivo: Iniciar uma coleta manual de telemetria da ANA.
- Funcionamento: Valida período e estações, cria um job em memória (`COLETA_JOBS`), marca `COLETA_ATIVA` e dispara `_executar_coleta_niveis`; responde `202` com o job.
- Entradas: Estações (opcional) e período (opcional).
- Saidas: `{success, data: job}` com HTTP 202.
- Erros e efeitos: 422 para período/estação inválidos; 409 se já houver coleta; grava leituras no PostGIS em background.
- Dependencias: FUN-PY-COL-065, FUN-PY-COL-067.
- Consumidores: FUN-TS-API-009; FUN-TS-UI-022.
- Testes: Verificado manualmente em produção (1 estação e lote completo).

#### FUN-PY-API-032 — graph_status()
- Status: Ativa
- Arquivo: `backend/main.py`
- Simbolo: `graph_status`
- Assinatura: `graph_status()`
- Objetivo: Expor métricas do grafo carregado.
- Funcionamento: Chama `river_graph.status()` e adiciona área ativa fixa e `pronto: true`.
- Entradas: Nenhuma.
- Saidas: `nos`, `arestas`, `portos_associados`, `area_ativa`, `ultima_reconstrucao`, `pronto`.
- Erros e efeitos: Carrega o grafo na primeira chamada (consulta o PostGIS).
- Dependencias: FUN-PY-ROUTE-005.
- Consumidores: `API-GRAPH-001`; `frontend/src/services/endpoints.ts` (`grafoStatus`).
- Testes: Sem teste automatizado identificado.

#### FUN-PY-API-033 — calculate_route(input)
- Status: Ativa
- Arquivo: `backend/main.py`
- Simbolo: `calculate_route`
- Assinatura: `calculate_route(input: RouteInput)`
- Objetivo: Calcular rota navegável entre origem e destino.
- Funcionamento: Resolve códigos de estação, chama `RiverGraph.route`, agrega distância/tempo e monta GeoJSON e itens por aresta com flag `transitavel`.
- Entradas: `origem_nome`, `destino_nome`, `calado_m`, `margem_seguranca_m`, `velocidade_embarcacao_kmh`, `monitorar`.
- Saidas: Resumo da rota, `geojson` e `items`.
- Erros e efeitos: `422` para porto sem trecho; `404` para rota inexistente.
- Dependencias: FUN-PY-API-003, FUN-PY-ROUTE-006.
- Consumidores: `API-ROUTE-001`; `frontend/src/stores/rota.ts` → `api.calcularRota`.
- Testes: `frontend/src/stores/rota.spec.ts` (cliente e fallback offline).
- Observação: endpoint público (não exige JWT).

#### FUN-PY-API-034 — save_route(input, user)
- Status: Ativa
- Arquivo: `backend/main.py`
- Simbolo: `save_route`
- Assinatura: `save_route(input: RouteSaveInput, user: dict = Depends(current_user))`
- Objetivo: Persistir rota calculada no histórico do usuário.
- Funcionamento: Insere os parâmetros e resultados em `rotas`; registra evento; devolve o registro público.
- Entradas: Payload completo da rota salva.
- Saidas: Rota persistida (201).
- Erros e efeitos: `401` sem sessão; grava log `rota_salva`.
- Dependencias: FUN-PY-AUTH-006, FUN-PY-API-002, FUN-PY-API-008.
- Consumidores: `API-ROUTE-002`; `frontend/src/stores/rota.ts` → `api.salvarRota`.
- Testes: `frontend/src/stores/rota.spec.ts`.

#### FUN-PY-API-035 — list_routes(user)
- Status: Ativa
- Arquivo: `backend/main.py`
- Simbolo: `list_routes`
- Assinatura: `list_routes(user: dict = Depends(current_user))`
- Objetivo: Listar rotas do usuário autenticado.
- Funcionamento: Seleciona por `usuario_id` ordenando por criação e id decrescentes.
- Entradas: Sessão.
- Saidas: `{items, total}`.
- Erros e efeitos: `401` sem sessão.
- Dependencias: FUN-PY-AUTH-006, FUN-PY-API-008.
- Consumidores: `API-ROUTE-003`; `frontend/src/stores/rota.ts` e `offline.ts`.
- Testes: `frontend/src/stores/rota.spec.ts`.

#### FUN-PY-API-036 — get_route(rota_id, user)
- Status: Ativa
- Arquivo: `backend/main.py`
- Simbolo: `get_route`
- Assinatura: `get_route(rota_id: int, user: dict = Depends(current_user))`
- Objetivo: Consultar uma rota do próprio usuário.
- Funcionamento: Filtra por `id` e `usuario_id`.
- Entradas: ID da rota e sessão.
- Saidas: Rota pública.
- Erros e efeitos: `404` quando não pertence ao usuário.
- Dependencias: FUN-PY-AUTH-006, FUN-PY-API-008.
- Consumidores: `API-ROUTE-004`; `frontend/src/services/endpoints.ts` (`obterRota`).
- Testes: Sem teste automatizado identificado.

#### FUN-PY-API-037 — delete_route(rota_id, user)
- Status: Ativa
- Arquivo: `backend/main.py`
- Simbolo: `delete_route`
- Assinatura: `delete_route(rota_id: int, user: dict = Depends(current_user))`
- Objetivo: Remover uma rota do histórico.
- Funcionamento: `DELETE ... WHERE id=%s AND usuario_id=%s`.
- Entradas: ID e sessão.
- Saidas: `{id, removida: true}`.
- Erros e efeitos: `404` se não encontrada; `rota_alteracao` é removida por cascade.
- Dependencias: FUN-PY-AUTH-006.
- Consumidores: `API-ROUTE-005`; `frontend/src/stores/rota.ts`.
- Testes: `frontend/src/stores/rota.spec.ts`.

#### FUN-PY-API-038 — monitor_route(rota_id, input, user)
- Status: Ativa
- Arquivo: `backend/main.py`
- Simbolo: `monitor_route`
- Assinatura: `monitor_route(rota_id: int, input: MonitorInput, user: dict = Depends(current_user))`
- Objetivo: Ativar/desativar o monitoramento de uma rota.
- Funcionamento: Ao ativar, resolve a estação de referência (destino), lê a cota atual como baseline e grava `monitorar`, `estacao_referencia`, `nivel_baseline_cm` e `ultima_verificacao`.
- Entradas: ID da rota e `monitorar`.
- Saidas: Estado do monitoramento, referência, baseline, limiar e cooldown.
- Erros e efeitos: `404` se a rota não pertence ao usuário; falha ao resolver estação mantém referência nula.
- Dependencias: FUN-PY-AUTH-006, FUN-PY-API-003, FUN-PY-API-004.
- Consumidores: `API-ROUTE-006`; `frontend/src/stores/rota.ts`.
- Testes: `frontend/src/stores/rota.spec.ts`.

#### FUN-PY-API-039 — route_changes(rota_id, user)
- Status: Ativa
- Arquivo: `backend/main.py`
- Simbolo: `route_changes`
- Assinatura: `route_changes(rota_id: int, user: dict = Depends(current_user))`
- Objetivo: Listar alterações registradas para uma rota.
- Funcionamento: Valida propriedade da rota e retorna `rota_alteracao` em ordem decrescente.
- Entradas: ID e sessão.
- Saidas: `{items}`.
- Erros e efeitos: `404` se a rota não pertence ao usuário.
- Dependencias: FUN-PY-AUTH-006, FUN-PY-API-005.
- Consumidores: `API-ROUTE-007`; `frontend/src/stores/rota.ts` e `notificacao.ts`.
- Testes: `frontend/src/stores/rota.spec.ts`, `frontend/src/stores/notificacao.spec.ts`.

#### FUN-PY-API-040 — list_logs(limite, _)
- Status: Ativa
- Arquivo: `backend/main.py`
- Simbolo: `list_logs`
- Assinatura: `list_logs(limite: int = 100, _: dict = Depends(admin_user))`
- Objetivo: Consultar logs de auditoria.
- Funcionamento: Limita `limite` ao intervalo 1–500 e ordena por id decrescente.
- Entradas: Limite opcional.
- Saidas: `{items, total}`.
- Erros e efeitos: `403` para não-admin.
- Dependencias: FUN-PY-AUTH-007, FUN-PY-DATA-002.
- Consumidores: `API-ADMIN-001`; `frontend/src/views/admin/LogsView.vue`.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-API-041 — websocket_eventos(websocket, token)
- Status: Ativa
- Arquivo: `backend/main.py`
- Simbolo: `websocket_eventos`
- Assinatura: `websocket_eventos(websocket: WebSocket, token: str | None = None)`
- Objetivo: Entregar eventos de monitoramento por usuário.
- Funcionamento: Valida token via `read_token`, aceita a conexão, assina a fila do usuário no `EventBus` e envia eventos até desconectar.
- Entradas: Conexão WebSocket e token em query string.
- Saidas: Mensagens JSON de eventos.
- Erros e efeitos: Fecha com code `4401` sem token/token inválido; remove a assinatura no `finally`.
- Dependencias: FUN-PY-AUTH-005, FUN-PY-EVENT-003, FUN-PY-EVENT-004.
- Consumidores: `API-ROUTE-008`; `frontend/src/stores/notificacao.ts`.
- Testes: `frontend/src/stores/notificacao.spec.ts` (cliente).

#### FUN-PY-API-042 — monitor_executar(_)
- Status: Ativa
- Arquivo: `backend/main.py`
- Simbolo: `monitor_executar`
- Assinatura: `monitor_executar(_: dict = Depends(admin_user))`
- Objetivo: Executar um ciclo de verificação de rotas manualmente.
- Funcionamento: Chama `verificar_rotas_monitoradas`, publica cada evento no `EventBus` e retorna a quantidade.
- Entradas: Nenhuma (admin).
- Saidas: `{eventos, itens}`.
- Erros e efeitos: Pode consultar a ANA e recalcular rotas.
- Dependencias: FUN-PY-AUTH-007, FUN-PY-MON-003, FUN-PY-EVENT-005.
- Consumidores: `API-ADMIN-002`.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-API-043 — sync_snapshot(bbox, _)
- Status: Ativa
- Arquivo: `backend/main.py`
- Simbolo: `sync_snapshot`
- Assinatura: `sync_snapshot(bbox: str | None = None, _: dict = Depends(current_user))`
- Objetivo: Exportar grafo compacto para cálculo offline.
- Funcionamento: Lê `trechos_navegaveis` (com filtro `bbox` opcional), monta nós/arestas com coordenadas e distância (`ST_Length`), e associa estações via `estacoes_trechos`.
- Entradas: `bbox` opcional `minx,miny,maxx,maxy`, sessão.
- Saidas: `gerado_em`, `area`, totais, `nos`, `arestas`, `estacoes`.
- Erros e efeitos: `422, "invalid_bbox"`; resposta comprimida por GZip quando acima de 100 kB; exige JWT.
- Dependencias: FUN-PY-AUTH-006, FUN-PY-DATA-002.
- Consumidores: `API-SYNC-001`; `frontend/src/services/endpoints.ts` (`snapshot`) e `stores/offline.ts`.
- Testes: `frontend/src/stores/offline.spec.ts`.

#### FUN-PY-API-044 — ApiProblem.__init__(status_code, code, message)
- Status: Ativa
- Arquivo: `backend/main.py`
- Simbolo: `ApiProblem.__init__`
- Assinatura: `ApiProblem.__init__(self, status_code: int, code: str, message: str)`
- Objetivo: Representar erro de API com status, código e mensagem.
- Funcionamento: Armazena os três atributos; não chama o construtor de `Exception`.
- Entradas: Status HTTP, código e mensagem.
- Saidas: Instância de exceção.
- Erros e efeitos: Nenhum.
- Dependencias: Nenhuma.
- Consumidores: Todo o `backend/main.py` e `backend/criar_admin.py` (indiretamente).
- Testes: Sem teste automatizado identificado.

#### FUN-PY-API-045 - collect_status(job_id, _)
- Status: Ativa
- Arquivo: `backend/main.py`
- Simbolo: `collect_status`
- Assinatura: `collect_status(job_id: str, _: dict = Depends(admin_user)): JSONResponse`
- Objetivo: Consultar o andamento de uma coleta manual.
- Funcionamento: Devolve uma cópia do job armazenado em `COLETA_JOBS` sob lock; 404 se não existir.
- Entradas: `job_id`.
- Saidas: Objeto do job.
- Erros e efeitos: Nenhum (somente leitura).
- Dependencias: FUN-PY-API-031.
- Consumidores: FUN-TS-API-020; FUN-TS-UI-039.
- Testes: Verificado manualmente em produção.

### EVENT

#### FUN-PY-EVENT-001 — EventBus.__init__()
- Status: Ativa
- Arquivo: `backend/main.py`
- Simbolo: `EventBus.__init__`
- Assinatura: `EventBus.__init__(self) -> None`
- Objetivo: Inicializar o barramento de eventos em memória.
- Funcionamento: Cria mapa `user_id → set[Queue]`, lock e referência ao loop.
- Entradas: Nenhuma.
- Saidas: Nenhuma.
- Erros e efeitos: Estado somente em memória (não persiste).
- Dependencias: `asyncio`, `threading`.
- Consumidores: Instanciação do singleton `bus`.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-EVENT-002 — EventBus.set_loop(loop)
- Status: Ativa
- Arquivo: `backend/main.py`
- Simbolo: `EventBus.set_loop`
- Assinatura: `EventBus.set_loop(self, loop: asyncio.AbstractEventLoop) -> None`
- Objetivo: Registrar o loop para publicação thread-safe.
- Funcionamento: Guarda a referência em `self._loop`.
- Entradas: Loop assíncrono.
- Saidas: Nenhuma.
- Erros e efeitos: Nenhum.
- Dependencias: Nenhuma.
- Consumidores: FUN-PY-MON-004.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-EVENT-003 — EventBus.subscribe(user_id)
- Status: Ativa
- Arquivo: `backend/main.py`
- Simbolo: `EventBus.subscribe`
- Assinatura: `EventBus.subscribe(self, user_id: int) -> asyncio.Queue`
- Objetivo: Criar assinatura de eventos para um usuário.
- Funcionamento: Cria fila com capacidade 100 e registra no mapa sob lock.
- Entradas: ID do usuário.
- Saidas: Fila assíncrona.
- Erros e efeitos: Nenhum.
- Dependencias: FUN-PY-EVENT-001.
- Consumidores: FUN-PY-API-041.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-EVENT-004 — EventBus.unsubscribe(user_id, fila)
- Status: Ativa
- Arquivo: `backend/main.py`
- Simbolo: `EventBus.unsubscribe`
- Assinatura: `EventBus.unsubscribe(self, user_id: int, fila: asyncio.Queue) -> None`
- Objetivo: Remover assinatura encerrada.
- Funcionamento: Descarta a fila e remove a entrada do usuário quando vazia.
- Entradas: ID e fila.
- Saidas: Nenhuma.
- Erros e efeitos: Nenhum.
- Dependencias: FUN-PY-EVENT-001.
- Consumidores: FUN-PY-API-041.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-EVENT-005 — EventBus.publish(user_id, evento)
- Status: Ativa
- Arquivo: `backend/main.py`
- Simbolo: `EventBus.publish`
- Assinatura: `EventBus.publish(self, user_id: int, evento: dict) -> None`
- Objetivo: Publicar evento para as filas do usuário.
- Funcionamento: Copia as filas sob lock e enfileira via `call_soon_threadsafe` quando há loop; ignora filas cheias.
- Entradas: ID do usuário e evento.
- Saidas: Nenhuma.
- Erros e efeitos: Suprime `QueueFull` e `RuntimeError`.
- Dependencias: FUN-PY-EVENT-002.
- Consumidores: FUN-PY-MON-004, FUN-PY-API-042.
- Testes: Sem teste automatizado identificado.

### MON

#### FUN-PY-MON-001 — _ultimas_leituras_ana(codigos)
- Status: Ativa
- Arquivo: `backend/main.py`
- Simbolo: `_ultimas_leituras_ana`
- Assinatura: `_ultimas_leituras_ana(codigos: set[str]) -> dict[str, float]`
- Objetivo: Fazer pull dirigido das cotas atuais na ANA REST.
- Funcionamento: Cria `AnaClient`, consulta em lotes de 10 o endpoint `HidroinfoanaSerieTelemetricaAdotada/v2` para os últimos 30 dias e mantém a leitura mais recente por estação.
- Entradas: Conjunto de códigos.
- Saidas: `{codigo: cota_cm}`.
- Erros e efeitos: Retorna `{}` se credenciais/biblioteca falharem; erros por lote são impressos e ignorados.
- Dependencias: FUN-PY-COL-003, FUN-PY-COL-007.
- Consumidores: FUN-PY-MON-003.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-MON-002 — _verificar_rota(rota, leituras)
- Status: Ativa
- Arquivo: `backend/main.py`
- Simbolo: `_verificar_rota`
- Assinatura: `_verificar_rota(rota: dict, leituras: dict[str, float]) -> dict | None`
- Objetivo: Detectar variação de nível que justifique recalcular uma rota monitorada.
- Funcionamento: Usa a estação de referência; define baseline na primeira leitura; compara `|atual − baseline|` com `limiar_cm` (padrão 30); aplica cooldown de `cooldown_min` (padrão 30), ignorado para variação ≥ 100 cm; recalcula a rota e só registra alteração se os `fids` mudarem.
- Entradas: Linha de `rotas` e leituras externas.
- Saidas: Evento `{"evento": "rota_alterada", ...}` ou `None`.
- Erros e efeitos: Insere em `rota_alteracao` e atualiza `rotas`; pode levantar exceções de banco/grafo (tratadas pelo chamador).
- Dependencias: FUN-PY-API-003, FUN-PY-API-004, FUN-PY-API-006, FUN-PY-API-007, FUN-PY-ROUTE-006.
- Consumidores: FUN-PY-MON-003.
- Testes: Sem teste automatizado identificado.
- Observação: o baseline é atualizado mesmo quando não há mudança de traçado; o evento só é emitido quando os fids mudam.

#### FUN-PY-MON-003 — verificar_rotas_monitoradas()
- Status: Ativa
- Arquivo: `backend/main.py`
- Simbolo: `verificar_rotas_monitoradas`
- Assinatura: `verificar_rotas_monitoradas() -> list[tuple[int, dict]]`
- Objetivo: Verificar todas as rotas com `monitorar=TRUE`.
- Funcionamento: Carrega rotas monitoradas, busca leituras ANA para as estações de referência e isola falhas por rota.
- Entradas: Nenhuma.
- Saidas: Lista de `(usuario_id, evento)`.
- Erros e efeitos: Consulta banco e ANA; erros por rota são impressos.
- Dependencias: FUN-PY-MON-001, FUN-PY-MON-002.
- Consumidores: FUN-PY-MON-004, FUN-PY-API-042.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-MON-004 — monitor_loop()
- Status: Ativa
- Arquivo: `backend/main.py`
- Simbolo: `monitor_loop`
- Assinatura: `monitor_loop() -> None`
- Objetivo: Executar o vigia em ciclo contínuo.
- Funcionamento: Registra o loop no `EventBus`, executa `verificar_rotas_monitoradas` em thread separada a cada `HIDROWIZE_MONITOR_INTERVALO_MIN` (padrão 15 min) e publica eventos.
- Entradas: Nenhuma.
- Saidas: Nenhuma.
- Erros e efeitos: Loop infinito; exceções do ciclo são impressas e o loop continua.
- Dependencias: FUN-PY-MON-003, FUN-PY-EVENT-002, FUN-PY-EVENT-005.
- Consumidores: FUN-PY-API-010.
- Testes: Sem teste automatizado identificado.

### ROUTE

#### FUN-PY-ROUTE-001 — _lines(wkb)
- Status: Ativa
- Arquivo: `backend/routing_engine.py`
- Simbolo: `_lines`
- Assinatura: `_lines(wkb: bytes) -> list[list[list[float]]]`
- Objetivo: Decodificar WKB de `LineString`/`MultiLineString` vindo do PostGIS.
- Funcionalidade: Lê byte order, tipo e contagem; percorre pontos e linhas aninhadas.
- Entradas: WKB binário.
- Saidas: Lista de polilinhas de coordenadas.
- Erros e efeitos: Pode levantar `struct.error`/`IndexError` em WKB malformado; tipos não suportados retornam `[]`.
- Dependencias: `struct`.
- Consumidores: FUN-PY-ROUTE-004.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-ROUTE-002 — RiverGraph.__init__(config=None)
- Status: Ativa
- Arquivo: `backend/routing_engine.py`
- Simbolo: `RiverGraph.__init__`
- Assinatura: `RiverGraph.__init__(self, config: dict | None = None)`
- Objetivo: Inicializar o grafo em memória.
- Funcionamento: Guarda configuração (ou `pg_config()`), mapas `edges`, `adjacency`, `station_edges`, flag `_loaded` e lock.
- Entradas: Configuração opcional do PostgreSQL.
- Saidas: Nenhuma.
- Erros e efeitos: Não conecta ao banco na construção.
- Dependencias: FUN-PY-DATA-001.
- Consumidores: `backend/main.py` (singleton `river_graph`).
- Testes: Sem teste automatizado identificado.

#### FUN-PY-ROUTE-003 — RiverGraph.load()
- Status: Ativa
- Arquivo: `backend/routing_engine.py`
- Simbolo: `RiverGraph.load`
- Assinatura: `RiverGraph.load(self) -> None`
- Objetivo: Carregar arestas, adjacência e associação estação→trecho.
- Funcionamento: Carregamento idempotente e protegido por lock; lê `trechos_navegaveis` com distância via `ST_Length` e cria adjacência bidirecional; carrega `estacoes_trechos`.
- Entradas: Nenhuma.
- Saidas: Nenhuma.
- Erros e efeitos: Conecta ao PostGIS; ignora arestas sem distância positiva; `_loaded=True` ao final.
- Dependencias: FUN-PY-DATA-001.
- Consumidores: FUN-PY-ROUTE-005, FUN-PY-ROUTE-006.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-ROUTE-004 — RiverGraph.geometries(fids)
- Status: Ativa
- Arquivo: `backend/routing_engine.py`
- Simbolo: `RiverGraph.geometries`
- Assinatura: `RiverGraph.geometries(self, fids: list[int]) -> dict[int, list[list[list[float]]]]`
- Objetivo: Buscar geometrias somente dos trechos da rota.
- Funcionamento: Consulta `ST_AsBinary(geom)` para os `fids` e decodifica com `_lines`.
- Entradas: Lista de fids.
- Saidas: Mapa `fid → polilinhas`.
- Erros e efeitos: Retorna `{}` para lista vazia; abre conexão por chamada.
- Dependencias: FUN-PY-ROUTE-001, FUN-PY-DATA-001.
- Consumidores: FUN-PY-API-007, `calculate_route`.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-ROUTE-005 — RiverGraph.status()
- Status: Ativa
- Arquivo: `backend/routing_engine.py`
- Simbolo: `RiverGraph.status`
- Assinatura: `RiverGraph.status(self) -> dict`
- Objetivo: Reportar tamanho do grafo.
- Funcionamento: Garante `load()` e conta nós, arestas e portos associados.
- Entradas: Nenhuma.
- Saidas: `{nos, arestas, portos_associados}`.
- Erros e efeitos: Pode carregar todo o grafo.
- Dependencias: FUN-PY-ROUTE-003.
- Consumidores: FUN-PY-API-032.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-ROUTE-006 — RiverGraph.route(origin_code, destination_code, draft_m, margin_m)
- Status: Ativa
- Arquivo: `backend/routing_engine.py`
- Simbolo: `RiverGraph.route`
- Assinatura: `RiverGraph.route(self, origin_code: str, destination_code: str, draft_m: float, margin_m: float) -> list[Edge]`
- Objetivo: Calcular o menor caminho navegável por distância.
- Funcionamento: Executa Dijkstra bidirecional a partir dos nós do trecho de origem, podando arestas com `depth_m < draft_m + margin_m` (profundidade `None` é considerada transitável); reconstrói a sequência de fids.
- Entradas: Códigos de origem/destino, calado e margem.
- Saidas: Lista ordenada de `Edge`.
- Erros e efeitos: `ValueError` se o porto não tem trecho; `LookupError` se não há rota transitável.
- Dependencias: FUN-PY-ROUTE-003.
- Consumidores: FUN-PY-API-033, FUN-PY-MON-002.
- Testes: Sem teste automatizado identificado.
- Observação: o custo é distância (não tempo) e `depth_m` vem de `hig_drn_depth_m`, não de nível − cota de fundo.

### DATA

#### FUN-PY-DATA-001 — pg_config()
- Status: Ativa
- Arquivo: `backend/db.py`
- Simbolo: `pg_config`
- Assinatura: `pg_config() -> dict`
- Objetivo: Montar a configuração de conexão PostgreSQL a partir do `.env`.
- Funcionamento: Lê `HIDROWIZE_PG_HOST/PORT/DB/USER/PASSWORD` com padrões locais (`127.0.0.1:5432/ygape/ygape`).
- Entradas: Variáveis de ambiente.
- Saidas: Dicionário compatível com `psycopg2.connect`.
- Erros e efeitos: Senha padrão vazia; não valida conectividade.
- Dependencias: `os`, `dotenv`.
- Consumidores: `db.connection`, `RiverGraph.__init__`, `carregar_postgis`.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-DATA-002 — connection()
- Status: Ativa
- Arquivo: `backend/db.py`
- Simbolo: `connection`
- Assinatura: `connection()`
- Objetivo: Gerenciar conexão transacional com o PostgreSQL.
- Funcionamento: Context manager que abre conexão com `RealDictCursor`, faz commit no sucesso e rollback em exceção.
- Entradas: Nenhuma.
- Saidas: Conexão `psycopg2` no contexto.
- Erros e efeitos: Propaga exceções após rollback; sempre fecha a conexão.
- Dependencias: FUN-PY-DATA-001, `psycopg2.extras`.
- Consumidores: `main.py`, `criar_admin.py`, `carregar_postgis.py` (conexão própria) e scripts.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-DATA-003 — ensure_schema()
- Status: Ativa
- Arquivo: `backend/db.py`
- Simbolo: `ensure_schema`
- Assinatura: `ensure_schema() -> None`
- Objetivo: Criar/atualizar o schema da aplicação.
- Funcionamento: Executa o script `SCHEMA` com `CREATE TABLE IF NOT EXISTS`, `ALTER TABLE ADD COLUMN IF NOT EXISTS` e índices.
- Entradas: Nenhuma.
- Saidas: Nenhuma.
- Erros e efeitos: DDL transacional; propaga erros de banco.
- Dependencias: FUN-PY-DATA-002.
- Consumidores: FUN-PY-API-010, FUN-PY-ADMIN-001.
- Testes: Sem teste automatizado identificado.

### ETL

#### FUN-PY-ETL-001 — pg_type(tipo)
- Status: Ativa
- Arquivo: `backend/carregar_postgis.py`
- Simbolo: `pg_type`
- Assinatura: `pg_type(tipo: str) -> str`
- Objetivo: Mapear tipos declarados no SQLite para tipos PostgreSQL.
- Funcionamento: Normaliza o tipo e decide entre `bigint`, `double precision`, `bytea`, `numeric` e `text`.
- Entradas: Tipo SQLite.
- Saidas: Tipo PostgreSQL.
- Erros e efeitos: Tipo desconhecido vira `text`.
- Dependencias: Nenhuma.
- Consumidores: FUN-PY-ETL-004.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-ETL-002 — _quote(names)
- Status: Ativa
- Arquivo: `backend/carregar_postgis.py`
- Simbolo: `_quote`
- Assinatura: `_quote(names: list[str]) -> str`
- Objetivo: Aspar identificadores para SQL.
- Funcionamento: Junta nomes entre aspas duplas separados por vírgula.
- Entradas: Lista de nomes.
- Saidas: Lista SQL.
- Erros e efeitos: Não escapa aspas internas (nomes vêm do schema local).
- Dependencias: Nenhuma.
- Consumidores: FUN-PY-ETL-004, FUN-PY-ETL-005.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-ETL-003 — conectar()
- Status: Ativa
- Arquivo: `backend/carregar_postgis.py`
- Simbolo: `conectar`
- Assinatura: `conectar()`
- Objetivo: Abrir conexão direta com o PostgreSQL do ETL.
- Funcionamento: Lê as mesmas variáveis `HIDROWIZE_PG_*` de `FUN-PY-DATA-001`, mas sem `RealDictCursor`.
- Entradas: Nenhuma.
- Saidas: Conexão `psycopg2`.
- Erros e efeitos: Propaga erro de conexão.
- Dependencias: `psycopg2`, `dotenv`.
- Consumidores: FUN-PY-ETL-005.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-ETL-004 — carregar_tabela(sqlite_con, pg_cur, tabela, limite=None)
- Status: Ativa
- Arquivo: `backend/carregar_postgis.py`
- Simbolo: `carregar_tabela`
- Assinatura: `carregar_tabela(sqlite_con, pg_cur, tabela: str, limite: int | None = None) -> int`
- Objetivo: Espelhar uma tabela do SQLite no PostGIS.
- Funcionamento: Lê `PRAGMA table_info`, recria a tabela no PostgreSQL (`DROP` + `CREATE`), copia via `COPY` a partir de CSV temporário, converte `geom_wkb` em geometria SRID 4326, cria índices GIST e índices de apoio.
- Entradas: Conexões, nome da tabela e limite opcional.
- Saidas: Número de linhas copiadas.
- Erros e efeitos: `SystemExit` se a tabela não existir; recria a tabela de destino (operação destrutiva/idempotente).
- Dependencias: FUN-PY-ETL-001, FUN-PY-ETL-002.
- Consumidores: FUN-PY-ETL-005.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-ETL-005 — main()
- Status: Ativa
- Arquivo: `backend/carregar_postgis.py`
- Simbolo: `main`
- Assinatura: `main() -> int`
- Objetivo: Executar o ETL SQLite → PostGIS.
- Funcionamento: Seleciona tabelas principais (ou `--todas`), abre SQLite somente leitura e PostgreSQL, garante PostGIS e carrega cada tabela; ao final verifica contagens.
- Entradas: `--tabelas`, `--todas`, `--limite`, `--sqlite`.
- Saidas: Código 0 e relatório no console.
- Erros e efeitos: Recria tabelas no destino; transação única com commit no fim.
- Dependencias: FUN-PY-ETL-003, FUN-PY-ETL-004.
- Consumidores: Execução manual/CLI.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-ETL-006 — _gpb_wkb_off(blob)
- Status: Ativa
- Arquivo: `backend/gerar_sqlite.py`
- Simbolo: `_gpb_wkb_off`
- Assinatura: `_gpb_wkb_off(blob: bytes) -> int`
- Objetivo: Calcular o offset do WKB dentro do GeoPackage Binary.
- Funcionamento: Interpreta flags e envelope para pular cabeçalho e SRS.
- Entradas: Blob GPB.
- Saidas: Offset em bytes.
- Erros e efeitos: `KeyError`/`IndexError` em blob malformado.
- Dependencias: Constante `ENV_VALS`.
- Consumidores: FUN-PY-ETL-007, FUN-PY-ETL-009.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-ETL-007 — _gpb_wkb(blob)
- Status: Ativa
- Arquivo: `backend/gerar_sqlite.py`
- Simbolo: `_gpb_wkb`
- Assinatura: `_gpb_wkb(blob: bytes) -> bytes`
- Objetivo: Extrair o WKB puro de um blob GeoPackage.
- Funcionamento: Retorna `blob[offset:]` usando `_gpb_wkb_off`.
- Entradas: Blob GPB.
- Saidas: WKB.
- Erros e efeitos: Herda erros de offset.
- Dependencias: FUN-PY-ETL-006.
- Consumidores: FUN-PY-ETL-036.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-ETL-008 — _parse_wkb(data, off)
- Status: Ativa
- Arquivo: `backend/gerar_sqlite.py`
- Simbolo: `_parse_wkb`
- Assinatura: `_parse_wkb(data: bytes, off: int) -> tuple[list[list[tuple[float, float]]], int]`
- Objetivo: Decodificar LineString/MultiLineString WKB.
- Funcionamento: Lê byte order, tipo, contagens e pontos; retorna polilinhas e novo offset.
- Entradas: Bytes e offset inicial.
- Saidas: Polilinhas e offset final.
- Erros e efeitos: `struct.error` em dados inválidos; tipos não suportados devolvem lista vazia.
- Dependencias: `struct`.
- Consumidores: FUN-PY-ETL-009.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-ETL-009 — _gpb_centroid(blob)
- Status: Ativa
- Arquivo: `backend/gerar_sqlite.py`
- Simbolo: `_gpb_centroid`
- Assinatura: `_gpb_centroid(blob: bytes) -> tuple[float, float]`
- Objetivo: Calcular centroide simples (média dos vértices) da geometria.
- Funcionamento: Decodifica o WKB e calcula média de longitude/latitude.
- Entradas: Blob GPB.
- Saidas: `(lon, lat)`; `(0.0, 0.0)` sem pontos.
- Erros e efeitos: Herda erros de decodificação.
- Dependencias: FUN-PY-ETL-006, FUN-PY-ETL-008.
- Consumidores: FUN-PY-ETL-036.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-ETL-010 — _num(v)
- Status: Ativa
- Arquivo: `backend/gerar_sqlite.py`
- Simbolo: `_num`
- Assinatura: `_num(v: str) -> float | None`
- Objetivo: Converter texto CSV em float tolerante.
- Funcionamento: Remove espaços; vazio vira `None`; falha de conversão vira `None`.
- Entradas: Texto.
- Saidas: Float ou `None`.
- Erros e efeitos: Nenhum.
- Dependencias: Nenhuma.
- Consumidores: Importadores de `gerar_sqlite.py`.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-ETL-011 — _int(v)
- Status: Ativa
- Arquivo: `backend/gerar_sqlite.py`
- Simbolo: `_int`
- Assinatura: `_int(v: str) -> int | None`
- Objetivo: Converter texto em inteiro a partir de `_num`.
- Funcionamento: Trunca o float retornado por `_num`.
- Entradas: Texto.
- Saidas: Inteiro ou `None`.
- Erros e efeitos: Nenhum.
- Dependencias: FUN-PY-ETL-010.
- Consumidores: Importadores de `gerar_sqlite.py`.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-ETL-012 — _ler_csv(caminho, delimitador)
- Status: Ativa
- Arquivo: `backend/gerar_sqlite.py`
- Simbolo: `_ler_csv`
- Assinatura: `_ler_csv(caminho: str, delimitador: str) -> list[dict]`
- Objetivo: Ler um CSV inteiro como lista de dicionários.
- Funcionamento: Ajusta `csv.field_size_limit`, abre UTF-8-SIG e usa `DictReader`.
- Entradas: Caminho e delimitador.
- Saidas: Linhas.
- Erros e efeitos: Carrega tudo em memória; propaga `OSError`.
- Dependencias: `csv`.
- Consumidores: `gerar_sqlite.py` (não usado pelos importadores atuais, que preferem `_iter_csv`).
- Testes: Sem teste automatizado identificado.

#### FUN-PY-ETL-013 — _iter_csv(caminho, delimitador)
- Status: Ativa
- Arquivo: `backend/gerar_sqlite.py`
- Simbolo: `_iter_csv`
- Assinatura: `_iter_csv(caminho: str, delimitador: str)`
- Objetivo: Iterar CSV em streaming.
- Funcionamento: Generator sobre `csv.DictReader` com limite de campo ampliado.
- Entradas: Caminho e delimitador.
- Saidas: Iterador de dicionários.
- Erros e efeitos: Mantém o arquivo aberto durante a iteração; propaga `OSError`.
- Dependencias: `csv`.
- Consumidores: Importadores de `gerar_sqlite.py` e `coletar_hydroweb.py`.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-ETL-014 — _inserir_em_lotes(con, sql, linhas)
- Status: Ativa
- Arquivo: `backend/gerar_sqlite.py`
- Simbolo: `_inserir_em_lotes`
- Assinatura: `_inserir_em_lotes(con: sqlite3.Connection, sql: str, linhas) -> int`
- Objetivo: Executar inserções em lotes de 20 mil.
- Funcionamento: Acumula tuplas e chama `executemany` a cada `LOTE_INSERCAO`.
- Entradas: Conexão, SQL e iterável de tuplas.
- Saidas: Total inserido.
- Erros e efeitos: Não faz commit; propaga erros de SQLite.
- Dependencias: `LOTE_INSERCAO`.
- Consumidores: Importadores de `gerar_sqlite.py`.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-ETL-015 — _real(v)
- Status: Ativa
- Arquivo: `backend/gerar_sqlite.py`
- Simbolo: `_real`
- Assinatura: `_real(v)`
- Objetivo: Normalizar valores numéricos de satélite.
- Funcionamento: Devolve `None` para vazio, `float` para números e delega texto a `_num`.
- Entradas: Valor arbitrário.
- Saidas: `float` ou `None`.
- Erros e efeitos: Nenhum.
- Dependencias: FUN-PY-ETL-010.
- Consumidores: FUN-PY-ETL-017, FUN-PY-ETL-018.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-ETL-016 — criar_schema_satelite(con)
- Status: Ativa
- Arquivo: `backend/gerar_sqlite.py`
- Simbolo: `criar_schema_satelite`
- Assinatura: `criar_schema_satelite(con: sqlite3.Connection) -> None`
- Objetivo: Criar tabelas de satélite/batimetria.
- Funcionamento: Executa `SQL_SATELITE` e `SQL_BATIMETRIA` (tabelas `estacoes_virtuais`, `series_nivel_satelite`, `batimetria_sicflow`, `series_vazao_satelite` e índices).
- Entradas: Conexão SQLite.
- Saidas: Nenhuma.
- Erros e efeitos: DDL idempotente; propaga erros de SQLite.
- Dependencias: Constantes `SQL_SATELITE`, `SQL_BATIMETRIA`.
- Consumidores: FUN-PY-ETL-025/026/028/037/038, `coletar_hydroweb.py`.
- Testes: Sem teste automatizado identificado.
- Observação: o símbolo é definido duas vezes no arquivo (linhas ~184 e ~277); a segunda definição prevalece em tempo de execução.

#### FUN-PY-ETL-017 — upsert_estacoes_virtuais(con, linhas)
- Status: Ativa
- Arquivo: `backend/gerar_sqlite.py`
- Simbolo: `upsert_estacoes_virtuais`
- Assinatura: `upsert_estacoes_virtuais(con: sqlite3.Connection, linhas) -> int`
- Objetivo: Inserir/substituir estações virtuais.
- Funcionamento: Usa `INSERT OR REPLACE` em lotes.
- Entradas: Conexão e iterável de dicionários.
- Saidas: Total processado.
- Erros e efeitos: Propaga erro se faltar a chave `codigo`.
- Dependencias: FUN-PY-ETL-014, FUN-PY-ETL-015.
- Consumidores: FUN-PY-ETL-037, `coletar_hydroweb.py`.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-ETL-018 — upsert_series_nivel_satelite(con, linhas)
- Status: Ativa
- Arquivo: `backend/gerar_sqlite.py`
- Simbolo: `upsert_series_nivel_satelite`
- Assinatura: `upsert_series_nivel_satelite(con: sqlite3.Connection, linhas) -> int`
- Objetivo: Inserir observações de nível por satélite sem duplicar.
- Funcionamento: `INSERT OR IGNORE` em lotes (chave única `codigo,data`).
- Entradas: Conexão e iterável.
- Saidas: Total processado.
- Erros e efeitos: Ignora duplicatas; propaga erros estruturais.
- Dependencias: FUN-PY-ETL-014, FUN-PY-ETL-015.
- Consumidores: FUN-PY-ETL-038, `coletar_hydroweb.py`.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-ETL-019 — _reach_de_node(node_id)
- Status: Ativa
- Arquivo: `backend/gerar_sqlite.py`
- Simbolo: `_reach_de_node`
- Assinatura: `_reach_de_node(node_id: int) -> int`
- Objetivo: Derivar `reach_id` a partir do `node_id` no formato SWORD.
- Funcionamento: `(node_id // 10000) * 10 + (node_id % 10)`.
- Entradas: `node_id`.
- Saidas: `reach_id`.
- Erros e efeitos: Nenhum.
- Dependencias: Nenhuma.
- Consumidores: FUN-PY-ETL-025.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-ETL-020 — _batimetria_cols()
- Status: Ativa
- Arquivo: `backend/gerar_sqlite.py`
- Simbolo: `_batimetria_cols`
- Assinatura: `_batimetria_cols() -> str`
- Objetivo: Gerar DDL das colunas mensais de batimetria.
- Funcionamento: Cria `elev_01..12`, `larg_01..12` e `metodo_01..12`.
- Entradas: Nenhuma.
- Saidas: Fragmento SQL.
- Erros e efeitos: Nenhum.
- Dependencias: Nenhuma.
- Consumidores: FUN-PY-ETL-022.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-ETL-021 — _batimetria_valores()
- Status: Ativa
- Arquivo: `backend/gerar_sqlite.py`
- Simbolo: `_batimetria_valores`
- Assinatura: `_batimetria_valores() -> list[str]`
- Objetivo: Listar nomes das colunas mensais na ordem de inserção.
- Funcionamento: Gera a mesma sequência de `elev/larg/metodo`.
- Entradas: Nenhuma.
- Saidas: Lista de nomes.
- Erros e efeitos: Nenhum.
- Dependencias: Nenhuma.
- Consumidores: FUN-PY-ETL-022.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-ETL-022 — upsert_batimetria_sicflow(con, linhas)
- Status: Ativa
- Arquivo: `backend/gerar_sqlite.py`
- Simbolo: `upsert_batimetria_sicflow`
- Assinatura: `upsert_batimetria_sicflow(con: sqlite3.Connection, linhas: list[tuple]) -> int`
- Objetivo: Inserir/substituir nós de batimetria.
- Funcionamento: `INSERT OR REPLACE` em lote por `node_id`.
- Entradas: Conexão e tuplas.
- Saidas: Número de linhas.
- Erros e efeitos: Propaga erro de SQLite.
- Dependencias: FUN-PY-ETL-020, FUN-PY-ETL-021.
- Consumidores: FUN-PY-ETL-025.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-ETL-023 — upsert_series_vazao_satelite(con, linhas)
- Status: Ativa
- Arquivo: `backend/gerar_sqlite.py`
- Simbolo: `upsert_series_vazao_satelite`
- Assinatura: `upsert_series_vazao_satelite(con: sqlite3.Connection, linhas: list[tuple]) -> int`
- Objetivo: Inserir vazões SWOT sem duplicar.
- Funcionamento: `INSERT OR IGNORE` (chave `reach_id,data`).
- Entradas: Conexão e tuplas.
- Saidas: Número de linhas processadas.
- Erros e efeitos: Ignora duplicatas.
- Dependencias: Nenhuma.
- Consumidores: FUN-PY-ETL-026.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-ETL-024 — _nc_satelite(pasta_coleta, prefixo)
- Status: Ativa
- Arquivo: `backend/gerar_sqlite.py`
- Simbolo: `_nc_satelite`
- Assinatura: `_nc_satelite(pasta_coleta: str, prefixo: str) -> str | None`
- Objetivo: Localizar o primeiro arquivo NetCDF de uma pasta de coleta.
- Funcionamento: Percorre recursivamente e escolhe o primeiro `.nc` que comece com o prefixo.
- Entradas: Pasta e prefixo.
- Saidas: Caminho ou `None`.
- Erros e efeitos: Retorna `None` se a pasta não existe.
- Dependencias: `os`.
- Consumidores: FUN-PY-ETL-025, FUN-PY-ETL-026.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-ETL-025 — importar_batimetria_sicflow(con)
- Status: Ativa
- Arquivo: `backend/gerar_sqlite.py`
- Simbolo: `importar_batimetria_sicflow`
- Assinatura: `importar_batimetria_sicflow(con: sqlite3.Connection) -> int`
- Objetivo: Importar batimetria SWOT L4 SICFLOW do NetCDF para o SQLite.
- Funcionamento: Lê `node_id`, coordenadas, elevação, largura, método e `h_interface` em blocos de 200 mil; filtra a bbox amazônica, calcula cota de fundo/banco e largura máxima e insere em lotes.
- Entradas: Conexão SQLite.
- Saidas: Número de nós importados (0 se `h5py` ausente ou arquivo inexistente).
- Erros e efeitos: Carrega `h5py`/`numpy` sob demanda; não faz commit.
- Dependencias: FUN-PY-ETL-019, FUN-PY-ETL-022, FUN-PY-ETL-024.
- Consumidores: FUN-PY-ETL-041, `coletar_hydroweb.py`.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-ETL-026 — importar_series_vazao_satelite(con)
- Status: Ativa
- Arquivo: `backend/gerar_sqlite.py`
- Simbolo: `importar_series_vazao_satelite`
- Assinatura: `importar_series_vazao_satelite(con: sqlite3.Connection) -> int`
- Objetivo: Importar séries de vazão SWOT (SOS Discharge).
- Funcionamento: Lê `reaches`/`consensus`, filtra bbox, converte tempo (epoch 2000) e insere em lotes.
- Entradas: Conexão SQLite.
- Saidas: Total de observações (0 sem arquivo/`h5py`).
- Erros e efeitos: Não faz commit.
- Dependencias: FUN-PY-ETL-023, FUN-PY-ETL-024.
- Consumidores: FUN-PY-ETL-041, `coletar_hydroweb.py`.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-ETL-027 — criar_schema_diarias(con)
- Status: Ativa
- Arquivo: `backend/gerar_sqlite.py`
- Simbolo: `criar_schema_diarias`
- Assinatura: `criar_schema_diarias(con: sqlite3.Connection) -> None`
- Objetivo: Criar `cotas_diarias` e `nivel_semanal`.
- Funcionamento: Executa `SQL_DIARIAS` com chaves primárias e índices.
- Entradas: Conexão.
- Saidas: Nenhuma.
- Erros e efeitos: DDL idempotente.
- Dependencias: Constante `SQL_DIARIAS`.
- Consumidores: FUN-PY-ETL-028, FUN-PY-ETL-041.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-ETL-028 — criar_schema(con)
- Status: Ativa
- Arquivo: `backend/gerar_sqlite.py`
- Simbolo: `criar_schema`
- Assinatura: `criar_schema(con: sqlite3.Connection) -> None`
- Objetivo: Criar todo o schema do `hidrowize.db`.
- Funcionamento: Executa DDL das tabelas principais, de satélite e diárias, com índices.
- Entradas: Conexão.
- Saidas: Nenhuma.
- Erros e efeitos: `PRAGMA journal_mode=OFF` e `synchronous=OFF` (desempenho, sem durabilidade durante a geração).
- Dependencias: FUN-PY-ETL-016, FUN-PY-ETL-027.
- Consumidores: FUN-PY-ETL-041.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-ETL-029 — importar_estacoes(con)
- Status: Ativa
- Arquivo: `backend/gerar_sqlite.py`
- Simbolo: `importar_estacoes`
- Assinatura: `importar_estacoes(con: sqlite3.Connection) -> int`
- Objetivo: Importar estações enriquecidas da ANA.
- Funcionamento: Lê `planilhas/estacoes_am_enriquecidas.csv` (`;`) e faz `INSERT OR REPLACE` em lotes.
- Entradas: Conexão.
- Saidas: Linhas importadas.
- Erros e efeitos: `FileNotFoundError` se o CSV não existir.
- Dependencias: FUN-PY-ETL-010, FUN-PY-ETL-011, FUN-PY-ETL-013, FUN-PY-ETL-014.
- Consumidores: FUN-PY-ETL-041.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-ETL-030 — importar_rios(con)
- Status: Ativa
- Arquivo: `backend/gerar_sqlite.py`
- Simbolo: `importar_rios`
- Assinatura: `importar_rios(con: sqlite3.Connection) -> int`
- Objetivo: Importar o catálogo de rios da ANA.
- Funcionamento: Lê `planilhas/rios_ana.csv` (`,`).
- Entradas: Conexão.
- Saidas: Linhas importadas.
- Erros e efeitos: `FileNotFoundError` se ausente.
- Dependencias: FUN-PY-ETL-010, FUN-PY-ETL-011, FUN-PY-ETL-013.
- Consumidores: FUN-PY-ETL-041.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-ETL-031 — importar_telemetria(con)
- Status: Ativa
- Arquivo: `backend/gerar_sqlite.py`
- Simbolo: `importar_telemetria`
- Assinatura: `importar_telemetria(con: sqlite3.Connection) -> int`
- Objetivo: Importar leituras de telemetria acumuladas.
- Funcionamento: Lê `planilhas/telemetria_cotas_am.csv` (`;`) e insere (sem chave de deduplicação).
- Entradas: Conexão.
- Saidas: Linhas importadas.
- Erros e efeitos: Pode duplicar leituras em execuções sucessivas; `FileNotFoundError` se ausente.
- Dependencias: FUN-PY-ETL-010, FUN-PY-ETL-013, FUN-PY-ETL-014.
- Consumidores: FUN-PY-ETL-041.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-ETL-032 — importar_cotas_historicas(con)
- Status: Ativa
- Arquivo: `backend/gerar_sqlite.py`
- Simbolo: `importar_cotas_historicas`
- Assinatura: `importar_cotas_historicas(con: sqlite3.Connection) -> int`
- Objetivo: Importar mín/máx/média históricos por estação.
- Funcionamento: Lê `planilhas/cotas_historicas_am.csv` e faz `INSERT OR REPLACE`.
- Entradas: Conexão.
- Saidas: Linhas importadas.
- Erros e efeitos: `FileNotFoundError` se ausente.
- Dependencias: FUN-PY-ETL-010, FUN-PY-ETL-011, FUN-PY-ETL-013.
- Consumidores: FUN-PY-ETL-041.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-ETL-033 — importar_navegabilidade(con)
- Status: Ativa
- Arquivo: `backend/gerar_sqlite.py`
- Simbolo: `importar_navegabilidade`
- Assinatura: `importar_navegabilidade(con: sqlite3.Connection) -> int`
- Objetivo: Importar a classificação de navegabilidade por estação.
- Funcionamento: Lê `planilhas/estacoes_am_navegabilidade.csv` e faz `INSERT OR REPLACE`.
- Entradas: Conexão.
- Saidas: Linhas importadas.
- Erros e efeitos: `FileNotFoundError` se ausente.
- Dependencias: FUN-PY-ETL-010, FUN-PY-ETL-011, FUN-PY-ETL-013.
- Consumidores: FUN-PY-ETL-041.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-ETL-034 — importar_decretos(con)
- Status: Ativa
- Arquivo: `backend/gerar_sqlite.py`
- Simbolo: `importar_decretos`
- Assinatura: `importar_decretos(con: sqlite3.Connection) -> int`
- Objetivo: Importar decretos do Legisla.AM.
- Funcionamento: Retorna 0 se o CSV não existe; caso contrário insere os registros.
- Entradas: Conexão.
- Saidas: Linhas importadas.
- Erros e efeitos: Inserção sem chave única (pode duplicar).
- Dependencias: FUN-PY-ETL-013, FUN-PY-ETL-014.
- Consumidores: FUN-PY-ETL-041.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-ETL-035 — importar_estacoes_trechos(con)
- Status: Ativa
- Arquivo: `backend/gerar_sqlite.py`
- Simbolo: `importar_estacoes_trechos`
- Assinatura: `importar_estacoes_trechos(con: sqlite3.Connection) -> int`
- Objetivo: Importar o cruzamento estação × trecho navegável.
- Funcionamento: Lê `planilhas/estacoes_am_x_hidrovias_navegaveis.csv` e insere em lotes.
- Entradas: Conexão.
- Saidas: Linhas importadas.
- Erros e efeitos: Pode duplicar em rebuild sem limpeza; `FileNotFoundError` se ausente.
- Dependencias: FUN-PY-ETL-010, FUN-PY-ETL-011, FUN-PY-ETL-013.
- Consumidores: FUN-PY-ETL-041.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-ETL-036 — importar_trechos(con)
- Status: Ativa
- Arquivo: `backend/gerar_sqlite.py`
- Simbolo: `importar_trechos`
- Assinatura: `importar_trechos(con: sqlite3.Connection) -> int`
- Objetivo: Importar trechos navegáveis do GeoPackage.
- Funcionamento: Lê `data/hidrovias_navegaveis_bhae.gpkg` (tabela `hidrovias_navegaveis_bhae`), converte GPB em WKB, calcula centroide e insere cada trecho.
- Entradas: Conexão.
- Saidas: Número de trechos importados.
- Erros e efeitos: Pula geometrias nulas; imprime progresso a cada 20 mil.
- Dependencias: FUN-PY-ETL-007, FUN-PY-ETL-009.
- Consumidores: FUN-PY-ETL-041.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-ETL-037 — importar_estacoes_virtuais(con)
- Status: Ativa
- Arquivo: `backend/gerar_sqlite.py`
- Simbolo: `importar_estacoes_virtuais`
- Assinatura: `importar_estacoes_virtuais(con: sqlite3.Connection) -> int`
- Objetivo: Importar estações virtuais do CSV de satélite.
- Funcionamento: Retorna 0 se ausente; define `fonte=HYDROWEB_RIVERS_OPE` e delega ao upsert.
- Entradas: Conexão.
- Saidas: Linhas importadas.
- Erros e efeitos: Nenhum commit.
- Dependencias: FUN-PY-ETL-013, FUN-PY-ETL-017.
- Consumidores: FUN-PY-ETL-041.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-ETL-038 — importar_series_nivel_satelite(con)
- Status: Ativa
- Arquivo: `backend/gerar_sqlite.py`
- Simbolo: `importar_series_nivel_satelite`
- Assinatura: `importar_series_nivel_satelite(con: sqlite3.Connection) -> int`
- Objetivo: Importar séries de nível de satélite do CSV.
- Funcionamento: Retorna 0 se ausente; define fonte e delega ao upsert.
- Entradas: Conexão.
- Saidas: Linhas processadas.
- Erros e efeitos: Ignora duplicatas.
- Dependencias: FUN-PY-ETL-013, FUN-PY-ETL-018.
- Consumidores: FUN-PY-ETL-041.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-ETL-039 — importar_cotas_diarias(con)
- Status: Ativa
- Arquivo: `backend/gerar_sqlite.py`
- Simbolo: `importar_cotas_diarias`
- Assinatura: `importar_cotas_diarias(con: sqlite3.Connection) -> int`
- Objetivo: Importar a série diária de cotas.
- Funcionamento: Retorna 0 se o CSV não existe; faz `INSERT OR REPLACE` por `(codigo_estacao,data)`.
- Entradas: Conexão.
- Saidas: Linhas importadas.
- Erros e efeitos: Nenhum commit.
- Dependencias: FUN-PY-ETL-010, FUN-PY-ETL-013, FUN-PY-ETL-014.
- Consumidores: FUN-PY-ETL-041.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-ETL-040 — gerar_nivel_semanal(con)
- Status: Ativa
- Arquivo: `backend/gerar_sqlite.py`
- Simbolo: `gerar_nivel_semanal`
- Assinatura: `gerar_nivel_semanal(con: sqlite3.Connection) -> int`
- Objetivo: Agregar cotas diárias em semanas ISO.
- Funcionamento: Agrupa por `(estacao, segunda-feira)`, calcula média/mín/máx, conta dias e classifica a fonte (`ANA_CONSISTIDO`, `ANA_BRUTO`, `ANA_MISTO`).
- Entradas: Conexão.
- Saidas: Linhas de `nivel_semanal` gravadas.
- Erros e efeitos: Ignora datas inválidas; `INSERT OR REPLACE`.
- Dependencias: `datetime`.
- Consumidores: FUN-PY-ETL-041.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-ETL-041 — main()
- Status: Ativa
- Arquivo: `backend/gerar_sqlite.py`
- Simbolo: `main`
- Assinatura: `main() -> None`
- Objetivo: Reconstruir o SQLite consolidado.
- Funcionamento: Remove o arquivo de saída (quando rebuild completo), cria schema, importa CSVs, satélite, trechos, séries diárias e imprime contagens.
- Entradas: `--out`, `--somente-diarias`.
- Saidas: Arquivo SQLite e relatório.
- Erros e efeitos: **Remove o banco de saída** no modo completo; operação destrutiva sobre `data/hidrowize.db`.
- Dependencias: FUN-PY-ETL-028/029/030/031/032/033/034/035/036/037/038/039/040.
- Consumidores: Execução manual/CLI; pipeline de coleta.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-ETL-042 — _extensao_km(blob)
- Status: Ativa
- Arquivo: `backend/gerar_dashboard_dados.py`
- Simbolo: `_extensao_km`
- Assinatura: `_extensao_km(blob: bytes) -> float`
- Objetivo: Estimar a extensão de uma polilinha WKB em km.
- Funcionamento: Percorre segmentos e soma distâncias aproximadas por conversão graus→metros.
- Entradas: WKB.
- Saidas: Extensão em km.
- Erros e efeitos: Aproximação plana; pode falhar em WKB inválido.
- Dependencias: FUN-PY-ETL-043.
- Consumidores: FUN-PY-ETL-055.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-ETL-043 — _wkb_linestrings(data)
- Status: Ativa
- Arquivo: `backend/gerar_dashboard_dados.py`
- Simbolo: `_wkb_linestrings`
- Assinatura: `_wkb_linestrings(data: bytes) -> list[list[tuple[float, float]]]`
- Objetivo: Decodificar LineString/MultiLineString WKB.
- Funcionamento: Interpreta tipos 2/3 e 5/7, incluindo dimensão Z.
- Entradas: WKB.
- Saidas: Polilinhas.
- Erros e efeitos: `struct.error`/`IndexError` em dados inválidos.
- Dependencias: FUN-PY-ETL-044.
- Consumidores: FUN-PY-ETL-042.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-ETL-044 — _wkb_line(data, end, off, n, gtype)
- Status: Ativa
- Arquivo: `backend/gerar_dashboard_dados.py`
- Simbolo: `_wkb_line`
- Assinatura: `_wkb_line(data: bytes, end: str, off: int, n: int, gtype: int) -> list[tuple[float, float]]`
- Objetivo: Ler `n` pontos de uma linha WKB, com ou sem Z.
- Funcionamento: Calcula o tamanho do ponto (16 ou 24 bytes) e desempacota pares `double`.
- Entradas: Bytes, endianness, offset, contagem e tipo.
- Saidas: Pontos `(x, y)`.
- Erros e efeitos: `struct.error` em buffer curto.
- Dependencias: `struct`.
- Consumidores: FUN-PY-ETL-043.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-ETL-045 — _num(v)
- Status: Ativa
- Arquivo: `backend/gerar_dashboard_dados.py`
- Simbolo: `_num`
- Assinatura: `_num(v)`
- Objetivo: Converter valor em float tolerante.
- Funcionamento: `None` permanece; falhas retornam `None`.
- Entradas: Valor arbitrário.
- Saidas: `float` ou `None`.
- Erros e efeitos: Nenhum.
- Dependencias: Nenhuma.
- Consumidores: FUN-PY-ETL-055.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-ETL-046 — _arred(v, d=1)
- Status: Ativa
- Arquivo: `backend/gerar_dashboard_dados.py`
- Simbolo: `_arred`
- Assinatura: `_arred(v, d=1)`
- Objetivo: Arredondar valores opcionais.
- Funcionamento: Retorna `None` para nulo; caso contrário `round(float(v), d)`.
- Entradas: Valor e casas decimais.
- Saidas: `float` ou `None`.
- Erros e efeitos: Pode levantar `TypeError`/`ValueError` para valores não numéricos.
- Dependencias: Nenhuma.
- Consumidores: FUN-PY-ETL-054/055/057.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-ETL-047 — _cota_m(v)
- Status: Ativa
- Arquivo: `backend/gerar_dashboard_dados.py`
- Simbolo: `_cota_m`
- Assinatura: `_cota_m(v)`
- Objetivo: Converter cota de centímetros para metros.
- Funcionamento: Divide por 100 e arredonda para 2 casas; nulos permanecem nulos.
- Entradas: Valor em cm.
- Saidas: Metros ou `None`.
- Erros e efeitos: Captura `TypeError`/`ValueError`.
- Dependencias: Nenhuma.
- Consumidores: FUN-PY-ETL-054.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-ETL-048 — _serie_data(v)
- Status: Ativa
- Arquivo: `backend/gerar_dashboard_dados.py`
- Simbolo: `_serie_data`
- Assinatura: `_serie_data(v)`
- Objetivo: Extrair apenas a data de um timestamp.
- Funcionamento: Divide por `T`/espaço e retorna a primeira parte; vazio vira `None`.
- Entradas: Texto.
- Saidas: `YYYY-MM-DD` ou `None`.
- Erros e efeitos: Retorna `None` em entrada vazia.
- Dependencias: Nenhuma.
- Consumidores: FUN-PY-ETL-053/054/057.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-ETL-049 — _data_hora(v)
- Status: Ativa
- Arquivo: `backend/gerar_dashboard_dados.py`
- Simbolo: `_data_hora`
- Assinatura: `_data_hora(v)`
- Objetivo: Normalizar timestamp para exibição.
- Funcionamento: Remove sufixo `.0` e troca `T` por espaço.
- Entradas: Texto.
- Saidas: Texto normalizado ou `None`.
- Erros e efeitos: Nenhum.
- Dependencias: Nenhuma.
- Consumidores: FUN-PY-ETL-053/054.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-ETL-050 — resumo(con)
- Status: Ativa
- Arquivo: `backend/gerar_dashboard_dados.py`
- Simbolo: `resumo`
- Assinatura: `resumo(con: sqlite3.Connection) -> dict`
- Objetivo: Contar linhas das tabelas exibidas no dashboard.
- Funcionamento: Executa `COUNT(*)` para 12 tabelas.
- Entradas: Conexão.
- Saidas: `{tabela: total}`.
- Erros e efeitos: `sqlite3.OperationalError` se alguma tabela não existir.
- Dependencias: Nenhuma.
- Consumidores: FUN-PY-ETL-053/059.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-ETL-051 — navegabilidade(con)
- Status: Ativa
- Arquivo: `backend/gerar_dashboard_dados.py`
- Simbolo: `navegabilidade`
- Assinatura: `navegabilidade(con: sqlite3.Connection) -> dict`
- Objetivo: Agregar estações por status de navegabilidade.
- Funcionamento: `GROUP BY status_navegabilidade`; rótulo `SEM DADOS` para nulo.
- Entradas: Conexão.
- Saidas: `{status: quantidade}`.
- Erros e efeitos: Nenhum.
- Dependencias: Nenhuma.
- Consumidores: FUN-PY-ETL-059.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-ETL-052 — dominio(con)
- Status: Ativa
- Arquivo: `backend/gerar_dashboard_dados.py`
- Simbolo: `dominio`
- Assinatura: `dominio(con: sqlite3.Connection) -> dict`
- Objetivo: Agregar trechos por domínio.
- Funcionamento: `GROUP BY dominio`; nulo vira `Sem classificação`.
- Entradas: Conexão.
- Saidas: `{dominio: quantidade}`.
- Erros e efeitos: Nenhum.
- Dependencias: Nenhuma.
- Consumidores: FUN-PY-ETL-059.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-ETL-053 — telemetria_stats(con)
- Status: Ativa
- Arquivo: `backend/gerar_dashboard_dados.py`
- Simbolo: `telemetria_stats`
- Assinatura: `telemetria_stats(con: sqlite3.Connection) -> dict`
- Objetivo: Calcular KPIs e recência das leituras de telemetria.
- Funcionamento: Conta leituras com cota/vazão/chuva, obtém período e classifica a última leitura por estação em ≤24 h, ≤7 d, ≤30 d e >30 d.
- Entradas: Conexão.
- Saidas: Totais, período e `recencia`.
- Erros e efeitos: Datas inválidas contam como >30 d.
- Dependencias: FUN-PY-ETL-048, FUN-PY-ETL-049, FUN-PY-ETL-050.
- Consumidores: FUN-PY-ETL-059.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-ETL-054 — estacoes(con)
- Status: Ativa
- Arquivo: `backend/gerar_dashboard_dados.py`
- Simbolo: `estacoes`
- Assinatura: `estacoes(con: sqlite3.Connection) -> list[dict]`
- Objetivo: Montar a lista de estações do dashboard.
- Funcionamento: Junta cadastro, última telemetria, navegabilidade, cotas históricas e associação a trecho; converte unidades.
- Entradas: Conexão.
- Saidas: Lista de dicionários.
- Erros e efeitos: Consultas por tabela; valores ausentes viram `None`.
- Dependencias: FUN-PY-ETL-046, FUN-PY-ETL-047, FUN-PY-ETL-048, FUN-PY-ETL-049.
- Consumidores: FUN-PY-ETL-059.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-ETL-055 — trechos_stats(con)
- Status: Ativa
- Arquivo: `backend/gerar_dashboard_dados.py`
- Simbolo: `trechos_stats`
- Assinatura: `trechos_stats(con: sqlite3.Connection) -> dict`
- Objetivo: Agregar extensão e profundidade dos trechos.
- Funcionamento: Soma extensões, calcula profundidade média e distribui trechos/km em faixas; ignora latitude fora de −8..5 na soma com profundidade.
- Entradas: Conexão.
- Saidas: Totais e faixas.
- Erros e efeitos: Depende de `geom_wkb` válido.
- Dependencias: FUN-PY-ETL-042.
- Consumidores: FUN-PY-ETL-059.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-ETL-056 — rios_top(con, limite=15)
- Status: Ativa
- Arquivo: `backend/gerar_dashboard_dados.py`
- Simbolo: `rios_top`
- Assinatura: `rios_top(con: sqlite3.Connection, limite: int = 15) -> list[dict]`
- Objetivo: Listar os rios com mais trechos e profundidade média.
- Funcionamento: `GROUP BY rio ORDER BY COUNT(*) DESC LIMIT ?`.
- Entradas: Conexão e limite.
- Saidas: Lista `{rio, trechos, prof_media}`.
- Erros e efeitos: Nenhum.
- Dependencias: FUN-PY-ETL-046.
- Consumidores: FUN-PY-ETL-059.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-ETL-057 — decretos(con, limite=60)
- Status: Ativa
- Arquivo: `backend/gerar_dashboard_dados.py`
- Simbolo: `decretos`
- Assinatura: `decretos(con: sqlite3.Connection, limite: int = 60) -> list[dict]`
- Objetivo: Listar decretos recentes para o dashboard.
- Funcionamento: Ordena por data decrescente e limita; campos ausentes viram string vazia.
- Entradas: Conexão e limite.
- Saidas: Lista de decretos.
- Erros e efeitos: Nenhum.
- Dependencias: FUN-PY-ETL-048.
- Consumidores: FUN-PY-ETL-059.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-ETL-058 — series_stats(con)
- Status: Ativa
- Arquivo: `backend/gerar_dashboard_dados.py`
- Simbolo: `series_stats`
- Assinatura: `series_stats(con: sqlite3.Connection) -> dict`
- Objetivo: Resumir períodos das séries de satélite e reaches da batimetria.
- Funcionamento: `MIN/MAX(data)` para nível e vazão e `COUNT(DISTINCT reach_id)`.
- Entradas: Conexão.
- Saidas: `{nivel, vazao, batimetria_reaches}`.
- Erros e efeitos: Nenhum.
- Dependencias: FUN-PY-ETL-048.
- Consumidores: FUN-PY-ETL-059.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-ETL-059 — main()
- Status: Ativa
- Arquivo: `backend/gerar_dashboard_dados.py`
- Simbolo: `main`
- Assinatura: `main() -> None`
- Objetivo: Exportar `window.DASHBOARD` para o dashboard estático.
- Funcionamento: Agrega todos os blocos e grava `frontend/dashboard/dashboard.js`.
- Entradas: `--out`.
- Saidas: Arquivo JavaScript e resumo no console.
- Erros e efeitos: Sobrescreve o arquivo de saída.
- Dependencias: FUN-PY-ETL-050/051/052/053/054/055/056/057/058.
- Consumidores: Execução manual/CLI; dashboard estático.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-ETL-060 — normalizar_nome(nome)
- Status: Ativa
- Arquivo: `backend/gerar_historico_geo.py`
- Simbolo: `normalizar_nome`
- Assinatura: `normalizar_nome(nome: str | None) -> str`
- Objetivo: Normalizar nomes de rios para comparação.
- Funcionamento: Remove acentos (NFKD), descarta diacríticos e converte para maiúsculas.
- Entradas: Nome.
- Saidas: Nome normalizado ou `""`.
- Erros e efeitos: Nenhum.
- Dependencias: `unicodedata`.
- Consumidores: FUN-PY-ETL-061.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-ETL-061 — calado_de_rio(nome_rio, largura_m, longitude=None)
- Status: Ativa
- Arquivo: `backend/gerar_historico_geo.py`
- Simbolo: `calado_de_rio`
- Assinatura: `calado_de_rio(nome_rio: str | None, largura_m: float | None, longitude: float | None = None) -> float`
- Objetivo: Aplicar o calado de referência por tramo (RN029) no histórico geográfico.
- Funcionamento: Negro=0; Madeira=13; Solimões=6; Amazonas=10 a jusante de −60,5 e 6 entre −70,5 e −60,5; demais usam proxy limitado a 2–6 m pela largura; padrão 6.
- Entradas: Rio, largura e longitude.
- Saidas: Calado em metros.
- Erros e efeitos: Nenhum.
- Dependencias: FUN-PY-ETL-060.
- Consumidores: FUN-PY-ETL-068.
- Testes: Sem teste automatizado identificado.
- Observação: a mesma regra **não** é aplicada pelo motor de rota (`routing_engine.route`).

#### FUN-PY-ETL-062 — carregar_estacoes()
- Status: Ativa
- Arquivo: `backend/gerar_historico_geo.py`
- Simbolo: `carregar_estacoes`
- Assinatura: `carregar_estacoes() -> list[dict]`
- Objetivo: Ler as estações virtuais do CSV.
- Funcionamento: Lê `data/satelite/estacoes_virtuais.csv` e converte lat/lon em float.
- Entradas: Nenhuma.
- Saidas: Lista de estações.
- Erros e efeitos: `FileNotFoundError`/`ValueError` se o CSV estiver ausente ou inválido.
- Dependencias: `csv`.
- Consumidores: FUN-PY-ETL-070.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-ETL-063 — carregar_trechos()
- Status: Ativa
- Arquivo: `backend/gerar_historico_geo.py`
- Simbolo: `carregar_trechos`
- Assinatura: `carregar_trechos() -> dict`
- Objetivo: Carregar trechos, geometria e cota de fundo do SQLite.
- Funcionamento: Consulta `trechos_navegaveis` com `LEFT JOIN cota_fundo_trecho` e converte WKB com Shapely.
- Entradas: Nenhuma.
- Saidas: `{fids, rios, larguras, geoms, cota_fundo}`.
- Erros e efeitos: `sqlite3.Error`/`FileNotFoundError`; depende de Shapely.
- Dependencias: `shapely`, `sqlite3`.
- Consumidores: FUN-PY-ETL-064, FUN-PY-ETL-070.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-ETL-064 — associar_trecho(estacoes, raio_m, trechos)
- Status: Ativa
- Arquivo: `backend/gerar_historico_geo.py`
- Simbolo: `associar_trecho`
- Assinatura: `associar_trecho(estacoes: list[dict], raio_m: float, trechos: dict) -> dict[str, dict]`
- Objetivo: Associar cada estação virtual ao trecho navegável mais próximo.
- Funcionamento: Usa `STRtree` e consulta `dwithin`, escolhendo o trecho de menor distância; guarda largura, cota de fundo e rio BHAE.
- Entradas: Estações, raio e trechos.
- Saidas: Mapa `codigo → associação | None`.
- Erros e efeitos: Projeta o raio em graus (`m/111320`).
- Dependencias: FUN-PY-ETL-063.
- Consumidores: FUN-PY-ETL-070.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-ETL-065 — classificar_navegabilidade(prof, calado)
- Status: Ativa
- Arquivo: `backend/gerar_historico_geo.py`
- Simbolo: `classificar_navegabilidade`
- Assinatura: `classificar_navegabilidade(prof: float, calado: float) -> str`
- Objetivo: Classificar a navegabilidade de um trecho no histórico.
- Funcionamento: `CRITICO` se `prof < calado`; `RESTRITO` se `prof < calado + 0.5`; caso contrário `NAVEGAVEL`.
- Entradas: Profundidade e calado.
- Saidas: Status textual.
- Erros e efeitos: Nenhum.
- Dependencias: Constante `MARGEM_M`.
- Consumidores: FUN-PY-ETL-068.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-ETL-066 — ler_series()
- Status: Ativa
- Arquivo: `backend/gerar_historico_geo.py`
- Simbolo: `ler_series`
- Assinatura: `ler_series() -> tuple[dict[str, list[float]], dict[str, dict[str, float]]]`
- Objetivo: Ler níveis e calcular médias mensais por estação.
- Funcionamento: Lê o CSV de séries, acumula níveis e agrupa por `AAAA-MM`.
- Entradas: Nenhuma.
- Saidas: Níveis por estação e médias mensais.
- Erros e efeitos: `FileNotFoundError` se o CSV ausente; ignora níveis vazios.
- Dependencias: `numpy`, `csv`.
- Consumidores: FUN-PY-ETL-070.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-ETL-067 — classificar(nivel, p25, p75)
- Status: Ativa
- Arquivo: `backend/gerar_historico_geo.py`
- Simbolo: `classificar`
- Assinatura: `classificar(nivel: float, p25: float, p75: float) -> str`
- Objetivo: Classificar o regime mensal em VAZANTE/NORMAL/CHEIA.
- Funcionamento: Compara com os percentis 25 e 75 da série.
- Entradas: Nível e percentis.
- Saidas: Classe textual.
- Erros e efeitos: Nenhum.
- Dependencias: Nenhuma.
- Consumidores: FUN-PY-ETL-068.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-ETL-068 — gerar(features_out, estacoes, trechos_assoc, niveis, medias)
- Status: Ativa
- Arquivo: `backend/gerar_historico_geo.py`
- Simbolo: `gerar`
- Assinatura: `gerar(features_out, estacoes, trechos_assoc, niveis, medias) -> list[str]`
- Objetivo: Montar features temporais de nível e navegabilidade.
- Funcionamento: Filtra estações com trecho largo (≥300 m), calcula p25/p75, classifica cada mês e calcula profundidade/status quando há cota de fundo.
- Entradas: Lista de saída, estações, associações, níveis e médias.
- Saidas: Lista de meses.
- Erros e efeitos: Muta `features_out`; usa `numpy.percentile`.
- Dependencias: FUN-PY-ETL-061, FUN-PY-ETL-065, FUN-PY-ETL-067.
- Consumidores: FUN-PY-ETL-070.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-ETL-069 — salvar(features, meses, saida)
- Status: Ativa
- Arquivo: `backend/gerar_historico_geo.py`
- Simbolo: `salvar`
- Assinatura: `salvar(features, meses, saida: Path) -> None`
- Objetivo: Gravar o histórico como `window.HISTORICO_NIVEL`.
- Funcionamento: Serializa JSON compacto e escreve o arquivo JS, criando diretórios.
- Entradas: Features, meses e caminho.
- Saidas: Nenhuma.
- Erros e efeitos: Sobrescreve o arquivo de saída.
- Dependencias: `json`, `pathlib`.
- Consumidores: FUN-PY-ETL-070.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-ETL-070 — main()
- Status: Ativa
- Arquivo: `backend/gerar_historico_geo.py`
- Simbolo: `main`
- Assinatura: `main() -> None`
- Objetivo: Gerar o GeoJSON temporal de cheias/vazantes.
- Funcionamento: Carrega estações/trechos, associa, lê séries, gera features e salva.
- Entradas: `--raio-m`, `--largura-min-m`, `--saida`.
- Saidas: Arquivo JS com `HISTORICO_NIVEL`.
- Erros e efeitos: Sobrescreve a saída padrão em `frontend/mapa-hidrovias/` (diretório pode não existir na cópia enxuta).
- Dependencias: FUN-PY-ETL-062/063/064/066/068/069.
- Consumidores: Execução manual/CLI.
- Testes: Sem teste automatizado identificado.

### COL

#### FUN-PY-COL-001 — _carregar_token()
- Status: Ativa
- Arquivo: `backend/ana_client.py`
- Simbolo: `_carregar_token`
- Assinatura: `_carregar_token() -> tuple[str | None, float]`
- Objetivo: Recuperar token JWT da ANA em cache local.
- Funcionamento: Lê `.ana_token.json` (`token`, `expira_em`) quando existe; falhas retornam `(None, 0.0)`.
- Entradas: Nenhuma.
- Saidas: Token e timestamp de expiração.
- Erros e efeitos: Silencia `ValueError`/`OSError`.
- Dependencias: `json`, `pathlib`.
- Consumidores: FUN-PY-COL-003.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-COL-002 — _salvar_token(token, expira_em)
- Status: Ativa
- Arquivo: `backend/ana_client.py`
- Simbolo: `_salvar_token`
- Assinatura: `_salvar_token(token: str, expira_em: float) -> None`
- Objetivo: Persistir o token da ANA em cache.
- Funcionamento: Escreve JSON em `.ana_token.json`; falhas de escrita são ignoradas.
- Entradas: Token e expiração.
- Saidas: Nenhuma.
- Erros e efeitos: Silencia `OSError`.
- Dependencias: `json`.
- Consumidores: FUN-PY-COL-005.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-COL-003 — AnaClient.__init__(identificador=None, senha=None, base_url=BASE_URL)
- Status: Ativa
- Arquivo: `backend/ana_client.py`
- Simbolo: `AnaClient.__init__`
- Assinatura: `AnaClient.__init__(self, identificador: str | None = None, senha: str | None = None, base_url: str = BASE_URL) -> None`
- Objetivo: Configurar o cliente REST da ANA.
- Funcionamento: Lê credenciais de argumentos ou `ANA_IDENTIFICADOR`/`ANA_SENHA`, cria `requests.Session`, carrega token em cache e define 6 tentativas.
- Entradas: Credenciais e URL base opcionais.
- Saidas: Nenhuma.
- Erros e efeitos: `ValueError` se credenciais ausentes.
- Dependencias: FUN-PY-COL-001.
- Consumidores: `coletar_telemetria.py`, `validar_estacoes.py`, `_ultimas_leituras_ana`.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-COL-004 — AnaClient._requisitar(metodo, url, **kwargs)
- Status: Ativa
- Arquivo: `backend/ana_client.py`
- Simbolo: `AnaClient._requisitar`
- Assinatura: `AnaClient._requisitar(self, metodo: str, url: str, **kwargs) -> requests.Response`
- Objetivo: Executar requisições com retentativa e backoff.
- Funcionamento: Tenta até 6 vezes; repete em erros de rede e status 417/429/500/502/503/504 com espera progressiva de 5 s × tentativa.
- Entradas: Método, URL e argumentos do `requests`.
- Saidas: `Response` bem-sucedida (qualquer status fora da lista).
- Erros e efeitos: Propaga erro de rede na última tentativa; `raise_for_status` em status persistente.
- Dependencias: `requests`, `time`.
- Consumidores: FUN-PY-COL-005, FUN-PY-COL-007.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-COL-005 — AnaClient._autenticar()
- Status: Ativa
- Arquivo: `backend/ana_client.py`
- Simbolo: `AnaClient._autenticar`
- Assinatura: `AnaClient._autenticar(self) -> None`
- Objetivo: Obter token JWT da ANA.
- Funcionamento: Chama `OAUth/v1` com headers `Identificador`/`Senha`, extrai `tokenautenticacao` e grava cache por 3500 s.
- Entradas: Nenhuma.
- Saidas: Nenhuma.
- Erros e efeitos: `RuntimeError` se não houver token; salva token em arquivo.
- Dependencias: FUN-PY-COL-004, FUN-PY-COL-002.
- Consumidores: FUN-PY-COL-006.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-COL-006 — AnaClient._token_atual()
- Status: Ativa
- Arquivo: `backend/ana_client.py`
- Simbolo: `AnaClient._token_atual`
- Assinatura: `AnaClient._token_atual(self) -> str`
- Objetivo: Garantir token válido.
- Funcionamento: Reautentica quando não há token ou quando expirou.
- Entradas: Nenhuma.
- Saidas: Token.
- Erros e efeitos: Propaga erros de autenticação.
- Dependencias: FUN-PY-COL-005.
- Consumidores: FUN-PY-COL-007.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-COL-007 — AnaClient._get(rota, params=None)
- Status: Ativa
- Arquivo: `backend/ana_client.py`
- Simbolo: `AnaClient._get`
- Assinatura: `AnaClient._get(self, rota: str, params: dict | None = None) -> dict`
- Objetivo: Fazer GET autenticado e devolver JSON.
- Funcionamento: Adiciona `Authorization: Bearer`, repete uma vez em 401 após limpar o token e retorna o JSON.
- Entradas: Rota relativa e parâmetros.
- Saidas: Dicionário JSON.
- Erros e efeitos: Propaga erros HTTP/JSON.
- Dependencias: FUN-PY-COL-006, FUN-PY-COL-004.
- Consumidores: FUN-PY-COL-008, FUN-PY-COL-009, `coletar_telemetria.baixar_lote`, `_ultimas_leituras_ana`.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-COL-008 — AnaClient.listar_rios(codigo_rio=None, data_ini=None, data_fim=None)
- Status: Ativa
- Arquivo: `backend/ana_client.py`
- Simbolo: `AnaClient.listar_rios`
- Assinatura: `AnaClient.listar_rios(self, codigo_rio: int | None = None, data_ini: str | None = None, data_fim: str | None = None) -> list[dict]`
- Objetivo: Consultar o catálogo de rios da ANA.
- Funcionamento: Monta parâmetros com os nomes de campo esperados pela API e chama `HidroRio/v1`.
- Entradas: Filtros opcionais.
- Saidas: Lista de rios.
- Erros e efeitos: Propaga erros de rede/API.
- Dependencias: FUN-PY-COL-007.
- Consumidores: FUN-PY-COL-012, `validar_estacoes.py` (indireto).
- Testes: Sem teste automatizado identificado.

#### FUN-PY-COL-009 — AnaClient.listar_estacoes(codigo_estacao=None, uf=None, codigo_bacia=None, data_ini=None, data_fim=None)
- Status: Ativa
- Arquivo: `backend/ana_client.py`
- Simbolo: `AnaClient.listar_estacoes`
- Assinatura: `AnaClient.listar_estacoes(self, codigo_estacao: int | None = None, uf: str | None = None, codigo_bacia: int | None = None, data_ini: str | None = None, data_fim: str | None = None) -> list[dict]`
- Objetivo: Consultar o inventário de estações da ANA.
- Funcionamento: Chama `HidroInventarioEstacoes/v1` com filtros; UF é convertida para maiúsculas.
- Entradas: Filtros opcionais.
- Saidas: Lista de estações.
- Erros e efeitos: Propaga erros.
- Dependencias: FUN-PY-COL-007.
- Consumidores: `validar_estacoes.main`.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-COL-010 — normalizar_rio(rio)
- Status: Ativa
- Arquivo: `backend/ana_client.py`
- Simbolo: `normalizar_rio`
- Assinatura: `normalizar_rio(rio: dict) -> dict`
- Objetivo: Mapear campos da API para nomes internos.
- Funcionamento: Extrai código, nome, bacia, sub-bacia, jurisdição e data de alteração.
- Entradas: Registro bruto.
- Saidas: Registro normalizado.
- Erros e efeitos: Campos ausentes viram `None`.
- Dependencias: Nenhuma.
- Consumidores: FUN-PY-COL-011, FUN-PY-COL-012.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-COL-011 — salvar_csv(rios, caminho)
- Status: Ativa
- Arquivo: `backend/ana_client.py`
- Simbolo: `salvar_csv`
- Assinatura: `salvar_csv(rios: list[dict], caminho: str) -> None`
- Objetivo: Exportar o catálogo de rios em CSV.
- Funcionamento: Usa `DictWriter` com as chaves de `normalizar_rio`.
- Entradas: Lista de rios e caminho.
- Saidas: Arquivo CSV.
- Erros e efeitos: `IndexError` se a lista estiver vazia; propaga `OSError`.
- Dependencias: FUN-PY-COL-010.
- Consumidores: FUN-PY-COL-012.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-COL-012 — main()
- Status: Ativa
- Arquivo: `backend/ana_client.py`
- Simbolo: `main`
- Assinatura: `main() -> None`
- Objetivo: CLI do cliente REST da ANA.
- Funcionamento: Lista rios e opcionalmente salva CSV; imprime resumo.
- Entradas: `--csv`, `--codigo`.
- Saidas: Saída no console e CSV opcional.
- Erros e efeitos: Cria `AnaClient` (exige credenciais).
- Dependencias: FUN-PY-COL-003, FUN-PY-COL-008, FUN-PY-COL-010, FUN-PY-COL-011.
- Consumidores: Execução manual/CLI.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-COL-013 — serie_historica(cod_estacao, data_inicio, data_fim="", tipo_dados="1", nivel_consistencia="2", timeout=180)
- Status: Ativa
- Arquivo: `backend/ana_soap.py`
- Simbolo: `serie_historica`
- Assinatura: `serie_historica(cod_estacao: str, data_inicio: str, data_fim: str = "", tipo_dados: str = TIPO_COTA, nivel_consistencia: str = NIVEL_CONSISTIDO, timeout: int = 180) -> list[dict[str, str]]`
- Objetivo: Consultar a série histórica mensal no SOAP da ANA.
- Funcionamento: Envia `POST` a `HidroSerieHistorica` com os parâmetros e converte o XML em registros `SerieHistorica`.
- Entradas: Código, datas `dd/MM/yyyy`, tipo e consistência.
- Saidas: Lista de registros ou `[]` quando o XML traz `ErrorTable`.
- Erros e efeitos: Propaga erro HTTP/XML (`requests`, `ElementTree`).
- Dependencias: `requests`, `xml.etree`.
- Consumidores: FUN-PY-COL-016, FUN-PY-COL-018.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-COL-014 — _cota_diaria_valida(valor)
- Status: Ativa
- Arquivo: `backend/ana_soap.py`
- Simbolo: `_cota_diaria_valida`
- Assinatura: `_cota_diaria_valida(valor: str | None) -> float | None`
- Objetivo: Validar uma cota diária do SOAP.
- Funcionamento: Converte para float e aceita apenas `0 < v < 100000`.
- Entradas: Texto.
- Saidas: Float válido ou `None`.
- Erros e efeitos: Silencia `TypeError`/`ValueError`.
- Dependencias: Nenhuma.
- Consumidores: FUN-PY-COL-017.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-COL-015 — _ano_mes(data_hora)
- Status: Ativa
- Arquivo: `backend/ana_soap.py`
- Simbolo: `_ano_mes`
- Assinatura: `_ano_mes(data_hora: str) -> tuple[int, int] | None`
- Objetivo: Extrair ano e mês de `YYYY-MM-DD HH:MM:SS`.
- Funcionamento: Valida tamanho e separador antes de converter.
- Entradas: Texto.
- Saidas: `(ano, mês)` ou `None`.
- Erros e efeitos: Silencia `ValueError`.
- Dependencias: Nenhuma.
- Consumidores: FUN-PY-COL-017.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-COL-016 — serie_diaria(cod_estacao, data_inicio, data_fim="", tipo_dados="1", nivel_consistencia="2", timeout=180)
- Status: Ativa
- Arquivo: `backend/ana_soap.py`
- Simbolo: `serie_diaria`
- Assinatura: `serie_diaria(cod_estacao: str, data_inicio: str, data_fim: str = "", tipo_dados: str = TIPO_COTA, nivel_consistencia: str = NIVEL_CONSISTIDO, timeout: int = 180) -> list[dict[str, Any]]`
- Objetivo: Obter uma cota por dia a partir do retorno mensal.
- Funcionamento: Chama `serie_historica` e delega a expansão dos campos `Cota01..Cota31`.
- Entradas: Mesmos parâmetros do SOAP.
- Saidas: Registros `{codigo_estacao, data, cota_cm, status, nivel_consistencia}`.
- Erros e efeitos: Propaga erros de rede.
- Dependencias: FUN-PY-COL-013, FUN-PY-COL-017.
- Consumidores: `coletar_cotas_diarias.coletar_estacao`.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-COL-017 — _expandir_diaria(cod_estacao, rows, nivel_consistencia)
- Status: Ativa
- Arquivo: `backend/ana_soap.py`
- Simbolo: `_expandir_diaria`
- Assinatura: `_expandir_diaria(cod_estacao: str, rows: list[dict[str, str]], nivel_consistencia: str) -> list[dict[str, Any]]`
- Objetivo: Deduplicar meses e expandir leituras diárias.
- Funcionamento: Mantém o registro de `DataHora` mais recente por `(ano,mês)`, percorre os dias do mês e descarta cotas inválidas.
- Entradas: Registros mensais e nível de consistência.
- Saidas: Registros diários.
- Erros e efeitos: Usa `calendar.monthrange`.
- Dependencias: FUN-PY-COL-014, FUN-PY-COL-015.
- Consumidores: FUN-PY-COL-016.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-COL-018 — resumo_cotas(cod_estacao, anos=5, timeout=180)
- Status: Ativa
- Arquivo: `backend/ana_soap.py`
- Simbolo: `resumo_cotas`
- Assinatura: `resumo_cotas(cod_estacao: str, anos: int = 5, timeout: int = 180) -> dict[str, Any] | None`
- Objetivo: Calcular mín/máx/média históricos de uma estação.
- Funcionamento: Consulta níveis consistido e bruto, mescla registros e delega as estatísticas.
- Entradas: Código, janela em anos.
- Saidas: Resumo ou `None` sem dados.
- Erros e efeitos: Erros de rede por nível são tratados como vazio; `ano_atual` está fixo em 2026.
- Dependencias: FUN-PY-COL-013, FUN-PY-COL-019.
- Consumidores: `coletar_cotas_historicas.main`.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-COL-019 — _estatisticas(cod_estacao, rows, nivel)
- Status: Ativa
- Arquivo: `backend/ana_soap.py`
- Simbolo: `_estatisticas`
- Assinatura: `_estatisticas(cod_estacao: str, rows: list[dict], nivel: str) -> dict[str, Any]`
- Objetivo: Calcular estatísticas de cota dos registros mensais.
- Funcionamento: Filtra status vazio/`0` e valores em `(0, 100000)`, calcula mínimo, máximo, média e extremos de datas.
- Entradas: Registros e rótulo de consistência.
- Saidas: Dicionário de estatísticas.
- Erros e efeitos: Campos vazios viram `None`/`""`.
- Dependencias: Nenhuma.
- Consumidores: FUN-PY-COL-018.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-COL-020 — carregar_csv(caminho)
- Status: Ativa
- Arquivo: `backend/coletar_telemetria.py`
- Simbolo: `carregar_csv`
- Assinatura: `carregar_csv(caminho: Path) -> list[dict]`
- Objetivo: Ler CSV de telemetria/estações.
- Funcionamento: Retorna `[]` se ausente; lê UTF-8-SIG com delimitador `;`.
- Entradas: Caminho.
- Saidas: Linhas.
- Erros e efeitos: Propaga `OSError` em arquivo ilegível.
- Dependencias: `csv`.
- Consumidores: FUN-PY-COL-022/024/025.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-COL-021 — salvar_csv(linhas, caminho)
- Status: Ativa
- Arquivo: `backend/coletar_telemetria.py`
- Simbolo: `salvar_csv`
- Assinatura: `salvar_csv(linhas: list[dict], caminho: Path) -> None`
- Objetivo: Gravar o acumulado de telemetria.
- Funcionamento: Escreve com `;` e UTF-8-SIG usando `CAMPOS`.
- Entradas: Linhas e caminho.
- Saidas: Nenhuma.
- Erros e efeitos: Sobrescreve o arquivo.
- Dependencias: `csv`.
- Consumidores: FUN-PY-COL-025.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-COL-022 — estacoes_telemetricas()
- Status: Ativa
- Arquivo: `backend/coletar_telemetria.py`
- Simbolo: `estacoes_telemetricas`
- Assinatura: `estacoes_telemetricas() -> list[str]`
- Objetivo: Listar códigos de estações telemétricas.
- Funcionamento: Usa `estacoes_am_enriquecidas.csv` filtrando `telemetrica == "1"`; sem esse arquivo, usa `estacoes_am.csv`.
- Entradas: Nenhuma.
- Saidas: Lista de códigos.
- Erros e efeitos: `FileNotFoundError` se o CSV base não existir.
- Dependencias: FUN-PY-COL-020.
- Consumidores: FUN-PY-COL-025.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-COL-023 — baixar_lote(cliente, codigos, data_busca)
- Status: Ativa
- Arquivo: `backend/coletar_telemetria.py`
- Simbolo: `baixar_lote`
- Assinatura: `baixar_lote(cliente: ana_client.AnaClient, codigos: list[str], data_busca: str) -> list[dict]`
- Objetivo: Baixar leituras de até 10 estações.
- Funcionamento: Consulta `HidroinfoanaSerieTelemetricaAdotada/v2` e normaliza cota/vazão/chuva e status.
- Entradas: Cliente, códigos e data.
- Saidas: Lista de leituras normalizadas.
- Erros e efeitos: Propaga erros da API.
- Dependencias: FUN-PY-COL-007.
- Consumidores: FUN-PY-COL-025.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-COL-024 — resumo_telemetria()
- Status: Ativa
- Arquivo: `backend/coletar_telemetria.py`
- Simbolo: `resumo_telemetria`
- Assinatura: `resumo_telemetria() -> None`
- Objetivo: Imprimir resumo mínimo/máximo/médio por estação.
- Funcionamento: Lê o CSV acumulado, ignora cotas não numéricas/≤0 e agrupa por estação.
- Entradas: Nenhuma.
- Saidas: Relatório no console.
- Erros e efeitos: Mensagem quando não há dados.
- Dependencias: FUN-PY-COL-020.
- Consumidores: FUN-PY-COL-025 (`--resumo`).
- Testes: Sem teste automatizado identificado.

#### FUN-PY-COL-025 — main()
- Status: Ativa
- Arquivo: `backend/coletar_telemetria.py`
- Simbolo: `main`
- Assinatura: `main() -> None`
- Objetivo: Coletar incrementalmente a telemetria ANA.
- Funcionamento: Baixa lotes de 10 estações, deduplica por `(codigo_estacao, data_hora_medicao)` e regrava o CSV.
- Entradas: `--resumo`, `--data-busca` (padrão fixo `2026-08-17`).
- Saidas: CSV acumulado e log por lote.
- Erros e efeitos: Cria `AnaClient` (credenciais obrigatórias); sobrescreve o CSV quando há novas linhas.
- Dependencias: FUN-PY-COL-003, FUN-PY-COL-020/021/022/023/024.
- Consumidores: Execução manual/CLI e timer de coleta.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-COL-026 — localizar_estacoes()
- Status: Ativa
- Arquivo: `backend/coletar_cotas_diarias.py`
- Simbolo: `localizar_estacoes`
- Assinatura: `localizar_estacoes() -> Path`
- Objetivo: Encontrar o CSV de estações para a coleta diária.
- Funcionamento: Testa `planilhas/estacoes_am.csv`, `estacoes_am.csv` e `planilhas/estacoes_am_enriquecidas.csv`.
- Entradas: Nenhuma.
- Saidas: Primeiro caminho existente.
- Erros e efeitos: `SystemExit` se nenhum existir.
- Dependencias: `pathlib`.
- Consumidores: `main` (FUN-PY-COL-030).
- Testes: Sem teste automatizado identificado.

#### FUN-PY-COL-027 — carregar_csv(caminho)
- Status: Ativa
- Arquivo: `backend/coletar_cotas_diarias.py`
- Simbolo: `carregar_csv`
- Assinatura: `carregar_csv(caminho: Path) -> list[dict]`
- Objetivo: Ler o CSV de estações.
- Funcionamento: UTF-8-SIG e delimitador `;`.
- Entradas: Caminho.
- Saidas: Linhas.
- Erros e efeitos: Propaga `OSError`.
- Dependencias: `csv`.
- Consumidores: FUN-PY-COL-030.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-COL-028 — salvar_csv(linhas, caminho)
- Status: Ativa
- Arquivo: `backend/coletar_cotas_diarias.py`
- Simbolo: `salvar_csv`
- Assinatura: `salvar_csv(linhas: list[dict], caminho: Path) -> None`
- Objetivo: Gravar a série diária coletada.
- Funcionamento: Cria diretórios e escreve colunas `codigo_estacao,nome_estacao,data,cota_cm,status,nivel_consistencia`.
- Entradas: Linhas e caminho.
- Saidas: Nenhuma.
- Erros e efeitos: Sobrescreve o arquivo.
- Dependencias: `csv`.
- Consumidores: FUN-PY-COL-030.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-COL-029 — coletar_estacao(codigo, anos, ano_atual)
- Status: Ativa
- Arquivo: `backend/coletar_cotas_diarias.py`
- Simbolo: `coletar_estacao`
- Assinatura: `coletar_estacao(codigo: str, anos: int, ano_atual: int) -> dict[str, dict]`
- Objetivo: Mesclar as séries diárias consistida e bruta de uma estação.
- Funcionamento: Consulta os níveis 2 e 1; a primeira ocorrência por data prevalece (consistido tem prioridade); erros por nível são impressos e ignorados.
- Entradas: Código, janela e ano atual.
- Saidas: `{data: linha}`.
- Erros e efeitos: Captura `Exception` por nível.
- Dependencias: FUN-PY-COL-016.
- Consumidores: FUN-PY-COL-030.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-COL-030 — main()
- Status: Ativa
- Arquivo: `backend/coletar_cotas_diarias.py`
- Simbolo: `main`
- Assinatura: `main() -> None`
- Objetivo: Coletar a série diária de cotas das estações AM.
- Funcionamento: Seleciona estações, coleta uma a uma com atraso, ordena e grava CSV.
- Entradas: `--anos`, `--ano-atual`, `--saida`, `--delay`, `--codigo`, `--limite`.
- Saidas: CSV e relatório.
- Erros e efeitos: `SystemExit` sem estações; imprime estações sem dados.
- Dependencias: FUN-PY-COL-026/027/028/029.
- Consumidores: Execução manual/CLI.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-COL-031 — main()
- Status: Ativa
- Arquivo: `backend/coletar_cotas_historicas.py`
- Simbolo: `main`
- Assinatura: `main() -> None`
- Objetivo: Coletar mín/máx/média históricos das estações AM.
- Funcionamento: Lê `estacoes_am.csv`, chama `resumo_cotas` por estação com atraso e grava CSV; preenche registro vazio quando não há dados.
- Entradas: `--anos`, `--saida`, `--delay`.
- Saidas: CSV de cotas históricas.
- Erros e efeitos: Sobrescreve o CSV de saída; propaga falhas de rede.
- Dependencias: FUN-PY-COL-018, `validar_estacoes.carregar_csv/salvar_csv` (FUN-PY-COL-062/063).
- Consumidores: Execução manual/CLI.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-COL-032 — _get(url, params=None)
- Status: Ativa
- Arquivo: `backend/coletar_hydroweb.py`
- Simbolo: `_get`
- Assinatura: `_get(url: str, params: dict | None = None) -> dict`
- Objetivo: Fazer GET no catálogo STAC do hydroweb.next.
- Funcionamento: Requisição com timeout de 120 s e `User-Agent: hidrowize/0.1`; retorna JSON.
- Entradas: URL e parâmetros.
- Saidas: Dicionário JSON.
- Erros e efeitos: `raise_for_status` em erro HTTP.
- Dependencias: `requests`.
- Consumidores: FUN-PY-COL-035.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-COL-033 — _api_key()
- Status: Ativa
- Arquivo: `backend/coletar_hydroweb.py`
- Simbolo: `_api_key`
- Assinatura: `_api_key() -> str`
- Objetivo: Obter a chave de API do hydroweb.next.
- Funcionamento: Lê `HYDROWEB_API_KEY` do ambiente.
- Entradas: Nenhuma.
- Saidas: Chave.
- Erros e efeitos: `RuntimeError` com instrução de configuração se ausente.
- Dependencias: `os`.
- Consumidores: FUN-PY-COL-036.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-COL-034 — _extrair_meta(feature)
- Status: Ativa
- Arquivo: `backend/coletar_hydroweb.py`
- Simbolo: `_extrair_meta`
- Assinatura: `_extrair_meta(feature: dict) -> dict`
- Objetivo: Normalizar um item STAC de estação virtual.
- Funcionamento: Deriva código, rio, km, estação e coordenadas a partir do `id` e da geometria.
- Entradas: Feature STAC.
- Saidas: Metadados normalizados.
- Erros e efeitos: Pode levantar `KeyError` sem `id`; assume formato `RIO_..._KM`.
- Dependencias: Nenhuma.
- Consumidores: FUN-PY-COL-035.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-COL-035 — listar_estacoes(bbox)
- Status: Ativa
- Arquivo: `backend/coletar_hydroweb.py`
- Simbolo: `listar_estacoes`
- Assinatura: `listar_estacoes(bbox: list[float]) -> list[dict]`
- Objetivo: Listar estações virtuais na bbox via STAC.
- Funcionamento: Pagina `/search` seguindo links `next`, com `limit=500`, e normaliza cada feature.
- Entradas: Bbox.
- Saidas: Lista de estações.
- Erros e efeitos: Propaga erros HTTP/JSON.
- Dependencias: FUN-PY-COL-032, FUN-PY-COL-034.
- Consumidores: FUN-PY-COL-048/050.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-COL-036 — _baixar_zip(collection_id, bbox, zip_nome, subpasta)
- Status: Ativa
- Arquivo: `backend/coletar_hydroweb.py`
- Simbolo: `_baixar_zip`
- Assinatura: `_baixar_zip(collection_id: str, bbox: list[float], zip_nome: str, subpasta: str) -> Path`
- Objetivo: Baixar uma coleção via `py_hydroweb`.
- Funcionamento: Exige API key, cria `Client`, `DownloadBasket` e chama `submit_and_download_zip`.
- Entradas: Coleção, bbox, nome do zip e subpasta.
- Saidas: Caminho do zip.
- Erros e efeitos: `ImportError`/`RuntimeError`; cria diretório e pode demorar minutos.
- Dependencias: FUN-PY-COL-033, `py_hydroweb`.
- Consumidores: FUN-PY-COL-050/051/052.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-COL-037 — _extrair_zip(zip_path, subpasta)
- Status: Ativa
- Arquivo: `backend/coletar_hydroweb.py`
- Simbolo: `_extrair_zip`
- Assinatura: `_extrair_zip(zip_path: Path, subpasta: str) -> Path`
- Objetivo: Extrair o zip baixado.
- Funcionamento: `zipfile.extractall` em `data/satelite/<subpasta>`.
- Entradas: Zip e subpasta.
- Saidas: Diretório de destino.
- Erros e efeitos: Sobrescreve arquivos existentes; propaga `BadZipFile`/`OSError`.
- Dependencias: `zipfile`.
- Consumidores: FUN-PY-COL-050/051/052.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-COL-038 — _parse_data(valor)
- Status: Ativa
- Arquivo: `backend/coletar_hydroweb.py`
- Simbolo: `_parse_data`
- Assinatura: `_parse_data(valor: str) -> str | None`
- Objetivo: Converter datas em múltiplos formatos para ISO.
- Funcionamento: Tenta `FORMATOS_DATA` em sequência.
- Entradas: Texto.
- Saidas: ISO ou `None`.
- Erros e efeitos: Nenhum.
- Dependencias: `datetime`.
- Consumidores: FUN-PY-COL-041.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-COL-039 — _parse_numero(valor)
- Status: Ativa
- Arquivo: `backend/coletar_hydroweb.py`
- Simbolo: `_parse_numero`
- Assinatura: `_parse_numero(valor: str) -> float | None`
- Objetivo: Converter número com vírgula decimal.
- Funcionamento: Troca `,` por `.` e converte para float.
- Entradas: Texto.
- Saidas: Float ou `None`.
- Erros e efeitos: Silencia `ValueError`.
- Dependencias: Nenhuma.
- Consumidores: FUN-PY-COL-041.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-COL-040 — _delimitador(linha)
- Status: Ativa
- Arquivo: `backend/coletar_hydroweb.py`
- Simbolo: `_delimitador`
- Assinatura: `_delimitador(linha: str) -> str | None`
- Objetivo: Detectar o separador de um arquivo de série.
- Funcionamento: Testa `;`, tabulação e `,` na primeira linha.
- Entradas: Linha.
- Saidas: Delimitador ou `None`.
- Erros e efeitos: Nenhum.
- Dependencias: Nenhuma.
- Consumidores: FUN-PY-COL-041.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-COL-041 — parsear_serie_txt(caminho)
- Status: Ativa
- Arquivo: `backend/coletar_hydroweb.py`
- Simbolo: `parsear_serie_txt`
- Assinatura: `parsear_serie_txt(caminho: Path) -> list[dict]`
- Objetivo: Converter arquivo `.txt` de estação virtual em observações.
- Funcionamento: Ignora comentários, detecta delimitador, interpreta data e os dois primeiros números como nível e incerteza.
- Entradas: Caminho.
- Saidas: Registros `{data, nivel_m, incerteza_m}`.
- Erros e efeitos: Retorna `[]` sem linhas; linhas sem data são descartadas.
- Dependencias: FUN-PY-COL-038/039/040.
- Consumidores: FUN-PY-COL-049.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-COL-042 — _codigo_de_nome(nome)
- Status: Ativa
- Arquivo: `backend/coletar_hydroweb.py`
- Simbolo: `_codigo_de_nome`
- Assinatura: `_codigo_de_nome(nome: str) -> str`
- Objetivo: Derivar o código da estação a partir do nome do arquivo.
- Funcionamento: Remove prefixo `hydroprd_`, extensão `.txt` e sufixos `_exp`/`_ope`.
- Entradas: Nome do arquivo.
- Saidas: Código.
- Erros e efeitos: Nenhum.
- Dependencias: Nenhuma.
- Consumidores: FUN-PY-COL-049.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-COL-043 — _salvar_csv(linhas, campos, caminho)
- Status: Ativa
- Arquivo: `backend/coletar_hydroweb.py`
- Simbolo: `_salvar_csv`
- Assinatura: `_salvar_csv(linhas: list[dict], campos: list[str], caminho: Path) -> None`
- Objetivo: Gravar CSV de satélite.
- Funcionamento: `DictWriter` com `;` e UTF-8-SIG.
- Entradas: Linhas, campos e caminho.
- Saidas: Nenhuma.
- Erros e efeitos: Sobrescreve o arquivo.
- Dependencias: `csv`.
- Consumidores: FUN-PY-COL-048/050.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-COL-044 — _persistir_satelite(estacoes, series, fonte)
- Status: Ativa
- Arquivo: `backend/coletar_hydroweb.py`
- Simbolo: `_persistir_satelite`
- Assinatura: `_persistir_satelite(estacoes: list[dict], series: list[dict], fonte: str) -> tuple[int, int]`
- Objetivo: Persistir estações e séries no SQLite.
- Funcionamento: Cria schema e faz upsert via `gerar_sqlite`, com commit.
- Entradas: Estações, séries e fonte.
- Saidas: `(n_estações, n_séries)`.
- Erros e efeitos: Abre/fecha conexão; propaga `sqlite3.Error`.
- Dependencias: FUN-PY-ETL-016/017/018.
- Consumidores: FUN-PY-COL-048/050.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-COL-045 — _persistir_netcdf(importador, rotulo)
- Status: Ativa
- Arquivo: `backend/coletar_hydroweb.py`
- Simbolo: `_persistir_netcdf`
- Assinatura: `_persistir_netcdf(importador: str, rotulo: str) -> int`
- Objetivo: Executar um importador NetCDF de `gerar_sqlite`.
- Funcionamento: Importa o módulo dinamicamente, cria schema, chama a função pelo nome e faz commit.
- Entradas: Nome da função e rótulo.
- Saidas: Registros importados.
- Erros e efeitos: `AttributeError` para importador inválido.
- Dependencias: FUN-PY-ETL-016/025/026.
- Consumidores: FUN-PY-COL-051/052.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-COL-046 — _contar_tabela(tabela)
- Status: Ativa
- Arquivo: `backend/coletar_hydroweb.py`
- Simbolo: `_contar_tabela`
- Assinatura: `_contar_tabela(tabela: str) -> int`
- Objetivo: Contar registros de uma tabela para evitar rebaixamento.
- Funcionamento: Retorna 0 sem banco ou se a tabela não existir.
- Entradas: Nome da tabela.
- Saidas: Contagem.
- Erros e efeitos: Silencia `sqlite3.OperationalError`.
- Dependencias: `sqlite3`.
- Consumidores: FUN-PY-COL-050/051/052.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-COL-047 — _limpar_subpasta(subpasta)
- Status: Ativa
- Arquivo: `backend/coletar_hydroweb.py`
- Simbolo: `_limpar_subpasta`
- Assinatura: `_limpar_subpasta(subpasta: str) -> None`
- Objetivo: Remover arquivos intermediários de download.
- Funcionamento: `shutil.rmtree` em `data/satelite/<subpasta>` quando existe.
- Entradas: Subpasta.
- Saidas: Nenhuma.
- Erros e efeitos: Remoção recursiva (destrutiva).
- Dependencias: `shutil`.
- Consumidores: FUN-PY-COL-050/051/052.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-COL-048 — comando_listar(bbox)
- Status: Ativa
- Arquivo: `backend/coletar_hydroweb.py`
- Simbolo: `comando_listar`
- Assinatura: `comando_listar(bbox: list[float]) -> None`
- Objetivo: Listar e persistir estações virtuais.
- Funcionamento: Chama `listar_estacoes`, salva CSV e persiste metadados.
- Entradas: Bbox.
- Saidas: CSV e relatório.
- Erros e efeitos: Sobrescreve CSV e faz upsert no SQLite.
- Dependencias: FUN-PY-COL-035/043/044.
- Consumidores: FUN-PY-COL-054.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-COL-049 — _consolidar_series(pasta, mapa)
- Status: Ativa
- Arquivo: `backend/coletar_hydroweb.py`
- Simbolo: `_consolidar_series`
- Assinatura: `_consolidar_series(pasta: Path, mapa: dict) -> tuple[int, int]`
- Objetivo: Consolidar séries de nível em CSV e SQLite com baixo uso de RAM.
- Funcionamento: Itera arquivos, escreve CSV e insere em lotes de 20 mil; conta observações e arquivos sem estação.
- Entradas: Pasta e mapa código→metadados.
- Saidas: `(total_observações, não_mapeadas)`.
- Erros e efeitos: Grava CSV e SQLite; `nonlocal` para contadores.
- Dependencias: FUN-PY-COL-041/042, FUN-PY-ETL-016/018.
- Consumidores: FUN-PY-COL-050.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-COL-050 — comando_estacoes(bbox, forcar=False)
- Status: Ativa
- Arquivo: `backend/coletar_hydroweb.py`
- Simbolo: `comando_estacoes`
- Assinatura: `comando_estacoes(bbox: list[float], forcar: bool = False) -> None`
- Objetivo: Baixar e consolidar estações virtuais.
- Funcionamento: Lista estações; sem `--forcar`, pula download se `series_nivel_satelite` já tem dados; caso contrário baixa zip, extrai, consolida e limpa a pasta.
- Entradas: Bbox e flag de força.
- Saidas: CSV, SQLite e relatório.
- Erros e efeitos: Download pesado; remove arquivos intermediários.
- Dependencias: FUN-PY-COL-035/036/037/043/044/046/047/049.
- Consumidores: FUN-PY-COL-054.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-COL-051 — comando_batimetria(bbox, forcar=False)
- Status: Ativa
- Arquivo: `backend/coletar_hydroweb.py`
- Simbolo: `comando_batimetria`
- Assinatura: `comando_batimetria(bbox: list[float], forcar: bool = False) -> None`
- Objetivo: Baixar e importar batimetria SICFLOW.
- Funcionamento: Pula se a tabela já tem dados; baixa zip, extrai, importa NetCDF e limpa.
- Entradas: Bbox e flag de força.
- Saidas: Registros no SQLite.
- Erros e efeitos: Download grande; remove intermediários.
- Dependencias: FUN-PY-COL-036/037/045/046/047, FUN-PY-ETL-025.
- Consumidores: FUN-PY-COL-054.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-COL-052 — comando_vazao(bbox, forcar=False)
- Status: Ativa
- Arquivo: `backend/coletar_hydroweb.py`
- Simbolo: `comando_vazao`
- Assinatura: `comando_vazao(bbox: list[float], forcar: bool = False) -> None`
- Objetivo: Baixar e importar vazão SWOT.
- Funcionamento: Pula se a tabela já tem dados; baixa zip, extrai, importa NetCDF e limpa.
- Entradas: Bbox e flag de força.
- Saidas: Registros no SQLite.
- Erros e efeitos: Download/remoção de intermediários.
- Dependencias: FUN-PY-COL-036/037/045/046/047, FUN-PY-ETL-026.
- Consumidores: FUN-PY-COL-054.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-COL-053 — _parse_bbox(texto)
- Status: Ativa
- Arquivo: `backend/coletar_hydroweb.py`
- Simbolo: `_parse_bbox`
- Assinatura: `_parse_bbox(texto: str) -> list[float]`
- Objetivo: Converter `minLon,minLat,maxLon,maxLat` em lista.
- Funcionamento: Divide por vírgula e converte cada item para float.
- Entradas: Texto.
- Saidas: Lista de 4 floats.
- Erros e efeitos: `ValueError` em formato inválido.
- Dependencias: Nenhuma.
- Consumidores: FUN-PY-COL-054.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-COL-054 — main()
- Status: Ativa
- Arquivo: `backend/coletar_hydroweb.py`
- Simbolo: `main`
- Assinatura: `main() -> None`
- Objetivo: CLI do coletor de satélite.
- Funcionamento: Interpreta flags e executa listar/estações/batimetria/vazão/tudo.
- Entradas: Flags e `--bbox`.
- Saidas: Arquivos/DB e relatório.
- Erros e efeitos: Downloads grandes; exige `HYDROWEB_API_KEY` para download.
- Dependencias: FUN-PY-COL-036/048/050/051/052/053.
- Consumidores: Execução manual/CLI.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-COL-055 — _get(session, url, params=None)
- Status: Ativa
- Arquivo: `backend/coletar_legisla_am.py`
- Simbolo: `_get`
- Assinatura: `_get(session: requests.Session, url: str, params: dict | None = None) -> str`
- Objetivo: Fazer GET no portal Legisla.AM.
- Funcionamento: Usa headers próprios, timeout 30 s e força codificação UTF-8.
- Entradas: Sessão, URL e parâmetros.
- Saidas: HTML.
- Erros e efeitos: `raise_for_status` em erro HTTP.
- Dependencias: `requests`.
- Consumidores: FUN-PY-COL-056/057.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-COL-056 — buscar(session, termo, pagina)
- Status: Ativa
- Arquivo: `backend/coletar_legisla_am.py`
- Simbolo: `buscar`
- Assinatura: `buscar(session: requests.Session, termo: str, pagina: int) -> list[dict]`
- Objetivo: Extrair resultados de uma página de busca.
- Funcionamento: Parseia `li.item-li` com BeautifulSoup/lxml e devolve título, ementa e URL absoluta.
- Entradas: Sessão, termo e página.
- Saidas: Lista de resultados.
- Erros e efeitos: Descarta itens sem link.
- Dependencias: FUN-PY-COL-055, `bs4`.
- Consumidores: FUN-PY-COL-060.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-COL-057 — extrair_detalhe(session, url)
- Status: Ativa
- Arquivo: `backend/coletar_legisla_am.py`
- Simbolo: `extrair_detalhe`
- Assinatura: `extrair_detalhe(session: requests.Session, url: str) -> dict`
- Objetivo: Extrair título, ementa e corpo da página do decreto.
- Funcionamento: Seleciona `div.materia` e usa os parágrafos na ordem.
- Entradas: Sessão e URL.
- Saidas: `{titulo, ementa, corpo}` (vazios se não houver matéria).
- Erros e efeitos: Propaga erro HTTP.
- Dependencias: FUN-PY-COL-055, `bs4`.
- Consumidores: FUN-PY-COL-060.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-COL-058 — parse_numero_data(titulo)
- Status: Ativa
- Arquivo: `backend/coletar_legisla_am.py`
- Simbolo: `parse_numero_data`
- Assinatura: `parse_numero_data(titulo: str) -> tuple[str, str]`
- Objetivo: Extrair número e data ISO do título do decreto.
- Funcionamento: Aplica regex para `Nº ... DE ...` (com fallback só de data) e traduz mês.
- Entradas: Título.
- Saidas: `(numero, data)`; vazios quando não reconhece.
- Erros e efeitos: Nenhum.
- Dependencias: `re`, `MESES`.
- Consumidores: FUN-PY-COL-060.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-COL-059 — classificar(texto)
- Status: Ativa
- Arquivo: `backend/coletar_legisla_am.py`
- Simbolo: `classificar`
- Assinatura: `classificar(texto: str) -> dict`
- Objetivo: Classificar evento hidrológico e extrair município, rio e COBRADE.
- Funcionamento: Procura palavras-chave de cheia/estiagem, regex de município, último nome de rio encontrado e código COBRADE.
- Entradas: Texto do decreto.
- Saidas: `{tipo, municipio, rio, cobrade}`.
- Erros e efeitos: Retorna `outro`/vazio quando não identifica.
- Dependencias: Constantes `KW_CHEIA`, `KW_ESTIAGEM`.
- Consumidores: FUN-PY-COL-060.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-COL-060 — main()
- Status: Ativa
- Arquivo: `backend/coletar_legisla_am.py`
- Simbolo: `main`
- Assinatura: `main() -> None`
- Objetivo: Coletar decretos hidrológicos do Legisla.AM.
- Funcionamento: Busca cada termo/página, deduplica por URL, extrai detalhes com atraso, classifica e grava CSV ordenado por data.
- Entradas: `--termos`, `--paginas`, `--sem-detalhe`, `--atraso`, `--out`.
- Saidas: CSV de decretos.
- Erros e efeitos: Falhas de rede são avisadas e interrompem apenas o termo/página; sobrescreve a saída.
- Dependencias: FUN-PY-COL-056/057/058/059.
- Consumidores: Execução manual/CLI.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-COL-061 — normalizar_codigo(codigo)
- Status: Ativa
- Arquivo: `backend/validar_estacoes.py`
- Simbolo: `normalizar_codigo`
- Assinatura: `normalizar_codigo(codigo: str | None) -> str`
- Objetivo: Normalizar códigos de estação para comparação.
- Funcionamento: Converte para string, remove espaços e zeros à esquerda.
- Entradas: Código.
- Saidas: Código normalizado ou `""`.
- Erros e efeitos: Nenhum.
- Dependencias: Nenhuma.
- Consumidores: `validar_estacoes.main`.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-COL-062 — carregar_csv(caminho)
- Status: Ativa
- Arquivo: `backend/validar_estacoes.py`
- Simbolo: `carregar_csv`
- Assinatura: `carregar_csv(caminho: Path) -> list[dict]`
- Objetivo: Ler CSV de estações com `;`.
- Funcionamento: UTF-8-SIG e `DictReader`.
- Entradas: Caminho.
- Saidas: Linhas.
- Erros e efeitos: Propaga `OSError`.
- Dependencias: `csv`.
- Consumidores: `coletar_cotas_historicas.main`, `validar_estacoes.main`.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-COL-063 — salvar_csv(linhas, caminho)
- Status: Ativa
- Arquivo: `backend/validar_estacoes.py`
- Simbolo: `salvar_csv`
- Assinatura: `salvar_csv(linhas: list[dict], caminho: Path) -> None`
- Objetivo: Gravar CSV reaproveitando as chaves da primeira linha.
- Funcionamento: `DictWriter` com `;` e UTF-8-SIG.
- Entradas: Linhas e caminho.
- Saidas: Nenhuma.
- Erros e efeitos: `IndexError` se a lista estiver vazia; sobrescreve o arquivo.
- Dependencias: `csv`.
- Consumidores: `coletar_cotas_historicas.main`, `validar_estacoes.main`.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-COL-064 — main()
- Status: Ativa
- Arquivo: `backend/validar_estacoes.py`
- Simbolo: `main`
- Assinatura: `main() -> None`
- Objetivo: Validar e enriquecer as estações locais contra o inventário ANA.
- Funcionamento: Consulta o inventário de estações do AM, normaliza códigos, separa válidas/inválidas e gera relatório/CSV enriquecido opcional.
- Entradas: `--relatorio`, `--enriquecido`.
- Saidas: Relatório no console e arquivos opcionais.
- Erros e efeitos: Cria `AnaClient` (credenciais) e rede.
- Dependencias: FUN-PY-COL-009, FUN-PY-COL-061/062/063.
- Consumidores: Execução manual/CLI.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-COL-065 - _resolver_estacoes_coleta(codigos)
- Status: Ativa
- Arquivo: `backend/main.py`
- Simbolo: `_resolver_estacoes_coleta`
- Assinatura: `_resolver_estacoes_coleta(codigos: list[str]) -> list[str]`
- Objetivo: Normalizar e validar as estações de uma coleta.
- Funcionamento: Sem seleção, usa `estacoes.telemetrica = 1`; com seleção, valida os códigos no banco e rejeita desconhecidos.
- Entradas: Lista de códigos.
- Saidas: Lista de códigos válidos.
- Erros e efeitos: `ApiProblem(422)` para códigos inexistentes.
- Dependencias: `connection`.
- Consumidores: FUN-PY-API-031.
- Testes: Verificado no teste manual.

#### FUN-PY-COL-066 - _inserir_leituras(leituras)
- Status: Ativa
- Arquivo: `backend/main.py`
- Simbolo: `_inserir_leituras`
- Assinatura: `_inserir_leituras(leituras: list[tuple]) -> int`
- Objetivo: Gravar leituras de telemetria no PostGIS sem duplicar.
- Funcionamento: Cria índice único `(codigo_estacao, data_hora_medicao)` se necessário, carrega um lote em tabela temporária e insere com `ON CONFLICT DO NOTHING`, calculando `id` a partir do maior existente.
- Entradas: Lote de leituras.
- Saidas: Quantidade inserida.
- Erros e efeitos: Pode falhar se houver duplicatas prévias impedindo o índice único.
- Dependencias: `connection`, `execute_values`.
- Consumidores: FUN-PY-COL-067.
- Testes: Verificado manualmente (inserção e reexecução idempotente).

#### FUN-PY-COL-067 - _executar_coleta_niveis(job_id, codigos, inicio, fim, usuario_id)
- Status: Ativa
- Arquivo: `backend/main.py`
- Simbolo: `_executar_coleta_niveis`
- Assinatura: `_executar_coleta_niveis(job_id: str, codigos: list[str], inicio: str | None, fim: str | None, usuario_id: int) -> None`
- Objetivo: Executar a coleta em background e atualizar o job.
- Funcionamento: Consulta a ANA em lotes de 10 estações (janela de 30 dias), filtra pelo período, grava no banco e atualiza progresso/estatísticas; registra log ao concluir.
- Entradas: ID do job, estações, período e usuário.
- Saidas: Nenhuma (efeitos no job e no banco).
- Erros e efeitos: Marca o job como `erro` e registra log em caso de exceção.
- Dependencias: FUN-PY-COL-066, FUN-PY-COL-068, FUN-PY-COL-069, `AnaClient`.
- Consumidores: FUN-PY-API-031.
- Testes: Verificado manualmente em produção.

#### FUN-PY-COL-068 - _atualizar_coleta(job_id, **campos)
- Status: Ativa
- Arquivo: `backend/main.py`
- Simbolo: `_atualizar_coleta`
- Assinatura: `_atualizar_coleta(job_id: str, **campos: object) -> None`
- Objetivo: Atualizar campos do job com segurança entre threads.
- Funcionamento: Adquire `COLETA_LOCK` e aplica `update` no dicionário do job.
- Entradas: ID e campos.
- Saidas: Nenhuma.
- Erros e efeitos: Ignora job inexistente.
- Dependencias: `COLETA_LOCK`.
- Consumidores: FUN-PY-COL-067.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-COL-069 - _converter_numero(valor)
- Status: Ativa
- Arquivo: `backend/main.py`
- Simbolo: `_converter_numero`
- Assinatura: `_converter_numero(valor: object) -> float | None`
- Objetivo: Converter valores numéricos da ANA com tolerância a vazios.
- Funcionamento: Retorna `None` para vazio/inválido e `float` para valores válidos.
- Entradas: Valor bruto.
- Saidas: Número ou None.
- Erros e efeitos: Nenhum.
- Dependencias: Nenhuma.
- Consumidores: FUN-PY-COL-067.
- Testes: Sem teste automatizado identificado.

### NAV

#### FUN-PY-NAV-001 — carregar_csv(caminho)
- Status: Ativa
- Arquivo: `backend/gerar_navegabilidade.py`
- Simbolo: `carregar_csv`
- Assinatura: `carregar_csv(caminho: Path) -> list[dict]`
- Objetivo: Ler CSVs de cadastro/cotas/telemetria.
- Funcionamento: Retorna `[]` se ausente; lê UTF-8-SIG com `;`.
- Entradas: Caminho.
- Saidas: Linhas.
- Erros e efeitos: Propaga `OSError`.
- Dependencias: `csv`.
- Consumidores: FUN-PY-NAV-003/005.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-NAV-002 — flutua(valor)
- Status: Ativa
- Arquivo: `backend/gerar_navegabilidade.py`
- Simbolo: `flutua`
- Assinatura: `flutua(valor) -> float | None`
- Objetivo: Converter cota textual em float.
- Funcionamento: Retorna `None` em falha.
- Entradas: Valor.
- Saidas: Float ou `None`.
- Erros e efeitos: Silencia `TypeError`/`ValueError`.
- Dependencias: Nenhuma.
- Consumidores: FUN-PY-NAV-003/005.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-NAV-003 — estatisticas_telemetria()
- Status: Ativa
- Arquivo: `backend/gerar_navegabilidade.py`
- Simbolo: `estatisticas_telemetria`
- Assinatura: `estatisticas_telemetria() -> dict[str, dict]`
- Objetivo: Calcular cota atual e mínima acumulada por estação.
- Funcionamento: Agrupa leituras, ignora cotas ≤0 e escolhe a leitura mais recente e o mínimo.
- Entradas: Nenhuma.
- Saidas: `{codigo: {cota_atual, cota_minima_tel}}`.
- Erros e efeitos: Lê o CSV de telemetria.
- Dependencias: FUN-PY-NAV-001/002.
- Consumidores: FUN-PY-NAV-005.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-NAV-004 — classificacao(cota_atual, cota_minima, limiar)
- Status: Ativa
- Arquivo: `backend/gerar_navegabilidade.py`
- Simbolo: `classificacao`
- Assinatura: `classificacao(cota_atual: float | None, cota_minima: float | None, limiar: float) -> str`
- Objetivo: Classificar navegabilidade por folga sobre a mínima histórica.
- Funcionamento: `SEM DADOS` se faltar cota; `NAVEGAVEL` se folga ≥ limiar; `RESTRITO` se folga ≥0; caso contrário `CRITICO`.
- Entradas: Cota atual, mínima e limiar.
- Saidas: Status textual.
- Erros e efeitos: Nenhum.
- Dependencias: Nenhuma.
- Consumidores: FUN-PY-NAV-005.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-NAV-005 — main()
- Status: Ativa
- Arquivo: `backend/gerar_navegabilidade.py`
- Simbolo: `main`
- Assinatura: `main() -> None`
- Objetivo: Gerar o CSV de navegabilidade por estação.
- Funcionamento: Cruza cadastro, histórico e telemetria; prefere a mínima do SOAP e completa com a da telemetria; usa a média histórica quando não há cota atual.
- Entradas: `--limiar` (padrão 50 cm), `--saida`.
- Saidas: CSV e contagem por status.
- Erros e efeitos: Sobrescreve a saída; `IndexError` se não houver estações.
- Dependencias: FUN-PY-NAV-001/002/003/004.
- Consumidores: Execução manual/CLI; `gerar_sqlite.importar_navegabilidade`.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-NAV-006 — carregar_estacoes_virtuais(con)
- Status: Ativa
- Arquivo: `backend/gerar_navegabilidade_semanal.py`
- Simbolo: `carregar_estacoes_virtuais`
- Assinatura: `carregar_estacoes_virtuais(con: sqlite3.Connection)`
- Objetivo: Carregar coordenadas das estações virtuais.
- Funcionamento: Lê `estacoes_virtuais`, converte lat/lon para radianos e monta índice código→posição.
- Entradas: Conexão.
- Saidas: `(codigos, lat_rad, lon_rad, indice)`.
- Erros e efeitos: Ignora estações sem coordenadas.
- Dependencias: `numpy`.
- Consumidores: FUN-PY-NAV-013.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-NAV-007 — carregar_trechos(con)
- Status: Ativa
- Arquivo: `backend/gerar_navegabilidade_semanal.py`
- Simbolo: `carregar_trechos`
- Assinatura: `carregar_trechos(con: sqlite3.Connection)`
- Objetivo: Carregar centroides dos trechos navegáveis.
- Funcionamento: Lê `fid`, `centroid_lon`, `centroid_lat` e converte para radianos.
- Entradas: Conexão.
- Saidas: `(fids, lat_rad, lon_rad)`.
- Erros e efeitos: Ignora trechos sem centroide.
- Dependencias: `numpy`.
- Consumidores: FUN-PY-NAV-013.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-NAV-008 — carregar_cota_fundo(con, fids)
- Status: Ativa
- Arquivo: `backend/gerar_navegabilidade_semanal.py`
- Simbolo: `carregar_cota_fundo`
- Assinatura: `carregar_cota_fundo(con: sqlite3.Connection, fids: np.ndarray)`
- Objetivo: Associar cota de fundo observada/estimada a cada trecho.
- Funcionamento: Prefere `cota_fundo_observada` e usa `cota_fundo_estimada` como fallback; alinha ao vetor de fids.
- Entradas: Conexão e fids.
- Saidas: `(cota, fonte)` por trecho.
- Erros e efeitos: `NaN` e fonte vazia quando não há cota.
- Dependencias: `numpy`.
- Consumidores: FUN-PY-NAV-013.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-NAV-009 — k_vizinhos(t_lat, t_lon, s_lat, s_lon, k)
- Status: Ativa
- Arquivo: `backend/gerar_navegabilidade_semanal.py`
- Simbolo: `k_vizinhos`
- Assinatura: `k_vizinhos(t_lat, t_lon, s_lat, s_lon, k: int)`
- Objetivo: Encontrar as k estações virtuais mais próximas de cada trecho.
- Funcionamento: Distância haversine vetorizada em blocos de 1000 trechos, `float32` e `argpartition` para limitar memória.
- Entradas: Coordenadas em radianos e k.
- Saidas: `(índices, distâncias_km)`.
- Erros e efeitos: Usa `BLOCO_VIZINHOS`; pode consumir memória proporcional a trechos × estações no bloco.
- Dependencias: `numpy`, constante `RAIO_TERRA_M`.
- Consumidores: FUN-PY-NAV-013.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-NAV-010 — _segunda(data_iso)
- Status: Ativa
- Arquivo: `backend/gerar_navegabilidade_semanal.py`
- Simbolo: `_segunda`
- Assinatura: `_segunda(data_iso: str) -> date | None`
- Objetivo: Obter a segunda-feira da semana de uma data.
- Funcionamento: Converte `YYYY-MM-DD` e subtrai `weekday()` dias.
- Entradas: Data ISO.
- Saidas: `date` ou `None`.
- Erros e efeitos: Silencia `TypeError`/`ValueError`.
- Dependencias: `datetime`.
- Consumidores: FUN-PY-NAV-011.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-NAV-011 — montar_niveis(con, cod_idx, janela_dias)
- Status: Ativa
- Arquivo: `backend/gerar_navegabilidade_semanal.py`
- Simbolo: `montar_niveis`
- Assinatura: `montar_niveis(con: sqlite3.Connection, cod_idx: dict, janela_dias: int)`
- Objetivo: Montar a matriz semanas × estações com nível médio em janela móvel.
- Funcionamento: Lê observações em streaming e acumula em semanas vizinhas quando a distância ao centro da semana ≤ `janela_dias`.
- Entradas: Conexão, índice de códigos e janela.
- Saidas: `(semanas, matriz float32)`.
- Erros e efeitos: Ignora códigos/datas desconhecidos; memória proporcional a semanas × estações.
- Dependencias: FUN-PY-NAV-010, `numpy`.
- Consumidores: FUN-PY-NAV-013.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-NAV-012 — classificar(prof, calado, margem)
- Status: Ativa
- Arquivo: `backend/gerar_navegabilidade_semanal.py`
- Simbolo: `classificar`
- Assinatura: `classificar(prof: np.ndarray, calado: float, margem: float) -> np.ndarray`
- Objetivo: Classificar vetorialmente a navegabilidade semanal.
- Funcionamento: `SEM_DADOS` para `NaN`; `NAVEGAVEL` se `prof >= calado+margem`; `RESTRITO` se `prof >= calado`; demais `CRITICO`.
- Entradas: Profundidades e parâmetros.
- Saidas: Array de status.
- Erros e efeitos: Nenhum.
- Dependencias: `numpy`.
- Consumidores: FUN-PY-NAV-013.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-NAV-013 — main()
- Status: Ativa
- Arquivo: `backend/gerar_navegabilidade_semanal.py`
- Simbolo: `main`
- Assinatura: `main() -> None`
- Objetivo: Gerar a navegabilidade semanal por trecho com nível de satélite.
- Funcionamento: Cria `naveg_trecho_semanal`, carrega estações/trechos/cota de fundo, calcula vizinhos e níveis, seleciona a primeira estação com dado dentro do raio e grava em lotes.
- Entradas: `--db`, `--calado` (padrão 6 m), `--margem` (0,5), `--raio-km` (50), `--vizinhos` (5), `--janela-dias` (10), `--desde`, `--tudo`.
- Saidas: Tabela `naveg_trecho_semanal` e contagens.
- Erros e efeitos: `SystemExit` sem banco/estações/semanas; `DELETE` do período antes de regravar.
- Dependencias: FUN-PY-NAV-006/007/008/009/011/012.
- Consumidores: Execução manual/CLI.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-NAV-014 — main()
- Status: Ativa
- Arquivo: `backend/classificar_navegabilidade.py`
- Simbolo: `main`
- Assinatura: `main() -> None`
- Objetivo: Comparar a regra RF018 com um classificador RandomForest para navegabilidade.
- Funcionamento: Extrai cota atual/mínima e atributos AHGN, calcula a acurácia da regra (folga < 50 cm ⇒ RESTRITO) e avalia modelos com validação cruzada estratificada (5 folds).
- Entradas: Nenhuma.
- Saidas: Métricas no console.
- Erros e efeitos: Exige scikit-learn/numpy; `FileNotFoundError`/`sqlite3.Error` sem banco.
- Dependencias: `sklearn`, `numpy`.
- Consumidores: Execução manual/CLI.
- Testes: Sem teste automatizado identificado.
- Observação: os rótulos vêm da própria regra, portanto o experimento não demonstra ganho independente (RF038 bloqueado).

### ML

#### FUN-PY-ML-001 — _proj(lon, lat)
- Status: Ativa
- Arquivo: `backend/interpolar_nivel.py`
- Simbolo: `_proj`
- Assinatura: `_proj(lon: np.ndarray, lat: np.ndarray) -> np.ndarray`
- Objetivo: Projetar coordenadas em metros para o modelo.
- Funcionamento: Aplica projeção local equiretangular centrada em `LON0/LAT0`.
- Entradas: Longitude e latitude.
- Saidas: Matriz `(n,2)` em metros.
- Erros e efeitos: Nenhum.
- Dependencias: `numpy`.
- Consumidores: `interpolar_nivel.main` (FUN-PY-ML-007).
- Testes: Sem teste automatizado identificado.

#### FUN-PY-ML-002 — carregar_estacoes_mes(con, mes)
- Status: Ativa
- Arquivo: `backend/interpolar_nivel.py`
- Simbolo: `carregar_estacoes_mes`
- Assinatura: `carregar_estacoes_mes(con: sqlite3.Connection, mes: str) -> np.ndarray`
- Objetivo: Obter longitude, latitude e nível médio mensal por estação virtual.
- Funcionamento: Agrupa `series_nivel_satelite` por código/coordenadas no mês `AAAA-MM`.
- Entradas: Conexão e mês.
- Saidas: Array `(n,3)`.
- Erros e efeitos: Retorna array vazio sem dados.
- Dependencias: `numpy`.
- Consumidores: FUN-PY-ML-007.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-ML-003 — carregar_elevacao_trechos(con)
- Status: Ativa
- Arquivo: `backend/interpolar_nivel.py`
- Simbolo: `carregar_elevacao_trechos`
- Assinatura: `carregar_elevacao_trechos(con: sqlite3.Connection) -> tuple[np.ndarray, np.ndarray]`
- Objetivo: Carregar centroides e elevação média dos trechos.
- Funcionamento: `SELECT centroid_lon, centroid_lat, hig_drn_elevation_avg`.
- Entradas: Conexão.
- Saidas: Coordenadas e elevação.
- Erros e efeitos: `ValueError` se houver nulos/não numéricos (conversão para float).
- Dependencias: `numpy`.
- Consumidores: FUN-PY-ML-007.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-ML-004 — join_elevacao(esta_xy, tre_xy, tre_elev)
- Status: Ativa
- Arquivo: `backend/interpolar_nivel.py`
- Simbolo: `join_elevacao`
- Assinatura: `join_elevacao(esta_xy: np.ndarray, tre_xy: np.ndarray, tre_elev: np.ndarray) -> np.ndarray`
- Objetivo: Associar a elevação do trecho mais próximo a cada estação.
- Funcionamento: `NearestNeighbors` com métrica haversine (coordenadas em radianos invertidas).
- Entradas: Coordenadas de estações/trechos e elevação.
- Saidas: Elevação por estação.
- Erros e efeitos: Exige scikit-learn.
- Dependencias: `sklearn.neighbors`.
- Consumidores: FUN-PY-ML-007.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-ML-005 — idw(x_train, y_train, x_test, k=12)
- Status: Ativa
- Arquivo: `backend/interpolar_nivel.py`
- Simbolo: `idw`
- Assinatura: `idw(x_train: np.ndarray, y_train: np.ndarray, x_test: np.ndarray, k: int = 12) -> np.ndarray`
- Objetivo: Interpolar por distância inversa ao quadrado (baseline).
- Funcionamento: Busca k vizinhos, limita distância mínima a 1,0 e calcula média ponderada por `1/d²`.
- Entradas: Treino, alvo e teste.
- Saidas: Valores previstos.
- Erros e efeitos: Exige scikit-learn; k maior que o número de amostras levanta erro.
- Dependencias: `sklearn.neighbors`.
- Consumidores: FUN-PY-ML-007.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-ML-006 — _metricas(y_true, y_pred)
- Status: Ativa
- Arquivo: `backend/interpolar_nivel.py`
- Simbolo: `_metricas`
- Assinatura: `_metricas(y_true: np.ndarray, y_pred: np.ndarray) -> dict`
- Objetivo: Calcular R², MAE, RMSE, viés e n.
- Funcionamento: Fórmulas amostrais sobre os resíduos; R² pode ser `NaN` sem variância.
- Entradas: Valores reais e previstos.
- Saidas: Dicionário de métricas.
- Erros e efeitos: Nenhum.
- Dependencias: `numpy`.
- Consumidores: FUN-PY-ML-007.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-ML-007 — main()
- Status: Ativa
- Arquivo: `backend/interpolar_nivel.py`
- Simbolo: `main`
- Assinatura: `main() -> None`
- Objetivo: Comparar IDW e modelos ML para interpolação de nível (RF036).
- Funcionamento: Carrega um mês, faz split espacial por célula de 0,5°, avalia IDW, kNN, RF e HGB com e sem elevação, e simula cenários esparsos.
- Entradas: `--mes` (padrão `2024-09`), `--teste`.
- Saidas: Métricas no console.
- Erros e efeitos: Exige scikit-learn; sem dados pode falhar em `min()/max()`.
- Dependencias: FUN-PY-ML-001/002/003/004/005/006.
- Consumidores: Execução manual/CLI.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-ML-008 — carregar_dados(con)
- Status: Ativa
- Arquivo: `backend/rating_curve.py`
- Simbolo: `carregar_dados`
- Assinatura: `carregar_dados(con: sqlite3.Connection) -> dict`
- Objetivo: Carregar pares nível–vazão com geometria AHGN.
- Funcionamento: Junta `telemetria` e `estacoes_trechos`, converte cota cm→m e devolve vetores nomeados.
- Entradas: Conexão.
- Saidas: `{codigo, cota_m, q, largura, profundidade, annual_flow, strahler, elev_avg}`.
- Erros e efeitos: `ValueError` se a consulta não retornar linhas (conversão de array vazio com `[0]` não ocorre; shape vazio pode falhar).
- Dependencias: `numpy`.
- Consumidores: FUN-PY-ML-012.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-ML-009 — _features(d)
- Status: Ativa
- Arquivo: `backend/rating_curve.py`
- Simbolo: `_features`
- Assinatura: `_features(d: dict) -> np.ndarray`
- Objetivo: Montar a matriz de features da rating curve.
- Funcionamento: Colunas cota, largura, profundidade, vazão média anual, Strahler e elevação média.
- Entradas: Dicionário de `carregar_dados`.
- Saidas: Matriz `(n,6)`.
- Erros e efeitos: Nenhum.
- Dependencias: `numpy`.
- Consumidores: FUN-PY-ML-012.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-ML-010 — _metricas(y_true, y_pred)
- Status: Ativa
- Arquivo: `backend/rating_curve.py`
- Simbolo: `_metricas`
- Assinatura: `_metricas(y_true: np.ndarray, y_pred: np.ndarray) -> dict`
- Objetivo: Calcular métricas de regressão de vazão.
- Funcionamento: R², MAE/RMSE em m³/s e MAE em log10 para valores positivos.
- Entradas: Reais e previstos.
- Saidas: Dicionário de métricas.
- Erros e efeitos: `NaN`/avisos com valores não positivos.
- Dependencias: `numpy`.
- Consumidores: FUN-PY-ML-012.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-ML-011 — _imprimir(rotulo, m)
- Status: Ativa
- Arquivo: `backend/rating_curve.py`
- Simbolo: `_imprimir`
- Assinatura: `_imprimir(rotulo: str, m: dict) -> None`
- Objetivo: Imprimir um bloco de métricas.
- Funcionamento: Formata MAE, RMSE, R², MAE log10 e n.
- Entradas: Rótulo e métricas.
- Saidas: Texto no console.
- Erros e efeitos: Nenhum.
- Dependencias: Nenhuma.
- Consumidores: FUN-PY-ML-012.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-ML-012 — main()
- Status: Ativa
- Arquivo: `backend/rating_curve.py`
- Simbolo: `main`
- Assinatura: `main() -> None`
- Objetivo: Treinar e avaliar a rating curve nível→vazão (RF037).
- Funcionamento: Compara baseline de vazão média AHGN, RF/HGB com `GroupKFold` por estação e RF in-station com split aleatório; imprime importâncias.
- Entradas: Nenhuma.
- Saidas: Métricas no console.
- Erros e efeitos: Exige scikit-learn; sem dados pode falhar.
- Dependencias: FUN-PY-ML-008/009/010/011.
- Consumidores: Execução manual/CLI.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-ML-013 — carregar_trechos(con)
- Status: Ativa
- Arquivo: `backend/treinar_cota_fundo.py`
- Simbolo: `carregar_trechos`
- Assinatura: `carregar_trechos(con: sqlite3.Connection) -> dict`
- Objetivo: Carregar atributos AHGN, geometria e centroides dos trechos.
- Funcionamento: Lê as colunas de `FEATURES`, converte WKB com Shapely e arrays numpy.
- Entradas: Conexão.
- Saidas: `{fids, X, geoms, lon, lat}`.
- Erros e efeitos: Exige Shapely; `ValueError` com atributos nulos.
- Dependencias: `numpy`, `shapely`.
- Consumidores: FUN-PY-ML-018.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-ML-014 — carregar_nos(con)
- Status: Ativa
- Arquivo: `backend/treinar_cota_fundo.py`
- Simbolo: `carregar_nos`
- Assinatura: `carregar_nos(con: sqlite3.Connection) -> tuple[np.ndarray, np.ndarray]`
- Objetivo: Carregar coordenadas e cota de fundo dos nós SICFLOW.
- Funcionamento: `SELECT longitude, latitude, cota_fundo FROM batimetria_sicflow`.
- Entradas: Conexão.
- Saidas: Coordenadas e cota.
- Erros e efeitos: `ValueError` com nulos.
- Dependencias: `numpy`.
- Consumidores: FUN-PY-ML-018.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-ML-015 — associar_cota_fundo(geoms, nos_xy, nos_cf, raio_m)
- Status: Ativa
- Arquivo: `backend/treinar_cota_fundo.py`
- Simbolo: `associar_cota_fundo`
- Assinatura: `associar_cota_fundo(geoms, nos_xy, nos_cf, raio_m: float) -> tuple[np.ndarray, np.ndarray]`
- Objetivo: Rotular cada trecho com a mediana da cota de fundo dos nós no raio.
- Funcionamento: Usa `STRtree.query(..., dwithin)` e mediana; conta nós associados.
- Entradas: Geometrias, nós, cotas e raio.
- Saidas: `(y, n_nos)`; `NaN` sem nós.
- Erros e efeitos: Exige Shapely; raio convertido para graus.
- Dependencias: `shapely`, `numpy`.
- Consumidores: FUN-PY-ML-018.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-ML-016 — _metricas(y_true, y_pred)
- Status: Ativa
- Arquivo: `backend/treinar_cota_fundo.py`
- Simbolo: `_metricas`
- Assinatura: `_metricas(y_true: np.ndarray, y_pred: np.ndarray) -> dict`
- Objetivo: Calcular métricas da regressão de cota de fundo.
- Funcionamento: R², MAE, RMSE, viés e n.
- Entradas: Reais e previstos.
- Saidas: Dicionário de métricas.
- Erros e efeitos: Nenhum.
- Dependencias: `numpy`.
- Consumidores: FUN-PY-ML-018.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-ML-017 — _modelos()
- Status: Ativa
- Arquivo: `backend/treinar_cota_fundo.py`
- Simbolo: `_modelos`
- Assinatura: `_modelos() -> dict`
- Objetivo: Instanciar os modelos candidatos.
- Funcionamento: Retorna `RandomForestRegressor` e `HistGradientBoostingRegressor` com hiperparâmetros fixos.
- Entradas: Nenhuma.
- Saidas: `{rf, hgb}`.
- Erros e efeitos: Exige scikit-learn.
- Dependencias: `sklearn.ensemble`.
- Consumidores: FUN-PY-ML-018.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-ML-018 — main()
- Status: Ativa
- Arquivo: `backend/treinar_cota_fundo.py`
- Simbolo: `main`
- Assinatura: `main() -> None`
- Objetivo: Treinar, avaliar e persistir a cota de fundo por trecho (RF035).
- Funcionamento: Associa rótulos SICFLOW, faz split espacial por célula de 0,5°, compara baseline `hig_drn_elevation_min`, treina RF/HGB, analisa erros e grava `cota_fundo_trecho` para todos os trechos.
- Entradas: `--raio` (1000 m), `--modelo` (ambos), `--nao-persistir`.
- Saidas: Tabela `cota_fundo_trecho` e métricas.
- Erros e efeitos: `INSERT OR REPLACE` (sobrescreve previsões); exige scikit-learn/Shapely.
- Dependencias: FUN-PY-ML-013/014/015/016/017.
- Consumidores: Execução manual/CLI; `gerar_navegabilidade_semanal`.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-ML-019 — carregar_serie(con, codigo)
- Status: Ativa
- Arquivo: `backend/prever_nivel.py`
- Simbolo: `carregar_serie`
- Assinatura: `carregar_serie(con: sqlite3.Connection, codigo: str) -> tuple[np.ndarray, np.ndarray]`
- Objetivo: Carregar a série temporal de nível de uma estação virtual.
- Funcionamento: Lê `data,nivel_m` ordenado e converte datas para `datetime`.
- Entradas: Conexão e código.
- Saidas: Datas e níveis.
- Erros e efeitos: `ValueError` em data inválida.
- Dependencias: `numpy`, `datetime`.
- Consumidores: FUN-PY-ML-023.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-ML-020 — _estacao_padrao(con)
- Status: Ativa
- Arquivo: `backend/prever_nivel.py`
- Simbolo: `_estacao_padrao`
- Assinatura: `_estacao_padrao(con: sqlite3.Connection) -> str`
- Objetivo: Escolher a estação com mais observações.
- Funcionamento: `GROUP BY codigo ORDER BY COUNT(*) DESC LIMIT 1`.
- Entradas: Conexão.
- Saidas: Código.
- Erros e efeitos: `TypeError` se a tabela estiver vazia.
- Dependencias: Nenhuma.
- Consumidores: FUN-PY-ML-023.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-ML-021 — _metricas(y_true, y_pred)
- Status: Ativa
- Arquivo: `backend/prever_nivel.py`
- Simbolo: `_metricas`
- Assinatura: `_metricas(y_true: np.ndarray, y_pred: np.ndarray) -> dict`
- Objetivo: Calcular R², MAE, RMSE e n.
- Funcionamento: Fórmulas sobre resíduos.
- Entradas: Reais e previstos.
- Saidas: Dicionário.
- Erros e efeitos: R² pode ser `NaN`.
- Dependencias: `numpy`.
- Consumidores: FUN-PY-ML-023.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-ML-022 — _imprimir(rotulo, m)
- Status: Ativa
- Arquivo: `backend/prever_nivel.py`
- Simbolo: `_imprimir`
- Assinatura: `_imprimir(rotulo: str, m: dict) -> None`
- Objetivo: Imprimir métricas de previsão.
- Funcionamento: Formata MAE, RMSE, R² e n.
- Entradas: Rótulo e métricas.
- Saidas: Texto.
- Erros e efeitos: Nenhum.
- Dependencias: Nenhuma.
- Consumidores: FUN-PY-ML-023.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-ML-023 — main()
- Status: Ativa
- Arquivo: `backend/prever_nivel.py`
- Simbolo: `main`
- Assinatura: `main() -> None`
- Objetivo: Comparar climatologia mensal e ML na previsão de nível (RF039).
- Funcionamento: Faz split temporal (`ano < ano_teste`), calcula climatologia mensal e treina RF/HGB com sazonalidade cíclica + tendência anual; identifica pico/baixa.
- Entradas: `--codigo`, `--ano_teste` (2024).
- Saidas: Métricas e meses de pico/baixa.
- Erros e efeitos: Retorna sem métricas quando não há dados nos dois períodos; exige scikit-learn.
- Dependencias: FUN-PY-ML-019/020/021/022.
- Consumidores: Execução manual/CLI.
- Testes: Sem teste automatizado identificado.

### GEO

#### FUN-PY-GEO-001 — _float(v)
- Status: Ativa
- Arquivo: `backend/extrair_sondagens_carta.py`
- Simbolo: `_float`
- Assinatura: `_float(v) -> float`
- Objetivo: Converter valores de tags GeoTIFF em float.
- Funcionamento: Chama `float(v)`.
- Entradas: Valor.
- Saidas: Float.
- Erros e efeitos: Propaga `TypeError`/`ValueError`.
- Dependencias: Nenhuma.
- Consumidores: FUN-PY-GEO-002.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-GEO-002 — ler_georef(im)
- Status: Ativa
- Arquivo: `backend/extrair_sondagens_carta.py`
- Simbolo: `ler_georef`
- Assinatura: `ler_georef(im: Image.Image) -> tuple[float, float, float, float]`
- Objetivo: Ler o georreferenciamento de um GeoTIFF.
- Funcionamento: Prioriza `ModelTransformationTag`; senão usa `ModelPixelScaleTag` + `ModelTiepointTag`.
- Entradas: Imagem PIL.
- Saidas: `(scale_x, scale_y, lon_origem, lat_origem)`.
- Erros e efeitos: `ValueError` sem tags/georreferência.
- Dependencias: FUN-PY-GEO-001, `PIL`.
- Consumidores: `main` (FUN-PY-GEO-010).
- Testes: Sem teste automatizado identificado.

#### FUN-PY-GEO-003 — pixel_para_lonlat(col, row, georef)
- Status: Ativa
- Arquivo: `backend/extrair_sondagens_carta.py`
- Simbolo: `pixel_para_lonlat`
- Assinatura: `pixel_para_lonlat(col: int, row: int, georef) -> tuple[float, float]`
- Objetivo: Converter pixel em coordenada geográfica.
- Funcionamento: `lon0 + col*sx`, `lat0 + row*sy`.
- Entradas: Coluna, linha e georreferência.
- Saidas: `(lon, lat)`.
- Erros e efeitos: Nenhum.
- Dependencias: Nenhuma.
- Consumidores: FUN-PY-GEO-006/007.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-GEO-004 — carregar_legenda(caminho)
- Status: Ativa
- Arquivo: `backend/extrair_sondagens_carta.py`
- Simbolo: `carregar_legenda`
- Assinatura: `carregar_legenda(caminho: str | None) -> list[dict]`
- Objetivo: Carregar a legenda cor→profundidade.
- Funcionamento: Lê JSON quando informado; caso contrário usa `LEGENDA_PADRAO`.
- Entradas: Caminho opcional.
- Saidas: Lista de entradas da legenda.
- Erros e efeitos: `OSError`/`json.JSONDecodeError`.
- Dependencias: `json`.
- Consumidores: `main` (FUN-PY-GEO-010).
- Testes: Sem teste automatizado identificado.

#### FUN-PY-GEO-005 — cor_proxima(rgb, legenda, tolerancia)
- Status: Ativa
- Arquivo: `backend/extrair_sondagens_carta.py`
- Simbolo: `cor_proxima`
- Assinatura: `cor_proxima(rgb, legenda: list[dict], tolerancia: float) -> dict | None`
- Objetivo: Encontrar a entrada de legenda mais próxima da cor do pixel.
- Funcionamento: Calcula distância euclidiana RGB e aceita a menor dentro da tolerância.
- Entradas: RGB, legenda e tolerância.
- Saidas: Entrada da legenda ou `None`.
- Erros e efeitos: Exige NumPy.
- Dependencias: `numpy`.
- Consumidores: FUN-PY-GEO-006.
- Testes: Sem teste automatizado identificado.

#### FUN-PY-GEO-006 — amostrar_pontos(img_np, legenda, tolerancia, passo, georef)
- Status: Ativa
- Arquivo: `backend/extrair_sondagens_carta.py`
- Simbolo: `amostrar_pontos`
- Assinatura: `amostrar_pontos(img_np: np.ndarray, legenda, tolerancia, passo, georef) -> list[dict]`
- Objetivo: Amostrar pontos de profundidade em grade.
- Funcionamento: Percorre a imagem com `passo`, classifica a cor e calcula profundidade média da faixa e coordenadas.
- Entradas: Imagem, legenda, tolerância, passo e georreferência.
- Saidas: Lista de pontos.
- Erros e efeitos: Loop Python sobre a grade (pode ser lento em cartas grandes).
- Dependencias: FUN-PY-GEO-003/005.
- Consumidores: `main` (FUN-PY-GEO-010).
- Testes: Sem teste automatizado identificado.

#### FUN-PY-GEO-007 — gerar_areas(img_np, legenda, tolerancia, georef, max_dim=2000)
- Status: Ativa
- Arquivo: `backend/extrair_sondagens_carta.py`
- Simbolo: `gerar_areas`
- Assinatura: `gerar_areas(img_np: np.ndarray, legenda, tolerancia, georef, max_dim=2000) -> list[dict]`
- Objetivo: Extrair polígonos das faixas de profundidade.
- Funcionamento: Redimensiona a imagem acima de `max_dim`, classifica cores, encontra contornos com OpenCV e converte para lon/lat.
- Entradas: Imagem, legenda, tolerância, georreferência e dimensão máxima.
- Saidas: Lista de áreas com coordenadas.
- Erros e efeitos: Exige `cv2`; descarta contornos menores que 20 px².
- Dependencias: FUN-PY-GEO-003, `cv2`.
- Consumidores: `main` (FUN-PY-GEO-010).
- Testes: Sem teste automatizado identificado.

#### FUN-PY-GEO-008 — salvar_geojson(pontos, areas, saida)
- Status: Ativa
- Arquivo: `backend/extrair_sondagens_carta.py`
- Simbolo: `salvar_geojson`
- Assinatura: `salvar_geojson(pontos: list[dict], areas: list[dict], saida: str) -> None`
- Objetivo: Exportar pontos e áreas como FeatureCollection.
- Funcionamento: Monta features `Point`/`Polygon` e escreve JSON UTF-8.
- Entradas: Pontos, áreas e caminho.
- Saidas: Arquivo GeoJSON.
- Erros e efeitos: Sobrescreve o arquivo.
- Dependencias: `json`.
- Consumidores: `main` (FUN-PY-GEO-010).
- Testes: Sem teste automatizado identificado.

#### FUN-PY-GEO-009 — salvar_csv(pontos, saida)
- Status: Ativa
- Arquivo: `backend/extrair_sondagens_carta.py`
- Simbolo: `salvar_csv`
- Assinatura: `salvar_csv(pontos: list[dict], saida: str) -> None`
- Objetivo: Exportar os pontos de sondagem em CSV.
- Funcionamento: Escreve colunas de coordenada/profundidade com `;`.
- Entradas: Pontos e caminho.
- Saidas: Arquivo CSV.
- Erros e efeitos: Sobrescreve o arquivo.
- Dependencias: `csv`.
- Consumidores: `main` (FUN-PY-GEO-010).
- Testes: Sem teste automatizado identificado.

#### FUN-PY-GEO-010 — main()
- Status: Ativa
- Arquivo: `backend/extrair_sondagens_carta.py`
- Simbolo: `main`
- Assinatura: `main() -> None`
- Objetivo: CLI de extração de sondagens de carta náutica.
- Funcionamento: Abre GeoTIFF, lê georreferência, amostra pontos, opcionalmente gera áreas e exporta GeoJSON/CSV.
- Entradas: `carta`, `--legenda`, `--passo`, `--tolerancia`, `--areas`, `--out`.
- Saidas: GeoJSON/CSV e relatório.
- Erros e efeitos: Exige Pillow/NumPy; `cv2` apenas com `--areas`.
- Dependencias: FUN-PY-GEO-002/004/006/007/008/009.
- Consumidores: Execução manual/CLI.
- Testes: Sem teste automatizado identificado.

### ADMIN

#### FUN-PY-ADMIN-001 — main()
- Status: Ativa
- Arquivo: `backend/criar_admin.py`
- Simbolo: `main`
- Assinatura: `main() -> None`
- Objetivo: Criar ou atualizar o primeiro administrador.
- Funcionamento: Exige nome/e-mail, solicita senha (ou `--senha`), valida mínimo de 8 caracteres, garante schema e faz upsert com papel `admin` e `ativo=TRUE`.
- Entradas: `--nome`, `--email`, `--senha`.
- Saidas: Mensagem de confirmação.
- Erros e efeitos: `parser.error` para senha curta; usa `getpass`; grava no PostgreSQL.
- Dependencias: FUN-PY-DATA-002/003, FUN-PY-AUTH-001.
- Consumidores: Execução manual/CLI (bootstrap).
- Testes: Sem teste automatizado identificado.

## TYPESCRIPT

### AUTH

#### FUN-TS-AUTH-001 — lerUsuarioCache()
- Status: Ativa
- Arquivo: `frontend/src/stores/session.ts`
- Simbolo: `lerUsuarioCache`
- Assinatura: `lerUsuarioCache(): Usuario | null`
- Objetivo: Recuperar o usuário do `localStorage` para sessão offline.
- Funcionamento: Lê a chave `hidrowize-usuario` e faz `JSON.parse`; retorna `null` sem registro.
- Entradas: Nenhuma.
- Saidas: Usuário ou `null`.
- Erros e efeitos: Silencia JSON inválido.
- Dependencias: `localStorage`.
- Consumidores: FUN-TS-AUTH-004.
- Testes: `frontend/src/stores/session.spec.ts` (sessão offline).

#### FUN-TS-AUTH-002 — guardarUsuarioCache(usuario)
- Status: Ativa
- Arquivo: `frontend/src/stores/session.ts`
- Simbolo: `guardarUsuarioCache`
- Assinatura: `guardarUsuarioCache(usuario: Usuario | null): void`
- Objetivo: Persistir/limpar o usuário em cache.
- Funcionamento: Serializa em `localStorage` ou remove a chave quando `null`.
- Entradas: Usuário ou `null`.
- Saidas: Nenhuma.
- Erros e efeitos: `QuotaExceededError` não tratado.
- Dependencias: `localStorage`.
- Consumidores: FUN-TS-AUTH-003/004/005/006.
- Testes: `frontend/src/stores/session.spec.ts`.

#### FUN-TS-AUTH-003 — login(email, senha)
- Status: Ativa
- Arquivo: `frontend/src/stores/session.ts`
- Simbolo: `login`
- Assinatura: `login(email: string, senha: string): Promise<Usuario>`
- Objetivo: Autenticar e iniciar a sessão.
- Funcionamento: Chama `api.login`, grava token (`setToken`) e usuário em cache; controla `carregando`.
- Entradas: E-mail e senha.
- Saidas: Usuário autenticado.
- Erros e efeitos: Propaga `ApiProblem`; limpa `carregando` no `finally`.
- Dependencias: FUN-TS-API-001, FUN-TS-HTTP-007, FUN-TS-AUTH-002.
- Consumidores: `frontend/src/views/LoginView.vue` (FUN-TS-UI-015).
- Testes: `frontend/src/stores/session.spec.ts`.

#### FUN-TS-AUTH-004 — restaurar()
- Status: Ativa
- Arquivo: `frontend/src/stores/session.ts`
- Simbolo: `restaurar`
- Assinatura: `restaurar(): Promise<void>`
- Objetivo: Restaurar a sessão no carregamento do app.
- Funcionamento: Sem token retorna; senão consulta `api.me` e atualiza o cache; em 401/403 limpa a sessão; em falha de rede usa o cache.
- Entradas: Nenhuma.
- Saidas: Nenhuma.
- Erros e efeitos: Atualiza `usuario` e `localStorage`.
- Dependencias: FUN-TS-HTTP-006, FUN-TS-API-002, FUN-TS-AUTH-001/002.
- Consumidores: `frontend/src/main.ts`.
- Testes: `frontend/src/stores/session.spec.ts`.

#### FUN-TS-AUTH-005 — logout()
- Status: Ativa
- Arquivo: `frontend/src/stores/session.ts`
- Simbolo: `logout`
- Assinatura: `logout(): void`
- Objetivo: Encerrar a sessão no cliente.
- Funcionamento: Remove token e usuário do `localStorage` e zera o estado.
- Entradas: Nenhuma.
- Saidas: Nenhuma.
- Erros e efeitos: Não chama a API (invalidação é apenas local).
- Dependencias: FUN-TS-HTTP-007, FUN-TS-AUTH-002.
- Consumidores: `frontend/src/layouts/AppLayout.vue`.
- Testes: Sem teste automatizado identificado.

#### FUN-TS-AUTH-006 — atualizarPerfil(input)
- Status: Ativa
- Arquivo: `frontend/src/stores/session.ts`
- Simbolo: `atualizarPerfil`
- Assinatura: `atualizarPerfil(input: PerfilUpdateInput): Promise<Usuario>`
- Objetivo: Atualizar nome/senha do usuário logado.
- Funcionamento: Chama `api.atualizarPerfil`, atualiza estado e cache.
- Entradas: Campos parciais.
- Saidas: Usuário atualizado.
- Erros e efeitos: Propaga erro ao chamador.
- Dependencias: FUN-TS-API-003, FUN-TS-AUTH-002.
- Consumidores: `frontend/src/views/ConfiguracoesView.vue` (FUN-TS-UI-017).
- Testes: `frontend/src/stores/session.spec.ts`.

### API

> Os itens desta seção são os métodos do objeto `api` em `frontend/src/services/endpoints.ts`; cada um é um cliente fino de um endpoint catalogado em `API-END.md`.

#### FUN-TS-API-001 — api.login(email, senha)
- Status: Ativa
- Arquivo: `frontend/src/services/endpoints.ts`
- Simbolo: `api.login`
- Assinatura: `(email: string, senha: string) => Promise<LoginResult>`
- Objetivo: Cliente de `POST /auth/login`.
- Funcionamento: `http.post('/auth/login', { email, senha })`.
- Entradas: E-mail e senha.
- Saidas: `LoginResult`.
- Erros e efeitos: Propaga `ApiProblem`.
- Dependencias: FUN-TS-HTTP-003.
- Consumidores: FUN-TS-AUTH-003.
- Testes: `frontend/src/stores/session.spec.ts`.

#### FUN-TS-API-002 — api.me()
- Status: Ativa
- Arquivo: `frontend/src/services/endpoints.ts`
- Simbolo: `api.me`
- Assinatura: `() => Promise<Usuario>`
- Objetivo: Cliente de `GET /auth/me`.
- Funcionamento: `http.get('/auth/me')`.
- Entradas: Nenhuma (token no header).
- Saidas: `Usuario`.
- Erros e efeitos: Propaga `ApiProblem`.
- Dependencias: FUN-TS-HTTP-002.
- Consumidores: FUN-TS-AUTH-004.
- Testes: `frontend/src/stores/session.spec.ts`.

#### FUN-TS-API-003 — api.atualizarPerfil(payload)
- Status: Ativa
- Arquivo: `frontend/src/services/endpoints.ts`
- Simbolo: `api.atualizarPerfil`
- Assinatura: `(payload: PerfilUpdateInput) => Promise<Usuario>`
- Objetivo: Cliente de `PUT /auth/me`.
- Funcionamento: `http.put('/auth/me', payload)`.
- Entradas: Campos parciais.
- Saidas: `Usuario`.
- Erros e efeitos: Propaga `ApiProblem`.
- Dependencias: FUN-TS-HTTP-004.
- Consumidores: FUN-TS-AUTH-006.
- Testes: `frontend/src/stores/session.spec.ts`.

#### FUN-TS-API-004 — api.listarUsuarios()
- Status: Ativa
- Arquivo: `frontend/src/services/endpoints.ts`
- Simbolo: `api.listarUsuarios`
- Assinatura: `() => Promise<ListaUsuarios>`
- Objetivo: Cliente de `GET /usuarios`.
- Funcionamento: `http.get('/usuarios')`.
- Entradas: Nenhuma.
- Saidas: `ListaUsuarios`.
- Erros e efeitos: Propaga erro (403 para piloto).
- Dependencias: FUN-TS-HTTP-002.
- Consumidores: `frontend/src/views/admin/UsuariosView.vue` (FUN-TS-UI-018).
- Testes: Sem teste automatizado identificado.

#### FUN-TS-API-005 — api.criarUsuario(payload)
- Status: Ativa
- Arquivo: `frontend/src/services/endpoints.ts`
- Simbolo: `api.criarUsuario`
- Assinatura: `(payload: CriarUsuarioInput) => Promise<Usuario>`
- Objetivo: Cliente de `POST /usuarios`.
- Funcionamento: `http.post('/usuarios', payload)`.
- Entradas: Dados do novo usuário.
- Saidas: `Usuario`.
- Erros e efeitos: Propaga `409`/`422`.
- Dependencias: FUN-TS-HTTP-003.
- Consumidores: FUN-TS-UI-019.
- Testes: Sem teste automatizado identificado.

#### FUN-TS-API-006 — api.atualizarUsuario(id, payload)
- Status: Ativa
- Arquivo: `frontend/src/services/endpoints.ts`
- Simbolo: `api.atualizarUsuario`
- Assinatura: `(id: number, payload: AtualizarUsuarioInput) => Promise<Usuario>`
- Objetivo: Cliente de `PUT /usuarios/{id}`.
- Funcionamento: `http.put(`/usuarios/${id}`, payload)`.
- Entradas: ID e campos.
- Saidas: `Usuario`.
- Erros e efeitos: Propaga `404`/`422`.
- Dependencias: FUN-TS-HTTP-004.
- Consumidores: FUN-TS-UI-020/021.
- Testes: Sem teste automatizado identificado.

#### FUN-TS-API-007 — api.desativarUsuario(id)
- Status: Ativa
- Arquivo: `frontend/src/services/endpoints.ts`
- Simbolo: `api.desativarUsuario`
- Assinatura: `(id: number) => Promise<{ id: number; ativo: boolean }>`
- Objetivo: Cliente de `DELETE /usuarios/{id}`.
- Funcionamento: `http.delete(...)`.
- Entradas: ID.
- Saidas: `{id, ativo}`.
- Erros e efeitos: Propaga `404`.
- Dependencias: FUN-TS-HTTP-005.
- Consumidores: FUN-TS-UI-021.
- Testes: Sem teste automatizado identificado.

#### FUN-TS-API-008 — api.listarEstacoes()
- Status: Ativa
- Arquivo: `frontend/src/services/endpoints.ts`
- Simbolo: `api.listarEstacoes`
- Assinatura: `() => Promise<ListaEstacoes>`
- Objetivo: Cliente de `GET /estacoes`.
- Funcionamento: `http.get('/estacoes')`.
- Entradas: Nenhuma.
- Saidas: `ListaEstacoes`.
- Erros e efeitos: Propaga erro de rede/API.
- Dependencias: FUN-TS-HTTP-002.
- Consumidores: FUN-TS-DATA-002, FUN-TS-OFFLINE-005.
- Testes: `frontend/src/stores/estacoes.spec.ts`, `frontend/src/stores/offline.spec.ts`.

#### FUN-TS-API-009 - api.coletarNiveis(payload)
- Status: Ativa
- Arquivo: `frontend/src/services/endpoints.ts`
- Simbolo: `api.coletarNiveis`
- Assinatura: `(payload: ColetaInput) => Promise<ColetaJob>`
- Objetivo: Cliente de `POST /niveis/coletar`.
- Funcionamento: `http.post('/niveis/coletar', payload)`.
- Entradas: Estações e período.
- Saidas: `ColetaJob` (HTTP 202).
- Erros e efeitos: Propaga `ApiProblem` (401/403/409/422).
- Dependencias: FUN-TS-HTTP-003.
- Consumidores: FUN-TS-UI-022.
- Testes: Sem teste automatizado identificado.

#### FUN-TS-API-010 — api.grafoStatus()
- Status: Ativa
- Arquivo: `frontend/src/services/endpoints.ts`
- Simbolo: `api.grafoStatus`
- Assinatura: `() => Promise<GrafoStatus>`
- Objetivo: Cliente de `GET /grafo/status`.
- Funcionamento: `http.get('/grafo/status')`.
- Entradas: Nenhuma.
- Saidas: `GrafoStatus`.
- Erros e efeitos: Propaga erro.
- Dependencias: FUN-TS-HTTP-002.
- Consumidores: Nenhum identificado no frontend atual.
- Testes: Sem teste automatizado identificado.

#### FUN-TS-API-011 — api.listarLogs(limite=100)
- Status: Ativa
- Arquivo: `frontend/src/services/endpoints.ts`
- Simbolo: `api.listarLogs`
- Assinatura: `(limite = 100) => Promise<ListaLogs>`
- Objetivo: Cliente de `GET /logs`.
- Funcionamento: `http.get(`/logs?limite=${limite}`)`.
- Entradas: Limite.
- Saidas: `ListaLogs`.
- Erros e efeitos: Propaga erro (403 para piloto).
- Dependencias: FUN-TS-HTTP-002.
- Consumidores: `frontend/src/views/admin/LogsView.vue` (FUN-TS-UI-023).
- Testes: Sem teste automatizado identificado.

#### FUN-TS-API-012 — api.calcularRota(payload)
- Status: Ativa
- Arquivo: `frontend/src/services/endpoints.ts`
- Simbolo: `api.calcularRota`
- Assinatura: `(payload: RouteRequest) => Promise<RouteResult>`
- Objetivo: Cliente de `POST /rotas/calcular`.
- Funcionamento: `http.post('/rotas/calcular', payload)`.
- Entradas: Origem/destino/calado/margem/velocidade.
- Saidas: `RouteResult`.
- Erros e efeitos: Propaga `422`/`404`.
- Dependencias: FUN-TS-HTTP-003.
- Consumidores: FUN-TS-ROUTE-004.
- Testes: `frontend/src/stores/rota.spec.ts`.

#### FUN-TS-API-013 — api.salvarRota(payload)
- Status: Ativa
- Arquivo: `frontend/src/services/endpoints.ts`
- Simbolo: `api.salvarRota`
- Assinatura: `(payload: SalvarRotaInput) => Promise<RotaSalva>`
- Objetivo: Cliente de `POST /rotas`.
- Funcionamento: `http.post('/rotas', payload)`.
- Entradas: Rota completa.
- Saidas: `RotaSalva`.
- Erros e efeitos: Propaga `401`.
- Dependencias: FUN-TS-HTTP-003.
- Consumidores: FUN-TS-ROUTE-005, FUN-TS-OFFLINE-004.
- Testes: `frontend/src/stores/rota.spec.ts`, `frontend/src/stores/offline.spec.ts`.

#### FUN-TS-API-014 — api.listarRotas()
- Status: Ativa
- Arquivo: `frontend/src/services/endpoints.ts`
- Simbolo: `api.listarRotas`
- Assinatura: `() => Promise<ListaRotas>`
- Objetivo: Cliente de `GET /rotas`.
- Funcionamento: `http.get('/rotas')`.
- Entradas: Nenhuma.
- Saidas: `ListaRotas`.
- Erros e efeitos: Propaga `401`.
- Dependencias: FUN-TS-HTTP-002.
- Consumidores: FUN-TS-ROUTE-006, FUN-TS-OFFLINE-005, FUN-TS-NOTIFY-004.
- Testes: `frontend/src/stores/rota.spec.ts`, `frontend/src/stores/offline.spec.ts`.

#### FUN-TS-API-015 — api.obterRota(id)
- Status: Ativa
- Arquivo: `frontend/src/services/endpoints.ts`
- Simbolo: `api.obterRota`
- Assinatura: `(id: number) => Promise<RotaSalva>`
- Objetivo: Cliente de `GET /rotas/{id}`.
- Funcionamento: `http.get(`/rotas/${id}`)`.
- Entradas: ID.
- Saidas: `RotaSalva`.
- Erros e efeitos: Propaga `404`.
- Dependencias: FUN-TS-HTTP-002.
- Consumidores: Nenhum identificado no frontend atual (o histórico usa a lista).
- Testes: Sem teste automatizado identificado.

#### FUN-TS-API-016 — api.removerRota(id)
- Status: Ativa
- Arquivo: `frontend/src/services/endpoints.ts`
- Simbolo: `api.removerRota`
- Assinatura: `(id: number) => Promise<{ id: number; removida: boolean }>`
- Objetivo: Cliente de `DELETE /rotas/{id}`.
- Funcionamento: `http.delete(...)`.
- Entradas: ID.
- Saidas: `{id, removida}`.
- Erros e efeitos: Propaga `404`.
- Dependencias: FUN-TS-HTTP-005.
- Consumidores: FUN-TS-ROUTE-007.
- Testes: `frontend/src/stores/rota.spec.ts`.

#### FUN-TS-API-017 — api.monitorarRota(id, monitorar)
- Status: Ativa
- Arquivo: `frontend/src/services/endpoints.ts`
- Simbolo: `api.monitorarRota`
- Assinatura: `(id: number, monitorar: boolean) => Promise<MonitorResultado>`
- Objetivo: Cliente de `POST /rotas/{id}/monitorar`.
- Funcionamento: `http.post(`/rotas/${id}/monitorar`, { monitorar })`.
- Entradas: ID e flag.
- Saidas: `MonitorResultado`.
- Erros e efeitos: Propaga erro.
- Dependencias: FUN-TS-HTTP-003.
- Consumidores: FUN-TS-ROUTE-008.
- Testes: `frontend/src/stores/rota.spec.ts`.

#### FUN-TS-API-018 — api.listarAlteracoes(id)
- Status: Ativa
- Arquivo: `frontend/src/services/endpoints.ts`
- Simbolo: `api.listarAlteracoes`
- Assinatura: `(id: number) => Promise<ListaAlteracoes>`
- Objetivo: Cliente de `GET /rotas/{id}/alteracoes`.
- Funcionamento: `http.get(`/rotas/${id}/alteracoes`)`.
- Entradas: ID.
- Saidas: `ListaAlteracoes`.
- Erros e efeitos: Propaga `404`.
- Dependencias: FUN-TS-HTTP-002.
- Consumidores: FUN-TS-ROUTE-009, FUN-TS-NOTIFY-004, FUN-TS-UI-026.
- Testes: `frontend/src/stores/rota.spec.ts`, `frontend/src/stores/notificacao.spec.ts`.

#### FUN-TS-API-019 — api.snapshot(bbox?)
- Status: Ativa
- Arquivo: `frontend/src/services/endpoints.ts`
- Simbolo: `api.snapshot`
- Assinatura: `(bbox?: string) => Promise<SnapshotGrafo>`
- Objetivo: Cliente de `GET /sync/snapshot`.
- Funcionamento: `http.get('/sync/snapshot' + ?bbox=...)`.
- Entradas: Bbox opcional.
- Saidas: `SnapshotGrafo`.
- Erros e efeitos: Propaga `401`/`422`.
- Dependencias: FUN-TS-HTTP-002.
- Consumidores: FUN-TS-OFFLINE-002.
- Testes: `frontend/src/stores/offline.spec.ts`.

#### FUN-TS-API-020 - api.statusColeta(jobId)
- Status: Ativa
- Arquivo: `frontend/src/services/endpoints.ts`
- Simbolo: `api.statusColeta`
- Assinatura: `(jobId: string) => Promise<ColetaJob>`
- Objetivo: Cliente de `GET /niveis/coletar/{jobId}`.
- Funcionamento: `http.get('/niveis/coletar/{jobId}')`.
- Entradas: ID do job.
- Saidas: `ColetaJob`.
- Erros e efeitos: Propaga `ApiProblem`.
- Dependencias: FUN-TS-HTTP-002.
- Consumidores: FUN-TS-UI-039.
- Testes: Sem teste automatizado identificado.

### HTTP

#### FUN-TS-HTTP-001 — request<T>(path, options)
- Status: Ativa
- Arquivo: `frontend/src/services/http.ts`
- Simbolo: `request`
- Assinatura: `request<T>(path: string, options: RequestOptions = {}): Promise<T>`
- Objetivo: Centralizar chamadas HTTP e desembalar o envelope da API.
- Funcionamento: Monta headers, anexa Bearer do `localStorage`, faz `fetch` em `apiBaseUrl`, interpreta JSON e lança `ApiProblem` quando `success` é falso.
- Entradas: Caminho, método, corpo e `AbortSignal`.
- Saidas: `data` tipado.
- Erros e efeitos: `ApiProblem("invalid_response")` para JSON inválido; `ApiProblem` com código/status do backend.
- Dependencias: FUN-TS-HTTP-006, FUN-TS-HTTP-008.
- Consumidores: FUN-TS-HTTP-002/003/004/005.
- Testes: `frontend/src/services/http.spec.ts`.

#### FUN-TS-HTTP-002 — get<T>(path, options?)
- Status: Ativa
- Arquivo: `frontend/src/services/http.ts`
- Simbolo: `get`
- Assinatura: `get<T>(path: string, options?): Promise<T>`
- Objetivo: Atalho para GET.
- Funcionamento: Delega a `request` com `method: 'GET'`.
- Entradas: Caminho e opções.
- Saidas: Dados.
- Erros e efeitos: Herda de `request`.
- Dependencias: FUN-TS-HTTP-001.
- Consumidores: Funções `api.*` de leitura.
- Testes: `frontend/src/services/http.spec.ts`.

#### FUN-TS-HTTP-003 — post<T>(path, body?, options?)
- Status: Ativa
- Arquivo: `frontend/src/services/http.ts`
- Simbolo: `post`
- Assinatura: `post<T>(path: string, body?: unknown, options?): Promise<T>`
- Objetivo: Atalho para POST com corpo JSON.
- Funcionamento: Delega a `request` com `method: 'POST'`.
- Entradas: Caminho e corpo.
- Saidas: Dados.
- Erros e efeitos: Herda de `request`.
- Dependencias: FUN-TS-HTTP-001.
- Consumidores: Funções `api.*` de escrita.
- Testes: `frontend/src/services/http.spec.ts`.

#### FUN-TS-HTTP-004 — put<T>(path, body?, options?)
- Status: Ativa
- Arquivo: `frontend/src/services/http.ts`
- Simbolo: `put`
- Assinatura: `put<T>(path: string, body?: unknown, options?): Promise<T>`
- Objetivo: Atalho para PUT.
- Funcionamento: Delega a `request` com `method: 'PUT'`.
- Entradas: Caminho e corpo.
- Saidas: Dados.
- Erros e efeitos: Herda de `request`.
- Dependencias: FUN-TS-HTTP-001.
- Consumidores: `api.atualizarPerfil`, `api.atualizarUsuario`.
- Testes: `frontend/src/services/http.spec.ts`.

#### FUN-TS-HTTP-005 — delete<T>(path, options?)
- Status: Ativa
- Arquivo: `frontend/src/services/http.ts`
- Simbolo: `delete`
- Assinatura: `delete<T>(path: string, options?): Promise<T>`
- Objetivo: Atalho para DELETE.
- Funcionamento: Delega a `request` com `method: 'DELETE'`.
- Entradas: Caminho.
- Saidas: Dados.
- Erros e efeitos: Herda de `request`.
- Dependencias: FUN-TS-HTTP-001.
- Consumidores: `api.desativarUsuario`, `api.removerRota`.
- Testes: `frontend/src/services/http.spec.ts`.

#### FUN-TS-HTTP-006 — getToken()
- Status: Ativa
- Arquivo: `frontend/src/services/http.ts`
- Simbolo: `getToken`
- Assinatura: `getToken(): string | null`
- Objetivo: Ler o token de acesso do `localStorage`.
- Funcionamento: Retorna `hidrowize-access-token`.
- Entradas: Nenhuma.
- Saidas: Token ou `null`.
- Erros e efeitos: Nenhum.
- Dependencias: `localStorage`.
- Consumidores: FUN-TS-HTTP-001, FUN-TS-AUTH-004, FUN-TS-NOTIFY-008.
- Testes: `frontend/src/services/http.spec.ts`.

#### FUN-TS-HTTP-007 — setToken(token)
- Status: Ativa
- Arquivo: `frontend/src/services/http.ts`
- Simbolo: `setToken`
- Assinatura: `setToken(token: string | null): void`
- Objetivo: Gravar/limpar o token.
- Funcionamento: `setItem` quando há token; `removeItem` quando `null`.
- Entradas: Token ou `null`.
- Saidas: Nenhuma.
- Erros e efeitos: Nenhum.
- Dependencias: `localStorage`.
- Consumidores: FUN-TS-AUTH-003/005.
- Testes: `frontend/src/services/http.spec.ts`.

#### FUN-TS-HTTP-008 — ApiProblem(code, message, status)
- Status: Ativa
- Arquivo: `frontend/src/services/http.ts`
- Simbolo: `ApiProblem`
- Assinatura: `constructor(code: string, message: string, status: number)`
- Objetivo: Representar erro de API no cliente.
- Funcionamento: Estende `Error`, define `name = 'ApiProblem'` e guarda `code`/`status`.
- Entradas: Código, mensagem e status.
- Saidas: Instância de erro.
- Erros e efeitos: Nenhum.
- Dependencias: Nenhuma.
- Consumidores: FUN-TS-HTTP-001, stores e views que tratam erros.
- Testes: `frontend/src/services/http.spec.ts`.

### CACHE

#### FUN-TS-CACHE-001 — guardarEstacoes(itens)
- Status: Ativa
- Arquivo: `frontend/src/services/cache.ts`
- Simbolo: `guardarEstacoes`
- Assinatura: `guardarEstacoes(itens: Estacao[]): Promise<void>`
- Objetivo: Substituir o snapshot local de estações.
- Funcionamento: Transação `rw`, `clear` e `bulkPut` na tabela `estacoes`.
- Entradas: Estações.
- Saidas: `Promise<void>`.
- Erros e efeitos: Propaga erro do Dexie.
- Dependencias: FUN-TS-DATA-001.
- Consumidores: FUN-TS-DATA-002, FUN-TS-OFFLINE-005.
- Testes: `frontend/src/services/cache.spec.ts`.

#### FUN-TS-CACHE-002 — lerEstacoes()
- Status: Ativa
- Arquivo: `frontend/src/services/cache.ts`
- Simbolo: `lerEstacoes`
- Assinatura: `lerEstacoes(): Promise<Estacao[]>`
- Objetivo: Ler as estações do cache.
- Funcionamento: `db.estacoes.toArray()`.
- Entradas: Nenhuma.
- Saidas: Estações.
- Erros e efeitos: Propaga erro do Dexie.
- Dependencias: FUN-TS-DATA-001.
- Consumidores: FUN-TS-DATA-002.
- Testes: `frontend/src/services/cache.spec.ts`.

#### FUN-TS-CACHE-003 — guardarRotas(itens)
- Status: Ativa
- Arquivo: `frontend/src/services/cache.ts`
- Simbolo: `guardarRotas`
- Assinatura: `guardarRotas(itens: RotaSalva[]): Promise<void>`
- Objetivo: Substituir o snapshot local de rotas.
- Funcionamento: Transação `rw`, `clear` e `bulkPut`.
- Entradas: Rotas.
- Saidas: `Promise<void>`.
- Erros e efeitos: Propaga erro do Dexie.
- Dependencias: FUN-TS-DATA-001.
- Consumidores: FUN-TS-ROUTE-006, FUN-TS-OFFLINE-005.
- Testes: `frontend/src/services/cache.spec.ts`.

#### FUN-TS-CACHE-004 — lerRotas()
- Status: Ativa
- Arquivo: `frontend/src/services/cache.ts`
- Simbolo: `lerRotas`
- Assinatura: `lerRotas(): Promise<RotaSalva[]>`
- Objetivo: Ler rotas do cache em ordem decrescente de criação.
- Funcionamento: `orderBy('created_at').reverse().toArray()`.
- Entradas: Nenhuma.
- Saidas: Rotas.
- Erros e efeitos: Propaga erro do Dexie.
- Dependencias: FUN-TS-DATA-001.
- Consumidores: FUN-TS-ROUTE-006.
- Testes: `frontend/src/services/cache.spec.ts`.

#### FUN-TS-CACHE-005 — enfileirarRota(payload)
- Status: Ativa
- Arquivo: `frontend/src/services/cache.ts`
- Simbolo: `enfileirarRota`
- Assinatura: `enfileirarRota(payload: SalvarRotaInput): Promise<number>`
- Objetivo: Enfileirar rota pendente de envio.
- Funcionamento: `db.pendentes.add({payload, criado_em})`.
- Entradas: Payload.
- Saidas: ID gerado.
- Erros e efeitos: Propaga erro do Dexie.
- Dependencias: FUN-TS-DATA-001.
- Consumidores: FUN-TS-OFFLINE-003.
- Testes: `frontend/src/services/cache.spec.ts`.

#### FUN-TS-CACHE-006 — lerPendentes()
- Status: Ativa
- Arquivo: `frontend/src/services/cache.ts`
- Simbolo: `lerPendentes`
- Assinatura: `lerPendentes(): Promise<RotaPendente[]>`
- Objetivo: Listar a fila de rotas pendentes em ordem de chegada.
- Funcionamento: `orderBy('id').toArray()`.
- Entradas: Nenhuma.
- Saidas: Pendentes.
- Erros e efeitos: Propaga erro do Dexie.
- Dependencias: FUN-TS-DATA-001.
- Consumidores: FUN-TS-OFFLINE-004.
- Testes: `frontend/src/services/cache.spec.ts`.

#### FUN-TS-CACHE-007 — removerPendente(id)
- Status: Ativa
- Arquivo: `frontend/src/services/cache.ts`
- Simbolo: `removerPendente`
- Assinatura: `removerPendente(id: number): Promise<void>`
- Objetivo: Remover item da fila após envio.
- Funcionamento: `db.pendentes.delete(id)`.
- Entradas: ID.
- Saidas: `Promise<void>`.
- Erros e efeitos: Propaga erro do Dexie.
- Dependencias: FUN-TS-DATA-001.
- Consumidores: FUN-TS-OFFLINE-004.
- Testes: `frontend/src/services/cache.spec.ts`.

#### FUN-TS-CACHE-008 — contarPendentes()
- Status: Ativa
- Arquivo: `frontend/src/services/cache.ts`
- Simbolo: `contarPendentes`
- Assinatura: `contarPendentes(): Promise<number>`
- Objetivo: Contar rotas pendentes.
- Funcionamento: `db.pendentes.count()`.
- Entradas: Nenhuma.
- Saidas: Número.
- Erros e efeitos: Propaga erro do Dexie.
- Dependencias: FUN-TS-DATA-001.
- Consumidores: FUN-TS-OFFLINE-001/003/005.
- Testes: `frontend/src/services/cache.spec.ts`.

#### FUN-TS-CACHE-009 — guardarUltimaSincronizacao(valor)
- Status: Ativa
- Arquivo: `frontend/src/services/cache.ts`
- Simbolo: `guardarUltimaSincronizacao`
- Assinatura: `guardarUltimaSincronizacao(valor: string): Promise<void>`
- Objetivo: Persistir o instante da última sincronização.
- Funcionamento: `db.meta.put({chave: 'ultima_sincronizacao', valor})`.
- Entradas: Data ISO.
- Saidas: `Promise<void>`.
- Erros e efeitos: Propaga erro do Dexie.
- Dependencias: FUN-TS-DATA-001.
- Consumidores: FUN-TS-OFFLINE-005.
- Testes: `frontend/src/services/cache.spec.ts`.

#### FUN-TS-CACHE-010 — lerUltimaSincronizacao()
- Status: Ativa
- Arquivo: `frontend/src/services/cache.ts`
- Simbolo: `lerUltimaSincronizacao`
- Assinatura: `lerUltimaSincronizacao(): Promise<string | null>`
- Objetivo: Ler o instante da última sincronização.
- Funcionamento: Consulta a tabela `meta`.
- Entradas: Nenhuma.
- Saidas: Data ISO ou `null`.
- Erros e efeitos: Propaga erro do Dexie.
- Dependencias: FUN-TS-DATA-001.
- Consumidores: FUN-TS-OFFLINE-001.
- Testes: `frontend/src/services/cache.spec.ts`.

#### FUN-TS-CACHE-011 — limparCache()
- Status: Ativa
- Arquivo: `frontend/src/services/cache.ts`
- Simbolo: `limparCache`
- Assinatura: `limparCache(): Promise<void>`
- Objetivo: Limpar todos os dados locais.
- Funcionamento: Transação `rw` e `clear` em estações, rotas, pendentes, meta e grafo.
- Entradas: Nenhuma.
- Saidas: `Promise<void>`.
- Erros e efeitos: Operação destrutiva local; propaga erro do Dexie.
- Dependencias: FUN-TS-DATA-001.
- Consumidores: Nenhum identificado no frontend atual.
- Testes: Sem teste automatizado identificado.

#### FUN-TS-CACHE-012 — guardarSnapshot(dados, geradoEm)
- Status: Ativa
- Arquivo: `frontend/src/services/cache.ts`
- Simbolo: `guardarSnapshot`
- Assinatura: `guardarSnapshot(dados: SnapshotGrafo, geradoEm: string): Promise<void>`
- Objetivo: Persistir o snapshot do grafo para uso offline.
- Funcionamento: `db.grafo.put({chave:'atual', gerado_em, dados})`.
- Entradas: Snapshot e timestamp.
- Saidas: `Promise<void>`.
- Erros e efeitos: Substitui o snapshot anterior; propaga erro do Dexie.
- Dependencias: FUN-TS-DATA-001.
- Consumidores: FUN-TS-OFFLINE-002.
- Testes: Sem teste automatizado identificado.

#### FUN-TS-CACHE-013 — lerSnapshot()
- Status: Ativa
- Arquivo: `frontend/src/services/cache.ts`
- Simbolo: `lerSnapshot`
- Assinatura: `lerSnapshot(): Promise<SnapshotArmazenado | undefined>`
- Objetivo: Ler o snapshot local.
- Funcionamento: `db.grafo.get('atual')`.
- Entradas: Nenhuma.
- Saidas: Snapshot armazenado ou `undefined`.
- Erros e efeitos: Propaga erro do Dexie.
- Dependencias: FUN-TS-DATA-001.
- Consumidores: FUN-TS-ROUTE-003, FUN-TS-OFFLINE-001.
- Testes: `frontend/src/services/cache.spec.ts` (indireto).

### DATA

#### FUN-TS-DATA-001 — YgapeDatabase (constructor)
- Status: Ativa
- Arquivo: `frontend/src/db/index.ts`
- Simbolo: `YgapeDatabase`
- Assinatura: `constructor()` (classes `YgapeDatabase`, tabelas `estacoes`, `rotas`, `pendentes`, `meta`, `grafo`)
- Objetivo: Definir o banco IndexedDB via Dexie.
- Funcionamento: Abre `ygape-offline`; versão 1 cria estações/rotas/pendentes/meta; versão 2 adiciona `grafo`.
- Entradas: Nenhuma.
- Saidas: Instância exportada `db`.
- Erros e efeitos: Cria/atualiza schema local no primeiro acesso.
- Dependencias: `dexie`.
- Consumidores: `frontend/src/services/cache.ts` (todos os FUN-TS-CACHE).
- Testes: `frontend/src/services/cache.spec.ts`.

#### FUN-TS-DATA-002 — carregar(forcar=false)
- Status: Ativa
- Arquivo: `frontend/src/stores/estacoes.ts`
- Simbolo: `carregar`
- Assinatura: `carregar(forcar = false): Promise<void>`
- Objetivo: Carregar estações da API com fallback para o cache.
- Funcionamento: Evita recarga quando já carregado; em sucesso marca `doCache=false` e grava o snapshot; em falha usa o cache e, sem cache, define mensagem de erro.
- Entradas: Flag de recarga.
- Saidas: Nenhuma.
- Erros e efeitos: Não propaga erro (registra em `erro`); grava cache em background.
- Dependencias: FUN-TS-API-008, FUN-TS-CACHE-001/002.
- Consumidores: `MapaView`, `RotaNovaView`, `HistoricoView`, `RiverMap` (via props).
- Testes: `frontend/src/stores/estacoes.spec.ts`.

### ROUTE

#### FUN-TS-ROUTE-001 — mensagemErro(erro, padrao)
- Status: Ativa
- Arquivo: `frontend/src/stores/rota.ts`
- Simbolo: `mensagemErro`
- Assinatura: `mensagemErro(erro: unknown, padrao: string): string`
- Objetivo: Extrair mensagem de `ApiProblem` ou usar fallback.
- Funcionamento: `erro instanceof ApiProblem ? erro.message : padrao`.
- Entradas: Erro e texto padrão.
- Saidas: Mensagem.
- Erros e efeitos: Nenhum.
- Dependencias: FUN-TS-HTTP-008.
- Consumidores: FUN-TS-ROUTE-004/006/007/008/009.
- Testes: `frontend/src/stores/rota.spec.ts` (indireto).

#### FUN-TS-ROUTE-002 — montarPayload(r)
- Status: Ativa
- Arquivo: `frontend/src/stores/rota.ts`
- Simbolo: `montarPayload`
- Assinatura: `montarPayload(r: RouteResult): SalvarRotaInput`
- Objetivo: Converter resultado calculado no payload de salvamento.
- Funcionamento: Copia parâmetros atuais e métricas do resultado, incluindo GeoJSON e `monitorar`.
- Entradas: Resultado da rota.
- Saidas: `SalvarRotaInput`.
- Erros e efeitos: Nenhum.
- Dependencias: `RouteResult`, `SalvarRotaInput`.
- Consumidores: FUN-TS-ROUTE-005.
- Testes: `frontend/src/stores/rota.spec.ts` (indireto).

#### FUN-TS-ROUTE-003 — calcularOfflineSePossivel()
- Status: Ativa
- Arquivo: `frontend/src/stores/rota.ts`
- Simbolo: `calcularOfflineSePossivel`
- Assinatura: `calcularOfflineSePossivel(): Promise<RouteResult | null>`
- Objetivo: Tentar calcular a rota localmente com o snapshot.
- Funcionamento: Lê o snapshot, resolve origem/destino por nome nas estações carregadas e chama `calcularOffline`.
- Entradas: Nenhuma.
- Saidas: Resultado ou `null` sem snapshot/estação.
- Erros e efeitos: Exige estações em memória (`useEstacoesStore`).
- Dependencias: FUN-TS-CACHE-013, FUN-TS-ROUTE-012.
- Consumidores: FUN-TS-ROUTE-004.
- Testes: `frontend/src/stores/rota.spec.ts`.

#### FUN-TS-ROUTE-004 — calcular()
- Status: Ativa
- Arquivo: `frontend/src/stores/rota.ts`
- Simbolo: `calcular`
- Assinatura: `calcular(): Promise<void>`
- Objetivo: Calcular a rota pela API com fallback offline.
- Funcionamento: Chama `api.calcularRota`; em erro de rede (não `ApiProblem`) tenta o cálculo offline; caso contrário registra a mensagem.
- Entradas: `parametros` do store.
- Saidas: Nenhuma (atualiza `resultado`/`erro`).
- Erros e efeitos: Falha de rede aciona fallback; erros de API não.
- Dependencias: FUN-TS-API-012, FUN-TS-ROUTE-003/001.
- Consumidores: `frontend/src/views/RotaNovaView.vue`.
- Testes: `frontend/src/stores/rota.spec.ts`.

#### FUN-TS-ROUTE-005 — salvar()
- Status: Ativa
- Arquivo: `frontend/src/stores/rota.ts`
- Simbolo: `salvar`
- Assinatura: `salvar(): Promise<RotaSalva | null>`
- Objetivo: Salvar a rota no histórico, com fila offline.
- Funcionamento: Exige resultado, monta payload, chama a API; em falha de rede enfileira e marca `salvoLocal`; erro de API é exibido.
- Entradas: Nenhuma.
- Saidas: Rota salva ou `null`.
- Erros e efeitos: Atualiza `historico`; grava em IndexedDB quando offline.
- Dependencias: FUN-TS-API-013, FUN-TS-ROUTE-002/001, FUN-TS-OFFLINE-003.
- Consumidores: `frontend/src/views/RotaNovaView.vue`.
- Testes: `frontend/src/stores/rota.spec.ts`.

#### FUN-TS-ROUTE-006 — carregarHistorico()
- Status: Ativa
- Arquivo: `frontend/src/stores/rota.ts`
- Simbolo: `carregarHistorico`
- Assinatura: `carregarHistorico(): Promise<void>`
- Objetivo: Carregar o histórico do usuário com fallback de cache.
- Funcionamento: Chama `api.listarRotas`, grava o cache; em falha usa `lerRotas` e marca `historicoDoCache`.
- Entradas: Nenhuma.
- Saidas: Nenhuma.
- Erros e efeitos: Atualiza `erroHistorico` sem propagar.
- Dependencias: FUN-TS-API-014, FUN-TS-CACHE-003/004, FUN-TS-ROUTE-001.
- Consumidores: `frontend/src/views/HistoricoView.vue`.
- Testes: `frontend/src/stores/rota.spec.ts`.

#### FUN-TS-ROUTE-007 — remover(id)
- Status: Ativa
- Arquivo: `frontend/src/stores/rota.ts`
- Simbolo: `remover`
- Assinatura: `remover(id: number): Promise<boolean>`
- Objetivo: Remover rota do histórico.
- Funcionamento: Chama `api.removerRota` e filtra a lista local; em erro registra mensagem.
- Entradas: ID.
- Saidas: `true` em sucesso; `false` em erro.
- Erros e efeitos: Não remove do cache local explicitamente.
- Dependencias: FUN-TS-API-016, FUN-TS-ROUTE-001.
- Consumidores: `frontend/src/views/HistoricoView.vue` (FUN-TS-UI-029).
- Testes: `frontend/src/stores/rota.spec.ts`.

#### FUN-TS-ROUTE-008 — monitorar(id, valor)
- Status: Ativa
- Arquivo: `frontend/src/stores/rota.ts`
- Simbolo: `monitorar`
- Assinatura: `monitorar(id: number, valor: boolean): Promise<MonitorResultado | null>`
- Objetivo: Ativar/desativar monitoramento de uma rota salva.
- Funcionamento: Chama `api.monitorarRota` e atualiza `item.monitorar` no histórico.
- Entradas: ID e flag.
- Saidas: Resultado ou `null` em erro.
- Erros e efeitos: Atualiza `erroHistorico`.
- Dependencias: FUN-TS-API-017, FUN-TS-ROUTE-001.
- Consumidores: `frontend/src/views/HistoricoView.vue` (FUN-TS-UI-028).
- Testes: `frontend/src/stores/rota.spec.ts`.

#### FUN-TS-ROUTE-009 — alteracoes(id)
- Status: Ativa
- Arquivo: `frontend/src/stores/rota.ts`
- Simbolo: `alteracoes`
- Assinatura: `alteracoes(id: number): Promise<AlteracaoRota[]>`
- Objetivo: Obter as alterações monitoradas de uma rota.
- Funcionamento: Chama `api.listarAlteracoes`; em erro registra mensagem e devolve `[]`.
- Entradas: ID.
- Saidas: Lista de alterações.
- Erros e efeitos: Atualiza `erroHistorico`.
- Dependencias: FUN-TS-API-018, FUN-TS-ROUTE-001.
- Consumidores: `frontend/src/views/HistoricoView.vue` (FUN-TS-UI-026).
- Testes: `frontend/src/stores/rota.spec.ts`.

#### FUN-TS-ROUTE-010 — inverter()
- Status: Ativa
- Arquivo: `frontend/src/stores/rota.ts`
- Simbolo: `inverter`
- Assinatura: `inverter(): void`
- Objetivo: Trocar origem e destino e limpar o resultado.
- Funcionamento: Cria novos parâmetros e zera `resultado`, `idSalvo`, `salvoLocal` e `calculadoOffline`.
- Entradas: Nenhuma.
- Saidas: Nenhuma.
- Erros e efeitos: Nenhum.
- Dependencias: Nenhuma.
- Consumidores: `frontend/src/views/RotaNovaView.vue`.
- Testes: `frontend/src/stores/rota.spec.ts`.

#### FUN-TS-ROUTE-011 — limpar()
- Status: Ativa
- Arquivo: `frontend/src/stores/rota.ts`
- Simbolo: `limpar`
- Assinatura: `limpar(): void`
- Objetivo: Limpar resultado e erros da rota atual.
- Funcionamento: Zera `resultado`, `erro`, `idSalvo`, `salvoLocal` e `calculadoOffline`.
- Entradas: Nenhuma.
- Saidas: Nenhuma.
- Erros e efeitos: Nenhum.
- Dependencias: Nenhuma.
- Consumidores: Nenhum identificado no frontend atual.
- Testes: `frontend/src/stores/rota.spec.ts` (indireto).

#### FUN-TS-ROUTE-012 — calcularOffline(snap, origemCodigo, destinoCodigo, calado, margem, velocidade)
- Status: Ativa
- Arquivo: `frontend/src/services/roteador.ts`
- Simbolo: `calcularOffline`
- Assinatura: `calcularOffline(snap: SnapshotGrafo, origemCodigo: string, destinoCodigo: string, calado: number, margem: number, velocidade: number): RouteResult | null`
- Objetivo: Calcular rota localmente (RF022/RN026).
- Funcionamento: Monta adjacência bidirecional, executa Dijkstra com heap binário, poda arestas com `prof < calado + margem` (`null` é transitável), monta GeoJSON/segmentos e métricas.
- Entradas: Snapshot, códigos, calado, margem e velocidade.
- Saidas: `RouteResult` ou `null` sem rota/estação.
- Erros e efeitos: Não acessa rede; usa apenas o snapshot.
- Dependencias: FUN-TS-ROUTE-013/014/015.
- Consumidores: FUN-TS-ROUTE-003; teste direto.
- Testes: `frontend/src/services/roteador.spec.ts`.

#### FUN-TS-ROUTE-013 — round(valor, digitos)
- Status: Ativa
- Arquivo: `frontend/src/services/roteador.ts`
- Simbolo: `round`
- Assinatura: `round(valor: number, digitos: number): number`
- Objetivo: Arredondar números do resultado offline.
- Funcionamento: `Number(valor.toFixed(digitos))`.
- Entradas: Valor e dígitos.
- Saidas: Número arredondado.
- Erros e efeitos: Nenhum.
- Dependencias: Nenhuma.
- Consumidores: FUN-TS-ROUTE-012.
- Testes: `frontend/src/services/roteador.spec.ts` (indireto).

#### FUN-TS-ROUTE-014 — MinHeap.push(custo, no)
- Status: Ativa
- Arquivo: `frontend/src/services/roteador.ts`
- Simbolo: `MinHeap.push`
- Assinatura: `push(custo: number, no: number): void`
- Objetivo: Inserir item no heap binário.
- Funcionamento: Adiciona ao fim e sobe enquanto o pai for maior.
- Entradas: Custo e nó.
- Saidas: Nenhuma.
- Erros e efeitos: Nenhum.
- Dependencias: Nenhuma.
- Consumidores: FUN-TS-ROUTE-012.
- Testes: `frontend/src/services/roteador.spec.ts` (indireto).

#### FUN-TS-ROUTE-015 — MinHeap.pop()
- Status: Ativa
- Arquivo: `frontend/src/services/roteador.ts`
- Simbolo: `MinHeap.pop`
- Assinatura: `pop(): [number, number] | undefined`
- Objetivo: Remover o menor item do heap.
- Funcionamento: Troca a raiz pelo último e desce até restabelecer a ordem.
- Entradas: Nenhuma.
- Saidas: `[custo, nó]` ou `undefined`.
- Erros e efeitos: Nenhum.
- Dependencias: Nenhuma.
- Consumidores: FUN-TS-ROUTE-012.
- Testes: `frontend/src/services/roteador.spec.ts` (indireto).

### OFFLINE

#### FUN-TS-OFFLINE-001 — atualizarContadores()
- Status: Ativa
- Arquivo: `frontend/src/stores/offline.ts`
- Simbolo: `atualizarContadores`
- Assinatura: `atualizarContadores(): Promise<void>`
- Objetivo: Atualizar pendências, última sincronização e estado do snapshot.
- Funcionamento: Consulta `contarPendentes`, `lerUltimaSincronizacao` e `lerSnapshot`.
- Entradas: Nenhuma.
- Saidas: Nenhuma.
- Erros e efeitos: Propaga erro do Dexie.
- Dependencias: FUN-TS-CACHE-008/010/013.
- Consumidores: `frontend/src/main.ts`.
- Testes: `frontend/src/stores/offline.spec.ts` (indireto).

#### FUN-TS-OFFLINE-002 — baixarSnapshot()
- Status: Ativa
- Arquivo: `frontend/src/stores/offline.ts`
- Simbolo: `baixarSnapshot`
- Assinatura: `baixarSnapshot(): Promise<boolean>`
- Objetivo: Baixar e persistir o grafo para o modo offline.
- Funcionamento: Chama `api.snapshot`, grava no Dexie e atualiza `temSnapshot`/`snapshotGeradoEm`.
- Entradas: Nenhuma.
- Saidas: `true` em sucesso; `false` em erro.
- Erros e efeitos: Registra `erro` sem propagar.
- Dependencias: FUN-TS-API-019, FUN-TS-CACHE-012.
- Consumidores: `frontend/src/views/ConfiguracoesView.vue` (FUN-TS-UI-016).
- Testes: `frontend/src/stores/offline.spec.ts` (indireto).

#### FUN-TS-OFFLINE-003 — enfileirar(payload)
- Status: Ativa
- Arquivo: `frontend/src/stores/offline.ts`
- Simbolo: `enfileirar`
- Assinatura: `enfileirar(payload: SalvarRotaInput): Promise<void>`
- Objetivo: Enfileirar rota criada offline.
- Funcionamento: Adiciona à fila e atualiza o contador de pendentes.
- Entradas: Payload.
- Saidas: Nenhuma.
- Erros e efeitos: Propaga erro do Dexie.
- Dependencias: FUN-TS-CACHE-005/008.
- Consumidores: FUN-TS-ROUTE-005.
- Testes: `frontend/src/stores/offline.spec.ts`.

#### FUN-TS-OFFLINE-004 — enviarPendentes()
- Status: Ativa
- Arquivo: `frontend/src/stores/offline.ts`
- Simbolo: `enviarPendentes`
- Assinatura: `enviarPendentes(): Promise<void>`
- Objetivo: Enviar rotas pendentes ao voltar a conexão.
- Funcionamento: Percorre a fila em ordem, chama `api.salvarRota` e remove cada item enviado; para no primeiro erro.
- Entradas: Nenhuma.
- Saidas: Nenhuma.
- Erros e efeitos: Interrompe o envio em erro, preservando o restante da fila.
- Dependencias: FUN-TS-CACHE-006/007, FUN-TS-API-013.
- Consumidores: FUN-TS-OFFLINE-005.
- Testes: `frontend/src/stores/offline.spec.ts`.

#### FUN-TS-OFFLINE-005 — sincronizar()
- Status: Ativa
- Arquivo: `frontend/src/stores/offline.ts`
- Simbolo: `sincronizar`
- Assinatura: `sincronizar(): Promise<void>`
- Objetivo: Executar pull de estações/rotas e push de pendências.
- Funcionamento: Só executa online e sem sincronização concorrente; grava estações, envia pendentes, tenta baixar rotas (ignora erro de sessão anônima) e salva o timestamp.
- Entradas: Nenhuma.
- Saidas: Nenhuma.
- Erros e efeitos: Registra `erro`; atualiza `pendentes` no `finally`.
- Dependencias: FUN-TS-API-008/014, FUN-TS-CACHE-001/003/009, FUN-TS-OFFLINE-004.
- Consumidores: `frontend/src/main.ts`, FUN-TS-OFFLINE-006.
- Testes: `frontend/src/stores/offline.spec.ts`.

#### FUN-TS-OFFLINE-006 — registarListeners()
- Status: Ativa
- Arquivo: `frontend/src/stores/offline.ts`
- Simbolo: `registarListeners`
- Assinatura: `registarListeners(): () => void`
- Objetivo: Reagir às transições online/offline do navegador.
- Funcionamento: Registra listeners `online`/`offline`; ao ficar online dispara `sincronizar`. Retorna função de limpeza.
- Entradas: Nenhuma.
- Saidas: Função de remoção dos listeners.
- Erros e efeitos: Nenhum.
- Dependencias: FUN-TS-OFFLINE-005, `window`.
- Consumidores: `frontend/src/main.ts`.
- Testes: `frontend/src/stores/offline.spec.ts` (indireto).

### NOTIFY

#### FUN-TS-NOTIFY-001 — urlWebSocket(token)
- Status: Ativa
- Arquivo: `frontend/src/stores/notificacao.ts`
- Simbolo: `urlWebSocket`
- Assinatura: `urlWebSocket(token: string): string`
- Objetivo: Montar a URL do WebSocket de eventos.
- Funcionamento: Converte `http(s)` em `ws(s)` e acrescenta `/ws?token=...`; em base relativa usa o host atual.
- Entradas: Token.
- Saidas: URL WebSocket.
- Erros e efeitos: Nenhum.
- Dependencias: `apiBaseUrl`.
- Consumidores: FUN-TS-NOTIFY-008.
- Testes: `frontend/src/stores/notificacao.spec.ts`.

#### FUN-TS-NOTIFY-002 — registar(evento)
- Status: Ativa
- Arquivo: `frontend/src/stores/notificacao.ts`
- Simbolo: `registar`
- Assinatura: `registar(evento: EventoRota): void`
- Objetivo: Transformar evento de rota em aviso para o usuário.
- Funcionamento: Monta texto para `rota_alterada` e adiciona aviso com id sequencial e `rota_id`.
- Entradas: Evento.
- Saidas: Nenhuma.
- Erros e efeitos: Nenhum.
- Dependencias: `EventoRota`.
- Consumidores: FUN-TS-NOTIFY-004/008.
- Testes: `frontend/src/stores/notificacao.spec.ts`.

#### FUN-TS-NOTIFY-003 — limparAviso(id)
- Status: Ativa
- Arquivo: `frontend/src/stores/notificacao.ts`
- Simbolo: `limparAviso`
- Assinatura: `limparAviso(id: number): void`
- Objetivo: Remover um aviso da lista.
- Funcionamento: Filtra por id.
- Entradas: ID do aviso.
- Saidas: Nenhuma.
- Erros e efeitos: Nenhum.
- Dependencias: Nenhuma.
- Consumidores: `frontend/src/layouts/AppLayout.vue`.
- Testes: `frontend/src/stores/notificacao.spec.ts` (indireto).

#### FUN-TS-NOTIFY-004 — checarAlteracoes(notificar)
- Status: Ativa
- Arquivo: `frontend/src/stores/notificacao.ts`
- Simbolo: `checarAlteracoes`
- Assinatura: `checarAlteracoes(notificar: boolean): Promise<void>`
- Objetivo: Fallback de polling para alterações de rotas monitoradas (RN027).
- Funcionamento: Lista rotas, filtra `monitorar`, busca alterações e registra apenas IDs ainda não vistos.
- Entradas: Se deve notificar.
- Saidas: Nenhuma.
- Erros e efeitos: Silencia erros de rede/sessão.
- Dependencias: FUN-TS-API-014/018, FUN-TS-NOTIFY-002.
- Consumidores: FUN-TS-NOTIFY-005.
- Testes: `frontend/src/stores/notificacao.spec.ts`.

#### FUN-TS-NOTIFY-005 — iniciarFallback()
- Status: Ativa
- Arquivo: `frontend/src/stores/notificacao.ts`
- Simbolo: `iniciarFallback`
- Assinatura: `iniciarFallback(): void`
- Objetivo: Iniciar polling periódico de alterações.
- Funcionamento: Cria intervalo de 5 minutos (`INTERVALO_POLL_MS`), se ainda não existir.
- Entradas: Nenhuma.
- Saidas: Nenhuma.
- Erros e efeitos: Timer no `window`.
- Dependencias: FUN-TS-NOTIFY-004.
- Consumidores: FUN-TS-NOTIFY-008.
- Testes: `frontend/src/stores/notificacao.spec.ts`.

#### FUN-TS-NOTIFY-006 — pararFallback()
- Status: Ativa
- Arquivo: `frontend/src/stores/notificacao.ts`
- Simbolo: `pararFallback`
- Assinatura: `pararFallback(): void`
- Objetivo: Parar o polling de alterações.
- Funcionamento: Limpa o intervalo e zera o timer.
- Entradas: Nenhuma.
- Saidas: Nenhuma.
- Erros e efeitos: Nenhum.
- Dependencias: Nenhuma.
- Consumidores: FUN-TS-NOTIFY-008/009.
- Testes: `frontend/src/stores/notificacao.spec.ts` (indireto).

#### FUN-TS-NOTIFY-007 — agendarReconexao()
- Status: Ativa
- Arquivo: `frontend/src/stores/notificacao.ts`
- Simbolo: `agendarReconexao`
- Assinatura: `agendarReconexao(): void`
- Objetivo: Reagendar conexão do WebSocket com backoff exponencial.
- Funcionamento: Espera `min(30 s, 1 s × 2^tentativas)` e chama `conectar`.
- Entradas: Nenhuma.
- Saidas: Nenhuma.
- Erros e efeitos: Timer único; tentativas incrementam.
- Dependencias: FUN-TS-NOTIFY-008.
- Consumidores: FUN-TS-NOTIFY-008.
- Testes: `frontend/src/stores/notificacao.spec.ts`.

#### FUN-TS-NOTIFY-008 — conectar()
- Status: Ativa
- Arquivo: `frontend/src/stores/notificacao.ts`
- Simbolo: `conectar`
- Assinatura: `conectar(): void`
- Objetivo: Abrir o WebSocket de eventos.
- Funcionamento: Exige token, evita conexões duplicadas, cria `WebSocket`, trata `open`/`message`/`close`/`error`, para o fallback ao abrir e reagenda ao fechar.
- Entradas: Nenhuma.
- Saidas: Nenhuma.
- Erros e efeitos: Em falha de construção agenda reconexão; mensagens inválidas são ignoradas.
- Dependencias: FUN-TS-HTTP-006, FUN-TS-NOTIFY-001/002/005/006/007.
- Consumidores: `frontend/src/layouts/AppLayout.vue`.
- Testes: `frontend/src/stores/notificacao.spec.ts`.

#### FUN-TS-NOTIFY-009 — desconectar()
- Status: Ativa
- Arquivo: `frontend/src/stores/notificacao.ts`
- Simbolo: `desconectar`
- Assinatura: `desconectar(): void`
- Objetivo: Encerrar o WebSocket e timers.
- Funcionamento: Limpa reconexão, para o fallback, fecha o socket e marca `conectado=false`.
- Entradas: Nenhuma.
- Saidas: Nenhuma.
- Erros e efeitos: Nenhum.
- Dependencias: FUN-TS-NOTIFY-006.
- Consumidores: `frontend/src/layouts/AppLayout.vue`.
- Testes: `frontend/src/stores/notificacao.spec.ts`.

### UI

#### FUN-TS-UI-001 — formatarNumero(valor, digitos=1)
- Status: Ativa
- Arquivo: `frontend/src/utils/formato.ts`
- Simbolo: `formatarNumero`
- Assinatura: `formatarNumero(valor: number | null | undefined, digitos = 1): string`
- Objetivo: Formatar números no padrão pt-BR.
- Funcionamento: Retorna `—` para nulo/NaN; caso contrário `toLocaleString('pt-BR')` com casas fixas.
- Entradas: Valor e casas decimais.
- Saidas: Texto.
- Erros e efeitos: Nenhum.
- Dependencias: `Intl`.
- Consumidores: `RouteSummary`, `HistoricoView`, `ConfiguracoesView`.
- Testes: `frontend/src/utils/formato.spec.ts`.

#### FUN-TS-UI-002 — formatarInteiro(valor)
- Status: Ativa
- Arquivo: `frontend/src/utils/formato.ts`
- Simbolo: `formatarInteiro`
- Assinatura: `formatarInteiro(valor: number | null | undefined): string`
- Objetivo: Formatar inteiros com separador de milhar.
- Funcionamento: Retorna `—` para nulo/NaN; caso contrário `toLocaleString('pt-BR')`.
- Entradas: Valor.
- Saidas: Texto.
- Erros e efeitos: Nenhum.
- Dependencias: `Intl`.
- Consumidores: `RouteSummary`.
- Testes: `frontend/src/utils/formato.spec.ts`.

#### FUN-TS-UI-003 — formatarDataHora(valor)
- Status: Ativa
- Arquivo: `frontend/src/utils/formato.ts`
- Simbolo: `formatarDataHora`
- Assinatura: `formatarDataHora(valor: string | null | undefined): string`
- Objetivo: Formatar timestamps para exibição pt-BR.
- Funcionamento: Normaliza `T`/espaço e assume UTC quando não há fuso; retorna o texto original se a data for inválida.
- Entradas: Texto.
- Saidas: Data/hora formatada ou `—`.
- Erros e efeitos: Nenhum.
- Dependencias: `Date`, `Intl`.
- Consumidores: `HistoricoView`, `UsuariosView`, `LogsView`, `ConfiguracoesView`.
- Testes: `frontend/src/utils/formato.spec.ts`.

#### FUN-TS-UI-004 — aplicar()
- Status: Ativa
- Arquivo: `frontend/src/stores/ui.ts`
- Simbolo: `aplicar`
- Assinatura: `aplicar(): void`
- Objetivo: Aplicar tema, contraste e escala de fonte ao documento.
- Funcionamento: Alterna classes `dark`/`contrast-high` no `<html>` e define `fontSize`.
- Entradas: Nenhuma.
- Saidas: Nenhuma.
- Erros e efeitos: Depende de `document`.
- Dependencias: Nenhuma.
- Consumidores: Watcher do store `ui`.
- Testes: `frontend/src/stores/ui.spec.ts`.

#### FUN-TS-UI-005 — alternarTema()
- Status: Ativa
- Arquivo: `frontend/src/stores/ui.ts`
- Simbolo: `alternarTema`
- Assinatura: `alternarTema(): void`
- Objetivo: Alternar claro/escuro.
- Funcionamento: Inverte `tema`; o watcher persiste e aplica.
- Entradas: Nenhuma.
- Saidas: Nenhuma.
- Erros e efeitos: Persiste em `localStorage`.
- Dependencias: FUN-TS-UI-004.
- Consumidores: `ConfiguracoesView`, `AppLayout`.
- Testes: `frontend/src/stores/ui.spec.ts`.

#### FUN-TS-UI-006 — alternarContraste()
- Status: Ativa
- Arquivo: `frontend/src/stores/ui.ts`
- Simbolo: `alternarContraste`
- Assinatura: `alternarContraste(): void`
- Objetivo: Alternar alto contraste.
- Funcionamento: Inverte `altoContraste`.
- Entradas: Nenhuma.
- Saidas: Nenhuma.
- Erros e efeitos: Persiste em `localStorage`.
- Dependencias: FUN-TS-UI-004.
- Consumidores: `ConfiguracoesView`.
- Testes: `frontend/src/stores/ui.spec.ts`.

#### FUN-TS-UI-007 — ciclarFonte()
- Status: Ativa
- Arquivo: `frontend/src/stores/ui.ts`
- Simbolo: `ciclarFonte`
- Assinatura: `ciclarFonte(): void`
- Objetivo: Ciclar a escala de fonte entre 16/18/20 px.
- Funcionamento: Incrementa módulo 3.
- Entradas: Nenhuma.
- Saidas: Nenhuma.
- Erros e efeitos: Persiste em `localStorage`.
- Dependencias: FUN-TS-UI-004.
- Consumidores: `ConfiguracoesView`.
- Testes: `frontend/src/stores/ui.spec.ts`.

#### FUN-TS-UI-008 — useConnectivity()
- Status: Ativa
- Arquivo: `frontend/src/composables/useConnectivity.ts`
- Simbolo: `useConnectivity`
- Assinatura: `useConnectivity(): { online; ultimaMudanca; atualizar }`
- Objetivo: Expor estado de conectividade reativo.
- Funcionamento: Inicializa com `navigator.onLine`, registra listeners no mount e remove no unmount.
- Entradas: Nenhuma.
- Saidas: Refs e função de atualização.
- Erros e efeitos: Depende de `window`/`navigator`.
- Dependencias: FUN-TS-UI-009.
- Consumidores: Nenhum identificado no frontend atual (o layout usa o store offline).
- Testes: `frontend/src/composables/useConnectivity.spec.ts`.

#### FUN-TS-UI-009 — atualizar()
- Status: Ativa
- Arquivo: `frontend/src/composables/useConnectivity.ts`
- Simbolo: `atualizar`
- Assinatura: `atualizar(): void`
- Objetivo: Atualizar o estado online e o instante da mudança.
- Funcionamento: Lê `navigator.onLine` e grava `new Date()`.
- Entradas: Nenhuma.
- Saidas: Nenhuma.
- Erros e efeitos: Nenhum.
- Dependencias: `navigator`.
- Consumidores: FUN-TS-UI-008.
- Testes: `frontend/src/composables/useConnectivity.spec.ts`.

#### FUN-TS-UI-010 — corEstacao(estacao)
- Status: Ativa
- Arquivo: `frontend/src/components/map/RiverMap.vue`
- Simbolo: `corEstacao`
- Assinatura: `corEstacao(estacao: Estacao): string`
- Objetivo: Escolher a cor do marcador conforme o nível.
- Funcionamento: Cinza sem nível; verde sem mínima; âmbar se nível ≤ mínima + 0,5 m; senão verde.
- Entradas: Estação.
- Saidas: Cor hexadecimal.
- Erros e efeitos: Nenhum.
- Dependencias: Nenhuma.
- Consumidores: FUN-TS-UI-012.
- Testes: `frontend/src/components/map/RiverMap.spec.ts` (renderização).

#### FUN-TS-UI-011 — criarPopup(estacao)
- Status: Ativa
- Arquivo: `frontend/src/components/map/RiverMap.vue`
- Simbolo: `criarPopup`
- Assinatura: `criarPopup(estacao: Estacao): HTMLElement`
- Objetivo: Montar o conteúdo do popup da estação.
- Funcionamento: Cria `div` com nome, rio, município, nível e atualização.
- Entradas: Estação.
- Saidas: Elemento HTML.
- Erros e efeitos: Usa `document`.
- Dependencias: Nenhuma.
- Consumidores: FUN-TS-UI-012.
- Testes: `frontend/src/components/map/RiverMap.spec.ts`.

#### FUN-TS-UI-012 — renderizarEstacoes()
- Status: Ativa
- Arquivo: `frontend/src/components/map/RiverMap.vue`
- Simbolo: `renderizarEstacoes`
- Assinatura: `renderizarEstacoes(): void`
- Objetivo: Desenhar os marcadores das estações no mapa.
- Funcionamento: Limpa a camada, cria `circleMarker` por estação, associa popup e evento de clique.
- Entradas: Nenhuma (usa props).
- Saidas: Nenhuma.
- Erros e efeitos: Depende de Leaflet e do mapa montado.
- Dependencias: FUN-TS-UI-010/011.
- Consumidores: `onMounted` e watcher de `estacoes` do componente.
- Testes: `frontend/src/components/map/RiverMap.spec.ts`.

#### FUN-TS-UI-013 — renderizarRota()
- Status: Ativa
- Arquivo: `frontend/src/components/map/RiverMap.vue`
- Simbolo: `renderizarRota`
- Assinatura: `renderizarRota(): void`
- Objetivo: Desenhar a rota calculada no mapa.
- Funcionamento: Remove a camada anterior e adiciona `L.geoJSON` da rota, ajustando o enquadramento.
- Entradas: Nenhuma (usa props).
- Saidas: Nenhuma.
- Erros e efeitos: Depende de Leaflet.
- Dependencias: Nenhuma.
- Consumidores: `onMounted` e watcher de `rota`.
- Testes: `frontend/src/components/map/RiverMap.spec.ts`.

#### FUN-TS-UI-014 — tomNivel(estacao)
- Status: Ativa
- Arquivo: `frontend/src/views/MapaView.vue`
- Simbolo: `tomNivel`
- Assinatura: `tomNivel(estacao: Estacao): 'success' | 'warning' | 'unknown'`
- Objetivo: Definir o tom do badge de nível na lista.
- Funcionamento: `unknown` sem nível; `success` sem mínima; `warning` se nível ≤ mínima + 0,5 m.
- Entradas: Estação.
- Saidas: Tom do badge.
- Erros e efeitos: Nenhum.
- Dependencias: Nenhuma.
- Consumidores: Template de `MapaView`.
- Testes: Sem teste automatizado identificado.

#### FUN-TS-UI-015 — entrar()
- Status: Ativa
- Arquivo: `frontend/src/views/LoginView.vue`
- Simbolo: `entrar`
- Assinatura: `entrar(): Promise<void>`
- Objetivo: Submeter o formulário de login.
- Funcionamento: Chama `session.login`, redireciona para `redirect` ou `/mapa`; em falha exibe mensagem.
- Entradas: E-mail/senha dos refs.
- Saidas: Nenhuma.
- Erros e efeitos: Navegação via Vue Router; trata `ApiProblem`.
- Dependencias: FUN-TS-AUTH-003, FUN-TS-HTTP-008.
- Consumidores: Template de `LoginView`.
- Testes: Sem teste automatizado identificado.

#### FUN-TS-UI-016 — baixarOffline()
- Status: Ativa
- Arquivo: `frontend/src/views/ConfiguracoesView.vue`
- Simbolo: `baixarOffline`
- Assinatura: `baixarOffline(): Promise<void>`
- Objetivo: Acionar o download do snapshot offline.
- Funcionamento: Chama `offline.baixarSnapshot` e define aviso de sucesso/falha.
- Entradas: Nenhuma.
- Saidas: Nenhuma.
- Erros e efeitos: Controla `baixando`/`avisoOffline`.
- Dependencias: FUN-TS-OFFLINE-002.
- Consumidores: Template de `ConfiguracoesView`.
- Testes: Sem teste automatizado identificado.

#### FUN-TS-UI-017 — salvarPerfil()
- Status: Ativa
- Arquivo: `frontend/src/views/ConfiguracoesView.vue`
- Simbolo: `salvarPerfil`
- Assinatura: `salvarPerfil(): Promise<void>`
- Objetivo: Salvar nome/senha do perfil.
- Funcionamento: Chama `session.atualizarPerfil`, limpa a senha e exibe aviso; trata `ApiProblem`.
- Entradas: Formulário reativo.
- Saidas: Nenhuma.
- Erros e efeitos: Controla `salvando`/`erro`/`aviso`.
- Dependencias: FUN-TS-AUTH-006, FUN-TS-HTTP-008.
- Consumidores: Template de `ConfiguracoesView`.
- Testes: Sem teste automatizado identificado.

#### FUN-TS-UI-018 — carregar()
- Status: Ativa
- Arquivo: `frontend/src/views/admin/UsuariosView.vue`
- Simbolo: `carregar`
- Assinatura: `carregar(): Promise<void>`
- Objetivo: Carregar a lista de usuários.
- Funcionamento: Chama `api.listarUsuarios` e trata erro com mensagem.
- Entradas: Nenhuma.
- Saidas: Nenhuma.
- Erros e efeitos: Controla `carregando`/`erro`.
- Dependencias: FUN-TS-API-004, FUN-TS-UI-030 (mensagem local).
- Consumidores: `onMounted` e `criar` (FUN-TS-UI-019).
- Testes: Sem teste automatizado identificado.

#### FUN-TS-UI-019 — criar()
- Status: Ativa
- Arquivo: `frontend/src/views/admin/UsuariosView.vue`
- Simbolo: `criar`
- Assinatura: `criar(): Promise<void>`
- Objetivo: Criar usuário pelo formulário administrativo.
- Funcionamento: Chama `api.criarUsuario`, limpa o formulário, recarrega a lista e exibe aviso.
- Entradas: Formulário `novoServidor`.
- Saidas: Nenhuma.
- Erros e efeitos: Controla `salvando`/`erro`/`aviso`.
- Dependencias: FUN-TS-API-005, FUN-TS-UI-018.
- Consumidores: Template de `UsuariosView`.
- Testes: Sem teste automatizado identificado.

#### FUN-TS-UI-020 — alterarPapel(usuario, papel)
- Status: Ativa
- Arquivo: `frontend/src/views/admin/UsuariosView.vue`
- Simbolo: `alterarPapel`
- Assinatura: `alterarPapel(usuario: UsuarioAdmin, papel: Papel): Promise<void>`
- Objetivo: Alterar o papel de um usuário.
- Funcionamento: Chama `api.atualizarUsuario` e atualiza o item local.
- Entradas: Usuário e novo papel.
- Saidas: Nenhuma.
- Erros e efeitos: Exibe erro em falha.
- Dependencias: FUN-TS-API-006.
- Consumidores: Template de `UsuariosView`.
- Testes: Sem teste automatizado identificado.

#### FUN-TS-UI-021 — alternarAtivo(usuario)
- Status: Ativa
- Arquivo: `frontend/src/views/admin/UsuariosView.vue`
- Simbolo: `alternarAtivo`
- Assinatura: `alternarAtivo(usuario: UsuarioAdmin): Promise<void>`
- Objetivo: Desativar/reativar usuário.
- Funcionamento: Se ativo, chama `api.desativarUsuario`; senão `api.atualizarUsuario({ativo:true})`.
- Entradas: Usuário.
- Saidas: Nenhuma.
- Erros e efeitos: Exibe erro e não altera o estado local em falha.
- Dependencias: FUN-TS-API-006/007.
- Consumidores: Template de `UsuariosView`.
- Testes: Sem teste automatizado identificado.

#### FUN-TS-UI-022 - solicitar()
- Status: Ativa
- Arquivo: `frontend/src/views/admin/ColetaView.vue`
- Simbolo: `solicitar`
- Assinatura: `solicitar(): Promise<void>`
- Objetivo: Solicitar a coleta de níveis à API.
- Funcionamento: Cancela polling anterior, chama `api.coletarNiveis` com estações/período, guarda o job e agenda `consultar` quando a coleta inicia.
- Entradas: Formulário de estações/período.
- Saidas: Nenhuma.
- Erros e efeitos: Preenche `erro` com a mensagem da API.
- Dependencias: FUN-TS-API-009, FUN-TS-UI-039.
- Consumidores: Submit do formulário.
- Testes: Sem teste automatizado identificado.

#### FUN-TS-UI-023 — carregar()
- Status: Ativa
- Arquivo: `frontend/src/views/admin/LogsView.vue`
- Simbolo: `carregar`
- Assinatura: `carregar(): Promise<void>`
- Objetivo: Carregar logs de auditoria.
- Funcionamento: Chama `api.listarLogs` e trata erro.
- Entradas: Nenhuma.
- Saidas: Nenhuma.
- Erros e efeitos: Controla `carregando`/`erro`.
- Dependencias: FUN-TS-API-011.
- Consumidores: `onMounted` e botão Atualizar.
- Testes: Sem teste automatizado identificado.

#### FUN-TS-UI-024 — tom(tipo)
- Status: Ativa
- Arquivo: `frontend/src/views/admin/LogsView.vue`
- Simbolo: `tom`
- Assinatura: `tom(tipo: string): 'success' | 'warning' | 'danger' | 'info' | 'unknown'`
- Objetivo: Mapear tipo de log para tom visual.
- Funcionamento: Consulta o mapa `TONS` com fallback `unknown`.
- Entradas: Tipo.
- Saidas: Tom.
- Erros e efeitos: Nenhum.
- Dependencias: Nenhuma.
- Consumidores: Template de `LogsView`.
- Testes: Sem teste automatizado identificado.

#### FUN-TS-UI-025 — resultadoDaRota(item)
- Status: Ativa
- Arquivo: `frontend/src/views/HistoricoView.vue`
- Simbolo: `resultadoDaRota`
- Assinatura: `resultadoDaRota(item: RotaSalva): RouteResult`
- Objetivo: Adaptar rota salva ao formato de resultado para o mapa/resumo.
- Funcionamento: Copia métricas e usa `rota_geojson` ou FeatureCollection vazia; `items` vazio.
- Entradas: Rota salva.
- Saidas: `RouteResult`.
- Erros e efeitos: Nenhum.
- Dependencias: `RouteResult`, `RotaSalva`.
- Consumidores: Template de `HistoricoView`.
- Testes: Sem teste automatizado identificado.

#### FUN-TS-UI-026 — carregarAlteracoes(id)
- Status: Ativa
- Arquivo: `frontend/src/views/HistoricoView.vue`
- Simbolo: `carregarAlteracoes`
- Assinatura: `carregarAlteracoes(id: number): Promise<void>`
- Objetivo: Carregar alterações de uma rota expandida.
- Funcionamento: Chama `rota.alteracoes` e guarda em `alteracoesPorRota[id]`.
- Entradas: ID.
- Saidas: Nenhuma.
- Erros e efeitos: Nenhum (store trata erro).
- Dependencias: FUN-TS-ROUTE-009.
- Consumidores: FUN-TS-UI-027/028.
- Testes: Sem teste automatizado identificado.

#### FUN-TS-UI-027 — alternar(item)
- Status: Ativa
- Arquivo: `frontend/src/views/HistoricoView.vue`
- Simbolo: `alternar`
- Assinatura: `alternar(item: RotaSalva): Promise<void>`
- Objetivo: Expandir/recolher os detalhes de uma rota.
- Funcionamento: Alterna `expandida` e carrega alterações quando a rota é monitorada.
- Entradas: Rota.
- Saidas: Nenhuma.
- Erros e efeitos: Nenhum.
- Dependencias: FUN-TS-UI-026.
- Consumidores: Template de `HistoricoView`.
- Testes: Sem teste automatizado identificado.

#### FUN-TS-UI-028 — alternarMonitoramento(item)
- Status: Ativa
- Arquivo: `frontend/src/views/HistoricoView.vue`
- Simbolo: `alternarMonitoramento`
- Assinatura: `alternarMonitoramento(item: RotaSalva): Promise<void>`
- Objetivo: Ativar/desativar monitoramento a partir do histórico.
- Funcionamento: Chama `rota.monitorar` com o valor invertido e carrega alterações ao ativar.
- Entradas: Rota.
- Saidas: Nenhuma.
- Erros e efeitos: Nenhum (store trata erro).
- Dependencias: FUN-TS-ROUTE-008, FUN-TS-UI-026.
- Consumidores: Template de `HistoricoView`.
- Testes: Sem teste automatizado identificado.

#### FUN-TS-UI-029 — remover(id)
- Status: Ativa
- Arquivo: `frontend/src/views/HistoricoView.vue`
- Simbolo: `remover`
- Assinatura: `remover(id: number): Promise<void>`
- Objetivo: Remover rota do histórico pela interface.
- Funcionamento: Chama `rota.remover` e recolhe os detalhes se necessário.
- Entradas: ID.
- Saidas: Nenhuma.
- Erros e efeitos: Nenhum.
- Dependencias: FUN-TS-ROUTE-007.
- Consumidores: Template de `HistoricoView`.
- Testes: Sem teste automatizado identificado.

#### FUN-TS-UI-030 — guard(to)
- Status: Ativa
- Arquivo: `frontend/src/app/router.ts`
- Simbolo: `beforeEach`
- Assinatura: `beforeEach((to) => boolean | RouteLocationRaw)`
- Objetivo: Proteger rotas autenticadas e administrativas.
- Funcionamento: Redireciona para `login` com `redirect` quando a rota não é pública e não há sessão; redireciona para `mapa` quando exige admin e o usuário não é admin.
- Entradas: Rota de destino.
- Saidas: `true` ou redirecionamento.
- Erros e efeitos: Usa o store de sessão (restaurado antes do mount).
- Dependencias: FUN-TS-AUTH-004.
- Consumidores: Vue Router.
- Testes: Sem teste automatizado identificado.

#### FUN-TS-UI-031 — tomProfundidade()
- Status: Ativa
- Arquivo: `frontend/src/components/route/RouteSummary.vue`
- Simbolo: `tomProfundidade`
- Assinatura: `computed<'success' | 'warning' | 'danger' | 'unknown'>()`
- Objetivo: Definir o tom do badge de profundidade mínima.
- Funcionamento: `unknown` sem dado; `danger` <2 m; `warning` <4 m; senão `success`.
- Entradas: Nenhuma (usa props).
- Saidas: Tom computado.
- Erros e efeitos: Nenhum.
- Dependencias: Nenhuma.
- Consumidores: Template de `RouteSummary`.
- Testes: Sem teste automatizado identificado.

#### FUN-TS-UI-032 — mensagem(e, padrao)
- Status: Ativa
- Arquivo: `frontend/src/views/admin/UsuariosView.vue`
- Simbolo: `mensagem`
- Assinatura: `mensagem(e: unknown, padrao: string): string`
- Objetivo: Extrair mensagem de erro para o formulário de usuários.
- Funcionamento: `e instanceof ApiProblem ? e.message : padrao`.
- Entradas: Erro e fallback.
- Saidas: Texto.
- Erros e efeitos: Nenhum.
- Dependencias: FUN-TS-HTTP-008.
- Consumidores: FUN-TS-UI-018/019/020/021.
- Testes: Sem teste automatizado identificado.

#### FUN-TS-UI-033 — trocarAba(nova)
- Status: Ativa
- Arquivo: `frontend/src/views/MapaView.vue`
- Simbolo: `trocarAba`
- Assinatura: `trocarAba(nova: Aba): void`
- Objetivo: Alternar entre as abas Mapa/Estacoes no layout mobile.
- Funcionamento: Atualiza `aba` e, ao exibir o mapa, agenda `redimensionar()` no `nextTick`.
- Entradas: Aba de destino.
- Saidas: Nenhuma.
- Erros e efeitos: Recalcula o tamanho do mapa Leaflet.
- Dependencias: FUN-TS-UI-035.
- Consumidores: Botoes da tablist de `MapaView`.
- Testes: Sem teste automatizado identificado.

#### FUN-TS-UI-034 — selecionarDaLista(estacao)
- Status: Ativa
- Arquivo: `frontend/src/views/MapaView.vue`
- Simbolo: `selecionarDaLista`
- Assinatura: `selecionarDaLista(estacao: Estacao): void`
- Objetivo: Selecionar estacao na lista e exibir sua posicao no mapa.
- Funcionamento: Guarda a estacao em `selecionada`; em telas < 1024px troca para a aba Mapa, recalcula o tamanho e centraliza o mapa na estacao.
- Entradas: Estacao.
- Saidas: Nenhuma.
- Erros e efeitos: Move o mapa e atualiza o painel de detalhes.
- Dependencias: FUN-TS-UI-033, FUN-TS-UI-035, FUN-TS-UI-036.
- Consumidores: Lista de estacoes de `MapaView`.
- Testes: Sem teste automatizado identificado.

#### FUN-TS-UI-035 — redimensionar()
- Status: Ativa
- Arquivo: `frontend/src/components/map/RiverMap.vue`
- Simbolo: `redimensionar` (exposto por `defineExpose`)
- Assinatura: `redimensionar(): void`
- Objetivo: Recalcular o tamanho do mapa apos mudanca de layout ou de aba.
- Funcionamento: Chama `invalidateSize()` no mapa quando ele existe.
- Entradas: Nenhuma.
- Saidas: Nenhuma.
- Erros e efeitos: Reajusta tiles e controles do Leaflet.
- Dependencias: Leaflet `Map`.
- Consumidores: FUN-TS-UI-033, FUN-TS-UI-034.
- Testes: Sem teste automatizado identificado.

#### FUN-TS-UI-036 — centralizar(lat, lng, zoom = 7)
- Status: Ativa
- Arquivo: `frontend/src/components/map/RiverMap.vue`
- Simbolo: `centralizar` (exposto por `defineExpose`)
- Assinatura: `centralizar(lat: number, lng: number, zoom = 7): void`
- Objetivo: Centralizar o mapa em uma coordenada.
- Funcionamento: Usa `setView` com o maior valor entre o zoom atual e o informado.
- Entradas: Latitude, longitude e zoom minimo.
- Saidas: Nenhuma.
- Erros e efeitos: Move a visualizacao do mapa.
- Dependencias: Leaflet `Map`.
- Consumidores: FUN-TS-UI-034.
- Testes: Sem teste automatizado identificado.

#### FUN-TS-UI-037 — fecharMenuComEsc(evento)
- Status: Ativa
- Arquivo: `frontend/src/layouts/AppLayout.vue`
- Simbolo: `fecharMenuComEsc`
- Assinatura: `fecharMenuComEsc(evento: KeyboardEvent): void`
- Objetivo: Fechar o menu mobile com a tecla Escape.
- Funcionamento: Verifica `evento.key === 'Escape'` e define `menuAberto` como falso.
- Entradas: Evento de teclado.
- Saidas: Nenhuma.
- Erros e efeitos: Nenhum.
- Dependencias: Nenhuma.
- Consumidores: Listener `keydown` do layout.
- Testes: Sem teste automatizado identificado.

#### FUN-TS-UI-038 — sair()
- Status: Ativa
- Arquivo: `frontend/src/layouts/AppLayout.vue`
- Simbolo: `sair`
- Assinatura: `sair(): void`
- Objetivo: Encerrar a sessao a partir do cabecalho ou do menu mobile.
- Funcionamento: Fecha o menu e chama `session.logout()`.
- Entradas: Nenhuma.
- Saidas: Nenhuma.
- Erros e efeitos: Remove token e usuario do armazenamento local.
- Dependencias: FUN-TS-AUTH-005.
- Consumidores: Botoes Sair do cabecalho e do menu mobile.
- Testes: Sem teste automatizado identificado.

#### FUN-TS-UI-039 - consultar(jobId)
- Status: Ativa
- Arquivo: `frontend/src/views/admin/ColetaView.vue`
- Simbolo: `consultar`
- Assinatura: `consultar(jobId: string): Promise<void>`
- Objetivo: Acompanhar o andamento da coleta até concluir ou falhar.
- Funcionamento: Consulta `api.statusColeta`, atualiza o job e reagenda a cada 2,5s (limite de 240 tentativas).
- Entradas: ID do job.
- Saidas: Nenhuma.
- Erros e efeitos: Preenche `erro` em falhas de consulta ou timeout.
- Dependencias: FUN-TS-API-020.
- Consumidores: FUN-TS-UI-022.
- Testes: Sem teste automatizado identificado.

## JAVASCRIPT

### UI

#### FUN-JS-UI-001 — staleWhileRevalidate(request)
- Status: Ativa
- Arquivo: `frontend/public/sw.js`
- Simbolo: `staleWhileRevalidate`
- Assinatura: `staleWhileRevalidate(request): Promise<Response>`
- Objetivo: Servir resposta em cache e revalidar em segundo plano no Service Worker.
- Funcionamento: Abre o cache, tenta `cache.match` e dispara `fetch`; grava a resposta 200 no cache e devolve o cache imediatamente quando existir.
- Entradas: Requisição.
- Saidas: `Response` do cache ou da rede.
- Erros e efeitos: Falha de rede cai para o cache; usado para `/api/` e assets GET.
- Dependencias: Cache API, `fetch`.
- Consumidores: Listener `fetch` do Service Worker.
- Testes: Sem teste automatizado identificado.
- Observação: escopo do Service Worker inclui `/api/` (stale-while-revalidate) e navegação com fallback para `index.html`.


## Limitações e cobertura incremental

- **Funções aninhadas/geradores** (ex.: `gerador` dentro dos importadores, `_ok` dentro de `_estatisticas`, `avaliar` em `classificar_navegabilidade.main`, `codigoDe` em `useRotaStore`) são descritas no item da função hospedeira, não recebem ID próprio.
- **Métodos de objeto/arrow properties** de `api` em `endpoints.ts` foram catalogados como `FUN-TS-API-*` (19 itens), mas a validação estática pode não confirmar a declaração; o contrato HTTP correspondente está em `API-END.md`.
- **Computed properties, watchers e handlers inline** de componentes Vue (ex.: `podeCalcular`, `filtradas`, `@click="rota.inverter()"`, `fitRota`) não recebem ID individual; as funções nomeadas com regra de negócio estão em `UI`.
- **Classes de dados** sem comportamento próprio (ex.: `Edge`, `RotaPendente`, tipos de `types/api.ts`) não são funções e não entram neste catálogo.
- **`backend_sqlite/`** e **`frontend/prototipos/`** são legado declarado e **não** foram catalogados. O primeiro replica as rotas da API sem PostGIS; o segundo é protótipo estático anterior.
- **`frontend/src/services/endpoints.ts`**: os clientes são finos; a fonte primária do contrato é `API-END.md`.
- Foram inseridas anotações `@id ... | @categoria ... | @catalogo FUNCOES.md` nas declarações do backend e nos módulos frontend sem alterações locais pendentes. Ficaram sem anotação: views/layouts que já possuíam modificações não commitadas, métodos de objeto (`api.*`, `MinHeap.*`) e o guard `beforeEach` — nesses casos a validação estática não confirma a declaração.
- A validação `check` retorna **0 erros** e **29 avisos** de confirmação estática (não são inconsistências de ID ou de arquivo).
