# Estado Atual do Projeto

Relatório de acompanhamento dos requisitos do sistema de roteamento fluvial dinâmico (Ygapé / HidroWize). Descreve o que já está implementado, o que está parcialmente atendido e o que permanece pendente.

Legenda de status: **Atendido**, **Parcial**, **Não iniciado**, **Bloqueado**.

---

## 1. Resumo Executivo

O projeto já conta com **base de dados, camada de inteligência (ML), backend FastAPI e aplicação Vue 3** funcionando. O motor de roteamento opera sobre a topologia real da BHAE, e o planejador de rota (mapa + resumo) está disponível no front.

Em termos de etapas:

- **Fase 1** (dados/ambiente) — avançada; **Fase 7** (ML/satélite) — concluída.
- **Fases 2, 3 e 4** (motor de roteamento, API e frontend core) — implementadas em código de produção.
- **Fases 5, 5b e 6** (offline/sincronização, notificações em tempo real, empacotamento) — pendentes.

**Entregáveis executáveis atuais**

- API: `backend/main.py` (FastAPI) servindo autenticação, usuários, estações, níveis, grafo e rotas.
- Motor: `backend/routing_engine.py` (grafo sobre `trechos_navegaveis` do PostGIS via `ST_AsBinary`, menor caminho por distância com poda de trechos intransitáveis).
- Front: `frontend/` (Vue 3 + Vite + TS + Tailwind 4 + Pinia + Leaflet) com login, mapa, planejador de rota e histórico.
- Testes de front: Vitest (18 testes) verdes; `lint`, `typecheck` e `build` limpos.

---

## 2. Infraestrutura de Dados Já Construída

| Ativo | Conteúdo | Localização |
|-------|----------|-------------|
| Rede hidrográfica (BHAE/AHGN) | 481.135 trechos nacionais; recortes de hidrovias navegáveis (121.661) e federais (22.926) | `data/*.gpkg` |
| Banco consolidado (dados) | `estacoes` (75), `rios` (14.135), `telemetria` (128.237), `cotas_historicas` (75), `navegabilidade` (75), `decretos` (144), `trechos_navegaveis` (121.661), `estacoes_trechos` (75) | `data/hidrowize.db` |
| Banco da aplicação/geoespacial | PostgreSQL + PostGIS (`ygape`) com estações, trechos (121.661, `geometry`/4326), telemetria, satélite, usuários, rotas e logs | container Docker `ygape-db` (VPS) |
| ETL de espelhamento | `backend/carregar_postgis.py` (SQLite → PostGIS, idempotente) | `backend/` |
| Dados de satélite | `estacoes_virtuais` (4.734), `series_nivel_satelite` (590.698), `batimetria_sicflow` (1.315.079), `series_vazao_satelite` (475.111) | `data/hidrowize.db` |
| Cota de fundo estimada | `cota_fundo_trecho` (121.661 trechos) | `data/hidrowize.db` |
| Coletores | Telemetria e cotas históricas ANA (SOAP e REST), satélite (SWOT), legislação | `backend/*.py` |
| Scripts derivados | Navegabilidade, histórico geográfico, extração de sondagens, geração do SQLite | `backend/*.py` |
| Mapa exploratório | Camadas de hidrovias, profundidade, estações e histórico de nível | `frontend/mapa-hidrovias/` |
| Dashboard de dados | Painel estático sobre os dados coletados | `frontend/dashboard/` |
| Protótipos de interface | Três alternativas de UI + protótipo PWA (`manifest.json`) | `frontend/prototipos/` |
| Aplicação web | Vue 3 + Vite (SPA) consumindo a API | `frontend/src/` |

---

## 3. Requisitos Funcionais — Status

### 3.1 Autenticação e Usuários

| ID | Requisito | Status | Observação |
|----|-----------|--------|------------|
| RF001 | Login do piloto | Atendido | `POST /auth/login` (JWT HMAC) + `LoginView` |
| RF002 | Cadastro de usuários pelo admin | Atendido | `POST /usuarios` (admin) |
| RF003 | Listar/editar/desativar usuários | Atendido | `GET/PUT/DELETE /usuarios` (admin) |
| RF004 | Atualização de perfil | Atendido | `PUT /auth/me` (nome/senha) + seção Perfil em Configurações |

### 3.2 Rede Hidrográfica e Grafo

| ID | Requisito | Status | Observação |
|----|-----------|--------|------------|
| RF005 | Importar shapefile da rede para o PostGIS | Atendido | Rede em `trechos_navegaveis` com geometria PostGIS (`MultiLineString`, SRID 4326) |
| RF033 | Importar pontos batimétricos | Atendido | Batimetria SICFLOW (1,3 mi nós) persistida no banco |
| RF006 | Construir grafo e validar conectividade | Atendido | `routing_engine.RiverGraph` monta adjacência bidirecional a partir de `noorigem`/`nodestino` |
| RF007 | Definir bacia/área ativa | Parcial | Área ativa = `hidrovias_navegaveis_bhae`; formalização da bacia pendente |
| RF008 | Listar nós e arestas para auditoria | Parcial | `GET /grafo/status` retorna contagens; sem listagem por nó/aresta |

### 3.3 Cotas e Níveis (ANA)

| ID | Requisito | Status | Observação |
|----|-----------|--------|------------|
| RF009 | Coleta automática de cotas (60 min) | Atendido | Coletores SOAP/REST + timers; telemetria com 128.237 leituras |
| RF010 | Coleta manual | Parcial | Executável por linha de comando; `POST /niveis/coletar` responde 501 |
| RF011 | Visualizar nível atual no mapa | Atendido | `GET /estacoes` + `MapaView`/`RiverMap` com nível e mínima histórica |
| RF012 | Mínimos históricos por estação | Atendido | Séries históricas e cota mínima persistidas |

### 3.4 Batimetria e Profundidade

| ID | Requisito | Status | Observação |
|----|-----------|--------|------------|
| RF013 | Importar pontos batimétricos | Atendido | SICFLOW no banco |
| RF031 | Interpolar cota de fundo por aresta | Parcial | Resolvido por modelo de ML (RF035), que substitui o IDW; `cota_fundo_trecho` gerado |
| RF014 | Recalcular profundidades com novos níveis | Parcial | Motor usa `hig_drn_depth_m`; falta integrar `nível − cota_fundo` e nivelar o datum |
| RF015 | Mapa de profundidades estimadas | Parcial | Camada de profundidade (proxy) no mapa; não é a profundidade calculada por nível |

### 3.5 Motor de Roteamento

| ID | Requisito | Status | Observação |
|----|-----------|--------|------------|
| RF016 | Calcular rota (origem, destino, calado, velocidade) | Atendido | `POST /rotas/calcular` + `RotaNovaView` |
| RF017 | Retorno da rota em GeoJSON | Atendido | Resposta inclui `geojson` + `items` |
| RF018 | Marcar arestas intransitáveis | Atendido | Arestas com `depth < calado + margem` são podadas; flag `transitavel` no retorno |
| RF032 | Derivação da correnteza (Q/A) | Parcial | Fórmula definida (RN025); Q e largura reais ainda não validados |
| RF019 | Roteamento A* por tempo | Parcial | Hoje é menor caminho por **distância** (Dijkstra); custo por tempo previsto |
| RF020 | Resumo da rota | Atendido | `RouteSummary` (distância, tempo, trechos críticos, profundidade mínima) |

### 3.6 Modo Offline e Sincronização

| ID | Requisito | Status | Observação |
|----|-----------|--------|------------|
| RF021 | Persistência local (rota, níveis, grafo) | Atendido | Dexie/IndexedDB: estações, rotas e fila de pendências |
| RF022 | Cálculo de rota offline | Atendido | `GET /sync/snapshot` (grafo ~9 MB) + `services/roteador.ts` (Dijkstra local) + fallback no `useRotaStore` |
| RF023 | Sincronização automática (pull/push) | Atendido | `useOfflineStore`: pull de estações/rotas e push das rotas pendentes ao voltar online |
| RF024 | Log de sincronização | Parcial | Data da última sincronização + fila de pendências; log de auditoria de eventos separado |

### 3.7 Monitoramento de Rota

| ID | Requisito | Status | Observação |
|----|-----------|--------|------------|
| RF027 | Ativar monitoramento de rota | Atendido | `POST /rotas/{id}/monitorar` + botão "Monitorar" no histórico |
| RF028 | Recálculo automático por variação ≥ 30 cm | Atendido | job de vigia (`monitor_loop`): limiar 30 cm, cooldown 30 min, evento extremo ≥ 100 cm |
| RF029 | Notificação em tempo real | Atendido | evento `rota_alterada` publicado no barramento |
| RF034 | Canal WebSocket/SSE por usuário | Atendido | `WS /api/v1/ws?token=` + `useNotificacaoStore` (reconexão automática) |
| RF030 | Histórico de alterações da rota | Atendido | tabela `rota_alteracao` + `GET /rotas/{id}/alteracoes` |

### 3.8 Relatórios e Auditoria

| ID | Requisito | Status | Observação |
|----|-----------|--------|------------|
| RF025 | Histórico de rotas do piloto | Atendido | `POST/GET/DELETE /rotas` (JWT) + `HistoricoView` |
| RF026 | Logs de coleta e sincronização | Atendido | Tabela `log_eventos` + `GET /logs` (admin) + `LogsView` |

### 3.9 Inteligência de Dados (Satélite + ML)

| ID | Requisito | Status | Observação |
|----|-----------|--------|------------|
| RF035 | Estimar cota de fundo com ML | Atendido | `treinar_cota_fundo.py`; previsões em `cota_fundo_trecho` (121.661) |
| RF036 | Interpolar nível com ML | Atendido | `interpolar_nivel.py`; ML supera IDW no regime esparso |
| RF037 | Rating curve (nível × vazão) | Atendido | `rating_curve.py`; vazão definida pela estação influente |
| RF038 | Classificar navegabilidade com ML | Bloqueado | Rótulos derivam da própria regra; falta rótulo independente |
| RF039 | Previsão de nível/vazão (cheia/estiagem) | Atendido | `prever_nivel.py`; climatologia mensal |

---

## 4. Requisitos Não Funcionais — Status

| ID | Requisito | Status | Observação |
|----|-----------|--------|------------|
| RNF01 | Roteamento ≤ 5 s para 10.000 nós | Parcial | Não medido formalmente; rota sobre 121k trechos responde em segundos |
| RNF02 | Front-end ≤ 3 s em 4G | Parcial | Build enxuto; sem medição Lighthouse |
| RNF03 | Suporte a 24 h offline | Parcial | Cache de estações/rotas e fila de pendências; sem cálculo offline |
| RNF04 | Python 3.10+ e Vue.js 3 | Atendido | Backend Python + front Vue 3 + Vite + TS |
| RNF05 | Armazenamento local (IndexedDB/SQLite) | Atendido | Dexie.js (IndexedDB) |
| RNF06 | Responsivo e multi-navegador | Parcial | Layout mobile-first; sem matriz de testes por navegador |
| RNF07 | Service Worker (stale-while-revalidate) | Atendido | `public/sw.js` (assets + API) + `manifest.webmanifest` |
| RNF08 | Autenticação JWT segura | Atendido | JWT HMAC + scrypt para senhas; token em `localStorage` |
| RNF09 | Criptografia de campos locais | Não iniciado | Previsto (WebCrypto) |
| RNF10 | Logs de auditoria | Atendido | `log_eventos` + `GET /logs` (admin); coletores com log em arquivo |

---

## 5. Regras de Negócio — Status

| Grupo de Regras | Regras | Status |
|-----------------|--------|--------|
| Usuário | RN001–RN005 | Atendidas (login, papéis, sessão) |
| Estação | RN006–RN008 | Parcialmente atendidas nos coletores (código único, coleta padronizada) |
| Rota | RN009–RN012, RN022, RN023, RN029 | RN010/RN011/RN012 integradas no motor; RN022/RN023 em aberto |
| Nível | RN013–RN015 | Atendidas nos dados (mínima histórica, série, janela) |
| Nível | RN019–RN021 | Atendidas (vigia: limiar 30 cm, cooldown 30 min, extremo ≥ 100 cm) |
| Batimetria e Correnteza | RN024, RN025, RN028 | Parcialmente apoiadas nos dados (cota de fundo, vazão, largura) |
| Sincronização | RN016–RN018, RN026, RN027 | Atendidas — RN016/RN017/RN018 via `useOfflineStore`; RN026 (paridade offline×backend) e RN027 (fallback de polling) implementadas |

---

## 6. O Que Falta (Lacunas e Próximos Passos)

### 6.1 Lacunas críticas

1. **Referência vertical (datum) inconsistente.** A cota da régua ANA (cm, referida ao zero da régua) não está na mesma referência da cota de fundo (m, geóide). Sem calibrar, `profundidade = nível − cota_fundo` não é confiável.
2. **Custo de rota por distância, não por tempo.** O motor ainda não incorpora a velocidade própria da embarcação e a correnteza no peso das arestas (RF019/RF032).
3. **Conectividade dos trechos.** Risco de pontas soltas, duplicatas e trechos desconexos no corredor.
4. **Estações deslocadas do canal** (até ~3 km) e proxies AHGN grosseiros em rios grandes afetam a associação estação→aresta.
5. **Offline real.** O grafo da BHAE (~820 MB) não cabe no cliente; o cálculo offline exige um subgrafo simplificado.

### 6.2 Próximos passos priorizados

| # | Ação | Depende de |
|---|------|------------|
| 1 | Calibrar o datum vertical (nível ANA × cota de fundo) | telemetria |
| 2 | Motor de pesos por tempo (correnteza + velocidade) e A* com heurística | #1 |
| 3 | Fase 5 — persistência local (Dexie), Service Worker/PWA e sincronização | — |
| 4 | Fase 5b — monitoramento de rota e notificações em tempo real (WS/SSE) | backend |
| 5 | Telas de administração (usuários, coleta, logs) | backend |
| 6 | Empacotamento PWA/Capacitor e testes ISO/IEC 25010 | Fases 5–6 |

### 6.3 Etapas de produto ainda ausentes

- Cálculo de rota offline (RF022) e paridade offline×backend (RN026) — dependem de subgrafo simplificado.
- Publicação do frontend e domínio público do Ygapé.
- Empacotamento mobile (Capacitor) e plano de testes (ISO/IEC 25010).

---

## 7. Bloqueios e Dúvidas Abertas

- **RF038** depende de rótulos independentes de navegabilidade (AIS, relatos de pilotos, calado efetivamente transitado); sem eles, a regra RF018 permanece como referência.
- **Validação com orientador** do uso do SICFLOW como cota de fundo e do limiar de transitabilidade (RN010) e calado de referência (RN029).
- **Preditores climáticos** (chuva/ENSO) para previsão além da climatologia mensal.
- **`/rotas/calcular` é público** — decisão de mantê-lo sem exigir JWT segue em aberto.
