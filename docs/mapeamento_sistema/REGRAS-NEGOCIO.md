# REGRAS DE NEGÓCIO

> Catálogo de regras do projeto Ygapé/HidroWize (verificado no código em 2026-10-20).
> Este documento descreve **o que o sistema deve cumprir** e o que o código efetivamente faz. As referências de implementação ficam em `FUNCOES.md` e `API-END.md`.
> A numeração legada (`RN001`…`RN029`) de `docs/specs/regras-negocio.md` é preservada no campo **Origem legada** para rastreabilidade; os IDs canônicos deste catálogo são `RN-<DOMINIO>-<NNN>` e nunca são reciclados.

## 1. Objetivo e utilização

- Manter regras identificáveis, testáveis e rastreáveis entre requisito, código e contrato HTTP.
- Separar **regra documentada**, **comportamento verificado** e **mudança proposta**.
- Permitir análise de impacto antes de alterar comportamento.
- Alterar este Markdown **não autoriza** mudar código; a implementação exige pedido explícito e aprovação conforme o fluxo do agente.

## 2. Convenções

- ID: `RN-<DOMINIO>-<NNN>` (domínios: `AUTH`, `CAD`, `COL`, `ROTA`, `NIVEL`, `MON`, `BAT`, `SYNC`, `NAV`, `ETL`).
- Status usados: **Implementada** (código + evidência de teste), **Aprovada** (código cumpre, sem teste automatizado específico), **Parcial** (código cumpre parte ou há divergência documentada), **Proposta** (não implementada), **Substituída**, **Revogada**.
- `docs/specs/regras-negocio.md` é a origem histórica; divergências estão explicitadas em cada entrada. Não foram feitas alterações no código durante este mapeamento.
- Referências `FUN-*`/`API-*` apontam somente para registros existentes nos catálogos.

## 3. Índice das regras

| ID | Domínio | Regra | Status | Prioridade | Implementações relacionadas |
| --- | --- | --- | --- | --- | --- |
| `RN-AUTH-001` | Autenticação | Papel obrigatório (`admin` ou `piloto`) | Aprovada | Alta | `FUN-PY-API-025`, `FUN-PY-API-026`, `API-USER-002` |
| `RN-AUTH-002` | Autenticação | E-mail único | Aprovada | Alta | `FUN-PY-API-025`, `API-USER-002` |
| `RN-AUTH-003` | Autenticação | Senha mínima de 8 caracteres | Parcial | Alta | `FUN-PY-API-025`, `API-AUTH-003`, `API-USER-002` |
| `RN-AUTH-004` | Autenticação | Autocadastro bloqueado | Implementada | Alta | `FUN-PY-AUTH-007`, `API-USER-002` |
| `RN-AUTH-005` | Autenticação | Token com expiração e logout local | Aprovada | Alta | `FUN-PY-AUTH-004/005`, `API-AUTH-001`, `FUN-TS-AUTH-005` |
| `RN-AUTH-006` | Autenticação | Sessão offline pelo cache local | Aprovada | Média | `FUN-TS-AUTH-001/004`, `FUN-TS-DATA-002` |
| `RN-CAD-001` | Cadastro | Código de estação único | Implementada | Alta | `FUN-PY-DATA-003`, `API-DATA-002` |
| `RN-COL-001` | Coleta | Telemetria padronizada por estação/data | Parcial | Alta | `FUN-PY-COL-023`, `API-EXTERNA-004` |
| `RN-COL-002` | Coleta | Datas do SOAP em `dd/MM/yyyy` e armazenamento ISO | Aprovada | Média | `FUN-PY-COL-016`, `API-EXTERNA-005` |
| `RN-COL-003` | Coleta | Cotas válidas somente em `(0, 100000)` | Implementada | Média | `FUN-PY-COL-014/019`, `API-EXTERNA-005` |
| `RN-ROTA-001` | Rota | Calado obrigatório | Parcial | Alta | `FUN-PY-API-033`, `API-ROUTE-001` |
| `RN-ROTA-002` | Rota | Transitabilidade por profundidade | Aprovada | Alta | `FUN-PY-ROUTE-006`, `FUN-TS-ROUTE-012` |
| `RN-ROTA-003` | Rota | Custo por tempo com correnteza | Proposta | Alta | `FUN-PY-ROUTE-006`, `API-ROUTE-001` |
| `RN-ROTA-004` | Rota | Margem de segurança sobre o calado | Aprovada | Alta | `FUN-PY-ROUTE-006`, `API-ROUTE-001` |
| `RN-ROTA-005` | Rota | Profundidade = nível − cota de fundo | Parcial | Alta | `FUN-PY-NAV-013`, `FUN-PY-ML-018` |
| `RN-ROTA-006` | Rota | Estação influente por proximidade ao trecho | Parcial | Média | `FUN-PY-API-003`, `FUN-PY-ROUTE-003` |
| `RN-ROTA-007` | Rota | Calado de referência por tramo (RN029) | Parcial | Média | `FUN-PY-ETL-061`, `FUN-PY-NAV-013` |
| `RN-NIVEL-001` | Nível | Mínima histórica por estação | Implementada | Alta | `FUN-PY-COL-018/019`, `API-DATA-001` |
| `RN-NIVEL-002` | Nível | Deduplicação por estação + timestamp | Parcial | Média | `FUN-PY-COL-025`, `FUN-PY-ETL-039` |
| `RN-NIVEL-003` | Nível | Janela máxima de 90 dias na consulta | Proposta | Média | `FUN-PY-API-030`, `API-DATA-003` |
| `RN-MON-001` | Monitoramento | Limiar de variação de 30 cm | Aprovada | Alta | `FUN-PY-MON-002`, `API-ROUTE-006` |
| `RN-MON-002` | Monitoramento | Recomputação automática de rota monitorada | Aprovada | Alta | `FUN-PY-MON-002/003/004`, `API-ROUTE-008` |
| `RN-MON-003` | Monitoramento | Cooldown de 30 min, exceto evento extremo | Aprovada | Alta | `FUN-PY-MON-002` |
| `RN-MON-004` | Monitoramento | Notificar somente quando o traçado muda | Aprovada | Média | `FUN-PY-MON-002` |
| `RN-BAT-001` | Batimetria | Cota de fundo por trecho | Parcial | Alta | `FUN-PY-ML-018`, `FUN-PY-NAV-008` |
| `RN-BAT-002` | Batimetria | Correnteza derivada de Q/A | Proposta | Alta | `FUN-PY-ROUTE-006`, `FUN-PY-ML-012` |
| `RN-BAT-003` | Batimetria | Vazão padrão para aresta sem medição | Proposta | Média | `FUN-PY-ML-012`, `FUN-PY-ROUTE-006` |
| `RN-SYNC-001` | Sincronização | Snapshot offline do grafo | Parcial | Alta | `FUN-PY-API-043`, `FUN-TS-OFFLINE-002` |
| `RN-SYNC-002` | Sincronização | Fila local sem perda de rotas | Aprovada | Alta | `FUN-TS-OFFLINE-004`, `FUN-TS-CACHE-005/007` |
| `RN-SYNC-003` | Sincronização | Sincronização automática ao reconectar | Aprovada | Alta | `FUN-TS-OFFLINE-005/006` |
| `RN-SYNC-004` | Sincronização | Cálculo de rota offline | Implementada | Alta | `FUN-TS-ROUTE-012`, `FUN-TS-ROUTE-003` |
| `RN-SYNC-005` | Sincronização | Notificação em tempo real com fallback | Implementada | Alta | `FUN-PY-API-041`, `FUN-TS-NOTIFY-004/008` |
| `RN-NAV-001` | Navegabilidade | Classificação semanal por trecho | Aprovada | Alta | `FUN-PY-NAV-012/013` |
| `RN-NAV-002` | Navegabilidade | Classificação por estação com folga de 50 cm | Implementada | Média | `FUN-PY-NAV-004`, `FUN-PY-ETL-065` |
| `RN-ETL-001` | ETL | Espelho SQLite → PostGIS idempotente | Aprovada | Alta | `FUN-PY-ETL-004/005`, `FUN-PY-ETL-041` |

## 4. Regras por domínio

### AUTENTICAÇÃO

#### RN-AUTH-001 — Papel obrigatório (`admin` ou `piloto`)
- **Status:** Aprovada
- **Prioridade:** Alta
- **Origem legada:** RN001
- **Versão da regra:** 1.0
- **Última revisão:** 2026-10-20
- **Requisitos associados:** RF001–RF004

**Objetivo**

Garantir que todo usuário tenha um papel válido e que operações administrativas sejam restritas.

**Comportamento atual verificado**

`UserInput.papel` e `UserUpdate.papel` usam `Literal["admin","piloto"]`; o schema do banco impõe `CHECK (papel IN ('admin','piloto'))`; `admin_user` rejeita não-admin com `403`.

**Regra aprovada**

Somente `admin` e `piloto` são aceitos; operações de gestão exigem `admin`.

**Condições e exceções**

- O bootstrap do primeiro admin é feito por `backend/criar_admin.py`, que grava `papel='admin'` diretamente.

**Critérios de aceitação**

1. **Dado** um payload com papel diferente de `admin`/`piloto`, **quando** o usuário é criado/atualizado, **então** a API responde `422`.
2. **Dado** um piloto autenticado, **quando** chama `GET /usuarios`, **então** recebe `403`.
3. **Dado** um admin, **quando** cria um piloto, **então** o registro é persistido com papel `piloto`.

**Rastreabilidade**

- Funções: `FUN-PY-API-025`, `FUN-PY-API-026`, `FUN-PY-AUTH-007`, `FUN-PY-DATA-003`
- Endpoints: `API-USER-002`, `API-USER-003`
- Testes: Sem teste automatizado específico (verificação estática do schema/Pydantic).
- Dados / tabelas: `usuarios.papel`

**Impacto e riscos**

Mudar o conjunto de papéis exige migração do `CHECK` e revisão dos guards do frontend (`requerAdmin`).

**Histórico de decisões**

| Data | Decisão | Autor / aprovador | Referência |
| --- | --- | --- | --- |
| 2026-10-20 | Regra mapeada a partir do código e da documentação | Mapeamento automatizado | — |

---

#### RN-AUTH-002 — E-mail único
- **Status:** Aprovada
- **Prioridade:** Alta
- **Origem legada:** RN002
- **Versão da regra:** 1.0
- **Última revisão:** 2026-10-20
- **Requisitos associados:** RF002, RF003

**Objetivo**

Evitar duplicidade de contas e ambiguidade no login.

**Comportamento atual verificado**

`usuarios.email` é `UNIQUE`; `create_user` normaliza para minúsculas e traduz `UniqueViolation` em `409 email_exists`. O login compara com `lower(email)`.

**Regra aprovada**

Não pode existir mais de um usuário com o mesmo e-mail (comparação sem distinção de caixa).

**Condições e exceções**

- A atualização de usuário não captura `UniqueViolation`; uma colisão de e-mail em `PUT /usuarios/{id}` não retorna `409` explicitamente.

**Critérios de aceitação**

1. **Dado** um e-mail já cadastrado, **quando** um admin tenta criar outro usuário com o mesmo e-mail, **então** recebe `409`.
2. **Dado** e-mails com diferença de caixa, **quando** o login é feito, **então** a mesma conta é encontrada.

**Rastreabilidade**

- Funções: `FUN-PY-API-025`, `FUN-PY-API-021`
- Endpoints: `API-USER-002`, `API-AUTH-001`
- Testes: Sem teste automatizado específico.
- Dados / tabelas: `usuarios.email`

**Impacto e riscos**

Mudança de normalização (ex.: e-mail com `+`) afeta login e unicidade.

---

#### RN-AUTH-003 — Senha mínima de 8 caracteres
- **Status:** Parcial (divergente da documentação)
- **Prioridade:** Alta
- **Origem legada:** RN003
- **Versão da regra:** 1.0
- **Última revisão:** 2026-10-20
- **Requisitos associados:** RF001, RF002, RF004

**Objetivo**

Impedir senhas trivialmente curtas.

**Comportamento atual verificado**

O código exige `min_length=8` e `max_length=256` em criação, atualização administrativa e perfil. **Não há exigência de letras e números**, ao contrário do texto legado (“Senha minima de 8 caracteres com letras e numeros”). O frontend usa `minlength="8"`.

**Regra aprovada**

Senha com pelo menos 8 caracteres.

**Mudança proposta / comportamento desejado**

A documentação legada prevê composição (letras + números). Se essa política for mantida, é necessário implementar validação adicional no backend e alinhar o frontend.

**Condições e exceções**

- A senha nunca é armazenada em texto puro; é usado `scrypt` com sal aleatório.

**Critérios de aceitação**

1. **Dado** uma senha com 7 caracteres, **quando** o usuário é criado/atualizado, **então** a API responde `422`.
2. **Dado** uma senha com 8 caracteres, **quando** o usuário é criado, **então** a operação é aceita.
3. **Dado** a política de composição aprovada, **quando** uma senha só de letras é enviada, **então** deve ser rejeitada (não implementado hoje).

**Rastreabilidade**

- Funções: `FUN-PY-API-025`, `FUN-PY-API-026`, `FUN-PY-API-023`, `FUN-PY-AUTH-001`
- Endpoints: `API-USER-002`, `API-USER-003`, `API-AUTH-003`
- Testes: Sem teste automatizado específico.
- Dados / tabelas: `usuarios.senha_hash`

**Impacto e riscos**

Endurecer a política pode invalidar senhas existentes e exige comunicação/UX.

---

#### RN-AUTH-004 — Autocadastro bloqueado
- **Status:** Implementada
- **Prioridade:** Alta
- **Origem legada:** RN004
- **Versão da regra:** 1.0
- **Última revisão:** 2026-10-20
- **Requisitos associados:** RF002

**Objetivo**

Garantir que somente administradores criem contas.

**Comportamento atual verificado**

Não existe rota pública de registro; `POST /usuarios` exige `admin_user`. O único bootstrap é o script `criar_admin.py`.

**Regra aprovada**

Cadastro público não permitido; criação de usuários exige `admin`.

**Condições e exceções**

- O bootstrap inicial é operacional (CLI), não uma rota pública.

**Critérios de aceitação**

1. **Dado** um usuário não autenticado, **quando** tenta `POST /usuarios`, **então** recebe `401`.
2. **Dado** um piloto autenticado, **quando** tenta `POST /usuarios`, **então** recebe `403`.
3. **Dado** um admin, **quando** cria um usuário, **então** recebe `201`.

**Rastreabilidade**

- Funções: `FUN-PY-AUTH-007`, `FUN-PY-API-025`, `FUN-PY-ADMIN-001`
- Endpoints: `API-USER-002`
- Testes: Sem teste automatizado específico.
- Dados / tabelas: `usuarios`

**Impacto e riscos**

A criação do primeiro admin depende de acesso ao servidor/banco.

---

#### RN-AUTH-005 — Token com expiração e logout local
- **Status:** Aprovada
- **Prioridade:** Alta
- **Origem legada:** RN005
- **Versão da regra:** 1.0
- **Última revisão:** 2026-10-20
- **Requisitos associados:** RF001, RNF08

**Objetivo**

Limitar a validade da sessão e permitir encerramento no cliente.

**Comportamento atual verificado**

Token HMAC-SHA256 com payload `id:papel:expira_em`; TTL padrão `HIDROWIZE_TOKEN_TTL_SECONDS=28800` (8 h); `read_token` valida assinatura, expiração e papel. O logout remove token/usuário do `localStorage` sem chamada ao servidor.

**Regra aprovada**

Token expira em 8 h (configurável) e o logout limpa a sessão local.

**Condições e exceções**

- Não há revogação central de token; um token válido continua aceito até expirar, mesmo após logout em outro dispositivo.

**Critérios de aceitação**

1. **Dado** um token expirado, **quando** usado em rota autenticada, **então** recebe `401 invalid_token`.
2. **Dado** um token com assinatura inválida, **quando** usado, **então** recebe `401`.
3. **Dado** logout, **quando** o app recarrega, **então** não há sessão restaurada.

**Rastreabilidade**

- Funções: `FUN-PY-AUTH-003/004/005/006`, `FUN-TS-AUTH-004/005`, `FUN-TS-HTTP-006/007`
- Endpoints: `API-AUTH-001`, `API-AUTH-002`
- Testes: `frontend/src/stores/session.spec.ts`, `frontend/src/services/http.spec.ts` (cliente); sem teste de expiração no backend.
- Dados / tabelas: `usuarios`

**Impacto e riscos**

Migrar para revogação/refresh token exige mudança de contrato e armazenamento.

---

#### RN-AUTH-006 — Sessão offline pelo cache local
- **Status:** Aprovada
- **Prioridade:** Média
- **Origem legada:** Não documentada
- **Versão da regra:** 1.0
- **Última revisão:** 2026-10-20
- **Requisitos associados:** RF021, RNF03

**Objetivo**

Permitir consulta offline sem perder a identidade do usuário.

**Comportamento atual verificado**

`restaurar()` tenta `GET /auth/me`; em `401/403` limpa token/usuário; em falha de rede usa `lerUsuarioCache()` (`localStorage`).

**Regra aprovada**

Sem rede, a sessão é mantida a partir do cache local; credenciais inválidas limpam a sessão.

**Condições e exceções**

- O cache não é criptografado (RNF09 não iniciado).

**Critérios de aceitação**

1. **Dado** token válido e API inacessível, **quando** o app inicia, **então** o usuário em cache é restaurado.
2. **Dado** token rejeitado com `401`, **quando** o app inicia, **então** token e usuário são removidos.

**Rastreabilidade**

- Funções: `FUN-TS-AUTH-001/002/004`, `FUN-TS-HTTP-006`
- Endpoints: `API-AUTH-002`
- Testes: `frontend/src/stores/session.spec.ts`
- Dados / tabelas: `localStorage` (`hidrowize-usuario`, `hidrowize-access-token`)

**Impacto e riscos**

Dados de sessão em `localStorage` são acessíveis a XSS; WebCrypto está previsto, não implementado.

---

### CADASTRO

#### RN-CAD-001 — Código de estação único
- **Status:** Implementada
- **Prioridade:** Alta
- **Origem legada:** RN006
- **Versão da regra:** 1.0
- **Última revisão:** 2026-10-20
- **Requisitos associados:** RF011, RF012

**Objetivo**

Usar o código ANA como identificador estável da estação.

**Comportamento atual verificado**

`estacoes.codigo_estacao` é `PRIMARY KEY` no schema da aplicação e a consulta de estação usa esse campo. A importação de estações usa `INSERT OR REPLACE`.

**Regra aprovada**

Cada estação é identificada por um único `codigo_estacao`.

**Condições e exceções**

- A base hidrográfica é recriada pelo ETL; duplicidade no CSV é resolvida pelo upsert.

**Critérios de aceitação**

1. **Dado** um código existente, **quando** a estação é reimportada, **então** o registro é substituído (não duplicado).
2. **Dado** um código inexistente, **quando** `GET /estacoes/{codigo}` é chamado, **então** recebe `404`.

**Rastreabilidade**

- Funções: `FUN-PY-DATA-003`, `FUN-PY-API-029`, `FUN-PY-ETL-029`
- Endpoints: `API-DATA-001`, `API-DATA-002`
- Testes: Sem teste automatizado específico.
- Dados / tabelas: `estacoes`

---

### COLETA

#### RN-COL-001 — Telemetria padronizada por estação/data
- **Status:** Parcial
- **Prioridade:** Alta
- **Origem legada:** RN007
- **Versão da regra:** 1.0
- **Última revisão:** 2026-10-20
- **Requisitos associados:** RF009, RNF10

**Objetivo**

Garantir leituras consistentes para séries e mínimas históricas.

**Comportamento atual verificado**

O coletor normaliza campos para `codigo_estacao`, `data_hora_medicao`, `cota_adotada`, status, vazão e chuva. No banco, as colunas de telemetria são anuláveis (`cota_adotada REAL`, sem `NOT NULL`); não há validação de obrigatoriedade no schema. A documentação legada exige `codigo_estacao`, `data_hora` e `nivel_cm` não nulos.

**Regra aprovada**

Cada leitura deve conter estação, timestamp e cota; valores ausentes são gravados como nulos.

**Mudança proposta / comportamento desejado**

Se a obrigatoriedade for mantida, avaliar `NOT NULL`/validação na importação — impacto alto, pois a API pode retornar leituras parciais.

**Condições e exceções**

- Estações sem telemetria são aceitas e aparecem com `nivel_atual_cm = null`.

**Critérios de aceitação**

1. **Dado** um item da ANA sem cota, **quando** importado, **então** a cota fica nula (não inventada).
2. **Dado** um item com estação/timestamp, **quando** importado, **então** a chave de deduplicação pode ser formada.

**Rastreabilidade**

- Funções: `FUN-PY-COL-023`, `FUN-PY-ETL-031`
- Endpoints: `API-EXTERNA-004`
- Testes: Sem teste automatizado específico.
- Dados / tabelas: `telemetria`

---

#### RN-COL-002 — Datas do SOAP em `dd/MM/yyyy` e armazenamento ISO
- **Status:** Aprovada
- **Prioridade:** Média
- **Origem legada:** RN008
- **Versão da regra:** 1.0
- **Última revisão:** 2026-10-20
- **Requisitos associados:** RF009

**Objetivo**

Padronizar entrada e armazenamento de datas.

**Comportamento atual verificado**

`serie_historica` envia `dataInicio`/`dataFim` como texto (`dd/MM/yyyy`); `_expandir_diaria` produz `YYYY-MM-DD`. A telemetria REST armazena o timestamp retornado pela ANA; não há conversão explícita de fuso para UTC.

**Regra aprovada**

Entrada SOAP em `dd/MM/yyyy`; série diária em ISO `YYYY-MM-DD`.

**Condições e exceções**

- A documentação fala em “armazenar UTC”, mas o código não normaliza fuso.

**Critérios de aceitação**

1. **Dado** uma data `01/01/2026`, **quando** a série é consultada, **então** o SOAP recebe esse formato.
2. **Dado** um registro diário, **quando** persistido, **então** a data está em `YYYY-MM-DD`.

**Rastreabilidade**

- Funções: `FUN-PY-COL-013`, `FUN-PY-COL-016`, `FUN-PY-COL-017`
- Endpoints: `API-EXTERNA-005`
- Testes: Sem teste automatizado específico.
- Dados / tabelas: `cotas_diarias`, `telemetria`

---

#### RN-COL-003 — Cotas válidas somente em `(0, 100000)`
- **Status:** Implementada
- **Prioridade:** Média
- **Origem legada:** Não documentada
- **Versão da regra:** 1.0
- **Última revisão:** 2026-10-20
- **Requisitos associados:** RF009, RF012

**Objetivo**

Descartar leituras inválidas (ex.: negativas, sentinelas) antes de calcular estatísticas.

**Comportamento atual verificado**

`_cota_diaria_valida` e o `_ok` interno de `_estatisticas` aceitam apenas `0 < v < 100000`; também exigem status vazio ou `"0"` no resumo histórico.

**Regra aprovada**

Cotas fora do intervalo ou com status de qualidade diferente de ok são descartadas do resumo.

**Condições e exceções**

- A telemetria REST não aplica o mesmo filtro no momento da coleta; os resumos podem incluir valores brutos.

**Critérios de aceitação**

1. **Dado** uma cota `-74`, **quando** a série é expandida, **então** o dia é descartado.
2. **Dado** uma cota `1500`, **quando** o resumo é calculado, **então** o valor é incluído.
3. **Dado** status `1`, **quando** o resumo é calculado, **então** o valor é descartado.

**Rastreabilidade**

- Funções: `FUN-PY-COL-014`, `FUN-PY-COL-019`
- Endpoints: `API-EXTERNA-005`
- Testes: Sem teste automatizado específico.
- Dados / tabelas: `cotas_historicas`, `cotas_diarias`

---

### ROTA

#### RN-ROTA-001 — Calado obrigatório
- **Status:** Parcial (divergente da documentação)
- **Prioridade:** Alta
- **Origem legada:** RN009
- **Versão da regra:** 1.0
- **Última revisão:** 2026-10-20
- **Requisitos associados:** RF016, RF018

**Objetivo**

Impedir cálculo sem calado válido e limitar valores absurdos.

**Comportamento atual verificado**

`RouteInput.calado_m` exige `0.5 ≤ calado ≤ 6`; `RouteSaveInput` repete a faixa. A documentação legada diz “> 0; máximo 20 m”. O frontend usa `min=0.5` e `max=6`.

**Regra aprovada**

Calado entre 0,5 m e 6 m por requisição.

**Mudança proposta / comportamento desejado**

Se o limite de 20 m for o correto para a bacia, ampliar o contrato e revisar validações do frontend e testes.

**Condições e exceções**

- O calado de referência por tramo (RN-ROTA-007) é um teto operacional, não o calado da requisição.

**Critérios de aceitação**

1. **Dado** `calado_m = 0.4`, **quando** a rota é solicitada, **então** a API responde `422`.
2. **Dado** `calado_m = 6.1`, **quando** a rota é solicitada, **então** a API responde `422`.
3. **Dado** `calado_m = 2`, **quando** há caminho transitável, **então** a rota é calculada.

**Rastreabilidade**

- Funções: `FUN-PY-API-033`, `FUN-PY-API-034`
- Endpoints: `API-ROUTE-001`, `API-ROUTE-002`
- Testes: `frontend/src/stores/rota.spec.ts` (cliente).
- Dados / tabelas: `rotas.calado_m`

**Impacto e riscos**

Mudar o limite é mudança de contrato público (PRO) e afeta o formulário do piloto.

---

#### RN-ROTA-002 — Transitabilidade por profundidade
- **Status:** Aprovada
- **Prioridade:** Alta
- **Origem legada:** RN010
- **Versão da regra:** 1.0
- **Última revisão:** 2026-10-20
- **Requisitos associados:** RF016, RF018

**Objetivo**

Excluir trechos mais rasos que o necessário para a embarcação.

**Comportamento atual verificado**

No backend (`RiverGraph.route`) e no cálculo offline (`calcularOffline`), arestas com `depth_m != null` e `depth_m < calado + margem` são podadas. Arestas com profundidade `NULL` são tratadas como transitáveis. A documentação legada fala apenas em `profundidade < calado`; o código já incorpora a margem (RN-ROTA-004).

**Regra aprovada**

Um trecho é transitável quando a profundidade é desconhecida ou `≥ calado + margem`.

**Condições e exceções**

- `NULL` significa “desconhecido” e **não** bloqueia a rota — decisão que precisa ser validada com o orientador.

**Critérios de aceitação**

1. **Dado** um trecho com profundidade 1,8 m, calado 2,0 m e margem 0,5 m, **quando** a rota é calculada, **então** o trecho é excluído.
2. **Dado** profundidade 2,5 m nas mesmas condições, **então** o trecho é elegível.
3. **Dado** profundidade nula, **então** o trecho é elegível (comportamento atual).

**Rastreabilidade**

- Funções: `FUN-PY-ROUTE-006`, `FUN-TS-ROUTE-012`
- Endpoints: `API-ROUTE-001`
- Testes: `frontend/src/services/roteador.spec.ts` (offline); sem teste do motor PostGIS.
- Dados / tabelas: `trechos_navegaveis.hig_drn_depth_m`

---

#### RN-ROTA-003 — Custo por tempo com correnteza
- **Status:** Proposta (não implementada)
- **Prioridade:** Alta
- **Origem legada:** RN011, RF019, RF032
- **Versão da regra:** 1.0
- **Última revisão:** 2026-10-20
- **Requisitos associados:** RF019, RF032

**Objetivo**

Calcular a rota mais rápida considerando velocidade própria e correnteza.

**Comportamento atual verificado**

O motor usa Dijkstra por **distância** (`edge.distance_km`); o tempo é derivado depois (`distância / velocidade_embarcacao_kmh`). Não há velocidade de correnteza, A* nem peso por tempo. Ofensiva: `RN025`/`RN028` também não estão integradas.

**Regra aprovada**

Nenhuma implementação vigente; a documentação descreve `Custo (h) = distância / (velocidade_embarcacao + velocidade_correnteza)`.

**Mudança proposta / comportamento desejado**

Implementar peso por tempo com correnteza (Q/A), A* com heurística e tratamento de `velocidade_liquida ≤ 0` como intransitável.

**Critérios de aceitação**

1. **Dado** dois caminhos com mesma distância e correntes opostas, **quando** o motor for por tempo, **então** escolhe o de menor tempo.
2. **Dado** correnteza que anula a velocidade própria, **então** a aresta é intransitável.

**Rastreabilidade**

- Funções: `FUN-PY-ROUTE-006`, `FUN-PY-API-033`
- Endpoints: `API-ROUTE-001`
- Testes: A definir.
- Dados / tabelas: `trechos_navegaveis` (largura, vazão, Manning)

**Impacto e riscos**

Muda o resultado de todas as rotas e o contrato `tempo_total_h`/`custo_total`; exige calibração de datum e correnteza.

---

#### RN-ROTA-004 — Margem de segurança sobre o calado
- **Status:** Aprovada
- **Prioridade:** Alta
- **Origem legada:** RN012
- **Versão da regra:** 1.0
- **Última revisão:** 2026-10-20
- **Requisitos associados:** RF018

**Objetivo**

Reduzir o risco de encalhe com uma folga configurável.

**Comportamento atual verificado**

`margem_seguranca_m` é aceita com `0 ≤ margem ≤ 3` e padrão 0,5; a poda usa `calado + margem`. O “modo arriscado” previsto na documentação **não** existe na API.

**Regra aprovada**

Aresta transitável exige folga de 0,5 m por padrão, configurável até 3 m.

**Condições e exceções**

- O piloto pode reduzir a margem a zero, mas não desativar a verificação de calado.

**Critérios de aceitação**

1. **Dado** margem 0,5 m, **quando** a profundidade é exatamente `calado + 0,5`, **então** o trecho é elegível.
2. **Dado** margem 0, **quando** a profundidade é igual ao calado, **então** o trecho é elegível.

**Rastreabilidade**

- Funções: `FUN-PY-ROUTE-006`, `FUN-PY-API-033`, `FUN-TS-ROUTE-012`
- Endpoints: `API-ROUTE-001`
- Testes: `frontend/src/services/roteador.spec.ts`.
- Dados / tabelas: `rotas.margem_seguranca_m`

---

#### RN-ROTA-005 — Profundidade = nível − cota de fundo
- **Status:** Parcial
- **Prioridade:** Alta
- **Origem legada:** RN022, RN024
- **Versão da regra:** 1.0
- **Última revisão:** 2026-10-20
- **Requisitos associados:** RF014, RF031, RF035

**Objetivo**

Estimar a profundidade real de cada trecho combinando batimetria e nível d'água.

**Comportamento atual verificado**

O motor de rota usa `hig_drn_depth_m` (profundidade média AHGN), **não** `nível − cota_fundo`. A regra é aplicada apenas nos scripts de navegabilidade: `gerar_navegabilidade_semanal` calcula `nivel_m − cota_fundo_m` e `gerar_historico_geo` faz o mesmo para o mapa. A cota de fundo é produzida por ML (`treinar_cota_fundo`).

**Regra aprovada**

A documentação define `profundidade = cota_nivel_atual − cota_fundo_batimetria`; `NULL` quando não há cota de fundo.

**Mudança proposta / comportamento desejado**

Integrar `cota_fundo_trecho` e o nível da estação influente ao motor de rota, após calibrar o datum vertical.

**Critérios de aceitação**

1. **Dado** nível 30 m e cota de fundo 24 m, **quando** a profundidade semanal é calculada, **então** resulta 6 m.
2. **Dado** ausência de cota de fundo, **então** o status é `SEM_DADOS`/profundidade nula.
3. **Dado** o motor de rota, **quando** a regra for integrada, **então** a poda usa a profundidade calculada (hoje usa `hig_drn_depth_m`).

**Rastreabilidade**

- Funções: `FUN-PY-NAV-008`, `FUN-PY-NAV-013`, `FUN-PY-ML-018`, `FUN-PY-ROUTE-006`
- Endpoints: `API-ROUTE-001`
- Testes: Sem teste automatizado específico.
- Dados / tabelas: `cota_fundo_trecho`, `series_nivel_satelite`, `trechos_navegaveis`

**Impacto e riscos**

O datum da régua ANA (cm sobre zero local) difere da cota de fundo (m geóide); sem calibração a profundidade é inconsistente.

---

#### RN-ROTA-006 — Estação influente por proximidade ao trecho
- **Status:** Parcial
- **Prioridade:** Média
- **Origem legada:** RN023
- **Versão da regra:** 1.0
- **Última revisão:** 2026-10-20
- **Requisitos associados:** RF014, RF023

**Objetivo**

Associar o nível correto a cada aresta.

**Comportamento atual verificado**

Existe a tabela `estacoes_trechos` (estação × `fid_trecho`, com `distancia_m`) e o motor associa estações a trechos por esse mapa; a rota usa o nível apenas para monitoramento, não para profundidade. Não há cálculo de “raio de 50 km” em tempo de execução nem seleção dinâmica por distância ao longo da rede.

**Regra aprovada**

Cada aresta deve usar o nível da estação mais próxima ao longo da rede (raio de 50 km), conforme documentação.

**Mudança proposta / comportamento desejado**

Formalizar a associação (pré-processada ou em runtime) e documentar o critério de distância (euclidiana vs. rede).

**Critérios de aceitação**

1. **Dado** um trecho com estação associada a menos de 50 km, **então** o nível dessa estação é usado.
2. **Dado** nenhuma estação no raio, **então** a profundidade é desconhecida.

**Rastreabilidade**

- Funções: `FUN-PY-API-003`, `FUN-PY-ROUTE-003`, `FUN-PY-ETL-035`
- Endpoints: `API-ROUTE-001`
- Testes: Sem teste automatizado específico.
- Dados / tabelas: `estacoes_trechos`

---

#### RN-ROTA-007 — Calado de referência por tramo (RN029)
- **Status:** Parcial
- **Prioridade:** Média
- **Origem legada:** RN029
- **Versão da regra:** 1.0
- **Última revisão:** 2026-10-20
- **Requisitos associados:** RF016, RF019

**Objetivo**

Parametrizar a navegabilidade por tramo, segundo DNIT/ANTAQ.

**Comportamento atual verificado**

`calado_de_rio` implementa: Negro 0 m, Madeira 13 m, Solimões 6 m, Amazonas 10 m a jusante de −60,5 e 6 m entre −70,5 e −60,5; demais rios usam proxy 2–6 m pela largura. **Esse cálculo não é usado pelo motor de rota**, apenas pelo histórico geográfico.

**Regra aprovada**

Calado de projeto por tramo conforme RN029; o calado da requisição continua sendo o do piloto.

**Condições e exceções**

- Rio fora da RN029 usa proxy por largura (mín. 2 m, máx. 6 m).

**Critérios de aceitação**

1. **Dado** rio Negro, **então** calado de referência 0 m.
2. **Dado** Madeira, **então** 13 m.
3. **Dado** Amazonas com longitude ≥ −60,5, **então** 10 m.
4. **Dado** rio desconhecido com largura 450 m, **então** proxy 4 m.

**Rastreabilidade**

- Funções: `FUN-PY-ETL-061`, `FUN-PY-NAV-013`
- Endpoints: Nenhum endpoint expõe o valor diretamente.
- Testes: Sem teste automatizado específico.
- Dados / tabelas: `trechos_navegaveis.hig_drn_width_m`

---

### NÍVEL

#### RN-NIVEL-001 — Mínima histórica por estação
- **Status:** Implementada
- **Prioridade:** Alta
- **Origem legada:** RN013
- **Versão da regra:** 1.0
- **Última revisão:** 2026-10-20
- **Requisitos associados:** RF012

**Objetivo**

Oferecer referência histórica para navegabilidade e para o mapa.

**Comportamento atual verificado**

`resumo_cotas` mescla níveis consistido e bruto e calcula mínimo/máximo/média; `_estatisticas` filtra valores inválidos; `GET /estacoes` expõe `cota_minima_historica_m` a partir de `cotas_historicas`.

**Regra aprovada**

A mínima histórica é o menor valor válido do período disponível da estação.

**Condições e exceções**

- A janela é de 5 anos por padrão (`resumo_cotas(anos=5)`), não “todo o histórico”.

**Critérios de aceitação**

1. **Dado** uma série com mínima 120 cm, **então** o resumo retorna 120.
2. **Dado** valores inválidos, **então** eles não afetam a mínima.

**Rastreabilidade**

- Funções: `FUN-PY-COL-018/019`, `FUN-PY-API-028`
- Endpoints: `API-DATA-001`
- Testes: Sem teste automatizado específico.
- Dados / tabelas: `cotas_historicas`

---

#### RN-NIVEL-002 — Deduplicação por estação + timestamp
- **Status:** Parcial
- **Prioridade:** Média
- **Origem legada:** RN014
- **Versão da regra:** 1.0
- **Última revisão:** 2026-10-20
- **Requisitos associados:** RF009

**Objetivo**

Evitar leituras duplicadas em execuções sucessivas.

**Comportamento atual verificado**

O coletor REST deduplica em memória por `(codigo_estacao, data_hora_medicao)` antes de regravar o CSV. A tabela `telemetria` **não** tem chave única nem `UPSERT`; `importar_telemetria` insere sem deduplicar. `cotas_diarias` tem PK `(codigo_estacao,data)` e usa `INSERT OR REPLACE`.

**Regra aprovada**

Uma leitura por `(codigo_estacao, data_hora)`.

**Mudança proposta / comportamento desejado**

Criar índice/chave única em `telemetria` ou tornar a importação idempotente; today a regra é garantida apenas no CSV.

**Critérios de aceitação**

1. **Dado** duas execuções seguidas do coletor, **então** não há leituras duplicadas no CSV.
2. **Dado** o rebuild do SQLite, **então** a telemetria não deve duplicar (hoje pode).

**Rastreabilidade**

- Funções: `FUN-PY-COL-025`, `FUN-PY-ETL-031`, `FUN-PY-ETL-039`
- Endpoints: `API-EXTERNA-004`
- Testes: Sem teste automatizado específico.
- Dados / tabelas: `telemetria`, `cotas_diarias`

---

#### RN-NIVEL-003 — Janela máxima de 90 dias na consulta
- **Status:** Proposta (não implementada)
- **Prioridade:** Média
- **Origem legada:** RN015
- **Versão da regra:** 1.0
- **Última revisão:** 2026-10-20
- **Requisitos associados:** RF011, RF012

**Objetivo**

Limitar consultas muito longas e respostas excessivas.

**Comportamento atual verificado**

`GET /niveis` aceita `data_inicio` e `data_fim` arbitrários, filtra por `substr(...)` e **não** valida `data_fim >= data_inicio` nem o intervalo máximo de 90 dias.

**Regra aprovada**

Nenhuma validação de janela no código atual.

**Mudança proposta / comportamento desejado**

Validar formato das datas, ordem e intervalo ≤ 90 dias, retornando `422` fora do contrato.

**Critérios de aceitação**

1. **Dado** `data_fim < data_inicio`, **então** a API responde `422`.
2. **Dado** intervalo de 91 dias, **então** a API responde `422`.
3. **Dado** intervalo de 90 dias, **então** a consulta é aceita.

**Rastreabilidade**

- Funções: `FUN-PY-API-030`
- Endpoints: `API-DATA-003`
- Testes: A definir.
- Dados / tabelas: `telemetria`

---

### MONITORAMENTO

#### RN-MON-001 — Limiar de variação de 30 cm
- **Status:** Aprovada
- **Prioridade:** Alta
- **Origem legada:** RN019
- **Versão da regra:** 1.0
- **Última revisão:** 2026-10-20
- **Requisitos associados:** RF028

**Objetivo**

Só recalcular quando a variação de nível for relevante.

**Comportamento atual verificado**

Cada rota tem `limiar_cm` com padrão 30 (schema `DEFAULT 30`); `_verificar_rota` compara `|nivel − baseline|` com esse valor. Na primeira verificação, grava o baseline e não recalcula.

**Regra aprovada**

Variação absoluta ≥ 30 cm na estação de referência dispara avaliação.

**Condições e exceções**

- O limiar é por rota (coluna), não uma constante global.

**Critérios de aceitação**

1. **Dado** baseline 500 cm e leitura 529 cm, **então** não recalcula.
2. **Dado** leitura 530 cm, **então** avalia o recálculo.
3. **Dado** primeira leitura, **então** apenas define o baseline.

**Rastreabilidade**

- Funções: `FUN-PY-MON-002`
- Endpoints: `API-ROUTE-006`
- Testes: Sem teste automatizado específico.
- Dados / tabelas: `rotas.limiar_cm`

---

#### RN-MON-002 — Recomputação automática de rota monitorada
- **Status:** Aprovada
- **Prioridade:** Alta
- **Origem legada:** RN020
- **Versão da regra:** 1.0
- **Última revisão:** 2026-10-20
- **Requisitos associados:** RF028, RF029

**Objetivo**

Manter a rota do piloto válida quando o nível muda.

**Comportamento atual verificado**

O `monitor_loop` roda a cada 15 min (configurável) e chama `_verificar_rota`; ao ultrapassar o limiar, recalcula com o calado/margem salvos, grava `rota_alteracao` e publica evento. Se os `fids` não mudarem, apenas atualiza o baseline.

**Regra aprovada**

Rota monitorada é recalculada quando a variação atinge o limiar; alterações de traçado são registradas e notificadas.

**Condições e exceções**

- Falha em uma rota não interrompe as demais (try/except por rota).
- A estação de referência é o **destino** da rota.

**Critérios de aceitação**

1. **Dado** variação ≥ limiar e novo traçado, **então** cria registro em `rota_alteracao`.
2. **Dado** variação ≥ limiar e mesmo traçado, **então** atualiza baseline sem notificar.
3. **Dado** erro em uma rota, **então** as outras continuam sendo verificadas.

**Rastreabilidade**

- Funções: `FUN-PY-MON-002/003/004`
- Endpoints: `API-ROUTE-006`, `API-ROUTE-008`, `API-ADMIN-002`
- Testes: Sem teste automatizado específico.
- Dados / tabelas: `rotas`, `rota_alteracao`

---

#### RN-MON-003 — Cooldown de 30 min, exceto evento extremo
- **Status:** Aprovada
- **Prioridade:** Alta
- **Origem legada:** RN021
- **Versão da regra:** 1.0
- **Última revisão:** 2026-10-20
- **Requisitos associados:** RF028

**Objetivo**

Evitar recálculos repetidos em sequência.

**Comportamento atual verificado**

`cooldown_min` padrão 30; `_verificar_rota` ignora recálculo se `agora − ultima_recomputacao < cooldown` e a variação for < 100 cm. Variação ≥ 100 cm ignora o cooldown (evento extremo).

**Regra aprovada**

Cooldown de 30 min por rota, contornado em eventos ≥ 100 cm.

**Condições e exceções**

- O cooldown só é gravado quando há mudança de traçado (`ultima_recomputacao`).

**Critérios de aceitação**

1. **Dado** recálculo há 10 min, **quando** há nova variação de 40 cm, **então** não recalcula.
2. **Dado** variação de 120 cm, **então** recalcula mesmo dentro do cooldown.

**Rastreabilidade**

- Funções: `FUN-PY-MON-002`
- Endpoints: `API-ROUTE-006`
- Testes: Sem teste automatizado específico.
- Dados / tabelas: `rotas.cooldown_min`, `rotas.ultima_recomputacao`

---

#### RN-MON-004 — Notificar somente quando o traçado muda
- **Status:** Aprovada
- **Prioridade:** Média
- **Origem legada:** Não documentada
- **Versão da regra:** 1.0
- **Última revisão:** 2026-10-20
- **Requisitos associados:** RF029, RF034

**Objetivo**

Evitar avisos inúteis quando o nível varia mas a rota continua a mesma.

**Comportamento atual verificado**

`_verificar_rota` compara a lista de `fids` recalculada com `fids_rota`; se igual, atualiza baseline e retorna `None`. Só há evento `rota_alterada` quando o traçado muda.

**Regra aprovada**

Eventos de alteração são emitidos apenas para mudança efetiva de traçado.

**Critérios de aceitação**

1. **Dado** mesmo conjunto de fids, **então** nenhum evento é emitido.
2. **Dado** fids diferentes, **então** evento + registro histórico.

**Rastreabilidade**

- Funções: `FUN-PY-MON-002`
- Endpoints: `API-ROUTE-007`, `API-ROUTE-008`
- Testes: Sem teste automatizado específico.
- Dados / tabelas: `rotas.fids_rota`, `rota_alteracao`

---

### BATIMETRIA E CORRENTEZA

#### RN-BAT-001 — Cota de fundo por trecho
- **Status:** Parcial
- **Prioridade:** Alta
- **Origem legada:** RN024, RF031, RF035
- **Versão da regra:** 1.0
- **Última revisão:** 2026-10-20
- **Requisitos associados:** RF013, RF031, RF035

**Objetivo**

Preencher a cota de fundo de trechos sem cobertura batimétrica.

**Comportamento atual verificado**

A documentação prevê IDW sobre pontos batimétricos. O código atual treina RandomForest/HGB para estimar a cota de fundo a partir de atributos AHGN, usando como rótulo a mediana dos nós SICFLOW em um raio (padrão 1000 m), e persiste `cota_fundo_trecho` (`cota_fundo_observada`, `cota_fundo_estimada`, `n_modelo`, `raio_m`). A navegabilidade semanal prefere a observada e usa a estimada como fallback.

**Regra aprovada**

Cota de fundo observada tem prioridade; na ausência, usa-se a estimada.

**Condições e exceções**

- Trecho sem nós no raio fica com observada nula, mas recebe estimativa do modelo.
- O IDW permanece apenas como baseline no experimento de interpolação de nível.

**Critérios de aceitação**

1. **Dado** trecho com nós SICFLOW no raio, **então** `cota_fundo_observada` é a mediana.
2. **Dado** trecho sem observação, **então** `cota_fundo_estimada` é usada.
3. **Dado** ausência de ambas, **então** profundidade/navegabilidade ficam sem dado.

**Rastreabilidade**

- Funções: `FUN-PY-ML-013/014/015/018`, `FUN-PY-NAV-008`
- Endpoints: Nenhum endpoint expõe a cota de fundo.
- Testes: Sem teste automatizado específico.
- Dados / tabelas: `cota_fundo_trecho`, `batimetria_sicflow`

---

#### RN-BAT-002 — Correnteza derivada de Q/A
- **Status:** Proposta (não implementada)
- **Prioridade:** Alta
- **Origem legada:** RN025, RF032
- **Versão da regra:** 1.0
- **Última revisão:** 2026-10-20
- **Requisitos associados:** RF019, RF032

**Objetivo**

Incorporar a correnteza ao custo da rota.

**Comportamento atual verificado**

Não há cálculo de `V = Q/A` no motor. `rating_curve.py` apenas experimenta estimar vazão por ML; `gerar_navegabilidade_semanal` calcula profundidade, não correnteza.

**Regra aprovada**

Nenhuma implementação vigente; a documentação define `V = Q / (largura × profundidade)`.

**Mudança proposta / comportamento desejado**

Derivar Q/A por trecho e usar no peso por tempo (RN-ROTA-003), com fallback de largura média.

**Critérios de aceitação**

1. **Dado** Q=1000 m³/s, largura 100 m e profundidade 5 m, **então** V=2 m/s.
2. **Dado** largura desconhecida, **então** usa largura média do segmento.
3. **Dado** ausência de Q, **então** V=0 (RN-BAT-003).

**Rastreabilidade**

- Funções: `FUN-PY-ML-012`, `FUN-PY-ROUTE-006`
- Endpoints: `API-ROUTE-001`
- Testes: A definir.
- Dados / tabelas: `trechos_navegaveis`, `series_vazao_satelite`

---

#### RN-BAT-003 — Vazão padrão para aresta sem medição
- **Status:** Proposta (não implementada)
- **Prioridade:** Média
- **Origem legada:** RN028
- **Versão da regra:** 1.0
- **Última revisão:** 2026-10-20
- **Requisitos associados:** RF032

**Objetivo**

Evitar ausência de correnteza em trechos sem vazão medida.

**Comportamento atual verificado**

Não implementado no motor; a rating curve é um experimento e não alimenta a rota.

**Regra aprovada**

Usar a vazão da estação influente mais próxima; sem nenhuma, `V=0`.

**Critérios de aceitação**

1. **Dado** trecho sem vazão própria e com estação influente, **então** usa Q da estação.
2. **Dado** nenhuma estação com vazão, **então** V=0.

**Rastreabilidade**

- Funções: `FUN-PY-ML-012`, `FUN-PY-ROUTE-006`
- Endpoints: `API-ROUTE-001`
- Testes: A definir.
- Dados / tabelas: `telemetria.vazao_adotada`, `series_vazao_satelite`

---

### SINCRONIZAÇÃO

#### RN-SYNC-001 — Snapshot offline do grafo
- **Status:** Parcial
- **Prioridade:** Alta
- **Origem legada:** RN016
- **Versão da regra:** 1.0
- **Última revisão:** 2026-10-20
- **Requisitos associados:** RF021, RF022

**Objetivo**

Permitir cálculo de rota sem conexão.

**Comportamento atual verificado**

`GET /sync/snapshot` retorna nós (`id,lon,lat`), arestas (`fid,o,d,dist,prof`) e associações de estações; o cliente grava em IndexedDB (`grafo`). **Não** inclui níveis, rotas nem geometria completa por aresta. A documentação prevê grafo + níveis + profundidades + rotas recentes.

**Regra aprovada**

Snapshot contém o grafo necessário ao cálculo offline; dados de nível/rotas vêm de sincronizações separadas.

**Condições e exceções**

- `bbox` opcional limita o subgrafo.
- O snapshot é substituído a cada download (chave `atual`).

**Critérios de aceitação**

1. **Dado** snapshot baixado, **então** o cálculo offline resolve origem/destino presentes.
2. **Dado** snapshot sem a estação, **então** o cálculo retorna `null`.
3. **Dado** novo download, **então** o snapshot anterior é substituído.

**Rastreabilidade**

- Funções: `FUN-PY-API-043`, `FUN-TS-OFFLINE-002`, `FUN-TS-CACHE-012`
- Endpoints: `API-SYNC-001`
- Testes: `frontend/src/stores/offline.spec.ts`, `frontend/src/services/roteador.spec.ts`.
- Dados / tabelas: `trechos_navegaveis`, `estacoes_trechos`, IndexedDB `grafo`

---

#### RN-SYNC-002 — Fila local sem perda de rotas
- **Status:** Aprovada
- **Prioridade:** Alta
- **Origem legada:** RN017
- **Versão da regra:** 1.0
- **Última revisão:** 2026-10-20
- **Requisitos associados:** RF023, RF025

**Objetivo**

Não perder rotas criadas offline.

**Comportamento atual verificado**

Rotas salvas sem rede são gravadas em `pendentes` com `payload` e `criado_em`; `enviarPendentes` envia em ordem de `id` e só remove após sucesso; para no primeiro erro, preservando o restante da fila.

**Regra aprovada**

Fila FIFO; item só sai após confirmação do servidor.

**Condições e exceções**

- **Não há resolução de conflito por timestamp** (a documentação fala em “merge sem perda”); o servidor sempre insere uma nova rota.
- Um item com erro permanente bloqueia os seguintes (não há retry seletivo).

**Critérios de aceitação**

1. **Dado** falha de rede no envio, **então** o item permanece na fila.
2. **Dado** envio bem-sucedido, **então** o item é removido e o contador cai.
3. **Dado** fila com 3 itens e falha no segundo, **então** o terceiro não é enviado nesta rodada.

**Rastreabilidade**

- Funções: `FUN-TS-OFFLINE-003/004`, `FUN-TS-CACHE-005/006/007/008`
- Endpoints: `API-ROUTE-002`
- Testes: `frontend/src/stores/offline.spec.ts`, `frontend/src/services/cache.spec.ts`.
- Dados / tabelas: IndexedDB `pendentes`

---

#### RN-SYNC-003 — Sincronização automática ao reconectar
- **Status:** Aprovada
- **Prioridade:** Alta
- **Origem legada:** RN018
- **Versão da regra:** 1.0
- **Última revisão:** 2026-10-20
- **Requisitos associados:** RF023, RF024

**Objetivo**

Manter dados locais atualizados sem ação manual.

**Comportamento atual verificado**

`registarListeners` escuta `online`/`offline`; ao ficar online chama `sincronizar`, que faz pull de estações, push de pendências, pull de rotas (ignora falha de sessão anônima) e grava `ultima_sincronizacao`. O app também sincroniza no boot quando online.

**Regra aprovada**

Pull + push automáticos ao reconectar; falha é registrada e nova tentativa ocorre no próximo evento/ciclo.

**Condições e exceções**

- Não há timer periódico de sincronização; depende de eventos online ou reload.
- O log de sincronização detalhado é parcial (apenas data + fila).

**Critérios de aceitação**

1. **Dado** app offline, **quando** a conexão volta, **então** estações são atualizadas e pendentes enviadas.
2. **Dado** falha no pull, **então** `erro` é preenchido e a fila permanece.
3. **Dado** usuário anônimo, **então** falha ao listar rotas não interrompe a sincronização.

**Rastreabilidade**

- Funções: `FUN-TS-OFFLINE-005/006`
- Endpoints: `API-DATA-001`, `API-ROUTE-002`, `API-ROUTE-003`
- Testes: `frontend/src/stores/offline.spec.ts`.
- Dados / tabelas: IndexedDB `estacoes`, `rotas`, `pendentes`, `meta`

---

#### RN-SYNC-004 — Cálculo de rota offline
- **Status:** Implementada
- **Prioridade:** Alta
- **Origem legada:** RN026, RF022
- **Versão da regra:** 1.0
- **Última revisão:** 2026-10-20
- **Requisitos associados:** RF022

**Objetivo**

Calcular rota sem consultar o backend.

**Comportamento atual verificado**

`calcularOffline` executa Dijkstra local sobre o snapshot, com adjacência bidirecional e a mesma poda `prof < calado + margem`; retorna `null` sem estação/rota. O store tenta offline somente quando o erro **não** é `ApiProblem` (falha de rede).

**Regra aprovada**

Offline usa apenas o snapshot local e as mesmas regras de calado/margem.

**Condições e exceções**

- É Dijkstra (distância), não A*.
- Aresta com profundidade nula é transitável.
- Origem/destino são resolvidos por **nome** entre as estações carregadas.

**Critérios de aceitação**

1. **Dado** snapshot com caminho transitável, **então** retorna rota.
2. **Dado** trecho intransitável, **então** retorna `null`.
3. **Dado** estação inexistente, **então** retorna `null`.

**Rastreabilidade**

- Funções: `FUN-TS-ROUTE-012`, `FUN-TS-ROUTE-003/004`
- Endpoints: `API-SYNC-001`
- Testes: `frontend/src/services/roteador.spec.ts`, `frontend/src/stores/rota.spec.ts`.
- Dados / tabelas: IndexedDB `grafo`, `estacoes`

---

#### RN-SYNC-005 — Notificação em tempo real com fallback
- **Status:** Implementada
- **Prioridade:** Alta
- **Origem legada:** RN027, RF029, RF034
- **Versão da regra:** 1.0
- **Última revisão:** 2026-10-20
- **Requisitos associados:** RF029, RF034

**Objetivo**

Entregar alterações de rota ao piloto com baixa latência e resiliência.

**Comportamento atual verificado**

Backend publica eventos por usuário no `EventBus` e os entrega em `GET /api/v1/ws?token=`. O frontend conecta ao abrir o app, reconecta com backoff exponencial (máx. 30 s) e, se o WS cair, faz polling de `GET /rotas` + `GET /rotas/{id}/alteracoes` a cada 5 min, deduplicando por ID de alteração.

**Regra aprovada**

WS é o canal principal; polling de 5 min é fallback.

**Condições e exceções**

- Sem token, não conecta.
- Mensagens inválidas são ignoradas.
- O evento só é publicado quando o traçado muda (RN-MON-004).

**Critérios de aceitação**

1. **Dado** WS aberto, **quando** chega `rota_alterada`, **então** um aviso é exibido.
2. **Dado** WS fechado, **então** o fallback inicia e detecta alterações sem duplicar.
3. **Dado** queda, **então** a reconexão é agendada.

**Rastreabilidade**

- Funções: `FUN-PY-API-041/042`, `FUN-PY-MON-004`, `FUN-TS-NOTIFY-004/005/007/008`
- Endpoints: `API-ROUTE-008`, `API-ROUTE-007`
- Testes: `frontend/src/stores/notificacao.spec.ts`.
- Dados / tabelas: `rota_alteracao`

---

### NAVEGABILIDADE

#### RN-NAV-001 — Classificação semanal por trecho
- **Status:** Aprovada
- **Prioridade:** Alta
- **Origem legada:** RN022 + RN029 + RN012 (script)
- **Versão da regra:** 1.0
- **Última revisão:** 2026-10-20
- **Requisitos associados:** RF015, RF019

**Objetivo**

Produzir uma visão semanal de navegabilidade por trecho com nível de satélite.

**Comportamento atual verificado**

`gerar_navegabilidade_semanal` seleciona, entre as 5 estações virtuais mais próximas, a primeira com nível na janela de ±10 dias dentro de 50 km; calcula `profundidade = nível − cota_fundo`, `folga = profundidade − calado` e classifica: `NAVEGAVEL` se `prof ≥ calado+margem`; `RESTRITO` se `calado ≤ prof < calado+margem`; `CRITICO` se `prof < calado`; senão `SEM_DADOS`. Calado padrão 6 m, margem 0,5 m.

**Regra aprovada**

Classificação semanal conforme fórmula e limiares acima, com fonte `SATELITE_HYDROWEB`.

**Condições e exceções**

- A janela agrega observações de ±10 dias; não é uma medição semanal exata.
- Rios estreitos (<~100 m) podem ficar `SEM_DADOS` porque o SWOT não os alcança.
- Trechos sem nível no raio/janela não são gravados.

**Critérios de aceitação**

1. **Dado** profundidade 7 m, calado 6 m e margem 0,5, **então** `NAVEGAVEL`.
2. **Dado** profundidade 6,2 m, **então** `RESTRITO`.
3. **Dado** profundidade 5,9 m, **então** `CRITICO`.
4. **Dado** sem nível/cota, **então** `SEM_DADOS`.

**Rastreabilidade**

- Funções: `FUN-PY-NAV-006/007/008/009/011/012/013`
- Endpoints: Nenhum endpoint expõe a tabela `naveg_trecho_semanal` na API atual.
- Testes: Sem teste automatizado específico.
- Dados / tabelas: `naveg_trecho_semanal`

---

#### RN-NAV-002 — Classificação por estação com folga de 50 cm
- **Status:** Implementada
- **Prioridade:** Média
- **Origem legada:** Regra de navegabilidade do `gerar_navegabilidade.py` (não numerada)
- **Versão da regra:** 1.0
- **Última revisão:** 2026-10-20
- **Requisitos associados:** RF011, RF012, RF038

**Objetivo**

Classificar a navegabilidade por estação com base na folga sobre a mínima histórica.

**Comportamento atual verificado**

`classificacao` e `classificar_navegabilidade` usam o mesmo critério: `NAVEGAVEL` se `cota_atual − cota_minima ≥ 50 cm`; `RESTRITO` se `0 ≤ folga < 50`; `CRITICO` se folga < 0; `SEM DADOS` sem valores. A versão semanal usa ainda a margem de 0,5 m sobre o calado.

**Regra aprovada**

Limiar de 50 cm de folga sobre a mínima histórica (parâmetro `--limiar`).

**Condições e exceções**

- A mínima prefere o SOAP e é completada pela telemetria.
- A cota atual pode vir da média histórica quando não há telemetria.

**Critérios de aceitação**

1. **Dado** folga 50 cm, **então** `NAVEGAVEL`.
2. **Dado** folga 20 cm, **então** `RESTRITO`.
3. **Dado** folga −10 cm, **então** `CRITICO`.

**Rastreabilidade**

- Funções: `FUN-PY-NAV-004`, `FUN-PY-ETL-065`, `FUN-PY-NAV-005`
- Endpoints: Nenhum endpoint expõe o CSV/tabela de status por estação.
- Testes: Sem teste automatizado específico.
- Dados / tabelas: `navegabilidade`

---

### ETL

#### RN-ETL-001 — Espelho SQLite → PostGIS idempotente
- **Status:** Aprovada
- **Prioridade:** Alta
- **Origem legada:** Não documentada
- **Versão da regra:** 1.0
- **Última revisão:** 2026-10-20
- **Requisitos associados:** RF005, RF033

**Objetivo**

Manter o PostGIS alinhado à base consolidada sem duplicar dados.

**Comportamento atual verificado**

`carregar_tabela` recria cada tabela (`DROP + CREATE + COPY`), converte `geom_wkb` em `geometry(Geometry,4326)`, cria índice GIST e índices de apoio; o processo roda em uma transação com commit único. `gerar_sqlite` recria o arquivo de saída no modo completo.

**Regra aprovada**

Cada execução do ETL substitui integralmente as tabelas espelhadas; o resultado é idempotente em relação ao conteúdo do SQLite.

**Condições e exceções**

- O ETL **destrói** as tabelas de destino antes de copiar; dados gravados apenas no PostGIS são perdidos.
- Tabelas grandes (`batimetria_sicflow`, séries de satélite) só entram com `--todas`.

**Critérios de aceitação**

1. **Dado** o mesmo SQLite, **quando** o ETL roda duas vezes, **então** as contagens são iguais.
2. **Dado** um `fid` com geometria, **então** `geom` é criada com SRID 4326.
3. **Dado** `--todas`, **então** as tabelas grandes também são carregadas.

**Rastreabilidade**

- Funções: `FUN-PY-ETL-004/005`, `FUN-PY-ETL-041`
- Endpoints: Nenhum (processo CLI).
- Testes: Sem teste automatizado específico.
- Dados / tabelas: todas as tabelas espelhadas

**Impacto e riscos**

Interrupção no meio do processo deixa o destino parcialmente recriado (a transação protege, mas o `DROP` é DDL transacional no PostgreSQL). Executar com a API no ar pode causar janelas de indisponibilidade/consultas sem tabela.

---

## 5. Divergências e pendências prioritárias

1. **Datum vertical** — nível ANA (cm, zero da régua) × cota de fundo (m, geóide); bloqueia a integração de `RN-ROTA-005` ao motor.
2. **Custo por tempo/correnteza** — `RN-ROTA-003`, `RN-BAT-002` e `RN-BAT-003` não implementados; o motor é por distância.
3. **Limites de contrato** — calado máximo 6 m no código vs. 20 m na documentação (`RN-ROTA-001`); senha sem composição (`RN-AUTH-003`).
4. **Telemetria sem unicidade** — `RN-NIVEL-002` garantida apenas no CSV, não no banco.
5. **Janela de consulta** — `RN-NIVEL-003` sem validação.
6. **Snapshot offline** — `RN-SYNC-001` não inclui níveis/rotas/geometria completa; `RN-SYNC-002` não faz merge por timestamp.
7. **Cobertura de testes** — não há testes automatizados de backend no repositório; as evidências de frontend estão em `frontend/src/**/*.spec.ts`.
8. **Legado** — `backend_sqlite/` repete as rotas sem PostGIS e não foi catalogado; qualquer alteração de contrato precisa considerar se ele ainda é usado.
