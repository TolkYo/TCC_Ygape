# API-END — catálogo de endpoints e integrações

> Fonte: rotas e clientes efetivamente presentes no código (verificado em 2026-10-20).
> Organização: categoria → operação HTTP. Uma entrada para cada combinação método + rota.
> **Cobertura:** API interna em `backend/main.py` e integrações externas chamadas por `backend/` e `frontend/src/`.
> **Fora de cobertura:** `backend_sqlite/main.py` (legado com as mesmas rotas, sem PostGIS) e protótipos estáticos.
> Envelope de sucesso: `{"success": true, "data": ...}`; erro: `{"success": false, "error": {"code", "message"}}`. A API é versionada em `/api/v1`.

## SYSTEM

### API-SYSTEM-001 — GET /health
- Status: Ativa
- Tipo: endpoint interno
- Arquivo: `backend/main.py`
- Metodo: GET
- Rota: /health
- Objetivo: Indicar disponibilidade da API e do banco.
- Funcionamento: Executa `SELECT 1` e devolve `status` (`ok`/`degraded`) e `db` booleano.
- Autenticacao: Nenhuma.
- Entrada: Nenhuma.
- Saida: `{status, db}`.
- Codigos HTTP: 200.
- Funcoes: FUN-PY-API-020
- Consumidores: Monitoramento/infra (não há chamada no frontend atual).
- Testes: Sem teste automatizado identificado.

## AUTH

### API-AUTH-001 — POST /api/v1/auth/login
- Status: Ativa
- Tipo: endpoint interno
- Arquivo: `backend/main.py`
- Metodo: POST
- Rota: /api/v1/auth/login
- Objetivo: Autenticar piloto/admin e emitir token.
- Funcionamento: Busca usuário por e-mail (case-insensitive), exige `ativo` e valida senha com scrypt; emite token HMAC com TTL de 8 h (padrão) e registra `login` em `log_eventos`.
- Autenticacao: Pública (credenciais no corpo).
- Entrada: `{email, senha}`.
- Saida: `{access_token, token_type: "bearer", expires_in, usuario: {id,nome,email,papel}}`.
- Codigos HTTP: 200; 401 `invalid_credentials`; 503 `auth_not_configured`.
- Funcoes: FUN-PY-API-021, FUN-PY-AUTH-002, FUN-PY-AUTH-004, FUN-PY-API-002
- Consumidores: FUN-TS-API-001; FUN-TS-AUTH-003.
- Testes: `frontend/src/stores/session.spec.ts` (cliente).

### API-AUTH-002 — GET /api/v1/auth/me
- Status: Ativa
- Tipo: endpoint interno
- Arquivo: `backend/main.py`
- Metodo: GET
- Rota: /api/v1/auth/me
- Objetivo: Retornar o usuário autenticado.
- Funcionamento: Usa a dependência `current_user` e projeta `id,nome,email,papel`.
- Autenticacao: Bearer JWT.
- Entrada: Nenhuma.
- Saida: `{id,nome,email,papel}`.
- Codigos HTTP: 200; 401 `missing_token`/`invalid_token`.
- Funcoes: FUN-PY-API-022, FUN-PY-AUTH-006
- Consumidores: FUN-TS-API-002; FUN-TS-AUTH-004.
- Testes: `frontend/src/stores/session.spec.ts`.

### API-AUTH-003 — PUT /api/v1/auth/me
- Status: Ativa
- Tipo: endpoint interno
- Arquivo: `backend/main.py`
- Metodo: PUT
- Rota: /api/v1/auth/me
- Objetivo: Atualizar nome/senha do próprio usuário.
- Funcionamento: Aceita `nome` e/ou `senha`, gera novo hash e atualiza apenas `id` autenticado; registra `perfil_atualizado`.
- Autenticacao: Bearer JWT.
- Entrada: `{nome?, senha?}` (nome 2–120; senha 8–256).
- Saida: `{id,nome,email,papel}`.
- Codigos HTTP: 200; 401; 422 `empty_update`.
- Funcoes: FUN-PY-API-023, FUN-PY-AUTH-001
- Consumidores: FUN-TS-API-003; FUN-TS-AUTH-006.
- Testes: `frontend/src/stores/session.spec.ts`.

## USER

### API-USER-001 — GET /api/v1/usuarios
- Status: Ativa
- Tipo: endpoint interno
- Arquivo: `backend/main.py`
- Metodo: GET
- Rota: /api/v1/usuarios
- Objetivo: Listar usuários para administração.
- Funcionamento: Seleciona `id,nome,email,papel,ativo,criado_em` ordenado por nome.
- Autenticacao: Bearer JWT + papel `admin`.
- Entrada: Nenhuma.
- Saida: `{items: [...], total}`.
- Codigos HTTP: 200; 401; 403 `forbidden`.
- Funcoes: FUN-PY-API-024, FUN-PY-AUTH-007
- Consumidores: FUN-TS-API-004; FUN-TS-UI-018.
- Testes: Sem teste automatizado identificado.

### API-USER-002 — POST /api/v1/usuarios
- Status: Ativa
- Tipo: endpoint interno
- Arquivo: `backend/main.py`
- Metodo: POST
- Rota: /api/v1/usuarios
- Objetivo: Criar usuário (somente admin).
- Funcionamento: Normaliza e-mail para minúsculas, gera hash e insere; registra `usuario_criado`.
- Autenticacao: Bearer JWT + papel `admin`.
- Entrada: `{nome, email, senha, papel}`.
- Saida: `{id,nome,email,papel,ativo}`.
- Codigos HTTP: 201; 401; 403; 409 `email_exists`; 422 (validação Pydantic).
- Funcoes: FUN-PY-API-025, FUN-PY-AUTH-001
- Consumidores: FUN-TS-API-005; FUN-TS-UI-019.
- Testes: Sem teste automatizado identificado.

### API-USER-003 — PUT /api/v1/usuarios/{user_id}
- Status: Ativa
- Tipo: endpoint interno
- Arquivo: `backend/main.py`
- Metodo: PUT
- Rota: /api/v1/usuarios/{user_id}
- Objetivo: Atualizar qualquer usuário.
- Funcionamento: Aceita `nome`, `senha`, `papel` e `ativo`; converte senha em hash; 404 se não existir.
- Autenticacao: Bearer JWT + papel `admin`.
- Entrada: `{nome?, senha?, papel?, ativo?}`.
- Saida: `{id,nome,email,papel,ativo}`.
- Codigos HTTP: 200; 401; 403; 404 `user_not_found`; 422 `empty_update`.
- Funcoes: FUN-PY-API-026
- Consumidores: FUN-TS-API-006; FUN-TS-UI-020/021.
- Testes: Sem teste automatizado identificado.
- Observação: a rota permite que um admin desative a própria conta (não há proteção específica).

### API-USER-004 — DELETE /api/v1/usuarios/{user_id}
- Status: Ativa
- Tipo: endpoint interno
- Arquivo: `backend/main.py`
- Metodo: DELETE
- Rota: /api/v1/usuarios/{user_id}
- Objetivo: Desativar usuário (soft delete).
- Funcionamento: `UPDATE usuarios SET ativo=FALSE`; registra `usuario_desativado`.
- Autenticacao: Bearer JWT + papel `admin`.
- Entrada: Nenhuma (ID na rota).
- Saida: `{id, ativo: false}`.
- Codigos HTTP: 200; 401; 403; 404 `user_not_found`.
- Funcoes: FUN-PY-API-027
- Consumidores: FUN-TS-API-007; FUN-TS-UI-021.
- Testes: Sem teste automatizado identificado.

## DATA

### API-DATA-001 — GET /api/v1/estacoes
- Status: Ativa
- Tipo: endpoint interno
- Arquivo: `backend/main.py`
- Metodo: GET
- Rota: /api/v1/estacoes
- Objetivo: Listar estações com cota mínima e nível atual.
- Funcionamento: Filtra por `rio`, `municipio` e `ativa` (padrão `true`); junta `cotas_historicas` e a leitura mais recente de `telemetria`; renomeia campos para o contrato do frontend.
- Autenticacao: Nenhuma.
- Entrada: Query `rio?`, `municipio?`, `ativa?` (bool).
- Saida: `{items: [{codigo_estacao,nome_estacao,nome_rio,municipio,latitude,longitude,cota_minima_historica_m,nivel_atual_cm,atualizado_em}], total}`.
- Codigos HTTP: 200.
- Funcoes: FUN-PY-API-028
- Consumidores: FUN-TS-API-008; FUN-TS-DATA-002; FUN-TS-OFFLINE-005.
- Testes: `frontend/src/stores/estacoes.spec.ts`.

### API-DATA-002 — GET /api/v1/estacoes/{codigo}
- Status: Ativa
- Tipo: endpoint interno
- Arquivo: `backend/main.py`
- Metodo: GET
- Rota: /api/v1/estacoes/{codigo}
- Objetivo: Consultar uma estação pelo código ANA.
- Funcionamento: `SELECT` em `estacoes` por `codigo_estacao`.
- Autenticacao: Nenhuma.
- Entrada: `codigo` na rota.
- Saida: `{codigo_estacao,nome_estacao,nome_rio,municipio,latitude,longitude}`.
- Codigos HTTP: 200; 404 `station_not_found`.
- Funcoes: FUN-PY-API-029
- Consumidores: Nenhum identificado no frontend atual.
- Testes: Sem teste automatizado identificado.

### API-DATA-003 — GET /api/v1/niveis
- Status: Ativa
- Tipo: endpoint interno
- Arquivo: `backend/main.py`
- Metodo: GET
- Rota: /api/v1/niveis
- Objetivo: Consultar a série de telemetria de uma estação.
- Funcionamento: Exige estação existente e filtra por data inicial/final usando `substr(data_hora_medicao,1,10)`.
- Autenticacao: Bearer JWT.
- Entrada: Query `estacao`, `data_inicio`, `data_fim?`.
- Saida: `{estacao, items: [{data_hora,nivel_cm,chuva_mm,vazao}]}`.
- Codigos HTTP: 200; 401; 404 `station_not_found`.
- Funcoes: FUN-PY-API-030
- Consumidores: Nenhum identificado no frontend atual.
- Testes: Sem teste automatizado identificado.
- Observação: não valida `data_fim >= data_inicio` nem o limite de 90 dias previsto na documentação.

### API-DATA-004 — POST /api/v1/niveis/coletar
- Status: Ativa
- Tipo: endpoint interno
- Arquivo: `backend/main.py`
- Metodo: POST
- Rota: /api/v1/niveis/coletar
- Objetivo: Iniciar uma coleta manual de telemetria (níveis) na ANA.
- Funcionamento: Valida estações e período, cria um job em memória e inicia uma thread que consulta a API REST da ANA em lotes de 10 estações (janela de 30 dias). Retorna o job imediatamente; o andamento é consultado em API-DATA-005.
- Autenticacao: Bearer JWT + papel `admin`.
- Entrada: `{estacoes?: string[], periodo_inicio?: "AAAA-MM-DD"|null, periodo_fim?: "AAAA-MM-DD"|null}`; lista vazia = todas as estações telemétricas.
- Saida: `{job_id, status, estacoes_total, estacoes_processadas, leituras, inseridas, ignoradas, janela, periodo, mensagem, iniciado_em, finalizado_em}`.
- Codigos HTTP: 202; 401; 403; 409 (coleta em andamento); 422 (estação/período inválido).
- Funcoes: FUN-PY-API-031; FUN-PY-COL-065; FUN-PY-COL-066; FUN-PY-COL-067; FUN-PY-COL-068; FUN-PY-COL-069.
- Consumidores: FUN-TS-API-009; FUN-TS-UI-022; FUN-TS-UI-039.
- Testes: Verificação manual em produção (1 estação e lote completo).
- Observação: a API da ANA retorna somente os últimos 30 dias; o período filtra as leituras retornadas.

### API-DATA-005 — GET /api/v1/niveis/coletar/{job_id}
- Status: Ativa
- Tipo: endpoint interno
- Arquivo: `backend/main.py`
- Metodo: GET
- Rota: /api/v1/niveis/coletar/{job_id}
- Objetivo: Consultar o andamento de uma coleta manual.
- Funcionamento: Lê o job em memória (protegido por lock) e devolve o estado atual.
- Autenticacao: Bearer JWT + papel `admin`.
- Entrada: `job_id` no caminho.
- Saida: mesmo objeto do job (status `em_andamento`, `concluida` ou `erro`).
- Codigos HTTP: 200; 401; 403; 404.
- Funcoes: FUN-PY-API-045.
- Consumidores: FUN-TS-API-020; FUN-TS-UI-039.
- Testes: Verificação manual em produção.

## GRAPH

### API-GRAPH-001 — GET /api/v1/grafo/status
- Status: Ativa
- Tipo: endpoint interno
- Arquivo: `backend/main.py`
- Metodo: GET
- Rota: /api/v1/grafo/status
- Objetivo: Expor métricas do grafo de navegação.
- Funcionamento: Garante o carregamento do `RiverGraph` e retorna contagens; adiciona `area_ativa` fixa e `pronto: true`.
- Autenticacao: Nenhuma.
- Entrada: Nenhuma.
- Saida: `{nos, arestas, portos_associados, area_ativa, ultima_reconstrucao, pronto}`.
- Codigos HTTP: 200.
- Funcoes: FUN-PY-API-032, FUN-PY-ROUTE-005
- Consumidores: FUN-TS-API-010 (atualmente sem uso no frontend).
- Testes: Sem teste automatizado identificado.

## ROUTE

### API-ROUTE-001 — POST /api/v1/rotas/calcular
- Status: Ativa
- Tipo: endpoint interno
- Arquivo: `backend/main.py`
- Metodo: POST
- Rota: /api/v1/rotas/calcular
- Objetivo: Calcular rota navegável por distância.
- Funcionamento: Resolve origem/destino, executa Dijkstra com poda por calado+margem, monta GeoJSON e itens por trecho.
- Autenticacao: **Pública** (não exige JWT; decisão em aberto no projeto).
- Entrada: `{origem_nome, destino_nome, calado_m (0.5–6), margem_seguranca_m (0–3, padrão 0.5), velocidade_embarcacao_kmh (6–35), monitorar?}`.
- Saida: `{rota_id:null, origem, destino, distancia_total_km, tempo_total_h, custo_total, trechos_criticos, profundidade_minima_m, geojson, items}`.
- Codigos HTTP: 200; 404 `route_not_found`; 422 `port_without_segment`/validação.
- Funcoes: FUN-PY-API-033, FUN-PY-API-003, FUN-PY-ROUTE-006
- Consumidores: FUN-TS-API-012; FUN-TS-ROUTE-004.
- Testes: `frontend/src/stores/rota.spec.ts`.

### API-ROUTE-002 — POST /api/v1/rotas
- Status: Ativa
- Tipo: endpoint interno
- Arquivo: `backend/main.py`
- Metodo: POST
- Rota: /api/v1/rotas
- Objetivo: Salvar rota no histórico do usuário.
- Funcionamento: Insere parâmetros, métricas e GeoJSON; registra `rota_salva`.
- Autenticacao: Bearer JWT.
- Entrada: `{origem_nome, destino_nome, calado_m, margem_seguranca_m, velocidade_embarcacao_kmh, distancia_total_km, tempo_total_h, custo_total, trechos_criticos, profundidade_minima_m?, geojson?, monitorar?}`.
- Saida: Rota persistida (inclui `id`, `usuario_id`, `created_at`).
- Codigos HTTP: 201; 401; 422.
- Funcoes: FUN-PY-API-034, FUN-PY-API-008
- Consumidores: FUN-TS-API-013; FUN-TS-ROUTE-005; FUN-TS-OFFLINE-004.
- Testes: `frontend/src/stores/rota.spec.ts`, `frontend/src/stores/offline.spec.ts`.

### API-ROUTE-003 — GET /api/v1/rotas
- Status: Ativa
- Tipo: endpoint interno
- Arquivo: `backend/main.py`
- Metodo: GET
- Rota: /api/v1/rotas
- Objetivo: Listar rotas do usuário autenticado.
- Funcionamento: Filtra por `usuario_id` e ordena por `created_at DESC, id DESC`.
- Autenticacao: Bearer JWT.
- Entrada: Nenhuma.
- Saida: `{items, total}`.
- Codigos HTTP: 200; 401.
- Funcoes: FUN-PY-API-035, FUN-PY-API-008
- Consumidores: FUN-TS-API-014; FUN-TS-ROUTE-006; FUN-TS-OFFLINE-005; FUN-TS-NOTIFY-004.
- Testes: `frontend/src/stores/rota.spec.ts`, `frontend/src/stores/offline.spec.ts`.

### API-ROUTE-004 — GET /api/v1/rotas/{rota_id}
- Status: Ativa
- Tipo: endpoint interno
- Arquivo: `backend/main.py`
- Metodo: GET
- Rota: /api/v1/rotas/{rota_id}
- Objetivo: Consultar uma rota do próprio usuário.
- Funcionamento: Filtra por `id` e `usuario_id`.
- Autenticacao: Bearer JWT.
- Entrada: `rota_id` na rota.
- Saida: Rota persistida.
- Codigos HTTP: 200; 401; 404 `route_not_found`.
- Funcoes: FUN-PY-API-036
- Consumidores: FUN-TS-API-015 (sem uso atual).
- Testes: Sem teste automatizado identificado.

### API-ROUTE-005 — DELETE /api/v1/rotas/{rota_id}
- Status: Ativa
- Tipo: endpoint interno
- Arquivo: `backend/main.py`
- Metodo: DELETE
- Rota: /api/v1/rotas/{rota_id}
- Objetivo: Remover rota do histórico.
- Funcionamento: `DELETE ... WHERE id AND usuario_id`; `rota_alteracao` cai por `ON DELETE CASCADE`.
- Autenticacao: Bearer JWT.
- Entrada: `rota_id`.
- Saida: `{id, removida: true}`.
- Codigos HTTP: 200; 401; 404.
- Funcoes: FUN-PY-API-037
- Consumidores: FUN-TS-API-016; FUN-TS-ROUTE-007.
- Testes: `frontend/src/stores/rota.spec.ts`.

### API-ROUTE-006 — POST /api/v1/rotas/{rota_id}/monitorar
- Status: Ativa
- Tipo: endpoint interno
- Arquivo: `backend/main.py`
- Metodo: POST
- Rota: /api/v1/rotas/{rota_id}/monitorar
- Objetivo: Ativar/desativar monitoramento de uma rota.
- Funcionamento: Ao ativar, usa o destino como estação de referência, lê a cota atual como baseline e grava `monitorar`, `estacao_referencia`, `nivel_baseline_cm` e `ultima_verificacao`.
- Autenticacao: Bearer JWT.
- Entrada: `{monitorar: boolean}`.
- Saida: `{rota_id, monitorar, estacao_referencia, nivel_baseline_cm, limiar_variacao_cm, cooldown_min}`.
- Codigos HTTP: 200; 401; 404.
- Funcoes: FUN-PY-API-038, FUN-PY-API-003, FUN-PY-API-004
- Consumidores: FUN-TS-API-017; FUN-TS-ROUTE-008.
- Testes: `frontend/src/stores/rota.spec.ts`.

### API-ROUTE-007 — GET /api/v1/rotas/{rota_id}/alteracoes
- Status: Ativa
- Tipo: endpoint interno
- Arquivo: `backend/main.py`
- Metodo: GET
- Rota: /api/v1/rotas/{rota_id}/alteracoes
- Objetivo: Listar alterações de traçado de uma rota monitorada.
- Funcionamento: Valida propriedade e retorna `rota_alteracao` em ordem decrescente.
- Autenticacao: Bearer JWT.
- Entrada: `rota_id`.
- Saida: `{items: [{id,data_alteracao,motivo,variacao_nivel_cm,estacao_origem,distancia_total_km,custo_total,rota_geojson}]}`.
- Codigos HTTP: 200; 401; 404.
- Funcoes: FUN-PY-API-039, FUN-PY-API-005
- Consumidores: FUN-TS-API-018; FUN-TS-ROUTE-009; FUN-TS-NOTIFY-004.
- Testes: `frontend/src/stores/rota.spec.ts`, `frontend/src/stores/notificacao.spec.ts`.

### API-ROUTE-008 — GET /api/v1/ws (upgrade WebSocket)
- Status: Ativa
- Tipo: endpoint interno (WebSocket)
- Arquivo: `backend/main.py`
- Metodo: GET
- Rota: /api/v1/ws
- Objetivo: Entregar eventos de monitoramento por usuário.
- Funcionamento: Exige `token` na query, valida com `read_token`, aceita a conexão, assina a fila do `EventBus` e envia JSON até a desconexão.
- Autenticacao: Token HMAC na query string (`?token=`).
- Entrada: Query `token`.
- Saida: Mensagens `{evento, rota_id, motivo, variacao_nivel_cm, nova_distancia_km}`.
- Codigos HTTP: 101 (upgrade); 4401 (fechamento sem token/token inválido).
- Funcoes: FUN-PY-API-041, FUN-PY-AUTH-005, FUN-PY-EVENT-003/004
- Consumidores: FUN-TS-NOTIFY-008; FUN-TS-NOTIFY-001.
- Testes: `frontend/src/stores/notificacao.spec.ts`.

## ADMIN

### API-ADMIN-001 — GET /api/v1/logs
- Status: Ativa
- Tipo: endpoint interno
- Arquivo: `backend/main.py`
- Metodo: GET
- Rota: /api/v1/logs
- Objetivo: Consultar logs de auditoria.
- Funcionamento: Limita `limite` a 1–500 (padrão 100) e ordena por id decrescente.
- Autenticacao: Bearer JWT + papel `admin`.
- Entrada: Query `limite?`.
- Saida: `{items: [{id,usuario_id,tipo,detalhe,data_hora}], total}`.
- Codigos HTTP: 200; 401; 403.
- Funcoes: FUN-PY-API-040
- Consumidores: FUN-TS-API-011; FUN-TS-UI-023.
- Testes: Sem teste automatizado identificado.

### API-ADMIN-002 — POST /api/v1/monitor/executar
- Status: Ativa
- Tipo: endpoint interno
- Arquivo: `backend/main.py`
- Metodo: POST
- Rota: /api/v1/monitor/executar
- Objetivo: Executar manualmente um ciclo do vigia de rotas.
- Funcionamento: Chama `verificar_rotas_monitoradas`, publica eventos no `EventBus` e retorna a quantidade.
- Autenticacao: Bearer JWT + papel `admin`.
- Entrada: Nenhuma.
- Saida: `{eventos, itens}`.
- Codigos HTTP: 200; 401; 403.
- Funcoes: FUN-PY-API-042, FUN-PY-MON-003
- Consumidores: Nenhum identificado no frontend atual.
- Testes: Sem teste automatizado identificado.

## SYNC

### API-SYNC-001 — GET /api/v1/sync/snapshot
- Status: Ativa
- Tipo: endpoint interno
- Arquivo: `backend/main.py`
- Metodo: GET
- Rota: /api/v1/sync/snapshot
- Objetivo: Exportar grafo compacto para cálculo offline (RF022/RN016).
- Funcionamento: Lê `trechos_navegaveis` com distância via `ST_Length(geom::geography)`, opcionalmente filtrado por `bbox` WGS84; monta nós/arestas e associa estações via `estacoes_trechos`.
- Autenticacao: Bearer JWT.
- Entrada: Query `bbox?` (`minx,miny,maxx,maxy`).
- Saida: `{gerado_em, area, total_nos, total_arestas, nos:[[id,lon,lat]], arestas:[[fid,o,d,dist,prof]], estacoes:[[codigo,fid]]}`.
- Codigos HTTP: 200; 401; 422 `invalid_bbox`.
- Funcoes: FUN-PY-API-043
- Consumidores: FUN-TS-API-019; FUN-TS-OFFLINE-002.
- Testes: `frontend/src/stores/offline.spec.ts`.
- Observação: não inclui níveis, rotas nem geometria por aresta; o snapshot usa coordenadas de extremidades.

## EXTERNA

### API-EXTERNA-001 — GET https://www.ana.gov.br/hidrowebservice/EstacoesTelemetricas/OAUth/v1
- Status: Ativa
- Tipo: integração externa (ANA Hidro Webservice REST)
- Arquivo: `backend/ana_client.py`
- Metodo: GET
- Rota: /EstacoesTelemetricas/OAUth/v1
- Objetivo: Obter token JWT da ANA.
- Funcionamento: Envia headers `Identificador` e `Senha`; extrai `tokenautenticacao` de `items` e grava cache local por ~3500 s.
- Autenticacao: Credenciais `ANA_IDENTIFICADOR`/`ANA_SENHA` em headers.
- Entrada: Headers de credenciais.
- Saida: `{items: {tokenautenticacao, ...}}`.
- Codigos HTTP: 200; 4xx/5xx (cliente repete 417/429/500/502/503/504).
- Funcoes: FUN-PY-COL-005, FUN-PY-COL-004
- Consumidores: FUN-PY-COL-003/006/007; `_ultimas_leituras_ana`.
- Testes: Sem teste automatizado identificado.

### API-EXTERNA-002 — GET https://www.ana.gov.br/hidrowebservice/EstacoesTelemetricas/HidroRio/v1
- Status: Ativa
- Tipo: integração externa (ANA REST)
- Arquivo: `backend/ana_client.py`
- Metodo: GET
- Rota: /EstacoesTelemetricas/HidroRio/v1
- Objetivo: Consultar o catálogo de rios.
- Funcionamento: Parâmetros `Código do Rio`, `Data Atualização Inicial/Final`; retorna `items`.
- Autenticacao: Bearer JWT da ANA.
- Entrada: Query com filtros opcionais.
- Saida: `{items: [...]}`.
- Codigos HTTP: 200; 401 (reautentica uma vez); 4xx/5xx.
- Funcoes: FUN-PY-COL-008, FUN-PY-COL-007
- Consumidores: FUN-PY-COL-012.
- Testes: Sem teste automatizado identificado.

### API-EXTERNA-003 — GET https://www.ana.gov.br/hidrowebservice/EstacoesTelemetricas/HidroInventarioEstacoes/v1
- Status: Ativa
- Tipo: integração externa (ANA REST)
- Arquivo: `backend/ana_client.py`
- Metodo: GET
- Rota: /EstacoesTelemetricas/HidroInventarioEstacoes/v1
- Objetivo: Consultar o inventário de estações.
- Funcionamento: Filtros por código, UF, bacia e datas; retorna `items`.
- Autenticacao: Bearer JWT da ANA.
- Entrada: Query com filtros opcionais.
- Saida: `{items: [...]}`.
- Codigos HTTP: 200; 401; 4xx/5xx.
- Funcoes: FUN-PY-COL-009
- Consumidores: `backend/validar_estacoes.py` (FUN-PY-COL-064).
- Testes: Sem teste automatizado identificado.

### API-EXTERNA-004 — GET https://www.ana.gov.br/hidrowebservice/EstacoesTelemetricas/HidroinfoanaSerieTelemetricaAdotada/v2
- Status: Ativa
- Tipo: integração externa (ANA REST)
- Arquivo: `backend/ana_client.py`
- Metodo: GET
- Rota: /EstacoesTelemetricas/HidroinfoanaSerieTelemetricaAdotada/v2
- Objetivo: Obter leituras telemétricas adotadas (cota/vazão/chuva).
- Funcionamento: Consulta em lotes de 10 estações, com `Tipo Filtro Data=DATA_LEITURA`, `Data de Busca` e `Range Intervalo de busca=DIAS_30`.
- Autenticacao: Bearer JWT da ANA.
- Entrada: Query `Codigos_Estacoes`, `Tipo Filtro Data`, `Data de Busca`, `Range Intervalo de busca`.
- Saida: `{items: [{codigoestacao, Data_Hora_Medicao, Cota_Adotada, ...}]}`.
- Codigos HTTP: 200; 401; 4xx/5xx.
- Funcoes: FUN-PY-COL-023, FUN-PY-MON-001, FUN-PY-COL-007
- Consumidores: FUN-PY-COL-025; FUN-PY-MON-003.
- Testes: Sem teste automatizado identificado.

### API-EXTERNA-005 — POST https://telemetriaws1.ana.gov.br/ServiceANA.asmx/HidroSerieHistorica
- Status: Ativa
- Tipo: integração externa (ANA SOAP)
- Arquivo: `backend/ana_soap.py`
- Metodo: POST
- Rota: /ServiceANA.asmx/HidroSerieHistorica
- Objetivo: Obter a série histórica mensal de cotas/vazões/chuvas.
- Funcionamento: Envia formulário SOAP com `codEstacao`, `dataInicio`, `dataFim`, `tipoDados` e `nivelConsistencia`; parseia XML (`SerieHistorica`/`ErrorTable`).
- Autenticacao: Nenhuma (serviço público).
- Entrada: Form `codEstacao`, `dataInicio` (`dd/MM/yyyy`), `dataFim`, `tipoDados` (1 cota/2 chuva/3 vazão), `nivelConsistencia` (1 bruto/2 consistido).
- Saida: XML com registros mensais.
- Codigos HTTP: 200; 4xx/5xx.
- Funcoes: FUN-PY-COL-013
- Consumidores: FUN-PY-COL-016/018.
- Testes: Sem teste automatizado identificado.

### API-EXTERNA-006 — GET https://hydroweb.next.theia-land.fr/api/catalog/stac/search
- Status: Ativa
- Tipo: integração externa (STAC hydroweb.next)
- Arquivo: `backend/coletar_hydroweb.py`
- Metodo: GET
- Rota: /api/catalog/stac/search
- Objetivo: Listar estações virtuais de altimetria na bacia amazônica.
- Funcionamento: Pagina resultados (`limit=500`) seguindo links `next`, para a coleção `HYDROWEB_RIVERS_OPE`.
- Autenticacao: Nenhuma (catálogo público).
- Entrada: Query `collections`, `bbox`, `limit`.
- Saida: `{features: [...], links: [...]}`.
- Codigos HTTP: 200; 4xx/5xx.
- Funcoes: FUN-PY-COL-035, FUN-PY-COL-032
- Consumidores: FUN-PY-COL-048/050.
- Testes: Sem teste automatizado identificado.

### API-EXTERNA-007 — INTEGRAÇÃO py_hydroweb (DownloadBasket)
- Status: Ativa
- Tipo: integração externa (biblioteca `py_hydroweb`; rota HTTP não exposta no código)
- Arquivo: `backend/coletar_hydroweb.py`
- Metodo: A verificar
- Rota: A verificar (definida pela biblioteca)
- Objetivo: Baixar coleções NetCDF/TXT do hydroweb.next.
- Funcionamento: Cria `Client` e `DownloadBasket.add_collection(collection_id, bbox)`, chama `submit_and_download_zip`.
- Autenticacao: `HYDROWEB_API_KEY` (lida do ambiente; o cliente da biblioteca a utiliza).
- Entrada: Coleção, bbox e nome do zip.
- Saida: Arquivo `.zip`.
- Codigos HTTP: A verificar (gerenciado pela biblioteca).
- Funcoes: FUN-PY-COL-036, FUN-PY-COL-033
- Consumidores: FUN-PY-COL-050/051/052.
- Testes: Sem teste automatizado identificado.
- Observação: integração identificada pelo cliente, sem rota explícita no repositório; não foi inventado endpoint.

### API-EXTERNA-008 — GET https://legisla.imprensaoficial.am.gov.br/diario_am/pesquisar
- Status: Ativa
- Tipo: integração externa (Legisla.AM)
- Arquivo: `backend/coletar_legisla_am.py`
- Metodo: GET
- Rota: /diario_am/pesquisar
- Objetivo: Buscar decretos por palavras-chave.
- Funcionamento: Query `q` e `page`; HTML server-rendered parseado com BeautifulSoup.
- Autenticacao: Nenhuma.
- Entrada: Query `q`, `page`.
- Saida: HTML.
- Codigos HTTP: 200; 4xx/5xx.
- Funcoes: FUN-PY-COL-056, FUN-PY-COL-055
- Consumidores: FUN-PY-COL-060.
- Testes: Sem teste automatizado identificado.

### API-EXTERNA-009 — GET URL do decreto (página de detalhe)
- Status: Ativa
- Tipo: integração externa (Legisla.AM)
- Arquivo: `backend/coletar_legisla_am.py`
- Metodo: GET
- Rota: URL retornada pela busca (dinâmica)
- Objetivo: Extrair título, ementa e corpo completo do decreto.
- Funcionamento: Requisição à URL absoluta do resultado, parse de `div.materia`.
- Autenticacao: Nenhuma.
- Entrada: URL do resultado.
- Saida: HTML.
- Codigos HTTP: 200; 4xx/5xx.
- Funcoes: FUN-PY-COL-057, FUN-PY-COL-055
- Consumidores: FUN-PY-COL-060.
- Testes: Sem teste automatizado identificado.
