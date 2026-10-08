# Ygapé — Protótipo Funcional de Frontend (HidroWize)

> Protótipo estático do frontend do sistema de **roteamento fluvial dinâmico da bacia amazônica** (TCC — HidroWize). Nome de produto: **Ygapé**.

Este diretório contém duas visões funcionais em HTML/CSS/JS puro (sem build), usando **Bootstrap 5.3**, **Leaflet** e **Chart.js**. Os dados operacionais são carregados pela API HidroWize; a rede hidrográfica é exibida a partir de `mapa-hidrovias`.
a
---

## 1. Visão Geral

| Item | Descrição |
|------|-----------|
| **Visão Capitão** (`index.html`) | Planejar rota fluvial informando origem, destino, calado e velocidade. Exibe tempo, distância, nível de segurança (1–10), trechos e rota no mapa. |
| **Visão Administrador** (`admin.html`) | Dashboard gerencial: KPIs de navegabilidade, condições por estação, gestão de usuários e coleta ANA. |
| **Modo offline/PWA** | `manifest.json` + funcionamento offline planejado (Dexie/IndexedDB), com fallback local. |
| **Acessibilidade** | WCAG 2.1 AA e e-MAG (saltos, ARIA live, alto contraste, fonte A+). |

---

## 2. Stack de Tecnologias

| Camada | Tecnologia | Justificativa |
|--------|-----------|---------------|
| Estrutura | HTML5 semântico + vanilla JS (IIFE) | Protótipo leve, sem build tooling |
| Estilo | Bootstrap 5.3.3 + Bootstrap Icons 1.11 + Inter | UI responsiva mobile-first |
| Mapa | Leaflet 1.9.4 (tiles OSM + Esri) | Visualização GeoJSON das hidrovias |
| Gráficos | Chart.js 4.4.1 (apenas admin) | Série de nível da água |
| PWA | `manifest.json` | Instalável, offline-ready |
| Dados operacionais | `api.js` + API HidroWize | Estações, usuários e rotas autenticadas |
| Dados reais | `../../mapa-hidrovias/*.js` | Malha hidrográfica real (GeoJSON global) |

---

## 3. Estrutura de Arquivos

```
frontend/prototipos/hidrowaze/
├── index.html          # Visão do Capitão (planejamento de rota)
├── admin.html          # Visão do Administrador (dashboard + gestão)
├── app.js              # Lógica funcional da Visão Capitão (form, validação, roteamento)
├── map.js              # Integração Leaflet + GeoJSON (window.YgapeMapa)
├── styles.css          # Estilos customizados (Bootstrap + WCAG/e-MAG)
└── manifest.json       # Manifesto PWA

Dependências externas (fora desta pasta):
├── ./api.js                            # cliente HTTP da API HidroWize
└── ../../mapa-hidrovias/
    ├── hidrovias.js                   # window.HIDROVIAS (GeoJSON, domínio/Strahler)
    ├── hidrovias_profundidade.js      # window.HIDROVIAS_PROF (profundidade por trecho)
    └── estacoes.js                    # window.ESTACOES (estações ANA, GeoJSON)
```

Ordem de carregamento de scripts (em `index.html`):

1. `bootstrap.bundle.min.js`, `leaflet.js` (CDN)
2. `../../mapa-hidrovias/hidrovias.js`, `hidrovias_profundidade.js`, `estacoes.js`
3. `./api.js`
4. `./app.js`, `./map.js`

---

## 4. Visão Capitão (`index.html`)

### Funcionalidades

- **Formulário de rota** (`#formRota`): origem, destino (com inversão via `#btnSwap`), calado (0,5–6,0 m) e velocidade (6–35 km/h).
- **Cálculo da rota**: motor A* sobre a malha hidrográfica real (Dijkstra com penalidades), com fallback de distância tabulada.
- **Resultado**: tempo esperado, distância, trechos críticos, profundidade mínima, nível de segurança 1–10 e rota no mapa (GeoJSON).
- **Histórico de rotas salvas** + persistência em `localStorage` (`ygapé_ultima_rota`).
- **Estações do trecho** (lista) e **notificações** (offcanvas).

### Regras de negócio aplicadas

| Regra | Descrição | Local |
|-------|-----------|-------|
| RN010 | Transitável se `profundidade ≥ calado + 0,50 m` | `app.js` (`calcularRota`, `statusNav`) |
| RN011 | Custo por tempo = distância ÷ velocidade líquida | `app.js` (`calcularRota`) |
| RN022 | Penalidade por profundidade baixa no grafo | `app.js` (`dijkstraRio`) |

### Fórmulas principais (`app.js`)

- **Profundidade mínima exigida**: `calado + 0,50 m` (exibida em `#profMin`).
- **Velocidade líquida**: `velocidade + correnteza × 0,35` (correnteza média 5,5 km/h).
- **Folga**: `profundidade mínima − (calado + 0,50)`.
- **Segurança (1–10)**: 10 pontos base com deduções conforme a folga e o nº de trechos críticos (`segurancaMeta`).

---

## 5. Visão Administrador (`admin.html`)

### Funcionalidades

- **KPIs de navegabilidade**: nível atual, calado médio suportado, extensão monitorada, telemetria ANA (gauges + séries).
- **Explicação visual do calado**: SVG com barco, linha d'água, calado e folga de segurança.
- **Gráfico nível × histórico** (Chart.js): séries de Manaus e Itacoatiara.
- **Gestão de usuários**: busca, filtro por papel, toggle ativo/inativo, modal de novo usuário.
- **Tabela de condições por estação**: profundidade = nível − cota de fundo (IDW/SICFLOW), status NAVEGÁVEL/RESTRITO/CRÍTICO.

### Cota de fundo

O `admin.html` usa cotas de fundo fixas por estação (ex.: Manaus `14990000` → 20,1 m) para estimar profundidade. Na versão definitiva, esse valor virá do backend via **IDW/SICFLOW** (ver `backend/`).

---

## 6. Mapa (`map.js`)

### Camadas (Leaflet)

| Camada | Fonte | Estilo |
|--------|-------|--------|
| Base | OSM / Esri Satellite (alternável) | tiles |
| Hidrovias (domínio) | `window.HIDROVIAS` | cor por `dominio`, peso por `nustrahler` |
| Profundidade (trecho) | `window.HIDROVIAS_PROF` | cor por faixa de `hig_drn_depth_m` |
| Estações ANA | `window.ESTACOES` | `circleMarker` colorido por `status` |
| Rota calculada | GeoJSON gerado em `app.js` | polilinha laranja tracejada |

### API exposta (`window.YgapeMapa`)

- `ensureInit()` — inicialização preguiçosa (aguarda dados via `aguardarDados`).
- `mostrarRota(geojson, origem, destino)` — desenha e centraliza a rota.
- `limparRota()` — remove a camada de rota.
- `getMap()` — retorna a instância do mapa.

### Escalas de cores de profundidade (`corProfundidade`)

| Faixa | Cor | Rótulo |
|-------|-----|--------|
| 0–2 m | amarelo | raso |
| 2–5 m | laranja | — |
| 5–10 m | azul | — |
| > 10 m | azul escuro | profundo |

---

## 7. Dados operacionais e geográficos

### API HidroWize (`api.js`)

- Estações, usuários e rotas são carregados pelos endpoints autenticados.
- Sem sessão ou em falha de rede, a interface mostra estado vazio; não apresenta estimativas fictícias como dados operacionais.

### `window.HIDROVIAS` / `HIDROVIAS_PROF` / `ESTACOES` (`../../mapa-hidrovias/`)

GeoJSON reais com propriedades usadas no mapa e no roteamento:

| Propriedade | Uso |
|-------------|-----|
| `nustrahler` | ordem de Strahler (peso da aresta e espessura da linha) |
| `hig_drn_depth_m` | profundidade média (AHGN/SICFLOW) |
| `hig_drn_width_m`, `hig_drn_annual_flow` | popup informativo |
| `dominio` | Federal / Estadual / Internacional |
| `status` (estações) | OK / WARN / FAR (cor do marcador) |

---

## 8. Acessibilidade (WCAG 2.1 AA / e-MAG)

- **Saltos** (`accesskey` 1–4): conteúdo, menu, rota, rodapé (`.hw-skip`).
- **Regiões ARIA live**: `#announcer` (`polite`) e `#announcer-assertive` (`assertive`) para anúncios dinâmicos.
- **Alto contraste** (`#btnA11yContraste`): classe `html.hw-contrast`, persistida em `localStorage` (`hw-contrast`).
- **Fonte A+** (`#btnA11yFonte`): cicla 16/18/20px, persistida (`hw-fontlvl`).
- **Validação acessível**: `aria-invalid`, `is-invalid`, mensagens em `role="alert"`, foco movido para o primeiro campo inválido.
- **`prefers-reduced-motion`**: desativa animações e scroll suave.
- **Foco visível**: outline de 3px amarelo (`--hw-focus`) em todos os elementos interativos.

---

## 9. Integração com Backend (planejada)

O protótipo documenta os contratos futuros (ainda não conectados):

```text
POST /api/v1/rotas/calcular
{ origem, destino, calado, velocidade }
→ { tempo_h, distancia_km, seguranca_1_10, geojson, trechos }

POST /api/v1/usuarios        # criação de usuário (admin)
WebSocket /ws                # notificações em tempo real (fallback: polling)
```

- **Offline**: `services/roteador.ts` (A* local) + Dexie (IndexedDB) — vide `docs/specs/componentes-frontend.md`.
- **Cálculo local atual**: `app.js` já implementa um Dijkstra sobre `window.HIDROVIAS_PROF` com penalidade por profundidade/Strahler — base para o roteador offline definitivo.

---

## 10. Integração com a API

O cliente `api.js` segue o contrato de `docs/specs/api-spec.md`. Os endpoints
autenticados são chamados apenas quando houver um JWT em `localStorage`, na
chave `hidrowize-access-token`. A URL padrão é `http://localhost:8000/api/v1` e
pode ser alterada pela meta tag `hidrowize-api-url` ou por
`HidroWizeApi.configurar(url, token)` no console durante a homologação.

Quando não há sessão, a API está indisponível ou ocorre uma falha de rede, o
protótipo preserva o cálculo local e identifica o resultado como estimativa.

## 11. Como Executar

Sem build — basta servir os arquivos estáticos a partir da raiz do projeto (os caminhos relativos `../../mapa-hidrovias/*.js` exigem essa hierarquia).

```bash
# a partir da raiz do repositório
python -m http.server 8080
# ou
npx serve .
```

Acesse:
- `http://localhost:8080/frontend/prototipos/hidrowaze/index.html` (Capitão)
- `http://localhost:8080/frontend/prototipos/hidrowaze/admin.html` (Admin)

---

## 11. Limitações e Riscos

1. **Caminhos relativos frágeis** (`../../mapa-hidrovias/`) — quebram se a pasta for movida; documentar no deploy.
2. **Carregamento inicial do roteador** — o primeiro cálculo monta o grafo BHAE em memória e pode demorar mais que os seguintes.
3. **Cota de fundo no admin** — depende de endpoint que exponha a profundidade calculada por trecho.
4. **Autenticação visual** — a tela de login ainda precisa ser implementada para armazenar o JWT sem uso do console.
