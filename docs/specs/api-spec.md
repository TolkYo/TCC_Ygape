# Especificacao da API

## Convencoes
- **Base URL**: `http://localhost:8000/api/v1`
- **Autenticacao**: Bearer Token (JWT) — exceto login
- **Formato**: JSON
- **Erros**: retorno padrao `{ "success": false, "error": { "code": "...", "message": "..." } }`
- **Sucesso**:
  ```json
  {
    "success": true,
    "data": {}
  }
  ```

---

## Autenticacao

| Metodo | Rota | Auth | Descricao |
|--------|------|------|-----------|
| POST | /auth/login | Nao | Autenticar e retornar token |
| GET | /auth/me | Sim | Dados do usuario logado |
| PUT | /auth/me | Sim | Atualizar proprio perfil/senha |

### POST /auth/login

**Request**:
```json
{ "email": "piloto@exemplo.com", "senha": "segredo123" }
```

**Response 200**:
```json
{
  "success": true,
  "data": {
    "access_token": "eyJhbGciOi...",
    "token_type": "bearer",
    "expires_in": 28800,
    "usuario": { "id": 1, "nome": "Maria Piloto", "email": "piloto@exemplo.com", "papel": "piloto" }
  }
}
```

**Erros**: 401 (credenciais invalidas), 403 (usuario desativado).

---

## Usuarios (admin)

| Metodo | Rota | Auth | Descricao |
|--------|------|------|-----------|
| GET | /usuarios | admin | Listar usuarios |
| POST | /usuarios | admin | Criar usuario |
| PUT | /usuarios/{id} | admin | Atualizar usuario |
| DELETE | /usuarios/{id} | admin | Desativar/remover usuario |

### POST /usuarios

**Request**:
```json
{ "nome": "Joao Piloto", "email": "joao@exemplo.com", "senha": "segredo123", "papel": "piloto" }
```

**Response 201**: usuario criado (sem senha).
**Erros**: 409 (email ja existe), 422 (dados invalidos).

---

## Estacoes

| Metodo | Rota | Auth | Descricao |
|--------|------|------|-----------|
| GET | /estacoes | Nao | Listar estacoes/portos para o planejador |
| GET | /estacoes/{codigo} | Nao | Detalhar estacao |

### GET /estacoes

**Query Params**:
| Param | Tipo | Obrigatorio | Default | Descricao |
|-------|------|------------|---------|-----------|
| rio | string | Nao | - | Filtro por nome do rio |
| municipio | string | Nao | - | Filtro por municipio |
| ativa | boolean | Nao | true | Somente ativas |

**Response 200**:
```json
{
  "success": true,
  "data": {
    "items": [
      {
        "codigo_estacao": "14990000",
        "nome_estacao": "MANAUS",
        "nome_rio": "RIO NEGRO",
        "municipio": "MANAUS",
        "latitude": -3.13830,
        "longitude": -60.02720,
        "cota_minima_historica_m": 2.80,
        "nivel_atual_cm": 2603.00,
        "atualizado_em": "2026-08-16T15:45:00Z"
      }
    ],
    "total": 12
  }
}
```

---

## Niveis

| Metodo | Rota | Auth | Descricao |
|--------|------|------|-----------|
| GET | /niveis | Sim | Serie temporal de niveis |
| POST | /niveis/coletar | admin | Forcar coleta ANA |

### GET /niveis

**Query Params**:
| Param | Tipo | Obrigatorio | Default | Descricao |
|-------|------|------------|---------|-----------|
| estacao | string | Sim | - | Codigo da estacao |
| data_inicio | date | Sim | - | Inicio (YYYY-MM-DD) |
| data_fim | date | Nao | hoje | Fim (YYYY-MM-DD) |

**Response 200**:
```json
{
  "success": true,
  "data": {
    "estacao": "14990000",
    "items": [
      { "data_hora": "2026-08-16T15:45:00Z", "nivel_cm": 2603.0, "chuva_mm": 0.0, "vazao": null }
    ],
    "cota_minima_historica_m": 2.80
  }
}
```

**Erros**: 422 (janela > 90 dias), 404 (estacao nao encontrada).

### POST /niveis/coletar

**Request**:
```json
{ "estacoes": ["14990000", "16030000"], "periodo_inicio": "2026-08-16", "periodo_fim": "2026-08-16" }
```
*(Se `estacoes` vazio, coleta todas do trecho.)*

**Response 202**:
```json
{ "success": true, "data": { "coletadas": 2, "leituras_gravadas": 128, "falhas": [] } }
```

---

## Roteamento

| Metodo | Rota | Auth | Descricao |
|--------|------|------|-----------|
| POST | /rotas/calcular | Nao | Calcular rota sobre a malha hidroviária pública |
| POST | /rotas | Sim | Salvar rota calculada no historico do usuario |
| GET | /rotas/{id} | Sim | Detalhar rota salva |
| GET | /rotas | Sim | Historico do usuario |
| DELETE | /rotas/{id} | Sim | Remover rota do historico |
| GET | /grafo/status | Sim | Estado do grafo (nos/arestas) |
| POST | /rotas/{id}/monitorar | Sim | Ativar/desativar monitoramento (RF027) |
| GET | /rotas/{id}/alteracoes | Sim | Historico de recomputacoes (RF030) |

### POST /rotas/calcular

**Request**:
```json
{
  "origem_nome": "MANAUS",
  "destino_nome": "ITACOATIARA",
  "calado_m": 4.5,
  "margem_seguranca_m": 0.5,
  "velocidade_embarcacao_kmh": 20,
  "monitorar": true
}
```

**Response 200**:
```json
{
  "success": true,
  "data": {
    "rota_id": 15,
    "origem": "MANAUS",
    "destino": "ITACOATIARA",
    "distancia_total_km": 194.32,
    "tempo_total_h": 10.1,
    "custo_total": 10.1,
    "trechos_criticos": 2,
    "geojson": {
      "type": "FeatureCollection",
      "features": []
    },
    "items": [
      { "no_origem": "M1", "no_destino": "M2", "distancia_km": 12.4, "profundidade_m": 6.1, "tempo_h": 0.6, "transitavel": true }
    ]
  }
}
```

**Erros**: 422 (calado invalido), 404 (origem/destino inexistentes ou rota nao encontrada),
500 (grafo nao carregado).

### POST /rotas

Salva uma rota calculada no historico do usuario autenticado (RF025).

**Request**:
```json
{
  "origem_nome": "MANAUS",
  "destino_nome": "ITACOATIARA",
  "calado_m": 3.2,
  "margem_seguranca_m": 0.5,
  "velocidade_embarcacao_kmh": 12,
  "distancia_total_km": 194.32,
  "tempo_total_h": 16.19,
  "custo_total": 16.19,
  "trechos_criticos": 2,
  "profundidade_minima_m": 4.1,
  "geojson": { "type": "FeatureCollection", "features": [] },
  "monitorar": false
}
```

**Response 201**: objeto da rota salva (campo `id`, `rota_geojson`, `monitorar`, `created_at`).
**Erros**: 401 (sem token), 422 (dados invalidos).

### GET /rotas

Historico do usuario autenticado, ordenado por `created_at` decrescente.
**Response 200**: `{ "items": [ { "id": 15, "origem_nome": "MANAUS", ... } ], "total": 1 }`

### GET /rotas/{id}

Detalha uma rota salva do proprio usuario. **Erros**: 404 (nao encontrada ou de outro usuario).

### DELETE /rotas/{id}

Remove uma rota do historico do proprio usuario. **Response 200**: `{ "id": 15, "removida": true }`.

### POST /rotas/{id}/monitorar

Ativa ou desativa o monitoramento de nivel da rota (RF027).

**Request**:
```json
{ "monitorar": true }
```

**Response 200**:
```json
{
  "success": true,
  "data": {
    "rota_id": 15,
    "monitorar": true,
    "limiar_variacao_cm": 30,
    "cooldown_min": 30
  }
}
```

**Erros**: 404 (rota nao encontrada ou de outro usuario).

### GET /rotas/{id}/alteracoes

Historico de recomputacoes da rota monitorada (RF030).

**Response 200**:
```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": 3,
        "data_alteracao": "2026-08-16T14:10:00Z",
        "motivo": "variacao_nivel",
        "variacao_nivel_cm": 32.0,
        "estacao_origem": "15040000",
        "distancia_total_km": 197.55,
        "custo_total": 218.20,
        "rota_geojson": {}
      }
    ]
  }
}
```

### GET /grafo/status

**Response 200**:
```json
{
  "success": true,
  "data": {
    "nos": 842,
    "arestas": 1187,
      "area_ativa": "bacia-amazonica",
    "ultima_reconstrucao": "2026-08-15T10:00:00Z"
  }
}
```

---

## Sincronizacao

| Metodo | Rota | Auth | Descricao |
|--------|------|------|-----------|
| GET | /sync/snapshot | Sim | Ultimo snapshot (rotas, niveis, profundidades) |
| POST | /sync/push | Sim | Enviar rotas/logs locais |

### GET /sync/snapshot

**Response 200**:
```json
{
  "success": true,
  "data": {
    "gerado_em": "2026-08-16T16:00:00Z",
    "grafo": {
    "area_ativa": "bacia-amazonica",
      "nos": 842,
      "arestas": [
        { "id": 1, "no_origem": 10, "no_destino": 11, "distancia_m": 12400,
          "cota_fundo_batimetria_m": 21.5, "largura_canal_m": 1800 }
      ]
    },
    "estacoes": [],
    "niveis": [],
    "profundidades": [],
    "minhas_rotas": []
  }
}
```

**Nota**: o snapshot inclui o **grafo do trecho ativo** (nos, arestas, cota de fundo, largura) para
permitir o recálculo offline (RF022/RN026). Arestas desconhecidas chegam com `cota_fundo_batimetria_m = null`.

### POST /sync/push

**Request**:
```json
{
  "rotas_locais": [
    { "origem_nome": "MANAUS", "destino_nome": "ITACOATIARA", "calado_m": 3.2,
      "geojson": {}, "created_at_local": "2026-08-16T14:00:00Z" }
  ],
  "logs": []
}
```

**Response 200**: `{ "success": true, "data": { "rotas_recebidas": 3, "conflitos": 0 } }`

---

## WebSocket (Notificacoes em Tempo Real)

| Conexao | Auth | Descricao |
|---------|------|-----------|
| `WS /ws` | Token no header | Canal de eventos do usuario logado (RF034) |

### Eventos emitidos pelo backend

| Evento | Payload | Descricao |
|--------|---------|-----------|
| `rota_alterada` | `{ "rota_id": 15, "motivo": "variacao_nivel", "variacao_nivel_cm": 32, "nova_distancia_km": 197.55 }` | Tracado de rota monitorada mudou (RF029) |
| `nivel_atualizado` | `{ "estacao": "15040000", "nivel_cm": 945, "data_hora": "..." }` | Nova leitura em estacao do trecho |

### Fallback

Se o WebSocket nao estiver disponivel (rede corporativa/proxy), o front-end faz polling de
`GET /rotas/{id}/alteracoes` a cada 5 minutos (RN027).

---

## Logs (auditoria)

| Metodo | Rota | Auth | Descricao |
|--------|------|------|-----------|
| GET | /logs | admin | Eventos recentes da aplicacao (login, usuarios, rotas) |

**Query Params**: `limite` (int, default 100, max 500).

**Response 200**:
```json
{
  "success": true,
  "data": {
    "items": [
      { "id": 12, "usuario_id": 2, "tipo": "rota_salva", "detalhe": "Rota MANAUS → ITACOATIARA", "data_hora": "2026-10-11 13:20:00" }
    ],
    "total": 1
  }
}
```

---

## Erros Globais

| Codigo | Condicao |
|--------|----------|
| 400 | Requisicao malformada |
| 401 | Token ausente/invalido/expirado |
| 403 | Sem permissao (papel incorreto) |
| 404 | Recurso nao encontrado |
| 409 | Conflito (ex: email duplicado) |
| 422 | Erro de validacao de dados |
| 500 | Erro interno do servidor |
| 504 | Timeout na integracao com ANA |
