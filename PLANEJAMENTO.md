# Sistema de Roteamento Fluvial Dinâmico – Web App com suporte Offline

**Autores:** [Nome da Dupla]  
**Data:** Agosto/2026  
**Versão:** 2.0 (atualizado)

---

## 1. Visão Geral do Projeto

O projeto consiste em uma aplicação web interativa para **roteamento dinâmico de embarcações em hidrovias amazônicas**, considerando variações sazonais do nível dos rios (seca/cheia) e o calado das embarcações. A solução é desenvolvida como um **Web App progressivo (PWA)** ou aplicativo híbrido, permitindo que o usuário o instale em seu dispositivo móvel para uso offline.

**Diferenciais:**
- Front-end moderno com **Vue.js** (Composition API) e visualização cartográfica baseada em **Leaflet** ou **MapLibre**.
- Possibilidade de instalação como aplicativo (via Capacitor/Cordova) para distribuição em lojas (Google Play/App Store) ou como PWA.
- **Modo offline completo**: a última atualização de rotas, níveis dos rios e dados hidrológicos são armazenados localmente (IndexedDB, SQLite ou similar) para consulta quando o dispositivo estiver sem conexão com a internet.
- Sincronização automática quando o dispositivo estiver online, atualizando os dados em segundo plano.

**Backend:** API REST em Python (FastAPI) que processa as requisições de roteamento, consome dados da ANA/CPRM e gerencia a lógica de interpolação e cálculos geoespaciais (GeoPandas, NetworkX, PostGIS).

---

## 2. Requisitos do Sistema

### 2.1. Requisitos Funcionais (RF)

| ID  | Descrição |
|-----|-----------|
| **RF01** | O backend deve representar a rede hidrográfica como um grafo com geometrias armazenadas no PostGIS e manipuladas via GeoPandas/Shapely. |
| **RF02** | Estimar profundidades em trechos sem medição direta utilizando o método **IDW** (SciPy/NumPy). |
| **RF03** | Calcular o peso dinâmico de cada aresta: `Custo = Distância × [1 + Penalidade_calado + Penalidade_corrente]`. |
| **RF04** | Validar transitabilidade: se `profundidade < calado`, a aresta é intransitável (peso infinito). |
| **RF05** | Implementar o algoritmo **A\*** (NetworkX ou customizado) para encontrar a rota de menor custo. |
| **RF06** | Consumir dados telemétricos das APIs da **ANA** e **CPRM** em tempo real (Requests/HTTPX). |
| **RF07** | Expor API REST (FastAPI) que retorne rotas em **GeoJSON** e também dados de níveis dos rios. |
| **RF08** | Simplificar polilinhas com o algoritmo **Ramer-Douglas-Peucker** (Shapely/RDP) para otimização. |
| **RF09** | O front-end em **Vue.js** deve exibir um mapa interativo (Leaflet/MapLibre) com a rota calculada, estações telemétricas e profundidades estimadas. |
| **RF10** | O usuário deve poder **baixar/instalar** o aplicativo a partir do navegador (PWA) ou via lojas de aplicativos (empacotado com Capacitor/Cordova). |
| **RF11** | O aplicativo deve armazenar localmente (IndexedDB / SQLite) a **última atualização** dos dados: rotas, níveis dos rios, profundidades e histórico de consultas. |
| **RF12** | Quando offline, o aplicativo deve usar os dados armazenados localmente para simular rotas e exibir informações, mesmo que não atualizadas. |
| **RF13** | Quando online, o aplicativo deve **sincronizar** automaticamente os dados com o backend (pull de novas medições, push de logs locais). |

### 2.2. Requisitos Não Funcionais (RNF)

| ID  | Descrição |
|-----|-----------|
| **RNF01** | O backend deve responder às requisições de roteamento em ≤ **5 segundos** para redes com até 10.000 nós. |
| **RNF02** | O front-end deve carregar o mapa e os dados iniciais em ≤ **3 segundos** em conexão 4G. |
| **RNF03** | O aplicativo offline deve suportar **pelo menos 24 horas** de uso sem conexão, com os dados armazenados localmente. |
| **RNF04** | Desenvolvimento em **Python 3.10+** (backend) e **Vue.js 3** (front-end), com TypeScript opcional. |
| **RNF05** | Armazenamento local no front-end: **IndexedDB** (via Dexie.js) para PWA, ou **SQLite** (via Capacitor) para aplicativo híbrido. |
| **RNF06** | O front-end deve ser responsivo (mobile-first) e funcionar nos principais navegadores (Chrome, Firefox, Edge, Safari). |
| **RNF07** | O aplicativo deve utilizar **Service Worker** para caching de assets e dados (estratégia stale-while-revalidate). |
| **RNF08** | Autenticação via JWT no backend; o front-end armazena o token de forma segura (localStorage ou Secure Storage). |
| **RNF09** | Os dados armazenados localmente devem ser **criptografados** em nível de campo (sensíveis) e protegidos contra acesso indevido. |
| **RNF10** | Logs do backend e do front-end devem ser registrados para auditoria (backend: logging/structlog; front-end: console remoto ou envio em lote quando online). |

---

## 3. Metodologia de Gestão do Projeto – Scrumban

Adotamos **Scrumban** – híbrido de Scrum e Kanban – para uma equipe de 2 pessoas, com fluxo contínuo e limites de WIP.

**Regras:**
- **Backlog** contínuo e priorizado semanalmente.
- **Quadro Kanban**: *To Do*, *In Progress*, *Review*, *Done*.
- **Limite de WIP**: 2 tarefas por pessoa.
- **Reuniões**: Daily de 5 min e Retrospectiva quinzenal de 30 min.

**Etapas de desenvolvimento:**

| Fase | Atividades | Entregáveis |
|------|------------|-------------|
| **Configuração e Modelagem** | Modelo de dados (PostGIS); ambiente Python (Poetry); importação de shapefiles; estrutura do grafo (NetworkX). | Banco populado; grafo inicial. |
| **Motor de Roteamento (Backend)** | IDW, cálculo de pesos, A*; APIs de interpolação e roteamento. | Roteador funcional; testes unitários. |
| **Integração com Fontes de Dados** | Consumo das APIs da ANA/CPRM; implementação de cache e fallback para offline. | Módulo de sincronização; endpoint de status. |
| **API REST e Documentação** | FastAPI com endpoints para rotas, níveis e sincronização; Swagger UI. | API documentada e testada. |
| **Front-end Vue.js** | Estrutura do projeto (Vite), configuração do mapa, componentes de rota e estações; modo offline com IndexedDB/SQLite. | Protótipo visual com funcionalidade básica. |
| **Sincronização e Offline** | Service Worker, cache de assets, lógica de sincronização (pull/push) e gerenciamento de dados locais. | App funcional offline; sincronização automática. |
| **Empacotamento e Testes** | Build para PWA; empacotamento com Capacitor (Android/iOS); testes ISO 25010. | Aplicativo publicado em lojas (opcional); relatório de testes. |

**Ferramentas:** Git/GitHub, Poetry, Vue CLI/Vite, Dexie.js (IndexedDB), Capacitor, Trello/Notion.

---

## 4. Rastreabilidade entre Requisitos

| # | Requisito Funcional | Requisito Não Funcional Relacionado | Justificativa |
|---|---------------------|--------------------------------------|---------------|
| 1 | **RF05** – A* para roteamento (backend) | **RNF01** – Tempo de resposta ≤ 5s | O desempenho do algoritmo é crítico; o uso de NetworkX e a simplificação de vértices garantem rapidez. |
| 2 | **RF11** – Armazenamento offline (IndexedDB/SQLite) | **RNF03** – 24h de uso offline | A persistência local permite que o usuário continue navegando mesmo sem internet, essencial para áreas remotas. |
| 3 | **RF13** – Sincronização automática online/offline | **RNF10** – Logs e auditoria | A sincronização deve registrar falhas e sucessos para garantir a integridade dos dados; os logs auxiliam na depuração. |

---

## 5. Plano de Testes – ISO/IEC 25010

Avaliação do sistema com base nas 8 características da ISO 25010.

| Característica | Estratégia de Avaliação | Critério de Aceitação |
|----------------|--------------------------|------------------------|
| **Adequação Funcional** | Testes de caixa-preta (pytest) para roteamento, interpolação e sincronização; testes de interface com Cypress (front-end). | 100% dos casos de uso executados com sucesso, incluindo offline e sincronização. |
| **Confiabilidade** | Simulação de falhas de rede no front-end (offline) e no backend (APIs externas); verificação da recuperação. | O aplicativo deve funcionar com dados locais por ≥ 24h; ao recuperar a rede, a sincronização deve ser completada sem perda de dados. |
| **Usabilidade** | Teste com usuários reais (pilotos, operadores) utilizando o aplicativo em campo; coleta de feedback. | Taxa de sucesso na primeira utilização ≥ 90%; tempo médio para encontrar uma rota ≤ 1 minuto. |
| **Eficiência de Desempenho** | Medição do tempo de carregamento do mapa e da rota (Lighthouse); tempo de resposta do backend (cProfile). | Front-end: First Contentful Paint < 2s; Backend: rota em ≤ 5s para 10k nós. |
| **Manutenibilidade** | Análise estática (Ruff/Pylint para Python, ESLint para Vue); cobertura de testes. | Cobertura ≥ 80% para módulos críticos; baixa complexidade ciclomática. |
| **Portabilidade** | Teste do PWA em diferentes navegadores e dispositivos; teste do app empacotado (Capacitor) em Android e iOS. | O aplicativo deve funcionar em todas as plataformas alvo sem ajustes manuais. |
| **Segurança** | Testes de autenticação, injeção de dados maliciosos (backend), verificação de criptografia local (front-end). | 100% dos endpoints protegidos; dados locais criptografados; vulnerabilidades críticas zeradas (Bandit/Safety). |
| **Compatibilidade** | Verificação da integração com PostGIS, APIs da ANA/CPRM e com os principais navegadores. | Integração plena; front-end responsivo e consistente em todos os navegadores. |

---

## 6. Considerações Finais

Este documento reflete as novas diretrizes: o sistema é um Web App com Vue.js, com possibilidade de ser instalado como aplicativo híbrido (PWA ou Capacitor) e com suporte **offline** através de armazenamento local (IndexedDB/SQLite) e sincronização automática. Os requisitos foram atualizados para contemplar essas funcionalidades, e o plano de testes inclui cenários de desconexão.

A metodologia Scrumban permanece, com fases adaptadas para contemplar o front-end, o empacotamento e os testes de offline. A rastreabilidade agora inclui exemplos que conectam o armazenamento local e a sincronização aos atributos de qualidade.

### Status atual (Agosto/2026)

Coleta de dados da Fase 1 praticamente concluída:

- Rede hidrográfica (ANA/BHAE-AHGN) baixada e recortada em hidrovias navegáveis (GeoPackage + GeoJSON).
- 75 estações ANA cruzadas com os trechos, com atributos morfológicos (profundidade, largura, vazão, elevação, Manning).
- Telemetria e cotas históricas coletadas (coletor ANA SOAP + REST).
- Batimetria real indisponível como dado aberto → decisão: usar **proxy AHGN `hig_drn_depth_m`** (a validar com o orientador).
- Mapa interativo de exploração pronto (`frontend/mapa-hidrovias/`).
- Fontes e decisões documentadas em `mapeamento_fontes.md`.

Próximos passos: construir o grafo (RF006), subir o ambiente (PostGIS/FastAPI) e iniciar o motor de roteamento (IDW + A*).