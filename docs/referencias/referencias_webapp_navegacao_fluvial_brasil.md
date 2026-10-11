# Referências para Web App de Navegação Fluvial no Brasil

> Guia de inspiração visual, identidade de cores, interfaces cartográficas e fontes de dados para um aplicativo temático de navegação e monitoramento hidrográfico no território brasileiro.

## 1. Objetivo

Desenvolver um web app com **mapa como elemento central**, capaz de apresentar informações sobre rios, rotas fluviais, estações fluviométricas, níveis, vazões e condições de navegação. A interface deve integrar cartografia moderna, linguagem visual amazônica e painéis legíveis em desktop e dispositivos móveis.

> **Distinção técnica:** cota (nível de referência de uma estação), vazão (volume de água por unidade de tempo) e profundidade navegável não são equivalentes. A cota de uma estação, isoladamente, não permite determinar o calado seguro de uma embarcação.

## 2. Referências de web apps

| Referência | Link | Elementos para observar | Aplicação sugerida |
|---|---|---|---|
| CoVadem | https://www.covadem.com/ | Visualização fluvial, profundidades e informações para navegação | Painéis de condições do trecho e indicadores náuticos |
| RiverApp | https://www.riverapp.net/ | Consulta de estações, nível e vazão; séries temporais | Cartões de estações e gráficos hidrológicos |
| Windy | https://www.windy.com/ | Camadas geográficas, animação temporal, controles sobre o mapa | Seletor de camadas e linha do tempo |
| OpenSeaMap | https://www.openseamap.org/ | Elementos cartográficos e sinalização náutica | Símbolos de navegação e camadas especializadas |
| Ventusky | https://www.ventusky.com/ | Mapas ambientais temáticos e gradientes | Precipitação, vento e visualização de condições ambientais |

### Diretrizes extraídas das referências

- Deixar o mapa ocupar a maior área útil da tela.
- Usar painéis recolhíveis para filtros e dados da estação selecionada.
- Oferecer alternância clara entre camadas: hidrografia, estações, meteorologia, rotas e alertas.
- Exibir a data/hora e a origem de cada informação, sobretudo quando houver atualização irregular.
- Diferenciar dados observados, previsões e informações não disponíveis.
- Adotar legendas consistentes e acessíveis, sem depender somente das cores.

## 3. Fontes brasileiras de dados

| Fonte | Link | Utilização potencial |
|---|---|---|
| HidroWeb — Agência Nacional de Águas e Saneamento Básico (ANA) | https://www.snirh.gov.br/hidroweb/mapa | Estações hidrométricas e séries históricas |
| Sistema Nacional de Informações sobre Recursos Hídricos (SNIRH) | https://www.snirh.gov.br/ | Dados e mapas sobre recursos hídricos e bacias |
| SACE — Serviço Geológico do Brasil (SGB) | https://sace.sgb.gov.br/ | Acompanhamento e alertas hidrológicos para localidades cobertas |

**Observação:** verificar disponibilidade, licença, cobertura, frequência de atualização e forma de acesso (API, download ou serviço geográfico) antes da integração. Não presumir que todos os serviços possuem API pública em tempo real.

## 4. Identidade visual e paletas de cores

As paletas abaixo são **propostas de design**, não padrões oficiais de cartografia ou alerta hidrológico.

### 4.1 Amazônia Tecnológica — recomendada

Identidade contemporânea inspirada na floresta, rios e tecnologias geoespaciais.

| Papel | Cor | HEX |
|---|---|---|
| Fundo | Verde escuro | `#102B29` |
| Superfície | Verde petróleo | `#193D39` |
| Primária | Turquesa | `#16B8A6` |
| Rios | Ciano claro | `#55C8DD` |
| Destaque | Dourado suave | `#E6BC6A` |
| Texto | Branco esverdeado | `#F0F7F3` |

```css
:root {
  --fundo: #102B29;
  --superficie: #193D39;
  --primaria: #16B8A6;
  --rios: #55C8DD;
  --destaque: #E6BC6A;
  --texto: #F0F7F3;
}
```

### 4.2 Navegação Noturna

Indicada para interface operacional com destaque para rotas e camadas informativas.

| Papel | HEX |
|---|---|
| Fundo | `#0C1726` |
| Superfície | `#17283D` |
| Primária | `#26C6DA` |
| Rios | `#348BF2` |
| Destaque | `#F4B860` |
| Texto | `#E8F2FA` |

### 4.3 Cartografia Natural

Aparência de atlas, com tons terrosos e fundo claro.

| Papel | HEX |
|---|---|
| Fundo | `#F5F1E6` |
| Superfície | `#FFFFFF` |
| Primária | `#306B57` |
| Rios | `#4B9DB7` |
| Destaque | `#BA8B4B` |
| Texto | `#233C35` |

### 4.4 Hidrografia Brasileira

Visual técnico e institucional para plataformas públicas ou analíticas.

| Papel | HEX |
|---|---|
| Fundo | `#F1F6F9` |
| Superfície | `#FFFFFF` |
| Primária | `#136F93` |
| Rios | `#3CADD2` |
| Destaque | `#E6A542` |
| Texto | `#183B56` |

### Boas práticas de cor

- Reservar cores de alerta para **estados hidrológicos documentados**, com limiares explicitados.
- Evitar confundir a cor de um rio no mapa com indicadores de navegabilidade.
- Fornecer contraste adequado, ícones, valores e textos auxiliares para acessibilidade.
- Considerar modo claro e escuro e não depender exclusivamente de vermelho/verde.

## 5. Proposta de layout

### 5.1 Desktop

```text
┌────────────────────────────────────────────────────────────────────┐
│ HidroNavega                    Buscar rio/cidade     Status  Conta │
├────────────────┬───────────────────────────────────┬───────────────┤
│ Filtros        │                                   │ Estação/trecho│
│                │                                   │ selecionado   │
│ ▢ Estações     │          MAPA INTERATIVO          │               │
│ ▢ Hidrografia  │                                   │ Cota: —       │
│ ▢ Alertas      │   Rios, camadas, marcadores,      │ Vazão: —      │
│ ▢ Meteorologia │        rotas e legendas          │ Atualização: —│
│ ▢ Rotas        │                                   │               │
├────────────────┴───────────────────────────────────┴───────────────┤
│ Gráfico histórico | Alertas recentes | Dados da estação           │
└────────────────────────────────────────────────────────────────────┘
```

### 5.2 Mobile

- Barra superior compacta com busca e botão de camadas.
- Mapa ocupando a tela principal.
- Filtros em painel lateral ou *bottom sheet*.
- Ao tocar em um ponto do mapa, abrir um cartão com nome, última medição, fonte e gráfico.
- Ações de localização e retorno ao enquadramento acessíveis com o polegar.

### 5.3 Componentes principais

1. **Mapa interativo:** hidrografia, bacias, estações, rotas e pontos relevantes.
2. **Busca:** rio, município, estação, bacia ou coordenadas.
3. **Seletor de camadas:** controle de visibilidade e legenda.
4. **Painel de detalhes:** identificação, medições, unidades e horário da atualização.
5. **Gráficos:** níveis e vazões ao longo do tempo.
6. **Alertas:** eventos com origem, severidade e período de validade.
7. **Linha do tempo:** quando houver dados históricos ou previsões.
8. **Responsividade e acessibilidade:** navegação por teclado, contraste e rótulos textuais.

## 6. Tecnologias recomendadas

| Tecnologia | Link | Uso |
|---|---|---|
| MapLibre GL JS | https://maplibre.org/ | Mapas vetoriais, camadas e estilos customizáveis |
| Leaflet | https://leafletjs.com/ | Mapas interativos leves e extensíveis |
| Maputnik | https://maputnik.github.io/ | Edição visual de estilos para mapas vetoriais |
| OpenStreetMap | https://www.openstreetmap.org/ | Dados cartográficos abertos, respeitadas suas licenças |
| Apache ECharts | https://echarts.apache.org/ | Gráficos de vazão, nível e séries temporais |

### Sugestão de arquitetura de apresentação

- **Frontend:** mapa com MapLibre GL JS, filtros, legenda e painéis reativos.
- **Dados geográficos:** fontes vetoriais ou GeoJSON adequados à escala.
- **Backend/API:** normalização dos dados de estações e armazenamento de histórico quando permitido.
- **Gráficos:** Apache ECharts para visualização temporal.
- **Estilos:** tokens CSS centralizados, utilizando uma das paletas apresentadas.

Para mapas e rotas de navegação real, verificar a procedência dos dados hidrográficos e a adequação às exigências de segurança; uma base cartográfica geral não substitui cartas náuticas oficiais atualizadas.

## 7. Direção de design sugerida

**Combinação recomendada:**

- **Visual:** paleta *Amazônia Tecnológica*.
- **Experiência de mapa:** controles de camadas e linha do tempo inspirados no Windy.
- **Painéis fluviais:** organização de indicadores e séries inspirada em RiverApp e CoVadem.
- **Contexto brasileiro:** dados hidrológicos provenientes de ANA/SNIRH e SGB, conforme disponibilidade.
- **Tecnologia cartográfica:** MapLibre GL JS para maior controle de simbologia e cores.

### Possíveis funcionalidades iniciais (MVP)

1. Visualizar mapa e rede hidrográfica de uma região brasileira.
2. Localizar rios e estações por nome ou geografia.
3. Exibir níveis e vazões disponíveis, com unidades, fonte e data da medição.
4. Consultar gráficos históricos por estação.
5. Alternar camadas e filtrar informações.
6. Exibir avisos hidrológicos somente quando houver dados e critérios confiáveis.

### Expansões futuras

- Rotas fluviais e pontos de interesse.
- Camadas meteorológicas e previsão de precipitação.
- Perfis de embarcação e restrições de calado, condicionados a dados náuticos adequados.
- Favoritos, notificações e funcionamento com conexão limitada.
- Comparação de estações e exportação de séries históricas.

## 8. Pontos de decisão do produto

Antes de detalhar telas e fluxos, definir qual necessidade é prioritária:

- **Navegação de embarcações:** planejamento de trajetos, sinalização, riscos e condições de trecho.
- **Monitoramento hidrológico:** séries, estações, cheias, secas, vazão e alertas.
- **Produto híbrido:** mapa de navegação acompanhado de uma camada analítica hidrológica.

Essa escolha determina quais informações precisam aparecer imediatamente e quais podem permanecer em menus secundários.

---

**Nota:** Este documento reúne referências e propostas conceituais de design. Links e disponibilidade dos serviços devem ser validados durante a implementação. A presença de um recurso em um aplicativo de referência não implica que ele ofereça API pública ou permissão de reutilização.
