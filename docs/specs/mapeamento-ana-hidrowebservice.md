# Mapeamento da API ANA — Hidro Webservice (REST)

Data do mapeamento: 17/08/2026
Fonte: Swagger UI oficial (`https://www.ana.gov.br/hidrowebservice/swagger-ui/`)
Specs extraídos: `https://www.ana.gov.br/hidrowebservice/api-docs/swagger-config`
(existem 2 versões: `v1.0.3984.2` e `v2.0.6581.0`)

---

## 1. Visão Geral

| Item | Valor |
|---|---|
| **Base URL** | `https://www.ana.gov.br/hidrowebservice` |
| **Formato** | JSON (OpenAPI 3.0.1) |
| **Autenticação** | Bearer Token (JWT) — exceto `OAUth/v1` (login) |
| **Contato** | `stiatende@ana.gov.br` |
| **Documentação manual** | `https://www.ana.gov.br/hidrowebservice/manual` |
| **Tag** | `WSEstacoesTelemetricasController` — Consultas Hidro Webservice |

> **⚠️ Importante:** diferente do Web Service SOAP público de telemetria
> (`telemetriaws1.ana.gov.br`, sem login), esta API REST exige **autenticação JWT**
> (credenciais **já obtidas** — no `.env` da raiz do projeto, ignorado pelo git).

---

## 2. Autenticação

### POST/GET OAUth/v1 — Login

`GET /EstacoesTelemetricas/OAUth/v1`

| Header | Obrigatório | Descrição |
|---|---|---|
| `Identificador` | Sim | Usuário / IDENTIFICADOR |
| `Senha` | Sim | Senha |

Retorna `Devolucao` com o token a ser usado nas demais chamadas.

> ✅ **Testado em 17/08/2026** — login OK (status 200). No retorno:
> - `tokenautenticacao` → **JWT válido** para `Authorization: Bearer <token>`.
> - `token` → **NÃO serve** como Bearer (retorna 401); é um id interno.
> - `validade` → ~1h (iat/exp no payload do JWT). Token atual: `C:\...\` (não versionar).

### OAUthPermissoes/v1 — Verificar permissões

`GET /EstacoesTelemetricas/OAUthPermissoes/v1`

| Header | Obrigatório | Descrição |
|---|---|---|
| `accesstoken` | Sim | Access Token (SSO) |
| `clientid` | Sim | Client ID |

---

## 3. Estrutura de Resposta Comum (schema `Devolucao`)

Todas as chamadas retornam:

```json
{
  "status": "200 OK",
  "code": 200,
  "message": "Chamada Realizada com Sucesso",
  "items": { }
}
```

| Campo | Tipo | Descrição |
|---|---|---|
| `status` | string | Código HTTP textual |
| `code` | integer | Código HTTP numérico |
| `message` | string | Mensagem |
| `items` | object | **Payload da consulta** (varia por endpoint) |

Erros possíveis: `417` (Expectativa falha), `401` (Não autorizado), `406`
(Parâmetro não aceitável), `500` (Erro inesperado).

---

## 4. Parâmetros Compartilhados

### `Tipo Filtro Data` (obrigatório na maioria)

| Valor | Significado |
|---|---|
| `DATA_LEITURA` | Filtra pela data/hora da leitura |
| `DATA_ULTIMA_ATUALIZACAO` | Filtra pela data de última atualização do registro |

### `Range Intervalo de busca` (séries telemétricas v1/v2)

Valores possíveis:
`MINUTO_5, MINUTO_10, MINUTO_15, MINUTO_30, HORA_1 ... HORA_24, DIAS_2, DIAS_7, DIAS_14, DIAS_21, DIAS_30`

> Na **v1** também aparecem os ranges `DIAS_7/14/21/30`; na **v2** idem. Limite de
> **30 dias** por requisição nas séries telemétricas.

### Intervalo explícito (séries de 366 dias)

| Parâmetro | Formato |
|---|---|
| `Data Inicial` | `yyyy-MM-dd` |
| `Data Final` | `yyyy-MM-dd` |
| `Horário Inicial` | `HH:mm:ss` (opcional) |
| `Horário Final` | `HH:mm:ss` (opcional) |

> Séries de estações convencionais (coleta manual) aceitam até **366 dias** por requisição.

---

## 5. Endpoints — Versão v2.0.6581.0 (séries multi-estação)

> A **v2** é a mais relevante para o projeto: permite consultar **até 10 estações**
> por requisição (códigos separados por vírgula).

| Método | Rota | Máx. estações | Limite período | Descrição |
|---|---|---|---|---|
| GET | `/EstacoesTelemetricas/HidroinfoanaSerieTelemetricaAdotada/v2` | 10 | 30 dias | Dados **adotados** de chuva, nível e vazão |
| GET | `/EstacoesTelemetricas/HidroinfoanaSerieTelemetricaDetalhada/v2` | 10 | 30 dias | Dados adotados **+ brutos** disponíveis |

### Parâmetros (v2)

| Parâmetro | Obrigatório | Descrição |
|---|---|---|
| `Codigos_Estacoes` | Sim | Códigos separados por vírgula (máx. 10) |
| `Tipo Filtro Data` | Sim | `DATA_LEITURA` / `DATA_ULTIMA_ATUALIZACAO` |
| `Data de Busca` | Não | `yyyy-MM-dd` (relativo ao tipo de filtro) |
| `Range Intervalo de busca` | Sim | `MINUTO_5` ... `DIAS_30` |

---

## 6. Endpoints — Versão v1.0.3984.2 (completo)

> Versão com todos os endpoints (inclusive inventários, séries históricas de estações
> convencionais e HidroSat). Séries telemétricas aceitam **1 estação** por chamada.

### 6.1. Séries Telemétricas (nível/vazão/chuva em tempo real)

| Método | Rota | Descrição |
|---|---|---|
| GET | `/EstacoesTelemetricas/HidroinfoanaSerieTelemetricaAdotada/v1` | Dados adotados de chuva, nível e vazão (30 dias) |
| GET | `/EstacoesTelemetricas/HidroinfoanaSerieTelemetricaDetalhada/v1` | Adotados + brutos (30 dias) |

Parâmetros: `Código da Estação` (integer), `Tipo Filtro Data`, `Data de Busca`, `Range Intervalo de busca`.

### 6.2. Séries de Estações Convencionais (coleta manual, até 366 dias)

| Método | Rota | Descrição |
|---|---|---|
| GET | `HidroSerieCotas/v1` | Séries de **cota** (nível) |
| GET | `HidroSerieChuva/v1` | Séries de **chuva** |
| GET | `HidroSerieVazao/v1` | Séries de **vazão** |
| GET | `HidroSerieResumoDescarga/v1` | Medições de descarga líquida |
| GET | `HidroSerieCurvaDescarga/v1` | Curvas de descarga líquida |
| GET | `HidroSeriePerfilTransversal/v1` | Perfil transversal da estação |
| GET | `HidroSerieGranulometria/v1` | Granulometria |
| GET | `HidroSerieSedimentos/v1` | Sedimentos em suspensão |
| GET | `HidroSerieQA/v1` | Qualidade de água |

Parâmetros comuns: `Código da Estação`, `Tipo Filtro Data`, `Data Inicial`, `Data Final`,
`Horário Inicial` (opc.), `Horário Final` (opc.).
`HidroSerieCurvaDescarga/v1` **não** tem `Tipo Filtro Data`.

> **⛔ INOPERANTE (testado em 17/08/2026):** `HidroSerieCotas`, `HidroSerieVazao` e
> `HidroSerieChuva` (v1) retornam **400 Bad Request** para **qualquer** combinação de
> parâmetros (inclusive vazio, sem estação, sem datas). Os endpoints existem no Swagger,
> mas o controller não responde. **Solução:** usar o SOAP público
> `HidroSerieHistorica` (veja seção 10).

### 6.3. Inventário e Tabelas de Referência

| Método | Rota | Descrição | Filtros |
|---|---|---|---|
| GET | `HidroInventarioEstacoes/v1` | **Inventário completo de estações** | Cód. Estação, Cód. Bacia, **UF**, Data Atualização Inicial/Final |
| GET | `HidroUF/v1` | Unidades federativas | Cód. UF, Data Atualização |
| GET | `HidroBacia/v1` | Bacias hidrográficas | Cód. Bacia, Data Atualização |
| GET | `HidroSubBacia/v1` | Sub-bacias | Cód. Sub-Bacia, Data Atualização |
| GET | `HidroRio/v1` | Corpos hídricos / rios | Cód. Rio, Data Atualização |
| GET | `HidroMunicipio/v1` | Municípios (código próprio da ANA, ≠ IBGE) | Cód. Município, Data Atualização |
| GET | `HidroEntidade/v1` | Entidades (responsável/operador da estação) | Cód. Entidade, Data Atualização |

### 6.4. HidroSat — Estações Virtuais (satélite)

| Método | Rota | Descrição |
|---|---|---|
| GET | `HidrosatInventarioEstacoes/v1` | Inventário de estações virtuais (estimação por satélite) — sem limite de busca |
| GET | `HidrosatSerieDados/v1` | Séries de altimetria (até 366 dias) |

---

## 7. Mapeamento para o HidroWize

| Necessidade do projeto | Endpoints recomendados | Observações |
|---|---|---|
| **Cotas/nível em tempo real** (RF06/RF09) | `HidroinfoanaSerieTelemetricaAdotada/v2` | Até 10 estações/requisição; usar `Range` horário |
| **Vazão em tempo real** | `HidroinfoanaSerieTelemetricaAdotada/v2` | Retorna chuva, nível e vazão adotados |
| **Série histórica de cotas** (mínima histórica p/ navegabilidade) | SOAP `HidroSerieHistorica` (tipoDados=1) | REST `HidroSerieCotas/v1` **inoperante**; SOAP mescla níveis bruto+consistido |
| **Vazão histórica** | `HidroSerieVazao/v1` | Coleta manual; até 366 dias |
| **Lista de estações (localização)** | `HidroInventarioEstacoes/v1` (UF=AM) | Substitui/valida o `estacoes_am.csv` |
| **Catálogo de rios/municípios/bacias** | `HidroRio/v1`, `HidroMunicipio/v1`, `HidroBacia/v1`, `HidroSubBacia/v1` | Código de município difere do IBGE |
| **Estações sem medição no terreno** | `HidrosatInventarioEstacoes/v1` + `HidrosatSerieDados/v1` | Dados por altimetria de satélite |

### Fluxo sugerido no coletor (backend FastAPI)

1. **Login**: `GET /EstacoesTelemetricas/OAUth/v1` com credenciais → guardar token.
2. **Inventário**: `HidroInventarioEstacoes/v1?Unidade%20Federativa=AM` → estações do trecho.
3. **Tempo real**: `HidroinfoanaSerieTelemetricaAdotada/v2?Codigos_Estacoes=14990000,...` →
   cota/vazão mais recente (cache para o modo offline — RF11/RF12).
4. **Histórico (cota mínima)**: SOAP `HidroSerieHistorica` por estação → base da regra de navegabilidade.

---

## 8. Exemplo de Requisição (token + séries v2)

```bash
# 1. Login
curl -X GET "https://www.ana.gov.br/hidrowebservice/EstacoesTelemetricas/OAUth/v1" \
  -H "Identificador: SEU_USUARIO" \
  -H "Senha: SUA_SENHA"
# → pegar o campo "tokenautenticacao" (JWT) do retorno

# 2. Séries adotadas (JWT, com Data de Busca + Range)
curl -X GET "https://www.ana.gov.br/hidrowebservice/EstacoesTelemetricas/HidroinfoanaSerieTelemetricaAdotada/v2" \
  -H "Authorization: Bearer SEU_TOKEN" \
  -G \
  -d "Codigos_Estacoes=14990000" \
  -d "Tipo Filtro Data=DATA_LEITURA" \
  -d "Data de Busca=2026-08-17" \
  -d "Range Intervalo de busca=DIAS_2"
```

### Resultado validado (estação Manaus 14990000, 17/08/2026)

Com `Tipo Filtro Data=DATA_LEITURA` é **necessário** informar `Data de Busca` + `Range`
(≥ DIAS_2), senão o endpoint retorna vazio (`"message": "Nǜo houve retorno de registros"`).
Campos do item retornado:

| Campo | Exemplo | Descrição |
|---|---|---|
| `codigoestacao` | `14990000` | Código da estação |
| `Data_Hora_Medicao` | `2026-08-17 00:00:00.0` | Data/hora da medição |
| `Cota_Adotada` | `2600.00` | Nível (cota) adotado, em cm |
| `Cota_Adotada_Status` | `0` | Status da cota |
| `Chuva_Adotada` | `0.00` | Precipitação adotada, em mm |
| `Chuva_Adotada_Status` | `0` | Status da chuva |
| `Vazao_Adotada` | `null` | Vazão adotada (nem toda estação mede) |
| `Vazao_Adotada_Status` | `null` | Status da vazão |
| `Data_Atualizacao` | `2026-08-17 00:53:40.62` | Última atualização do registro |

---

## 9. Conclusões e Recomendações

1. **Adotar a v2** para séries telemétricas (10 estações/requisição → menos chamadas).
2. Usar a **v1** para inventário e catálogos; para **histórico de cotas**, usar o
   **SOAP `HidroSerieHistorica`** (a v1 `HidroSerieCotas` está inoperante).
3. Credenciais da API REST **já obtidas e validadas** (no `.env` da raiz, ignorado pelo
   git). Usar `ANA_IDENTIFICADOR`/`ANA_SENHA` para o login e renovar o JWT a cada ~1h.
   Manter o SOAP público (`telemetriaws1.ana.gov.br`) como fallback de cotas em tempo real.
4. Planejar **cache/offline** (RF11/RF12) nas respostas das séries telemétricas,
   pois são o dado mais sensível a latência e limites de 30 dias por consulta.

---

## 10. SOAP `HidroSerieHistorica` — histórico de cotas (SOLUÇÃO VALIDADA)

A REST `HidroSerieCotas/v1` está inoperante; a alternativa validada é o Web Service
SOAP público de telemetria (`telemetriaws1.ana.gov.br`), sem autenticação.

| Item | Valor |
|---|---|
| URL | `POST https://telemetriaws1.ana.gov.br/ServiceANA.asmx/HidroSerieHistorica` |
| Parâmetros | `codEstacao`, `dataInicio` (dd/MM/yyyy), `dataFim` (vazio = até o mais recente), `tipoDados` (1=Cotas, 2=Chuvas, 3=Vazões), `nivelConsistencia` (1=Bruto, 2=Consistido) |
| Retorno | XML (`DataTable`) com 1 registro por **mês**: `Minima`, `Maxima`, `Media`, `DiaMinima`, `DiaMaxima`, `Cota01..Cota31` (cotas diárias), campos `*Status` (0=ok) |

**Observações (testado 17/08/2026):**
- O nível **Consistido (2)** cobre períodos antigos (ex.: até 2023-12) e o **Bruto (1)**
  os recentes — **mesclar ambos** para cobertura completa.
- Filtrar por `Status=0` e descartar valores ≤ 0 (o `Minima` pode trazer leituras
  inválidas, ex. `-74`).
- Estações puramente telemétricas (ex.: **Manaus 14990000**) e UHEs de reservatório
  podem **não ter dados** nessa base (HIDRO convencional). Para elas, usar o mínimo
  acumulado via telemetria (últimos 30 dias) ou a cota de referência da estação.

**Exemplo (estação 15400000 Porto Velho):**

```bash
curl -X POST "https://telemetriaws1.ana.gov.br/ServiceANA.asmx/HidroSerieHistorica" \
  -d "codEstacao=15400000" -d "dataInicio=01/01/2024" \
  -d "tipoDados=1" -d "nivelConsistencia=1"
```

**Entregável:** `backend/coletar_cotas_historicas.py` gerou `backend/cotas_historicas_am.csv`
(56 de 75 estações AM com histórico; Manaus e UHEs sem dados na base).

### Complemento — histórico via telemetria (REST v2)

Para estações sem dados no SOAP (ex.: Manaus 14990000, UHEs), o coletor
`backend/coletar_telemetria.py` acumula incrementalmente as leituras telemétricas
(últimos 30 dias por execução) em `backend/telemetria_cotas_am.csv`, com dedup
por (estação, data/hora). Execuções periódicas constroem a baseline histórica.
`--resumo` mostra min/max/média por estação. O token JWT é cacheado em
`backend/.ana_token.json` (gitignored) e o cliente tem retry automático
(6 tentativas, backoff 5s) para os erros transitórios da ANA (417/503/504).

**Resultado (17/08/2026):** 128.237 leituras acumuladas; Manaus 14990000 →
cota 2591–2800 cm (2.764 leituras).
