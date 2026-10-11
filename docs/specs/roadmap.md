# Roadmap

## Fase 1 — Fundacao (Ambiente + Dados)

- [x] RF009 — Coletor ANA (SOAP telemetria + REST v2) para estacoes da area ativa
- [x] RF005 — Rede hidrografica ANA: BHAE/AHGN baixado e recortado em hidrovias navegaveis (gpkg/geojson/csv). Falta: importar no PostGIS
- [ ] RF033 — Batimetria: PARCIAL — proxy AHGN `hig_drn_depth_m` + elevacao; batimetria satelital SICFLOW ja coletada (`batimetria_sicflow`, 1,3 mi nos) como fonte complementar de cota de fundo (validar com orientador)
- [ ] RF007 — Definir a bacia amazonica (prioridade area brasileira) como area ativa
- [ ] RF006 — Construir grafo NetworkX e validar conectividade (dados prontos: colunas `noorigem`/`nodestino`)
- [ ] Setup: Poetry, Docker (Postgres+PostGIS), FastAPI base, Vue+Vite
- [ ] Seed: PARCIAL — CSVs prontos (`estacoes_am.csv`, cruzamento, profundidade); admin pendente

**Entregaveis de dados ja prontos (Fase 1):**

- `data/hidrovias_navegaveis_bhae.gpkg` — 121.661 trechos navegaveis (Federal + Internacional + Estadual Strahler>=4)
- `data/hidrovias_federais_bhae.gpkg` — 22.926 trechos federais
- `planilhas/estacoes_am_x_hidrovias_navegaveis.csv` — 75 estacoes × trecho (dominio + atributos AHGN)
- `planilhas/profundidade_trechos_navegaveis.csv` — profundidade proxy + largura + elevacao por trecho (34.346)
- `frontend/mapa-hidrovias/` — mapa interativo (dominio / profundidade / estacoes)
- Fontes documentadas em `mapeamento_fontes.md` (secoes 9 e 10)

## Fase 2 — Motor de Roteamento

- [ ] RF013/RF031 — Importar batimetria e interpolar cota de fundo (IDW)
- [ ] RF014 — Profundidade por aresta (nivel atual - cota fundo) + estacao influente (RN023)
- [ ] RF018 — Regra de transitabilidade (profundidade < calado)
- [ ] RF032 — Correnteza derivada (V = Q/A) por aresta
- [ ] RF019 — Algoritmo A* minimizando tempo (custo = distancia/velocidade)
- [ ] RF016 — Endpoint POST /rotas/calcular (com velocidade da embarcacao)
- [ ] RF017 — Retorno em GeoJSON
- [ ] RF015 — Mapa de profundidades estimadas
- [ ] RF027 — Ativar/desativar monitoramento de rota
- [ ] RF028 — Recomputacao automatica por variacao >= 30cm (RN020/RN021)
- [ ] RF029 — Notificacao de rota alterada
- [ ] RF030 — Historico de alteracoes da rota monitorada

## Fase 3 — API Completa e Auth

- [x] RF001 — Login JWT + roles admin/piloto
- [x] RF002 — CRUD de usuarios (admin)
- [x] RF011 — Endpoints de estacoes e niveis
- [ ] RF010 — Coleta manual (admin) — endpoint responde 501 (depende do serviço agendado)
- [x] RF025 — Historico de rotas por usuario
- [x] Swagger/OpenAPI documentado automaticamente (FastAPI)
- [x] RF026 — Painel de auditoria (log_eventos + GET /logs + LogsView)

## Fase 4 — Frontend Core

- [x] RF009 — Mapa interativo (Leaflet) com estacoes e niveis
- [x] RF016 — Formulario de rota (origem/destino/calado)
- [x] RF017 — Exibicao da rota + resumo (distancia, trechos criticos)
- [x] RF011 — Marcadores de estacoes com nivel atual
- [x] RF025 — Historico de rotas no app

## Fase 5 — Offline e Sincronizacao

- [x] RF021 — Persistencia local (Dexie.js: estacoes, rotas, fila de pendencias)
- [x] RNF07 — Service Worker (stale-while-revalidate) + manifest PWA
- [ ] RF022 — Calculo offline com A* local (services/roteador.ts) sobre o grafo do snapshot
- [ ] RN026 — Paridade de resultados offline vs backend
- [x] RF023 — Sincronizacao automatica (pull/push)
- [x] RF024 — Logs de sincronizacao (data da ultima sync + fila)
- [ ] RNF03 — Validar 24h de uso offline

## Fase 5b — Notificacoes em Tempo Real

- [ ] RF034 — Canal WebSocket/SSE por usuario (FastAPI WebSocket)
- [ ] RF029 — Entrega do evento `rota_alterada` em tempo real
- [ ] RN027 — Fallback de polling quando WS indisponivel
- [ ] useNotificacaoStore + reconexao automatica no frontend

## Fase 6 — Polimento e Empacotamento

- [ ] RF026 — Logs de coleta para admin
- [ ] RNF09 — Criptografia de campos sensiveis locais (WebCrypto)
- [ ] Empacotar PWA instalavel + Capacitor (Android/iOS)
- [ ] Testes ISO 25010 (pytest backend, Cypress frontend)
- [ ] Testes de performance (10k nos < 5s)
- [ ] Documentacao final e relatorio de testes

## Fase 7 — Inteligencia de Dados (Satelite + ML)

Dados de satelite ja coletados e persistidos no `hidrowize.db` (ver `mapeamento_fontes.md` secoes 11 e 12):
`estacoes_virtuais` (4.734), `series_nivel_satelite` (590.698), `batimetria_sicflow` (1.315.079 nos),
`series_vazao_satelite` (475.111).

- [x] RF035 — Regressao de cota de fundo: modelo RandomForest treinado (`treinar_cota_fundo.py`) com labels do SICFLOW + atributos AHGN. Resultado: MAE 6,9 m (vs 8,6 m do baseline `hig_drn_elevation_min`), viés zerado; previsoes persistidas em `cota_fundo_trecho` (121.661 trechos). Ver `mapeamento_fontes.md` secao 12.3
- [x] RF036 — Interpolacao de nivel com ML: `interpolar_nivel.py` compara RandomForest/kNN/HGB (covariavel de elevacao) vs IDW. ML supera IDW em ~20-30% no regime esparso (~75 reguas ANA); no regime denso de satelite (~4.600 estacoes) o IDW ja basta. Ver `mapeamento_fontes.md` secao 12.5
- [x] RF037 — Curva nivel×vazao (rating curve): `rating_curve.py` (46.946 pares, 40 estacoes ANA). Curva-chave quase deterministica por estacao (in-station R2=1,0); regionalizacao falha (R2=0,04) → a vazao deve vir da estacao influente (RN028), nao de modelo global. Ver `mapeamento_fontes.md` secao 12.6
- [x] RF038 — Classificacao de navegabilidade: `classificar_navegabilidade.py` mostra que os rotulos atuais derivam da regra RF018 (acuracia 100%) → ML nao agrega (circular); bloqueado por falta de rotulo independente (decretos municipais insuficientes). Regra RF018 segue operacional. Ver `mapeamento_fontes.md` secao 12.7
- [x] RF039 — Previsao de nivel/vazao (cheia/estiagem): `prever_nivel.py`. A climatologia mensal captura o ciclo sazonal (Manaus: pico ~junho, baixa ~novembro; MAE 1-2 m); ML sazonal nao supera sem preditores climaticos externos. Ver `mapeamento_fontes.md` secao 12.8

**Observacoes:** separar treino/teste por trecho ou periodo (autocorrelacao hidrologica); adicionar
`scikit-learn`/`xgboost` ao `requirements.txt`; usar juncao espacial (lon/lat) entre batimetria
(SWORD v17b) e vazao (SWORD v16).
