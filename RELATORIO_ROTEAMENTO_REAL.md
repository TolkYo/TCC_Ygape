# Relatório Técnico — Implementação Real do Roteamento Fluvial
## Manaus → Itacoatiara (HidroWaze)

**Data:** 30/08/2026 · **Escopo:** análise do estado atual e plano para roteamento real na bacia amazônica (corredor Manaus–Itacoatiara)

---

## 1. Objetivo deste relatório

Responder, com base no que o projeto **já possui** (planilhas, coletores, ML, specs e o MVP de grafos):

1. O que falta para trocar os dados fictícios do MVP por dados reais.
2. **Onde ficarão os vértices (nós)** do grafo real.
3. **Como calcular o peso das arestas** a partir das planilhas e da API ANA.
4. Usar **pontos do rio** ou **pontos da ANA** — e qual é a melhor estratégia.
5. Quais os próximos passos para rodar **Manaus → Itacoatiara** de verdade.

---

## 2. Estado atual do projeto (o que já temos)

### 2.1 Dados coletados em `planilhas/`

| Arquivo | Conteúdo | Relevância para o grafo |
|---|---|---|
| `estacoes_am.csv` | 75 estações ANA (código, rio, município, lat/lon) | Âncoras de dados de nível |
| `estacoes_am_enriquecidas.csv` | + bacia, tipo, telemetrica, escala, altitude, área de drenagem, operadora | Contexto de cada estação |
| `estacoes_am_navegabilidade.csv` | cota atual, cota mínima histórica, `NAVEGAVEL/RESTRITO/CRITICO` | Estado atual da rede |
| `estacoes_am_x_hidrovias_navegaveis.csv` | 75 estações × trecho AHGN (dominio, profundidade, largura, vazão, elevação, Manning, sinuosidade, `distancia_m`, `status`) | **Associação estação→trecho (base do grafo)** |
| `estacoes_am_x_hidrovias_federais.csv` | idem para hidrovias federais | Rede federal |
| `profundidade_trechos_navegaveis.csv` | 34.346 trechos com `hig_drn_depth_m`, `width`, `annual_flow`, elevação, sinuosidade, `centroid_lon/lat` | **Proxy de profundidade por trecho** |
| `cotas_historicas_am.csv` | mínimo/máximo/média por estação | Sazonalidade e cota mínima |
| `telemetria_cotas_am.csv` | leituras a cada 15 min (`cota_adotada`, `vazao_adotada`) | **Nível atual (dinâmico)** |
| `decretos_legisla_am.csv` | decretos de emergência (cheia/estiagem) | Validação qualitativa |
| `rios_ana.csv` | catálogo de rios | Contexto geográfico |

### 2.2 Scripts em `backend/` (funcionais)

- **Coleta ANA:** `ana_soap.py`, `ana_client.py`, `coletar_telemetria.py`, `coletar_cotas_historicas.py`
- **Satélite:** `coletar_hydroweb.py` (SWOT/SICFLOW/vazão/altimetria)
- **Legislação:** `coletar_legisla_am.py`
- **Derivados:** `gerar_navegabilidade.py`, `gerar_historico_geo.py`, `extrair_sondagens_carta.py`
- **Banco:** `gerar_sqlite.py` → gera `data/hidrowize.db` com as tabelas: `estacoes`, `rios`, `telemetria`, `cotas_historicas`, `navegabilidade`, `decretos`, `trechos_navegaveis`, `estacoes_trechos`, além do satélite: `estacoes_virtuais`, `series_nivel_satelite`, `batimetria_sicflow`, `series_vazao_satelite`
- **ML (fase 7, já treinado):** `treinar_cota_fundo.py` (RF035), `interpolar_nivel.py` (RF036), `rating_curve.py` (RF037), `classificar_navegabilidade.py` (RF038), `prever_nivel.py` (RF039)

### 2.3 Rede hidrográfica (BHAE/AHGN da ANA)

- GeoPackage nacional: 481.135 trechos (`MULTILINESTRING`), colunas **`noorigem`, `nodestino`, `cotrecho`, `cocursodag`** → **grafo NetworkX direto** (RF006).
- Recortes: `hidrovias_federais_bhae.gpkg` (22.926 trechos) e `hidrovias_navegaveis_bhae.gpkg` (121.661 trechos).
- Exportações para o mapa: `frontend/mapa-hidrovias/hidrovias.geojson`, `hidrovias_profundidade.geojson`, `estacoes.geojson`, `historico_nivel.js`.

### 2.4 Dados de satélite (SWOT / hydroweb.next)

- `estacoes_virtuais` (4.734) + `series_nivel_satelite` (590.698 obs).
- `batimetria_sicflow` (1.315.079 nós, seção transversal de 12 pontos + `cota_fundo` + `largura_m`) → **cota de fundo**.
- `series_vazao_satelite` (475.111 obs `consensus_q`) → vazão independente.

### 2.5 Resultados de ML (diretamente utilizáveis)

| Modelo | Resultado | Uso no grafo |
|---|---|---|
| RF035 — cota de fundo | MAE 6,9 m (vs 8,6 m baseline), viés zerado; previsto p/ 121.661 trechos | `cota_fundo_trecho` por aresta |
| RF036 — nível | ML supera IDW em ~20–30% no regime esparso (~75 réguas) | nível em trechos sem régua |
| RF037 — rating curve | curva-chave quase determinística **por estação** (R²=1,0) | vazão da estação influente |
| RF038 — navegabilidade | regra RF018 (limiar) supera ML; rótulos são derivados dela | manter regra de limiar |
| RF039 — previsão | climatologia mensal captura cheia/estiagem (MAE 1–2 m) | planejamento |

### 2.6 Documentação e specs (`docs/specs/`)

- `visao-geral.md`, `api-spec.md`, `requisitos-funcionais.md`, `regras-negocio.md` (RN009–RN029), `roadmap.md`, `modelo-dados.md` (ER PostGIS), `mapeamento-ana-hidrowebservice.md`.
- `mapeamento_fontes.md` — mapa completo de fontes e decisões.

### 2.7 MVP de grafos (`Implementação Grafos/ManausPraiaDaLua/roteamento-fluvial-amazonas/`)

- NetworkX + Dijkstra com dados **fictícios** (Marina do Davi → Praia da Lua), peso = `distance_m`.
- Já valida a arquitetura: `builder → router → visualização → testes`. A lógica central será **reaproveitada** com dados reais.

---

## 3. O que falta para o roteamento real (gap analysis)

| Capacidade | Status | Falta fazer |
|---|---|---|
| Grafo construído de dados reais (RF006) | ❌ Pendente | Importar trechos BHAE/AHGN → NetworkX |
| Área ativa recortada (RF007) | ⚠️ Parcial | Recorte do corredor Manaus–Itacoatiara |
| Cota de fundo por aresta (RF031/RN024) | ✅ Cálculo pronto | Associar `cota_fundo` ao grafo |
| Profundidade por aresta (RF014/RN022) | ⚠️ Lógica definida | Resolver datum vertical (ver §5) |
| Transitabilidade (RF018/RN010) | ⚠️ Regra pronta | Integrar ao peso da aresta |
| Correnteza V=Q/A (RF032/RN025) | ⚠️ Lógica definida | Validar Q/largura reais |
| Roteador tempo-ótimo A* (RF019) | ❌ Pendente | Substituir Dijkstra fictício por A* com heurística de tempo |
| Endpoint `/rotas/calcular` (RF016/17) | ❌ Pendente | FastAPI + GeoJSON |
| Frontend exibindo rota | ⚠️ Mapa existe | Camada de rota + formulário |

### 3.1 Lacunas críticas (atenção!)

1. **`data/` não está presente localmente.** Os `.gpkg`, o `hidrowize.db` e os dados de satélite são regeneráveis, mas estão fora do repositório (`.gitignore`). **Primeiro passo:** rodar `backend/gerar_sqlite.py` e os coletores (ou restaurar a pasta `data/`) para ter o banco e a malha reais.
2. **Referência vertical (datum) inconsistente.** A cota da régua ANA (cm, referida ao zero da régua) NÃO está na mesma referência da `cota_fundo` (m, SICFLOW/AHGN, referida ao geóide). A fórmula `profundidade = nível − cota_fundo` só vale se as duas cotas forem **na mesma referência**. Precisa de uma etapa de nivelamento/calibração (ex.: regressão por estação entre a cota da régua e o nível absoluto do satélite).
3. **Conectividade do grafo.** `MultiLineString` por trecho, sem garantia de que os trechos do corredor estejam topologicamente conectados (ex.: pontas soltas, paranás, duplicatas). Requer validação (e eventuais snap de extremidades).
4. **Estações deslocadas do canal** (até ~3 km; coluna `rio_confere=PARCIAL`) → afeta o snap da RN023.
5. **Proxies AHGN grosseiros em rios grandes** (elevação = 11,0 em Manaus/Itacoatiara) → preferir SICFLOW/RF035 para `cota_fundo`.

---

## 4. Onde ficarão os vértices (nós)

### 4.1 Três estratégias possíveis

**A) Nós = pontos do rio (trechos BHAE/AHGN) — RECOMENDADA ✅**
- Cada trecho do BHAE tem `noorigem`/`nodestino` → vira **uma aresta** entre dois nós.
- Nós = extremidades/interseções dos trechos (topologia real da drenagem).
- **Vantagens:** fiel à rede de navegação (paranás, braços, confluências), atributos AHGN já vêm por trecho, escala controlada (corredor Manaus–Itacoatiara = centenas de nós, não milhões).
- **Desvantagens:** pontos de interesse (marina, porto, praia) precisam de *snap* para o nó mais próximo.

**B) Nós = estações ANA — DESCARTADA ❌**
- Só 75 estações no AM, esparsas e nem sempre no canal principal.
- Aresta longa entre estações → não representa bifurcações nem trechos curtos.
- Útil apenas como **âncora de dados de nível** (RN023), não como nó de rota.

**C) Híbrido: nós de junção + POIs + snap — USO PRÁTICO**
- Vértices = junções dos trechos + **pontos de interesse** (Manaus, Itacoatiara, portos, marinas) com *snap* à rede.
- Estações ANA/virtuais ficam **associadas ao trecho mais próximo** (RN023), atualizando os pesos — **estações ≠ nós obrigatoriamente**.

### 4.2 Recomendação para o MVP real

> **Vértices = topologia dos trechos BHAE (noorigem/nodestino) + snapping de origem/destino.**
> Estações entram como **fontes de dados** (nível/cota), nunca como nós impostos.
> Modelo futuro: `REDE DE NAVEGAÇÃO → GRAFO ↑ DADOS ANA/ESTAÇÕES → ATUALIZAÇÃO DE PESOS`.

### 4.3 Origem/destino no cenário real

- **Origem — Manaus:** porto/marina mais próximo do nó da rede no trecho do Rio Negro/Amazonas (estação 14990000 está a ~? km do canal, `rio_confere=PARCIAL`).
- **Destino — Itacoatiara:** nó mais próximo do trecho 416801 (Rio Amazonas, estação 16030000).
- O *snap* = projetar o ponto do POI sobre a geometria do trecho e criar (ou escolher) o nó mais próximo.

---

## 5. Cálculo do peso das arestas (o coração do sistema)

### 5.1 Variáveis por aresta e fonte de dados

| Variável | Fórmula / origem | Fonte no projeto |
|---|---|---|
| `distancia_m` | comprimento do trecho | geometria do trecho (BHAE) |
| `cota_fundo` (m) | leito do rio | `batimetria_sicflow.cota_fundo` (se nó <1 km) → senão `cota_fundo_estimada` (RF035) → senão proxy `hig_drn_elevation_min − hig_drn_depth_m` |
| `nivel_atual` (m) | nível d'água | `telemetria_cotas_am.cota_adotada` da **estação influente** (RN023) ou nível interpolado (RF036); **calibrar datum** (ver §3.1.2) |
| `profundidade_estimada` | `nivel_atual − cota_fundo` | RN022 |
| `largura_canal` | largura do trecho | `hig_drn_width_m` ou `largura_m` SICFLOW |
| `vazao` (m³/s) | descarga | `vazao_adotada` (ANA) da estação influente; senão `hig_drn_annual_flow` (RN028); validar com `consensus_q` (SWOT) |
| `vel_correnteza` (m/s) | `Q / A` (A = largura × profundidade) | RN025 |
| `calado` + `margem` | parâmetro do piloto | RN009, RN012 (padrão 0,5 m) |

### 5.2 Pipeline de custo (ordem de cálculo)

Para **cada aresta** `e`, no momento do roteamento:

```
1. TRANSITABILIDADE (restrição dura)
   profundidade_e = nivel_e − cota_fundo_e
   transitavel_e   = profundidade_e >= calado + margem      [RN010/RN012]
   se NOT transitavel_e → peso_e = +inf   (aresta bloqueada)

2. CORRENTEZA (RF032)
   Q_e  = vazao da estação influente (ou hig_drn_annual_flow)  [RN028]
   A_e  = largura_e × profundidade_e                          [RN025]
   V_correnteza_e = Q_e / A_e        (m/s)

3. VELOCIDADE LÍQUIDA (RN011)
   V_liquida_e = V_embarcacao ± V_correnteza
     (+ quando a favor da corrente, − quando contra)
   se V_liquida_e <= 0 → peso_e = +inf

4. TEMPO (custo primário)
   tempo_e = distancia_e / V_liquida_e      [horas]

5. CUSTO COMPOSTO (extensível, como no MVP)
   custo_e = tempo_e + risk_penalty + depth_penalty + current_penalty
```

**Custo usado no roteamento = `tempo_e`** (mínimo tempo), que já embute:
- bloqueio por profundidade (passo 1), e
- efeito da correnteza (passos 2–3).

Isso corresponde exatamente ao peso que o MVP preparou (`distance_m` → no futuro custo composto) e à regra RF019 (A* minimizando tempo).

### 5.3 Exemplo ilustrativo — trecho Rio Amazonas (Itacoatiara, fid 416801)

```
calado = 4,5 m | margem = 0,5 m  →  exige profundidade >= 5,0 m

cota_fundo (RF035/SICFLOW)     = 9,0  m   (leito, ref. geóide)
nível atual (estação influente)= 14,5 m   (mesma referência, após calibração de datum)
profundidade                   = 14,5 − 9,0 = 5,5 m   → 5,5 >= 5,0 ✓ TRANSITÁVEL

largura (hig_drn_width_m)      = 1.570 m
seção A                        = 1.570 × 5,5 ≈ 8.635 m²
vazão Q                        = 107.243 m³/s (média anual AHGN do trecho)
V_correnteza (bruta)           = 107.243 / 8.635 ≈ 12,4 m/s   ⚠️ proxy grosseiro

embarcação                     = 5,56 m/s (20 km/h), descendo o rio (a favor)
V_liquida                      = 5,56 + (valor real de correnteza 1–2 m/s) ≈ 6,6–7,6 m/s

trecho de 30 km                → tempo ≈ 30.000 / 7.000 ≈ 4,3 h (contra ~5,4 h sem correnteza)
```

> ⚠️ **Atenção:** o `V = Q/A` com proxies AHGN superestima a correnteza. Para o peso final, usar **largura da seção SICFLOW** e **Q real da estação** (`vazao_adotada`), validando com `consensus_q` (SWOT). O valor deve ficar na faixa real do Amazonas (~1–2 m/s).

### 5.4 Estimativa do corredor Manaus → Itacoatiara

- Distância por rio: **~180–230 km** (reta ~180 km; meandros do Amazonas).
- Embarcação a 20 km/h a favor da corrente (~2 km/h): **~8–11 h**.
- Estações âncora no corredor: **MANAUS (14990000, Rio Negro)** → **JATUARANA (15030000)** → **CAREIRO (15040000, Paraná do Careiro)** → **ITACOATIARA (16030000, Rio Amazonas)**.
- Trechos AHGN relevantes: 419249 (Jatuarana), 417176 (Careiro), 416801 (Itacoatiara).
- Recorte espacial sugerido: bbox ~ `lat [-3,35, -3,00] × lon [-60,10, -58,35]`, filtrando `rio ∈ {Amazonas, Solimões, Negro}` e `nustrahler >= 6`.

### 5.5 Qual algoritmo usar?

| Critério | Dijkstra (MVP) | A* (produção, RF019) |
|---|---|---|
| Corredor linear Manaus–Itacoatiara | ✅ suficiente | ✅ melhor |
| Rede completa 10k+ nós | lento | ✅ heurística acelera |

**Recomendação:** implementar `A*` (NetworkX `astar_path`) com heurística = `distância_haversine / velocidade_máxima`, e manter Dijkstra como fallback/validação. O `DijkstraRouter` do MVP é reaproveitado quase integralmente.

---

## 6. Pontos do rio vs estações ANA — qual usar?

| Critério | Pontos do rio (BHAE/AHGN) | Estações ANA (75) | Estações virtuais (SWOT, 4.734) |
|---|---|---|---|
| Define a topologia do grafo | ✅ sim (nós/arestas) | ❌ não | ❌ não |
| Geometria por trecho | ✅ sim | ❌ | ❌ |
| Nível/cota (dinâmico) | ❌ | ✅ (15 min) | ⚠️ (revisita ~21 dias) |
| Cota de fundo | ✅ proxy AHGN | ❌ | ✅ SICFLOW |
| Vazão | ✅ `annual_flow` | ✅ `vazao_adotada` | ✅ `consensus_q` |
| Atualização em tempo real | ❌ | ✅ | ❌ |

**Conclusão:** 
- A **malha/geometria vem dos pontos do rio (BHAE)** — é a base do grafo.
- O **estado dinâmico vem das estações ANA** (nível atual) associadas aos trechos (RN023).
- O **satélite complementa** (cota de fundo SICFLOW + vazão + nível em trechos sem régua).

> **ESTAÇÕES ≠ NÓS.** Estações são âncoras de dados que atualizam os pesos; quem define o grafo é a rede de navegação.

---

## 7. Roteiro prático Manaus → Itacoatiara (passo a passo)

1. **Restaurar dados:** rodar coletores/`gerar_sqlite.py` (ou restaurar `data/`) → `hidrowize.db` com trechos, estações, batimetria, vazão.
2. **Recortar o corredor:** extrair do BHAE os trechos do Amazonas/Solimões/Negro entre Manaus e Itacoatiara (bbox + filtro por `rio`/`nustrahler`).
3. **Construir o grafo real:** nós = `noorigem/nodestino`; arestas = trechos com `distance_m` (geometria) e atributos AHGN.
4. **Validar conectividade:** DFS/BFS garante um caminho contínuo Manaus→Itacoatiara (corrigir pontas soltas/duplicatas).
5. **Associar estações (RN023):** cada aresta ganha a estação influente mais próxima na rede (raio 50 km) → `telemetria.cota_adotada` e `vazao_adotada`.
6. **Cota de fundo:** join espacial SICFLOW (<1 km) → senão `cota_fundo_estimada` (RF035) → senão proxy AHGN.
7. **Calibrar datum vertical:** alinhar cota da régua ANA com a cota de fundo (mesma referência) usando regressão por estação vs nível do satélite.
8. **Motor de pesos:** implementar o pipeline da §5.2 (transitabilidade → correnteza → velocidade → tempo).
9. **Roteador:** `A*` (tempo) no grafo real; origem = snap de Manaus, destino = snap de Itacoatiara.
10. **Saída:** rota em GeoJSON + resumo (distância, tempo, trechos críticos) — conforme `api-spec.md`.
11. **Testes:** repetir a suíte do MVP com os dados reais (conectividade, menor tempo, transitabilidade).
12. **Visualização:** plotar a rota real no mapa (Leaflet já pronto em `frontend/mapa-hidrovias/`) e na imagem matplotlib.

---

## 8. Tópicos / stack que deveremos utilizar

| Área | Tecnologia | Uso |
|---|---|---|
| Linguagem | Python 3.12 | Backend e modelos |
| Grafos | **NetworkX** | Grafo + A*/Dijkstra (já no MVP) |
| Geoespacial | **GeoPandas**, **Shapely**, **pyproj** | Geometrias, snapping, reprojeção |
| Banco | **SQLite** (`hidrowize.db`) agora; **PostGIS** na fase de API | Trechos, estações, níveis |
| Dados tabulares | **pandas** | Planilhas/CSVs |
| Visualização | **matplotlib** + Leaflet (frontend) | Imagem da rota + mapa |
| Web | **FastAPI** | Endpoints (`/rotas/calcular`) e GeoJSON |
| ML (já pronto) | **scikit-learn** | `cota_fundo` (RF035), nível (RF036), vazão (RF037) |
| Coleta | **requests**, SOAP ANA, `py-hydroweb` | Nível em tempo real + satélite |
| Testes | **pytest** | Suíte do MVP estendida |
| Qualidade | type hints + docstrings (padrão do MVP) | Manutenibilidade |

**Tópicos conceituais para o relatório/TCC:** teoria dos grafos (caminho mínimo), A* vs Dijkstra, snapping/geocodificação de pontos em rede, interpolação espacial (IDW/ML), datum vertical e calibração, hidráulica simplificada (V=Q/A), séries temporais hidrológicas.

---

## 9. Próximos passos (ordem priorizada)

| # | Ação | Esforço | Depende de |
|---|---|---|---|
| 1 | Restaurar `data/` e gerar `hidrowize.db` | M | coletores |
| 2 | Recortar corredor Manaus–Itacoatiara do BHAE | M | #1 |
| 3 | Construir grafo real (NetworkX) + validar conectividade | M | #2 |
| 4 | Associar estação influente (RN023) e calibração de datum | A | #3, telemetria |
| 5 | Cota de fundo por aresta (SICFLOW/RF035) | M | #1 |
| 6 | Motor de pesos (transitabilidade + correnteza + tempo) | A | #4, #5 |
| 7 | A* com heurística de tempo | M | #6 |
| 8 | Endpoint `/rotas/calcular` (FastAPI + GeoJSON) | A | #7 |
| 9 | Camada de rota no mapa (frontend) | M | #8 |
| 10 | Testes e validação do cenário Manaus→Itacoatiara | M | #6–#9 |

> **Ação mais importante primeiro:** resolver a **consistência vertical (datum)** entre a cota da régua ANA e a cota de fundo — sem isso, `profundidade = nível − fundo` não é confiável e a transitabilidade pode ser decidida errado (erro de cota de fundo já é da ordem do calado, mediana 2,9 m — ver `mapeamento_fontes.md` §12.4).

---

## 10. Referências (arquivos-chave)

- `mapeamento_fontes.md` — fontes, decisões e resultados de ML (§9–12)
- `PLANEJAMENTO.md` — visão do sistema e requisitos
- `docs/specs/` — `regras-negocio.md` (RN009–RN029), `api-spec.md`, `requisitos-funcionais.md`, `roadmap.md`, `modelo-dados.md`, `visao-geral.md`
- `planilhas/` — dados ANA coletados
- `backend/gerar_sqlite.py` — esquema do `hidrowize.db`
- `frontend/mapa-hidrovias/` — mapa exploratório (Leaflet)
- `Implementação Grafos/ManausPraiaDaLua/roteamento-fluvial-amazonas/` — MVP de grafos (Dijkstra + arquitetura reutilizável)
