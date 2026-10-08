# Estado Atual do Projeto

Relatório de acompanhamento dos requisitos do sistema de roteamento fluvial dinâmico. Descreve o que já está implementado, o que está parcialmente atendido e o que permanece pendente.

Legenda de status: **Atendido**, **Parcial**, **Não iniciado**, **Bloqueado**.

---

## 1. Resumo Executivo

O projeto encontra-se com **toda a base de dados e a camada de inteligência (ML) concluídas**, além dos coletores de dados da ANA e do satélite. O que ainda não existe é o **produto final executável**: não há backend FastAPI, não há aplicação Vue, não há motor de roteamento A* sobre dados reais, nem recursos de offline, autenticação e monitoramento.

Em termos de etapas:

- **Fases 1 (parcial) e 7 (completa)** avançadas — dados, coletores e ML.
- **Fases 2 a 6 (motor de roteamento, API, frontend, offline, notificações)** não iniciadas em código de produção.
- Existe um **MVP de grafo** com Dijkstra e dados fictícios que valida a arquitetura a ser reaproveitada.

---

## 2. Infraestrutura de Dados Já Construída

| Ativo | Conteúdo | Localização |
|-------|----------|-------------|
| Rede hidrográfica (BHAE/AHGN) | 481.135 trechos nacionais; recortes de hidrovias navegáveis (121.661) e federais (22.926) | `data/*.gpkg` |
| Banco consolidado | `estacoes` (75), `rios` (14.135), `telemetria` (128.237), `cotas_historicas` (75), `navegabilidade` (75), `decretos` (144), `trechos_navegaveis` (121.661), `estacoes_trechos` (75) | `data/hidrowize.db` |
| Dados de satélite | `estacoes_virtuais` (4.734), `series_nivel_satelite` (590.698), `batimetria_sicflow` (1.315.079), `series_vazao_satelite` (475.111) | `data/hidrowize.db` |
| Cota de fundo estimada | `cota_fundo_trecho` (121.661 trechos) | `data/hidrowize.db` |
| Coletores | Telemetria e cotas históricas ANA (SOAP e REST), satélite (SWOT), legislação | `backend/*.py` |
| Scripts derivados | Navegabilidade, histórico geográfico, extração de sondagens, geração do SQLite | `backend/*.py` |
| Mapa exploratório | Camadas de hidrovias, profundidade, estações e histórico de nível | `frontend/mapa-hidrovias/` |
| Dashboard de dados | Painel estático sobre os dados coletados | `frontend/dashboard/` |
| Protótipos de interface | Três alternativas de UI + protótipo PWA (`manifest.json`) | `frontend/prototipos/` |

---

## 3. Requisitos Funcionais — Status

### 3.1 Autenticação e Usuários

| ID | Requisito | Status | Observação |
|----|-----------|--------|------------|
| RF001 | Login do piloto | Não iniciado | Sem camada de API/autenticação |
| RF002 | Cadastro de usuários pelo admin | Não iniciado | — |
| RF003 | Listar/editar/desativar usuários | Não iniciado | — |
| RF004 | Atualização de perfil | Não iniciado | — |

### 3.2 Rede Hidrográfica e Grafo

| ID | Requisito | Status | Observação |
|----|-----------|--------|------------|
| RF005 | Importar shapefile da rede para o PostGIS | Parcial | Rede baixada e recortada em GeoPackage; não importada no PostGIS |
| RF033 | Importar pontos batimétricos | Atendido | Batimetria SICFLOW (1,3 mi nós) persistida no banco |
| RF006 | Reconstruir grafo NetworkX e validar conectividade | Parcial | Arquitetura validada no MVP com dados fictícios; grafo real ainda não construído |
| RF007 | Definir bacia/área ativa | Parcial | Corredor Manaus–Itacoatiara proposto; área ativa não formalizada |
| RF008 | Listar nós e arestas para auditoria | Não iniciado | Há apenas mapa exploratório |

### 3.3 Cotas e Níveis (ANA)

| ID | Requisito | Status | Observação |
|----|-----------|--------|------------|
| RF009 | Coleta automática de cotas (60 min) | Atendido | Coletores SOAP/REST + timers systemd; telemetria com 128.237 leituras |
| RF010 | Coleta manual | Parcial | Executável por linha de comando (com flag de forçar); sem endpoint de admin |
| RF011 | Visualizar nível atual no mapa | Parcial | Exibição em mapa estático; sem consumo via API |
| RF012 | Mínimos históricos por estação | Atendido | Séries históricas e cota mínima persistidas |

### 3.4 Batimetria e Profundidade

| ID | Requisito | Status | Observação |
|----|-----------|--------|------------|
| RF013 | Importar pontos batimétricos | Atendido | SICFLOW no banco |
| RF031 | Interpolar cota de fundo por aresta (IDW) | Parcial | Resolvido por modelo de ML (RF035), que substitui o IDW; `cota_fundo_trecho` gerado |
| RF014 | Recalcular profundidades com novos níveis | Não iniciado | Fórmula definida (RN022); falta integração e nivelamento de datum |
| RF015 | Mapa de profundidades estimadas | Parcial | Camada de profundidade (proxy) publicada no mapa; não é a profundidade calculada por nível |

### 3.5 Motor de Roteamento

| ID | Requisito | Status | Observação |
|----|-----------|--------|------------|
| RF016 | Calcular rota (origem, destino, calado, velocidade) | Não iniciado | Pipeline de custo definido, sem implementação |
| RF017 | Retorno da rota em GeoJSON | Não iniciado | — |
| RF018 | Marcar arestas intransitáveis | Parcial | Regra definida (RN010/RN012) e limiar de calado documentado (RN029); não integrada ao motor |
| RF032 | Derivação da correnteza (Q/A) | Parcial | Fórmula definida (RN025); Q e largura reais ainda não validados |
| RF019 | Roteamento A* por tempo | Não iniciado | Apenas Dijkstra fictício no MVP |
| RF020 | Resumo da rota | Não iniciado | — |

### 3.6 Modo Offline e Sincronização

| ID | Requisito | Status | Observação |
|----|-----------|--------|------------|
| RF021 | Persistência local (rota, níveis, grafo) | Não iniciado | — |
| RF022 | Cálculo de rota offline | Não iniciado | — |
| RF023 | Sincronização automática (pull/push) | Não iniciado | — |
| RF024 | Log de sincronização | Não iniciado | — |

### 3.7 Monitoramento de Rota

| ID | Requisito | Status | Observação |
|----|-----------|--------|------------|
| RF027 | Ativar monitoramento de rota | Não iniciado | — |
| RF028 | Recálculo automático por variação ≥ 30 cm | Não iniciado | Regra definida (RN020/RN021), sem implementação |
| RF029 | Notificação em tempo real | Não iniciado | — |
| RF034 | Canal WebSocket/SSE por usuário | Não iniciado | — |
| RF030 | Histórico de alterações da rota | Não iniciado | — |

### 3.8 Relatórios e Auditoria

| ID | Requisito | Status | Observação |
|----|-----------|--------|------------|
| RF025 | Histórico de rotas do piloto | Não iniciado | — |
| RF026 | Logs de coleta e sincronização | Parcial | Coleta gera logs em arquivo; sem painel de administração |

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
| RNF01 | Roteamento ≤ 5 s para 10.000 nós | Não iniciado | Depende do backend e do A* |
| RNF02 | Front-end ≤ 3 s em 4G | Parcial | Mapas estáticos carregam, mas o app não existe |
| RNF03 | Suporte a 24 h offline | Não iniciado | — |
| RNF04 | Python 3.10+ e Vue.js 3 | Parcial | Backend em Python; front-end ainda em protótipos sem Vue |
| RNF05 | Armazenamento local (IndexedDB/SQLite) | Não iniciado | — |
| RNF06 | Responsivo e multi-navegador | Parcial | Protótipos de UI existem, sem aplicação consolidada |
| RNF07 | Service Worker (stale-while-revalidate) | Não iniciado | — |
| RNF08 | Autenticação JWT segura | Não iniciado | — |
| RNF09 | Criptografia de campos locais | Não iniciado | — |
| RNF10 | Logs de auditoria | Parcial | Logs de coleta em arquivo; sem auditoria no front-end |

---

## 5. Regras de Negócio — Status

| Grupo de Regras | Regras | Status |
|-----------------|--------|--------|
| Usuário | RN001–RN005 | Não implementadas (sem módulo de usuários) |
| Estação | RN006–RN008 | Parcialmente atendidas nos coletores (código único, coleta padronizada) |
| Rota | RN009–RN012, RN022, RN023, RN029 | Definidas e documentadas; não integradas (motor inexistente). RN029 (calado DNIT/ANTAQ) formalizada |
| Nível | RN013–RN015 | Atendidas nos dados (mínima histórica, série, janela) |
| Nível | RN019–RN021 | Não implementadas (dependem do monitoramento) |
| Batimetria e Correnteza | RN024, RN025, RN028 | Parcialmente apoiadas nos dados (cota de fundo, vazão, largura) |
| Sincronização | RN016–RN018, RN026, RN027 | Não implementadas |

---

## 6. O Que Falta (Lacunas e Próximos Passos)

### 6.1 Lacunas críticas

1. **Backend e frontend inexistentes.** Não há API FastAPI nem aplicação Vue; os dados e modelos ainda não são servidos ao usuário.
2. **Referência vertical (datum) inconsistente.** A cota da régua ANA (cm, referida ao zero da régua) não está na mesma referência da cota de fundo (m, geóide). Sem calibrar, `profundidade = nível − cota_fundo` não é confiável.
3. **Grafo real não construído.** A topologia `noorigem`/`nodestino` da BHAE ainda não foi convertida em grafo NetworkX nem teve conectividade validada.
4. **Conectividade dos trechos.** Risco de pontas soltas, duplicatas e trechos desconexos no corredor.
5. **Estações deslocadas do canal** (até ~3 km) e proxies AHGN grosseiros em rios grandes afetam a associação estação→aresta.

### 6.2 Próximos passos priorizados

| # | Ação | Depende de |
|---|------|------------|
| 1 | Restaurar/gerar `data/` e o banco consolidado | Coletores |
| 2 | Recortar o corredor da área ativa (ex.: Manaus–Itacoatiara) | #1 |
| 3 | Construir o grafo real (NetworkX) e validar conectividade | #2 |
| 4 | Associar estação influente (RN023) e calibrar o datum vertical | #3, telemetria |
| 5 | Associar cota de fundo por aresta (SICFLOW/RF035) | #1 |
| 6 | Implementar o motor de pesos (transitabilidade + correnteza + tempo) | #4, #5 |
| 7 | Implementar o roteamento A* com heurística de tempo | #6 |
| 8 | Expor endpoint `/rotas/calcular` (FastAPI + GeoJSON) | #7 |
| 9 | Camada de rota no mapa (frontend) | #8 |
| 10 | Testes e validação do cenário real | #6–#9 |

### 6.3 Etapas de produto ainda ausentes

- Autenticação e gestão de usuários (RF001–RF004).
- Aplicação Vue 3 + PWA e empacotamento mobile.
- Persistência local e sincronização offline (RF021–RF024).
- Monitoramento de rota e notificações em tempo real (RF027–RF030, RF034).
- Histórico de rotas e painel de auditoria (RF025, RF026).
- Plano de testes (ISO/IEC 25010) e empacotamento.

---

## 7. Bloqueios e Dúvidas Abertas

- **RF038** depende de rótulos independentes de navegabilidade (AIS, relatos de pilotos, calado efetivamente transitado); sem eles, a regra RF018 permanece como referência.
- **Validação com orientador** do uso do SICFLOW como cota de fundo e do limiar de transitabilidade (RN010) e calado de referência (RN029).
- **Preditores climáticos** (chuva/ENSO) para previsão além da climatologia mensal.
