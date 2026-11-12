# Mapeamento de Fontes de Dados — Coleta Automatizada Hidrológica (Amazonas)

Data do mapeamento: 16/08/2026
Atualização: 28/08/2026 — fontes de rede hidrográfica (BHAE/BHO) e batimetria adicionadas (seções 9 e 10).
Atualização: 29/08/2026 — dados de satélite (altimetria hydroweb.next/SWOT) adicionados (seção 11).
Método: requisições HTTP diretas (GET/POST/SOAP), inspeção de HTML e discovery de APIs.

---

## 1. ANA — HidroWeb / Telemetria (FONTE PRINCIPAL ✔ FUNCIONAL)

A API REST oficial do HidroWeb (`api.snirh.gov.br`) retorna **401** sem autenticação.
Porém foi descoberto o **Web Service SOAP público de telemetria** que retorna dados de cotas **sem login**:

### Endpoints

| Endpoint | Método | Descrição |
|---|---|---|
| `https://telemetriaws1.ana.gov.br/ServiceANA.asmx` | POST (SOAP 1.1) | WSDL raiz. Namespace: `http://MRCS/` |
| `https://telemetriaws1.ana.gov.br/ServiceANA.asmx/ListaEstacoesTelemetricas` | POST form | Lista estações telemétricas (4.947 no total). Params: `statusEstacoes` (0=Ativo,1=Manutenção), `origem` |
| `https://telemetriaws1.ana.gov.br/ServiceANA.asmx/HidroInventario` | POST form/SOAP | Inventário completo (nome, rio, município, lat/lon, tipos de estação). Params: `nmEstado`, `telemetrica` (0/1), `nmMunicipio`, `nmRio`, etc. |
| `https://telemetriaws1.ana.gov.br/ServiceANA.asmx/DadosHidrometeorologicos` | POST form | Nível/Vazão/Chuva (campos simples). Params: `codEstacao`, `dataInicio`, `dataFim` (formato `dd/MM/yyyy`) |
| `https://telemetriaws1.ana.gov.br/ServiceANA.asmx/DadosHidrometeorologicosGerais` | POST form | Nível detalhado: `NivelSensor`, `NivelManual`, `NivelDisplay`, `NivelFinal`, `VazaoFinal`, `ChuvaFinal` |

### Exemplo de chamada (POST form)

```bash
curl -X POST "https://telemetriaws1.ana.gov.br/ServiceANA.asmx/DadosHidrometeorologicosGerais" \
  -d "codEstacao=14990000&dataInicio=16/08/2026&dataFim=16/08/2026"
```

Retorna XML com registros a cada 15 minutos.

### Métodos adicionais disponíveis (12 no total)

`DadosHidrometeorologicos`, `DadosHidrometeorologicosGerais`, `HidroBaciaSubBacia`, `HidroEntidades`,
`HidroEstado`, `HidroInventario`, `HidroMunicipio`, `HidroRio`, `HidroSerieHistorica`,
`ListaEstacoesTelemetricas`, `IncluirDados_CotaOnline`, `Excluir_CotaOnline`.

### Teste validado — Estação Manaus (14990000), 16/08/2026

- 15:45 → Nivel 2603.00 cm (NivelSensor 2603.00)
- 09:00 → Nivel 2606.00 cm
- 00:00 → Nivel 2611.00 cm

### Entregável

✅ `estacoes_am.csv` — **75 estações únicas** do Amazonas (Solimões, Negro, Javari, Jutaí, Juruá,
Madeira, Purus, etc.) com colunas: `codigo_estacao;nome_estacao;nome_rio;municipio;latitude;longitude`.

### Recomendação

- Priorizar a extração das estações fluviométricas de escala/telemetria (códigos de 8 dígitos).
- Para séries históricas completas: usar `HidroSerieHistorica` (testar parâmetros).
- Contatos: `atendimento@ana.gov.br` (credenciais da API REST já solicitadas conforme passos.md).

---

## 2. SGB — Serviço Geológico do Brasil (PARCIAL)

### A. Geoserviços GeoServer (✔ Funcional, mas SEM cotas em tempo real)

- Base: `https://geoservicos.sgb.gov.br/`
- WMS Capabilities: `https://geoservicos.sgb.gov.br/geoserver/ows?service=WMS&request=GetCapabilities`
- **45 camadas** — focadas em geologia, hidrogeologia e **gestão de riscos**:
  - `gestao-territorial:risco_geologico`
  - `gestao-territorial:suscet_inundacao`, `suscet_enxurrada`, `suscet_corrida_de_massa`
  - `hidrogeologia:siagas`, `hidrogeologia:pocos_siagas_prod`
  - `geosgb:*` (litoestratigrafia, bacias sedimentares, etc.)
- ⚠️ **Não possui camadas de cotas/níveis de rios em tempo real.**
- Swagger: `https://geoservicos.sgb.gov.br/swagger/` → 404 (não existe).

### B. Boletins Hidrológicos (⚠️ Não localizados via scraping simples)

- Site: `https://www.sgb.gov.br/` (Liferay)
- Páginas existentes: `/hidrologia`, `/monitoramento-hidrologico-e-hidrogeologico`,
  `/rede-hidrometeorologica-nacional-rhn`, `/dados-abertos`, `/relat%C3%B3rios1`
- As seções "DADOS DAS ESTAÇÕES CONVENCIONAIS/TELEMÉTRICAS" e boletins são **carregadas via JavaScript**.
- ⚠️ **Ação pendente:** usar Selenium/Playwright para renderizar `/rede-hidrometeorologica-nacional-rhn`
  e capturar os links reais dos boletins de alerta hidrológico da Bacia Amazônica.
- API interna do Liferay: `https://www.sgb.gov.br/api/jsonws` existe (não autenticado retorna lista de serviços).

### Recomendação

- A alternativa mais simples: **substituir boletins do SGB pela API de telemetria da ANA** (fonte estruturada, JSON/XML).
- Manter o SGB apenas como fonte de **validação qualitativa** (alertas de risco/emergência) e camadas de suscetibilidade a inundação.

---

## 3. Legisla.AM — Diário Oficial do Amazonas (✔ FUNCIONAL — MELHOR FONTE DE DECRETOS)

### Endpoints

| Endpoint | Método | Descrição |
|---|---|---|
| `https://legisla.imprensaoficial.am.gov.br/` | GET | Home |
| `https://legisla.imprensaoficial.am.gov.br/diario_am/pesquisar?q=emergencia` | GET | **Busca textual** (server-rendered, sem JS) |
| `https://legisla.imprensaoficial.am.gov.br/diario_am/pesquisar?q=...&page=2` | GET | Paginação (`page=N`) |
| `https://legisla.imprensaoficial.am.gov.br/diario_am/{categoria}/{ano}/{mes}/{id}` | GET | Página de detalhe do ato (ex: `/diario_am/41534/2026/7/19775`) |
| `https://legisla.imprensaoficial.am.gov.br/diario_am/consultar` | GET/POST | Consulta por código do ato |
| `https://legisla.imprensaoficial.am.gov.br/diario_am/41536` | GET | Categoria "DECRETOS NUMERADOS" |

### Categorias (menu lateral)

- CONSTITUIÇÃO DO ESTADO DO AMAZONAS
- EMENDAS CONSTITUCIONAIS
- LEIS COMPLEMENTARES / DELEGADAS / ORDINÁRIAS / PROMULGADAS
- DECRETOS LEGISLATIVOS
- **DECRETOS NUMERADOS** (`/diario_am/41536`)
- REGIMENTO INTERNO

### Estrutura HTML (selectors mapeados)

**Página de busca** (lista de resultados):
- Link do ato: `<a href="/diario_am/{cat}/{ano}/{mes}/{id}">DECRETO Nº ...</a>`
- Texto: `DECRETO Nº {num}, DE {dia} DE {mês} DE {ano}`

**Página de detalhe** (`/diario_am/{cat}/{ano}/{mes}/{id}`):
- Título/ementa: dentro de `div.materia`
  - `<p><b>DECRETO Nº 54.712, DE 17 DE JULHO DE 2026</b></p>`
  - Ementa: `<p><b>HOMOLOGA</b> Situação de Emergência no Município de Careiro da Várzea, na forma que especifica.</p>`
- Corpo completo do decreto: `div.materia > p` (texto justificado)
- Mês/dia no rodapé: `.mes-menu-ano`, `.m-timeline-2__item-time`
- Ano: `.anos-versoes` (abas `#tab_2026`)

### Teste validado — Decreto Nº 54.712, DE 17 DE JULHO DE 2026

"DECRETO Nº 54.712, DE 17 DE JULHO DE 2026 — **HOMOLOGA** Situação de Emergência no Município de
Careiro da Várzea, na forma que especifica. ... devido à **elevação das águas do Rio Solimões** e seus
afluentes, ocasionando inundação... COBRADE 1.2.1.0.0"

### Estratégia de scraping

```python
import requests
from bs4 import BeautifulSoup

URL_BUSCA = "https://legisla.imprensaoficial.am.gov.br/diario_am/pesquisar"
res = requests.get(URL_BUSCA, params={"q": "emergência", "page": 1}, timeout=15)
soup = BeautifulSoup(res.text, "html.parser")

# Links dos decretos na busca
for a in soup.select('a[href*="/diario_am/"]'):
    if "DECRETO" in a.get_text(" ", strip=True).upper():
        print(a.get("href"), a.get_text(" ", strip=True))

# Detalhe
res2 = requests.get("https://legisla.imprensaoficial.am.gov.br" + href, timeout=15)
soup2 = BeautifulSoup(res2.text, "html.parser")
materia = soup2.select_one("div.materia")
```

### Recomendação

- Buscar por palavras-chave: `emergência`, `emergencia`, `situação de emergência`, `calamidade`,
  `enchente`, `estiagem`, `cheia`, `decretar`.
- Extrair do texto: `Número`, `Data`, `Ementa`, e classificar tipo (`Cheia`/`Estiagem`) por regex
  sobre `Rio X` e `COBRADE`.
- Verificar `robots.txt` antes de implementar em escala.

---

## 4. Portal da Transparência do Amazonas (PARCIAL — WordPress REST)

- Base: `https://www.transparencia.am.gov.br/`
- Plataforma: **WordPress** com REST API ativa.
- API base: `https://www.transparencia.am.gov.br/wp-json/`
- Rotas de **atores/órgãos protegidas (401)**:
  - `/wp-json/wp/v2/orgao` → 401
  - `/wp-json/wp/v2/posts` → 401 (protegida por auth)
  - `/wp-json/wp/v2/types` → 401
- Rotas **públicas confirmadas**:
  - `/wp-json/wp/v2/search?search=decreto&per_page=5` → ✅ retorna JSON (id, title, url, type)
  - `/wp-json/` → ✅ índice de rotas (lista completa de endpoints)
- Swagger interno: `/wp-json/wp/v2/swagger_ui` (presente no índice de rotas).

### Recomendação

- Explorar `/wp-json/wp/v2/search?search=<termo>&per_page=100` para localizar páginas de legislação.
- A rota `swagger_ui` pode expor a documentação de custom endpoints.
- Verificar se existe plugin de "Atos Oficiais" com rotas próprias (pesquisar no índice de rotas).

---

## 5. Defesa Civil do Amazonas (PARCIAL — HTML + busca, API REST BLOQUEADA)

- Base: `https://www.defesacivil.am.gov.br/`
- Plataforma: WordPress **com plugin Solid Security** que bloqueia a REST API:
  - `/wp-json/wp/v2/posts` → **401** (`itsec_rest_api_access_restricted`)
  - `/wp-json/wp/v2/pages` → **401**
  - `/wp-json/wp/v2/search` → **403**
  - `/wp-json/` → ✅ 200 (índice exposto)
- ✅ **Busca HTML funciona**: `https://www.defesacivil.am.gov.br/?s=emergencia` (resultados renderizados).
- ✅ **Conteúdo dos posts**: `div.article-content` / `div.article-body` (server-rendered).
- ⚠️ Feed RSS (`?feed=rss2`) retorna HTML da homepage (feed quebrado no tema).
- Página `/monitoramento/` existe mas **sem mapa interativo/API de cotas**.
- Apps: **Cota Rio** (`com.defesa_civil.cotarioapp`) e **Aplicativo Cidadão** — exibem "a cota do nível do rio em seu município", mas **sem API pública documentada**; os dados provêm do backend do app.

### Estratégia recomendada

1. **Ignorar a REST API** (bloqueada).
2. Usar a **busca HTML** `?s={termo}` para listar notícias/comunicados oficiais.
3. Extrair pares (Município, Rio, Cota) via regex sobre o texto dos posts.
4. Cota exata real → usar a **API de telemetria da ANA** (fonte 1), não a Defesa Civil.

---

## 6. Navegabilidade (Inferência)

- **Fonte de cotas:** API de telemetria da ANA (atual, a cada 15 min).
- **Mínima histórica:** série histórica por estação via `HidroSerieHistorica` (A NA) ou tabelas de referência
  da própria estação (níveis de cota mínima/máxima disponíveis no inventário/estações).
- **Regra proposta (a validar):**
  - `status = NAVEGÁVEL` se `cota_atual - cota_minima_historica >= 50 cm`
  - `status = RESTRITO` se `0 <= diferenca < 50 cm`
  - `status = CRÍTICO` se `cota_atual < cota_minima_historica`
- Validação qualitativa: notícias da Defesa Civil e decretos do Legisla.AM (interdições, calado crítico).

> **Atualização (30/08/2026) — Calado de referência (RF018) determinado:**
> fonte **DNIT/ANTAQ**. Calado de projeto por tramo da hidrovia Solimões–Amazonas:
>
> | Tramo | Extensão | Calado de projeto |
> |---|---|---|
> | Solimões (Tabatinga → Manaus) | ~1.600 km | **6 m** (mínimo; pontos críticos na seca) |
> | Amazonas (Manaus → Belém) | ~1.650 km | **10 m** (navios até 60.000 TPB) |
> | Madeira (Porto Velho → Itacoatiara) | ~1.450 km | **>13 m na cheia**; restrito na seca (praias) |
> | Negro (Porto de Manaus) | — | navios de qualquer calado mesmo nas vazantes |
>
> Na **cheia** (mai–jun) o calado disponível fica ≥10 m (Amazonas) e >13 m (Madeira); na **seca**
> (out–nov) cai ao mínimo de projeto (6 m no Solimões, com pontos críticos abaixo). Formalizado
> como **RN029** em `docs/specs/regras-negocio.md`.

---

## 7. Matriz de Validação Final

| Fonte | URL / Endpoint Testado | Retorno | Observações |
|---|---|---|---|
| ANA — Telemetria (ListaEstações) | `https://telemetriaws1.ana.gov.br/ServiceANA.asmx/ListaEstacoesTelemetricas` | ✅ 200 (4.947 estações) | SOAP público, sem login |
| ANA — Inventário | `.../ServiceANA.asmx/HidroInventario` (nmEstado, telemetrica) | ✅ 200 (462 rows; 139 AM) | Filtro por SOAP retorna todos; usar nmEstado completo "AMAZONAS" no form |
| ANA — Dados Hidrometeorológicos | `.../ServiceANA.asmx/DadosHidrometeorologicosGerais` | ✅ 200 (64 leituras/dia) | Nível a cada 15 min; `codEstacao=14990000` Manaus = 2603 cm |
| ANA — API REST HidroWeb | `https://www.snirh.gov.br/hidroweb/rest/api/...` | ⛔ 401 | Requer credenciais (já solicitadas) |
| SGB — Geoserviços | `https://geoservicos.sgb.gov.br/geoserver/ows?service=WMS&request=GetCapabilities` | ✅ 200 (45 camadas) | Sem cotas em tempo real; só risco/suscetibilidade |
| SGB — Boletim PDF | `/rede-hidrometeorologica-nacional-rhn` | ⚠️ Conteúdo via JS | Requer Selenium/Playwright; substituível pela ANA |
| Legisla.AM — Busca | `/diario_am/pesquisar?q=emergencia` | ✅ 200 (paginado) | Server-rendered, sem JS |
| Legisla.AM — Detalhe | `/diario_am/41534/2026/7/19775` | ✅ 200 | `div.materia` com decreto completo |
| Transparência AM — API | `/wp-json/wp/v2/search?search=decreto` | ✅ 200 (JSON) | Posts/órgãos → 401 |
| Defesa Civil — Busca | `/?s=emergencia` | ✅ 200 | API REST bloqueada (401/403) |
| Defesa Civil — Feed RSS | `/?feed=rss2` | ⚠️ HTML | Feed quebrado no tema |
| Defesa Civil — Monitoramento | `/monitoramento/` | ✅ 200 | Sem mapa/API de cotas |
| ANA — Catálogo de Metadados (busca) | `https://metadados.snirh.gov.br/geonetwork/srv/api/search/records/_search` | ✅ 200 (JSON) | GeoNetwork com 25 datasets hidrográficos (23 vetoriais) |
| ANA — BHAE/AHGN (trecho drenagem) | `https://metadados.snirh.gov.br/files/79f92322-f806-4e52-ab6c-4ef348fae938/geoft_bhae_trecho_drenagem_hgm.gpkg` | ✅ 200 (1,8 GB) | GeoPackage íntegro; download lento (~60 KB/s, conexão reseta) |
| ANA — BHO 2017 5k (trecho drenagem) | `https://metadados.snirh.gov.br/files/f7b1fc91-f5bc-4d0d-9f4f-f4e5061e5d8f/geoft_bho_2017_5k_trecho_drenagem.gpkg` | ✅ 200 (826 MB) | Desatualizada; substituída pela BHAE |
| ANA — HidroSeriePerfilTransversal | `.../HidroSeriePerfilTransversal/v1` (e `/v2`) | ⛔ timeout/503 | Inoperante (mesma família de Cotas/Vazao/Chuva) |

---

## 8. Próximos Passos Recomendados

1. **Construir o coletor da ANA** (prioridade máxima): lista de estações AM → cotas a cada intervalo (15 min ou horária) → CSV/DB.
2. **Construir o scraper do Legisla.AM**: busca `emergência` + página de detalhe → extrair número, data, ementa, município, rio, tipo (cheia/estiagem).
3. **Complementar** com busca da Defesa Civil (`?s=`) para validação qualitativa (regex de município/rio/cota).
4. **Testar `HidroSerieHistorica`** da ANA para calcular cotas mínimas históricas → regra de navegabilidade.
5. **Opcional**: renderizar SGB com Playwright para boletins; testar `swagger_ui` do Transparência AM.
6. Verificar `robots.txt` de cada site antes do scraping em escala.
7. **Recortar a área ativa (bacia amazônica, prioridade Brasil)** do `geoft_bhae_trecho_drenagem_hgm.gpkg` (QGIS/PostGIS) e validar a conectividade do grafo (RF006). *(Recorte geral de hidrovias já feito — ver seção 9.C; falta o recorte da área específica e a validação do grafo.)*
8. **Definir a derivação da `cota_fundo`**: `hig_drn_depth_m` + elevação (AHGN) vs. perfil transversal do HidroWeb (ver seção 10).

---

## 9. ANA — Catálogo de Metadados / Base Hidrográfica (REDE HIDROGRÁFICA) ✔ RESOLVIDO

Fonte oficial do shapefile/GeoPackage da rede de drenagem (RF005/RF006), publicada como dado
aberto no Catálogo de Metadados da ANA (GeoNetwork), formato GeoPackage.

- Portal: `https://metadados.snirh.gov.br/geonetwork`
- API de busca (JSON): `https://metadados.snirh.gov.br/geonetwork/srv/api/search/records/_search`
- Metadados ISO19139 (XML): `https://metadados.snirh.gov.br/geonetwork/srv/api/records/{uuid}/formatters/xml`

### A. BHAE / AHGN — Atlas Hidrogeomorfológico Nacional (2024) — RECOMENDADA ✔

- Escala (Amazônia): 1:250.000
- Arquivo (trecho de drenagem): `https://metadados.snirh.gov.br/files/79f92322-f806-4e52-ab6c-4ef348fae938/geoft_bhae_trecho_drenagem_hgm.gpkg`
- Tamanho: 1,8 GB (Brasil inteiro)
- **Entregável baixado e validado:** `data/geoft_bhae_trecho_drenagem_hgm.gpkg` (1,72 GB, íntegro,
  EPSG:4674/SIRGAS 2000, 481.135 trechos `MULTILINESTRING`).
- Grafo pronto: colunas `noorigem`, `nodestino`, `cotrecho`, `cocursodag`, `cobacia` → NetworkX direto (RF006).
- Atributos geomorfológicos (cobrem parte do gap de batimetria/correnteza):

  | Coluna | Uso no projeto |
  |---|---|
  | `hig_drn_depth_m`, `hig_drn_width_m` | profundidade/largura do canal (proxy de cota de fundo) |
  | `hig_drn_annual_flow`, `hig_drn_event_flow` | vazão estimada → correnteza `V=Q/A` (RF032) |
  | `hig_drn_manning_n`, `hig_drn_velmann` | rugosidade e velocidade de Manning |
  | `hig_drn_slope_*`, `hig_drn_sinuosity` | gradiente/sinuosidade do trecho |
  | `hig_drn_elevation_avg/min/max` | altimetria do leito/trecho |
  | `nustrahler`, `hig_drn_strahler` | ordem de Strahler (rio principal) |

### B. BHO 2017 5k — Base Hidrográfica Ottocodificada (DESATUALIZADA)

- Escala (Amazônia): 1:1.000.000
- Arquivo: `https://metadados.snirh.gov.br/files/f7b1fc91-f5bc-4d0d-9f4f-f4e5061e5d8f/geoft_bho_2017_5k_trecho_drenagem.gpkg`
- Tamanho: 826 MB
- ⚠️ Marcada como desatualizada no catálogo — substituída pela BHAE.

### Observações de download

- O servidor da ANA entrega a ~60 KB/s e derruba a conexão a cada ~5 MB; o arquivo nacional é
  inviável numa conexão comum (1,8 GB ≈ 8 h). Comando usado (retomável):

  ```powershell
  curl.exe -L -C - -o "data\geoft_bhae_trecho_drenagem_hgm.gpkg" "https://metadados.snirh.gov.br/files/79f92322-f806-4e52-ab6c-4ef348fae938/geoft_bhae_trecho_drenagem_hgm.gpkg"
  ```

- Alternativas: recorte via WFS/GeoServer da ANA (bbox Manaus–Itacoatiara) ou fallback OSM
  (`way["waterway"="river"]` via Overpass/Geofabrik).

### C. Derivados — recortes de hidrovias e cruzamento com estações ANA

Gerados a partir do GeoPackage nacional (sem GDAL — parser GPB/WKB próprio em Python):

| Arquivo | Critério | Trechos | Tamanho |
|---|---|---|---|
| `data/hidrovias_federais_bhae.gpkg` | `dedominial='Federal'` | 22.926 | 85,8 MB |
| `data/hidrovias_navegaveis_bhae.gpkg` | `dedominial IN ('Federal','Internacional') OR (dedominial='Estadual' AND nustrahler>=4)` | 121.661 | 351,6 MB |

**Critério "navegável" (ampliado):** o campo `dedominial` do BHAE reflete o domínio legal do curso
d'água (Federal/Estadual/Internacional/Linha de Costa). Só `Federal` deixa de fora rios estaduais
navegáveis (Jutaí, Tefé, Coari, Manacapuru, Uatumã, Pitinga…) e braços/paranás classificados como
"Estadual". O recorte ampliado soma:

- **Federal** (22.926) — hidrovias interestaduais;
- **Internacional** (56.779) — rios de fronteira (inclui muitos córregos de baixa ordem; opcional filtrar por `nustrahler>=3`);
- **Estadual navegável** (`nustrahler>=4`, 41.956).

**Cruzamento com as estações ANA:**

- `planilhas/estacoes_am_x_hidrovias_federais.csv` — 75 estações × trecho federal mais próximo.
- `planilhas/estacoes_am_x_hidrovias_navegaveis.csv` — 75 estações × trecho navegável mais próximo,
  com coluna `dominio` e atributos AHGN (`hig_drn_depth_m`, `hig_drn_width_m`, `hig_drn_annual_flow`,
  Strahler, elevação, Manning, velocidade, sinuosidade) + `distancia_m` + `status` (OK/WARN/FAR).

Resultado (critério ampliado): **59 OK (<1 km) · 10 WARN (1–5 km) · 6 FAR (>5 km)**. Os FAR restantes
são tributários pequenos (Strahler 2–3) e reservatórios de UHE. Ressalva: coordenadas de algumas
estações plotadas no centro da cidade e a escala 1:250.000 geram desvios de 1–3 km em rios largos
(ex.: Manaus, Barcelos, Parintins) — a coluna `rio_confere` sinaliza esses casos (PARCIAL/NA).

---

## 10. Batimetria / Cota de Fundo ⚠ GAP — sem dado aberto consolidado

Não existe batimetria aberta do leito na bacia amazônica. Fontes mapeadas:

| Fonte | Entrega | Status |
|---|---|---|
| ANA HidroWeb — Perfil Transversal / Curva de Descarga | geometria do leito (cota de fundo) na seção de cada estação | REST `HidroSeriePerfilTransversal/v1` e `/v2` **inoperantes** (timeout/503); só via portal HidroWeb clássico (download manual por estação, exige login/chave) |
| Marinha (CHM) — Cartas Náuticas do Amazonas | profundidade do canal navegável (não o leito todo) | raster gratuito limitado; ENC licenciado |
| SGB/CPRM — levantamentos batimétricos | sondagens pontuais de projetos (dragagem) | não consolidado em bulk |
| **AHGN/BHAE** (proxy recomendado) | `hig_drn_depth_m` + elevação por trecho | ✅ já disponível no GeoPackage baixado |

**Implicação:** a `cota_fundo_batimetria_m` do modelo e o IDW (RF031) dependem de dado fragmentado.
Para o MVP, validar com o orientador: usar `hig_drn_depth_m` + elevação (AHGN) como proxy de cota
de fundo, ou simplificar para `nível − cota de referência` por estação — em vez de batimetria completa.

> **Atualização (29/08/2026):** a batimetria do leito ganhou uma fonte aberta por satélite — o
> produto **SWOT L4 River Bathymetry (SICFLOW)**, distribuído no hydroweb.next. Ver seção 11.

---

## 11. Dados de Satélite — Altimetria Espacial (hydroweb.next / CNES) ✔ FUNCIONAL

Fonte complementar aos dados in situ (ANA) e ao proxy AHGN: níveis d'água, batimetria e vazão
derivados de altimetria por satélite (SWOT, Sentinel-3, Jason), distribuídos pela plataforma
**hydroweb.next** (CNES/LEGOS/Theia/Data Terra).

### Acesso

| Camada | URL / Mecanismo | Auth |
|---|---|---|
| Catálogo STAC (metadados/busca) | `https://hydroweb.next.theia-land.fr/api/catalog/stac` | público (sem login) |
| Download de produtos | cliente `py_hydroweb` (`pip install py-hydroweb`) | API key gratuita (`HYDROWEB_API_KEY`) |

- O STAC expõe 53 coleções; a busca é pública (`/search` com `collections` + `bbox`).
- Download exige conta gratuita + API key no hydroweb.next (lida do `.env` como `HYDROWEB_API_KEY`).
- Observação: nesta máquina `requests` funciona (o `urllib`/`ssl` falha por cert self-signed na cadeia).

### Produtos validados (cobertura na bacia amazônica completa, bbox `-80,-21,-48,6`)

| Coleção | Entrega | Cobertura na bacia | Período |
|---|---|---|---|
| `HYDROWEB_RIVERS_OPE` | estações virtuais de nível d'água (altimetria) | **4.734 estações** | 2008-07 → atual |
| `HYDROWEB_RIVERS_RESEARCH` | estações virtuais (pesquisa) | 3.660 | 1992 → 2021 |
| `SWOT_L4_BATHY_SICFLOW` | batimetria "seca" do leito (1D, node+reach) | 1 NetCDF (América do Sul) | 2023-03 → 2026-02 |
| `SWOT_L4_SOS_DISCHARGE` | vazão (descarga) derivada do SWOT | 1 NetCDF (continental) | 2023-03 → 2025-05 |
| `SWOT_L2_HR_RIVERSP_REACH` | elevação/largura/declividade por passagem | 472 passagens na área de teste Manaus–Itacoatiara | 21 dias/ciclo |

### Exemplo validado — Manaus

- `R_AMAZONAS_AMAZONAS_KM1298` (lon -59.90, lat -3.23) — série 2018-12 → 2026-08, arquivo `.txt`.
- `R_AMAZONAS_NEGRO_KM1295` (lon -59.95, lat -3.16).
- Cabeceiras andinas/meridionais confirmadas: `R_AMAZONAS_CAQUETA` (Colômbia), `R_AMAZONAS_BENI`
  (Bolívia), `R_AMAZONAS_IACO` (Acre/Peru), `R_SAN-JUAN-2` (Andes colombianos).

### Uso no projeto (mapeamento por lacuna)

| Lacuna | Produto satelital | RF |
|---|---|---|
| Batimetria / cota de fundo | `SWOT_L4_BATHY_SICFLOW` | RF014, RF018, RF031 |
| Cota em trechos sem régua ANA | `HYDROWEB_RIVERS_OPE` | RF002/RF031 (IDW), RF019 |
| Vazão independente (`V=Q/A`) | `SWOT_L4_SOS_DISCHARGE` | RF032 |
| Largura/declividade (validação BHAE) | `SWOT_L2_HR_RIVERSP_REACH` | RF006 |

### Entregável

- ✅ `backend/coletar_hydroweb.py` — coletor com `--listar`, `--estacoes`, `--batimetria`, `--vazao`, `--tudo`.
- ✅ `data/satelite/estacoes_virtuais.csv` — 4.734 estações da bacia (`codigo;rio;estacao;km;latitude;longitude;inicio;fim`).
- ✅ `data/satelite/series_nivel_satelite.csv` — 590.698 observações de nível (2008-07 → 2026-08).
- ✅ `data/satelite/batimetria/SWOT_L4_BATHY_SICFLOW/sa_river_bathymetry_L4_SWOT.nc` — batimetria SICFLOW (490 MB, América do Sul).
- ✅ `data/satelite/vazao/SWOT_L4_SOS_DISCHARGE/sa_sword_v16_SOS_results_*.nc` — vazão SWOT SOS (8,7 GB).
- ✅ Persistência no `hidrowize.db`: `batimetria_sicflow` (1.315.079 nós, seção transversal de 12 pontos + `cota_fundo`/`largura_m`/`h_interface`) e `series_vazao_satelite` (475.111 observações de `consensus_q` por reach).

### Notas de implementação (batimetria/vazão no banco)

- **Batimetria SICFLOW**: os dados reais estão nos **nós** (`SICFLOW/nodes/*`), não nos reaches
  (vazios no arquivo SA). Cada nó tem seção transversal de 12 pontos (`elevation`, `width`, `method`)
  + `h_interface` (separa o trecho observado do estimado por inversão SIC4DVar). A `cota_fundo`
  (thalweg) é o mínimo da seção; `reach_id` é derivado de `node_id` (formato SWORD `CBBBBBRRRRNNNT`
  → `CBBBBBRRRRT`), permitindo o join com a vazão.
- **Vazão SWOT SOS**: produto `constrained` v16, série temporal por reach (`consensus/consensus_q`
  + `consensus/time_int`, segundos desde 2000-01-01). `river_name` vem como `NODATA`; a ligação
  com os rios é via `reach_id` (SWORD) ou junção espacial por lon/lat.
- **Versão SWORD divergente**: batimetria usa SWORD v17b e a vazão usa v16 — `reach_id` coincide em
  parte dos trechos, mas a junção robusta é espacial (lon/lat).

### Limitações

- **Sem tempo real:** SWOT revisita a cada 21 dias; a altimetria é periódica — serve de complemento
  espacial/histórico, não de alerta imediato (a telemetria ANA de 15 min continua sendo a fonte operacional).
- **Rios < ~100 m de largura** ficam fora do alcance do SWOT (tributários pequenos seguem dependendo da ANA).
- **SICFLOW é produto v1** (2026) — validar com o orientador antes de usar como cota de fundo definitiva
  (mesma ressalva do proxy AHGN).

---

## 12. Uso dos Dados de Satélite e Oportunidades de Machine Learning

Como os dados coletados (seção 11) entram no modelo do HidroWize, e o que dá para fazer com
Machine Learning sobre eles.

### 12.1 Uso direto no modelo (sem ML)

A regra central de navegabilidade:

```
profundidade_disponivel = nível_d'água − cota_fundo
status = navegável se profundidade_disponivel >= calado_referência (RF018)
```

| Dataset (tabela) | Lacuna que resolve | Uso concreto |
|---|---|---|
| `series_nivel_satelite` (4.734 estações, 2008–2026) | cota em trechos sem régua ANA (só 75) | estender o monitoramento de nível; cota mínima histórica (RF019); tendência cheia/estiagem |
| `batimetria_sicflow` (`cota_fundo`, `largura_m`, seção 12 pts) | cota de fundo (gap da seção 10) | `profundidade_disponivel` e calado navegável por trecho (RF014/RF018) |
| `series_vazao_satelite` (`consensus_q`) | vazão independente | correnteza `V=Q/A` (RF032); validar a `vazao_adotada` da ANA; curva nível×vazão |
| juntos (virtuais + batimetria + vazão) | cobertura espacial | mapa contínuo de navegabilidade via interpolação (RF031) com mais âncoras |

> **Regra de ouro:** satélite é **complemento espacial/histórico** (SWOT revisita ~21 dias), não
> tempo real. A telemetria ANA (15 min) continua sendo a fonte operacional de alerta imediato.

### 12.2 Oportunidades de Machine Learning

| # | Aplicação | Alvo (label) | Features | Ganho | RF relacionada |
|---|---|---|---|---|---|
| a | **Regressão de cota de fundo** | `cota_fundo` (SICFLOW, 1,3 mi nós) | `hig_drn_depth_m`, `hig_drn_width_m`, `hig_drn_annual_flow`, `hig_drn_elevation_*`, `nustrahler` | estender batimetria aos 121.661 trechos sem SICFLOW | RF033/RF031 |
| b | **Interpolação de nível** | nível d'água | posição + rede de 4.734 virtuais + 75 ANA | substituir IDW simples (Gaussian Process / RF / k-NN) | RF031 |
| c | **Curva nível→vazão (rating curve)** | vazão | nível, largura, profundidade, declividade, Strahler | estimar Q em trechos sem medição | RF032 |
| d | **Classificação de navegabilidade** | classe (navegável/restrito/crítico) | nível, fundo, largura, vazão | classificar sem depender só de limiar fixo | RF018 |
| e | **Forecasting de nível/vazão** | nível/vazão futuros | série histórica (LSTM/Prophet) | planejamento + alerta de cheia/estiagem | — |

**Recomendação:** começar por **(a)** — regressão tabular limpa, labels abundantes (1,3 mi nós do
SICFLOW), features já no banco e resultado diretamente útil ao objetivo do projeto.

**Riscos / trade-offs:**
- **Leakage temporal/espacial:** separar treino/teste por trecho ou por período (autocorrelação forte
  em hidrologia); senão a métrica fica inflada.
- **Versão SWORD divergente** (batimetria v17b × vazão v16): preferir junção espacial (lon/lat) ao
  invés de `reach_id`.
- **Novas dependências:** `scikit-learn` (e opcionalmente `xgboost`) no `requirements.txt`.
- **Calado de referência (RF018):** determinado pelo DNIT/ANTAQ (Amazonas 10 m; Solimões 6 m; ver
  RN029 e seção 6) — falta apenas validar o limiar de transitabilidade com o orientador.
- Para dados tabulares de tamanho moderado, modelos de árvore/ensemble superam deep learning.

### 12.3 Resultado inicial (RF035 — regressão de cota de fundo)

`backend/treinar_cota_fundo.py` associa cada trecho navegável ao SICFLOW (mediana da
`cota_fundo` dos nós num raio de 1 km, via STRtree/dwithin) e treina um RandomForest sobre
os atributos AHGN. Resultado (split espacial 80/20 por célula de 0,5°, 39.811 trechos rotulados):

| Modelo | MAE (m) | RMSE (m) | viés (m) | R² |
|---|---|---|---|---|
| Baseline `hig_drn_elevation_min` | 8,61 | 21,57 | −5,98 | 0,998 |
| RandomForest (300 árvores) | 6,91 | 22,83 | +0,67 | 0,997 |

**Achado principal:** o proxy AHGN `hig_drn_elevation_min` já é quase idêntico ao SICFLOW
(correlação 0,999) — valida a estratégia da seção 10. O SICFLOW serve sobretudo para **corrigir
o viés** (−6 m) do AHGN; o RandomForest reduz o MAE em ~20% (8,6 → 6,9 m) e zera o viés.
`hig_drn_elevation_min` responde por 97% da importância do modelo.

- Persistido em `cota_fundo_trecho` (121.661 trechos: `cota_fundo_observada` em 42.721 com
  nó SICFLOW no raio, `cota_fundo_estimada` em todos).
- **Cobertura:** ~33% dos trechos têm SICFLOW a <1 km (rios largos); os demais (~67%, rios
  <100 m ou sem passagem SWOT) dependem da estimativa — foco do RF035.
- **Limitação:** RMSE do RandomForest levemente pior que o baseline (cauda de erros em rios
  profundos); para navegabilidade o MAE/viés são as métricas que importam.

### 12.4 Análise de erro do RF035 (por largura e relevância ao calado)

Erro do RandomForest no conjunto de teste (`|erro|` = |cota_fundo_pred − cota_fundo_obs|):

| Métrica | Valor |
|---|---|
| `|erro|` mediana (p50) | 2,86 m |
| `|erro|` p90 | 9,69 m |
| `|erro|` p99 | 104,4 m |

**MAE por largura do canal:**

| Largura (m) | n | MAE (m) | viés (m) |
|---|---|---|---|
| 0–200 | 7.394 | 7,07 | −0,74 |
| 200–500 | 404 | 4,28 | +0,83 |
| 500–1.000 | 41 | 4,48 | −2,05 |
| 1.000–3.000 | 6 | 2,76 | +0,35 |

**Relevância ao calado** — fração de trechos cujo erro de cota de fundo excede o calado
(isto é, onde a estimativa pode inverter a decisão de transitabilidade):

| Calado (m) | P(\|erro\| > calado) |
|---|---|
| 1 | 81,5% |
| 2 | 63,7% |
| 3 | 48,0% |
| 4 | 35,8% |
| 5 | 26,8% |

**Leitura:** o erro é maior nos rios estreitos (<200 m — que são a maioria e onde o SWOT não
alcança) e menor nos rios largos (2,8–4,5 m). Como o erro de cota de fundo (mediana 2,9 m) é da
ordem do calado típico (2–5 m), a regra de transitabilidade depende da **margem de segurança
(RN012, +0,5 m)** e do nível sazonal para não inverter decisões. O `|erro|` p99 de ~104 m indica
trechos onde o AHGN diverge fortemente do SICFLOW (a auditar).

### 12.5 Resultado RF036 (interpolação de nível com ML vs IDW)

`backend/interpolar_nivel.py` interpola o nível d'água (superfície, m rel. geoide) num mês de
observações das estações virtuais, comparando ML (RandomForest/kNN/HGB com covariável de
elevação AHGN) contra o IDW (RF031). Split espacial 80/20 por célula de 0,5° (4.601 estações
em 2024-09).

**Denso (3.730 estações de treino):**

| Modelo | MAE (m) | R² |
|---|---|---|
| IDW (só distância) | **13,75** | 0,987 |
| RandomForest (xy + elevação) | 14,01 | 0,969 |
| RandomForest (só xy) | 20,73 | 0,977 |

**Esparso (subamostra das estações de treino — simula cobertura limitada, ex. só as ~75 réguas ANA):**

| Estações | IDW MAE (m) | RF MAE (m) |
|---|---|---|
| 50 | 102,4 | **70,9** |
| 100 | 91,5 | **75,3** |
| 200 | 46,3 | **43,5** |
| 400 | 52,0 | **31,8** |
| 800 | 24,0 | 26,6 |

**Achado principal:** com cobertura **densa** de satélite (~4.600 estações) o IDW já é muito bom
(MAE ~14 m) e o ML não agrega; com cobertura **esparsa** (50–200 estações, o regime operacional
das ~75 réguas ANA) o ML com covariável de elevação reduz o MAE em ~20–30% em relação ao IDW
(elevação responde por ~89% da importância). Ou seja: **o ganho do ML está justamente no cenário
atual do projeto (poucas réguas)**, e o valor das estações virtuais é densificar a malha — aí o
IDW simples já basta.

- Erros absolutos elevados (dezenas de m) no regime esparso refletem o gradiente de ~3.800 m de
  nível entre cabeceiras andinas e a foz; a leitura é o **ganho relativo** ML vs IDW.
- Resultados de subamostra têm variância (amostra única); uma avaliação robusta exige repetir com
  múltiplas sementes.

### 12.6 Resultado RF037 (rating curve nível→vazão)

`backend/rating_curve.py` estima a vazão a partir do nível + geometria AHGN (largura, profundidade,
vazão média anual, Strahler, elevação), treinado nos 46.946 pares (nível, vazão) das 40 estações
ANA com medição de vazão.

| Cenário | MAE (m³/s) | R² | MAE_log10 |
|---|---|---|---|
| Baseline `hig_drn_annual_flow` | 25.846 | 0,277 | 0,775 |
| RandomForest cross-station (CV por estação) | 35.755 | 0,040 | 0,781 |
| HGB cross-station | 34.633 | 0,046 | 0,584 |
| RandomForest in-station (split aleatório) | **24** | **1,000** | **0,004** |

**Achado principal:** a curva-chave (Q = f(nível)) é **quase determinística por estação** — quando
a estação está no treino, o ML ajusta com erro ≈ 0 (R²=1,0; MAE 24 m³/s num intervalo de ~210 mil).
Porém a **regionalização** (estimar Q em trecho sem medição) falha: o modelo global não generaliza
(R²=0,04), porque os coeficientes da curva-chave são locais e as features AHGN são constantes por
estação (`hig_drn_elevation_avg` responde por 90% da importância e age como "identificador" de
estação, não como física transferível).

**Implicação (RF032/RN028):** a vazão deve vir da **estação influente mais próxima** (curva-chave
conhecida), não de um modelo global — exatamente o desenho atual do projeto. O `hig_drn_annual_flow`
segue como prior razoável para trechos sem estação próxima.

### 12.7 Resultado RF038 (classificação de navegabilidade)

`backend/classificar_navegabilidade.py` treina um RandomForest para classificar
`NAVEGAVEL`/`RESTRITO` (rótulos de `navegabilidade.status_navegabilidade`, 66 estações: 53/13)
usando features de geometria AHGN e cota.

| Modelo | Acurácia | Recall (RESTRITO) | F1 |
|---|---|---|---|
| Regra RF018 (`cota_atual − cota_min ≥ 50 cm`) | **1,000** | — | — |
| ML só geometria AHGN | 0,803 | 0,692 | 0,581 |
| ML geometria + cota_atual | 0,803 | 0,692 | 0,581 |
| ML geometria + cota_atual + cota_min | 0,864 | 0,769 | 0,690 |

**Achado principal (negativo, porém informativo):** os rótulos disponíveis são **derivados da
própria regra RF018** — a regra os recupera com 100% de acurácia. Logo, o ML não tem como superar
a regra: treinar sobre esses rótulos é circular. O recall de 0,69 com "só geometria" é espúrio
(rios estreitos coincidentemente RESTRITO no snapshot). Só com `cota_atual` **e** `cota_min` o ML
chega a 0,86 — ou seja, apenas reconstrói o `diff` da regra.

- **Bloqueio:** não há rótulo de navegabilidade independente. Os decretos do Legisla.AM são
  municipais e de tópico misto (muitos "estiagem" referem-se a diretrizes escolares, não à
  navegação) — insuficientes como ground truth.
- **Caminho para tornar o RF038 real:** obter rótulos por trecho (tráfego de embarcações/AIS,
  relatos de pilotos, calado efetivamente transitado) ou validar um calado de referência (RF018)
  com o orientador. Até lá, a regra RF018 permanece o modelo operacional.

### 12.8 Resultado RF039 (previsão de nível — cheia/estiagem)

`backend/prever_nivel.py` prevê o nível a partir do ciclo sazonal (dia-do-ano cíclico) e tendência
anual, com split temporal (treino < 2024, teste ≥ 2024), contra um baseline de climatologia mensal.

| Estação | Baseline climatologia (MAE/R²) | ML RF (MAE/R²) | ML HGB (MAE/R²) |
|---|---|---|---|
| Casiquiare (661 obs, 2008–2026) | 0,73 m / 0,72 | 0,84 m / 0,60 | 0,75 m / 0,69 |
| Manaus (101 obs, 2018–2026) | 1,75 m / 0,70 | 1,82 m / 0,65 | 1,92 m / 0,67 |

**Achado principal:** a previsão sazonal é dominada pelo ciclo anual — a **climatologia mensal**
já captura a cheia/estiagem (Manaus: pico ~junho, baixa ~novembro, corretos) com MAE de 1–2 m.
O ML com features apenas sazonais **não supera** a climatologia (e chega a ser pior por overfitting).
Ganho real de previsão exige preditores climáticos externos (chuva, ENSO, vazão a montante) ainda
fora do banco.

- Para o MVP, a climatologia mensal (por estação virtual) já fornece o ciclo de cheia/estiagem para
  planejamento de navegação, sem custo computacional.
- O RF039 cumpre o objetivo de "prever cheia/estiagem" no nível do ciclo sazonal; previsão de curto
  prazo (horas–dias, a partir da telemetria ANA) fica como extensão futura.
