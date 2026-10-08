# Requisitos e Critérios de Aceite

Documento consolidado dos requisitos funcionais, requisitos não funcionais, regras de negócio e critérios de aceite do sistema de roteamento fluvial dinâmico.

---

## 1. Requisitos Funcionais (RF)

### 1.1 Módulo: Autenticação e Usuários

**Descrição**: Registro, login e gestão de usuários com papéis (admin/piloto).

| ID | História de Usuário | Prioridade | Dependências |
|----|---------------------|------------|--------------|
| RF001 | Como piloto, quero fazer login para acessar o sistema | Alta | Nenhuma |
| RF002 | Como admin, quero cadastrar usuários para conceder acesso à equipe | Alta | Nenhuma |
| RF003 | Como admin, quero listar/editar/desativar usuários para controlar acesso | Média | RF002 |
| RF004 | Como piloto, quero atualizar meu perfil (nome, senha) | Baixa | RF001 |

**Critérios de Aceite**
- CA-RF001.1: Dado um usuário com credenciais válidas, quando ele faz login, então recebe um token JWT com o papel correto.
- CA-RF002.1: Dado um admin logado, quando cadastra um piloto, então o piloto consegue logar.
- CA-RF003.1: Dado um usuário desativado, quando tenta logar, então recebe erro 401.

### 1.2 Módulo: Rede Hidrográfica e Grafo

**Descrição**: Importação e gestão do grafo de navegação (nós/arestas) a partir do shapefile ANA.

| ID | História de Usuário | Prioridade | Dependências |
|----|---------------------|------------|--------------|
| RF005 | Como admin, quero importar o shapefile da rede hidrográfica para popular o PostGIS | Alta | Nenhuma |
| RF033 | Como admin, quero importar os pontos batimétricos da área ativa (cota de fundo) | Alta | RF005 |
| RF006 | Como admin, quero reconstruir o grafo (NetworkX) para validar conectividade | Alta | RF005 |
| RF007 | Como admin, quero definir a bacia amazônica (priorizando a área brasileira) como área ativa do MVP | Alta | RF005 |
| RF008 | Como admin, quero listar nós e arestas para auditar a malha | Média | RF006 |

**Critérios de Aceite**
- CA-RF005.1: Dado um shapefile válido, quando importado, então a geometria aparece como LINESTRING no PostGIS.
- CA-RF006.1: Dado um grafo reconstruído, quando validado, então todos os nós do trecho estão conectados.
- CA-RF007.1: Dado o trecho definido, quando o roteador consulta, então usa apenas nós/arestas do trecho.

### 1.3 Módulo: Cotas e Níveis (Dados ANA)

**Descrição**: Coleta e armazenamento de níveis telemétricos das estações da área ativa.

| ID | História de Usuário | Prioridade | Dependências |
|----|---------------------|------------|--------------|
| RF009 | Como sistema, quero coletar cotas das estações ANA da área ativa a cada 60 min | Alta | Nenhuma |
| RF010 | Como admin, quero forçar uma coleta manual para atualizar dados | Média | RF009 |
| RF011 | Como piloto, quero visualizar o nível atual de uma estação no mapa | Alta | RF009 |
| RF012 | Como sistema, quero armazenar mínimos históricos por estação para a regra de navegabilidade | Média | RF009 |

**Critérios de Aceite**
- CA-RF009.1: Dado um código de estação válido, quando o coletor roda, então grava nível, chuva e vazão com timestamp.
- CA-RF010.1: Dado um endpoint de coleta manual, quando admin aciona, então retorna o resumo da coleta.
- CA-RF012.1: Dado dados históricos, quando calculada a mínima, então a cota mínima da estação fica disponível.

### 1.4 Módulo: Batimetria e Estimativa de Profundidade (IDW)

**Descrição**: Modelagem do fundo do rio e derivação da profundidade por trecho.

| ID | História de Usuário | Prioridade | Dependências |
|----|---------------------|------------|--------------|
| RF013 | Como admin, quero importar pontos batimétricos (cota de fundo) para basear a estimativa | Alta | RF005 |
| RF031 | Como sistema, quero interpolar a cota de fundo por aresta usando IDW (SciPy) sobre os pontos batimétricos | Alta | RF013 |
| RF014 | Como sistema, quero recalcular profundidades quando novos níveis chegam | Alta | RF031, RF009 |
| RF015 | Como admin, quero visualizar o mapa de profundidades estimadas | Média | RF014 |

**Critérios de Aceite**
- CA-RF031.1: Dado um conjunto de pontos batimétricos, quando o IDW roda, então cada aresta ganha `cota_fundo_batimetria`.
- CA-RF014.1: Dada uma aresta com cota de fundo e nível atual, quando calculada, então a profundidade = nível − cota_fundo.
- CA-RF014.2: Dado novos níveis, quando recalcula, então a profundidade muda sem refazer o IDW (cota de fundo é estática).
- CA-RF031.2: Dada uma aresta sem pontos batimétricos no raio, quando processada, então fica marcada como desconhecida.

### 1.5 Módulo: Motor de Roteamento

**Descrição**: Cálculo da rota de menor tempo considerando calado, correnteza e profundidade.

| ID | História de Usuário | Prioridade | Dependências |
|----|---------------------|------------|--------------|
| RF016 | Como piloto, quero calcular uma rota informando origem, destino, calado e velocidade da embarcação | Alta | RF006, RF014 |
| RF017 | Como piloto, quero receber a rota em GeoJSON para exibir no mapa | Alta | RF016 |
| RF018 | Como sistema, quero marcar arestas intransitáveis (profundidade < calado) | Alta | RF014 |
| RF032 | Como sistema, quero derivar a velocidade da correnteza por aresta a partir da vazão e seção | Alta | RF014 |
| RF019 | Como sistema, quero aplicar o algoritmo A* minimizando o tempo total (custo = distância / velocidade) | Alta | RF018, RF032 |
| RF020 | Como piloto, quero ver o resumo da rota (distância, tempo estimado, trechos críticos) | Média | RF016 |

**Critérios de Aceite**
- CA-RF016.1: Dado origem e destino válidos, quando calculado, então retorna rota, distância e tempo total.
- CA-RF018.1: Dado calado maior que a profundidade de um trecho, quando calculado, então o trecho é desviado.
- CA-RF019.1: Dado um trecho a favor da correnteza, quando o custo é calculado, então o tempo é menor que contra a corrente.
- CA-RF016.2: Dado origem e destino desconectados, quando calculado, então retorna erro 404 (rota não encontrada).

### 1.6 Módulo: Modo Offline e Sincronização

**Descrição**: Persistência local (incluindo o grafo) e sincronização com o backend.

| ID | História de Usuário | Prioridade | Dependências |
|----|---------------------|------------|--------------|
| RF021 | Como piloto, quero que o app armazene localmente a última rota, níveis e o grafo da área ativa | Alta | RF009, RF016 |
| RF022 | Como piloto, quero calcular rota offline recalculando localmente sobre o grafo do snapshot | Alta | RF021 |
| RF023 | Como sistema, quero sincronizar automaticamente ao voltar online (pull/push) | Alta | RF021 |
| RF024 | Como sistema, quero logar sucessos e falhas de sincronização | Média | RF023 |

**Critérios de Aceite**
- CA-RF022.1: Dado o app sem conexão, quando piloto calcula rota, então o A* local recalcula sobre o grafo do snapshot.
- CA-RF022.2: Dado o snapshot completo, quando offline, então o app recalcula com os mesmos resultados do backend (para mesmo grafo).
- CA-RF021.1: Dado o app offline por 24h, quando consulta dados, então mantém funcionalidade básica.
- CA-RF023.1: Dado retorno da conexão, quando online, então o app sincroniza sem perder dados locais.

### 1.7 Módulo: Monitoramento de Rota (Nível do Rio)

**Descrição**: Acompanhamento da rota ativa e recomputação automática quando o nível do rio varia.

| ID | História de Usuário | Prioridade | Dependências |
|----|---------------------|------------|--------------|
| RF027 | Como piloto, quero ativar o monitoramento de uma rota para ser avisado se ela mudar | Alta | RF016 |
| RF028 | Como sistema, quero recalcular automaticamente a rota monitorada quando o nível variar ≥ 30 cm | Alta | RF014, RF027 |
| RF029 | Como piloto, quero receber notificação em tempo real quando a rota monitorada mudar | Alta | RF028 |
| RF034 | Como sistema, quero manter um canal WebSocket/SSE por usuário para entrega de eventos | Alta | RF029 |
| RF030 | Como piloto, quero ver o histórico de alterações de uma rota monitorada | Média | RF028 |

**Critérios de Aceite**
- CA-RF028.1: Dada uma rota com monitoramento ativo, quando nova leitura ANA chega, então o sistema compara a variação de nível.
- CA-RF028.2: Dada variação ≥ 30 cm em estação do trecho, quando validada, então a rota é recalculada e o piloto é notificado.
- CA-RF029.1: Dado o app online, quando o backend publica o evento, então o WebSocket entrega em < 2s.
- CA-RF029.2: Dado o app offline, quando a rota muda, então a notificação é entregue na próxima sincronização.
- CA-RF028.3: Dada variação < 30 cm, quando nova leitura chega, então apenas o nível é atualizado sem recalcular.
- CA-RF030.1: Dado recálculo com mudança de traçado, quando concluído, então o novo traçado fica disponível e o antigo é versionado.

### 1.8 Módulo: Relatórios e Auditoria

**Descrição**: Histórico de rotas e logs para auditoria.

| ID | História de Usuário | Prioridade | Dependências |
|----|---------------------|------------|--------------|
| RF025 | Como piloto, quero ver o histórico das minhas rotas calculadas | Média | RF016 |
| RF026 | Como admin, quero visualizar logs de coleta e sincronização | Baixa | RF024 |

**Critérios de Aceite**
- CA-RF025.1: Dado um piloto logado, quando abre histórico, então vê rotas com data, origem, destino e calado.
- CA-RF026.1: Dado um admin logado, quando abre logs, então vê status e erros de coletas/sincronizações.

### 1.9 Módulo: Inteligência de Dados (Satélite + ML)

**Descrição**: Aplicação dos dados satelitais (altimetria, batimetria SICFLOW, vazão SWOT) e de modelos de Machine Learning para preencher lacunas de batimetria, nível, vazão e navegabilidade.

| ID | História de Usuário | Prioridade | Dependências |
|----|---------------------|------------|--------------|
| RF035 | Como sistema, quero estimar a cota de fundo dos trechos sem batimetria usando um modelo treinado com os nós do SICFLOW e os atributos AHGN | Alta | RF005, RF033 |
| RF036 | Como sistema, quero interpolar o nível d'água da bacia com ML (em substituição ao IDW simples) usando as estações virtuais e as estações ANA | Média | RF009 |
| RF037 | Como sistema, quero estimar a vazão em trechos sem medição a partir do nível e da geometria do canal (rating curve) | Média | RF032 |
| RF038 | Como sistema, quero classificar a navegabilidade (navegável/restrito/crítico) com ML a partir de nível, fundo, largura e vazão | Baixa | RF014, RF018 |
| RF039 | Como piloto, quero ver a previsão de nível/vazão (cheia/estiagem) para planejar a navegação | Baixa | RF009 |

**Critérios de Aceite**
- CA-RF035.1: Dado os 1,3 mi nós do SICFLOW com cota de fundo, quando o modelo RF035 é treinado com os atributos AHGN, então os trechos sem batimetria recebem cota de fundo estimada.
- CA-RF035.2: Dada a validação com separação treino/teste por trecho ou período, quando avaliada, então a métrica é registrada sem inflação por leakage espacial/temporal.
- CA-RF036.1: Dada a rede de estações virtuais e ANA, quando a interpolação ML (RF036) roda, então cada aresta recebe nível estimado comparável ou melhor que o IDW.
- CA-RF037.1: Dados nível, largura, profundidade e declividade, quando a rating curve (RF037) roda, então a vazão estimada é comparada à vazão observada (ANA/SWOT).
- CA-RF038.1: Dadas as features de nível, fundo, largura e vazão, quando o classificador (RF038) roda, então retorna a classe de navegabilidade com métrica de acurácia/recall.
- CA-RF038.2: Dado o calado de referência (RF018) ainda indefinido, quando a classificação (RF038) é treinada, então as labels são derivadas de decretos (Legisla.AM) e Defesa Civil, não de limiar fixo.
- CA-RF039.1: Dada a série histórica, quando a previsão (RF039) roda, então gera previsão de cheia/estiagem com horizonte definido.

---

## 2. Requisitos Não Funcionais (RNF)

| ID | Descrição |
|----|-----------|
| RNF01 | O backend deve responder às requisições de roteamento em ≤ 5 segundos para redes com até 10.000 nós. |
| RNF02 | O front-end deve carregar o mapa e os dados iniciais em ≤ 3 segundos em conexão 4G. |
| RNF03 | O aplicativo offline deve suportar pelo menos 24 horas de uso sem conexão, com os dados armazenados localmente. |
| RNF04 | Desenvolvimento em Python 3.10+ (backend) e Vue.js 3 (front-end), com TypeScript opcional. |
| RNF05 | Armazenamento local no front-end: IndexedDB (via Dexie.js) para PWA, ou SQLite (via Capacitor) para aplicativo híbrido. |
| RNF06 | O front-end deve ser responsivo (mobile-first) e funcionar nos principais navegadores (Chrome, Firefox, Edge, Safari). |
| RNF07 | O aplicativo deve utilizar Service Worker para caching de assets e dados (estratégia stale-while-revalidate). |
| RNF08 | Autenticação via JWT no backend; o front-end armazena o token de forma segura (localStorage ou Secure Storage). |
| RNF09 | Os dados armazenados localmente devem ser criptografados em nível de campo (sensíveis) e protegidos contra acesso indevido. |
| RNF10 | Logs do backend e do front-end devem ser registrados para auditoria (backend: logging/structlog; front-end: console remoto ou envio em lote quando online). |

---

## 3. Regras de Negócio (RN)

### 3.1 Entidade: Usuário

| ID | Regra | Tipo | Descrição |
|----|-------|------|-----------|
| RN001 | Papel obrigatório | Validação | Todo usuário deve ter papel `admin` ou `piloto`. |
| RN002 | Email único | Validação | Não pode haver dois usuários com o mesmo email. |
| RN003 | Senha forte | Validação | Senha mínima de 8 caracteres com letras e números. |
| RN004 | Auto-registro bloqueado | Fluxo | Registro público não permitido; apenas admin cria usuários. |
| RN005 | Token JWT | Segurança | Token expira em 8h; logout invalida sessão no cliente. |

**Detalhamento**
- RN004: Dada qualquer requisição `POST /auth/register` sem papel de admin, então retorna 403; apenas admin autenticado cria usuários. Exceção: seed inicial cria o primeiro admin via script.

### 3.2 Entidade: Estação

| ID | Regra | Tipo | Descrição |
|----|-------|------|-----------|
| RN006 | Código único | Validação | `codigo_estacao` é único (identificador ANA). |
| RN007 | Coleta padronizada | Validação | Registro de nível exige `codigo_estacao`, `data_hora` e `nivel_cm` não nulos. |
| RN008 | Formato de dados | Validação | Datas no formato `dd/MM/yyyy` na entrada da API ANA; armazenar UTC. |

**Detalhamento**
- RN007: Dada cada leitura vinda da telemetria ANA, então grava `nivel_cm`, `chuva_mm`, `vazao` e timestamp; nulos viram NULL. Exceção: se `nivel` ausente, não grava; registra falha no log de coleta.

### 3.3 Entidade: Rota

| ID | Regra | Tipo | Descrição |
|----|-------|------|-----------|
| RN009 | Calado obrigatório | Validação | Rota exige `calado_m` > 0; máximo 20 m. |
| RN010 | Transitabilidade | Cálculo | Aresta intransitável se `profundidade_estimada < calado`. |
| RN011 | Custo da aresta (tempo) | Cálculo | `Custo (h) = Distância_km / Velocidade_líquida_kmh`. |
| RN012 | Cota limite | Cálculo | Aresta transitável exige margem mínima de 0,5 m sobre o calado. |
| RN022 | Profundidade da aresta | Cálculo | `profundidade = cota_nivel_atual − cota_fundo_batimetria` (não é interpolado diretamente). |
| RN023 | Estação influente | Cálculo | Aresta usa o nível da estação mais próxima ao longo da rede (raio de 50 km). |
| RN029 | Calado de referência | Parâmetro | Calado de projeto do DNIT/ANTAQ por tramo (ver detalhamento). |

**Detalhamento**
- RN010: No cálculo da rota, para cada aresta, se `profundidade < calado`, então peso = infinito (aresta removida do A*). Exceção: sem aresta viável → erro 404 "rota não encontrada".
- RN011: Sempre que se calcula o peso de uma aresta, então `Velocidade_líquida = Velocidade_embarcação + Velocidade_correnteza`, onde `Velocidade_correnteza > 0` a favor da corrente (descendo o rio) e `Velocidade_correnteza < 0` contra a corrente (subindo o rio); `Custo (h) = Distância_km / Velocidade_líquida_kmh`. Exceção: se `Velocidade_líquida ≤ 0`, peso = infinito (trecho não percorrível).
- RN012: Sempre que for calcular transitabilidade, considera navegável apenas se `profundidade ≥ calado + 0,5 m`. Exceção: piloto pode optar por "modo arriscado" desativando a margem (preferência do perfil).
- RN022: Toda vez que se estima a profundidade de uma aresta, o IDW interpola a cota do fundo do rio a partir dos pontos batimétricos (RF013); a cota do nível da aresta vem da estação influente (RN023); `profundidade = cota_nivel_atual − cota_fundo_batimetria`. Exceção: aresta sem cota de fundo (sem pontos batimétricos no raio) → `profundidade = NULL` e a aresta é tratada como desconhecida (exige revisão manual).
- RN023: Para associar nível a uma aresta, seleciona a estação com menor distância ao longo da rede hidrográfica (não distância euclidiana) dentro de um raio de 50 km; se nenhuma, aresta fica sem nível. Exceção: estação fora do raio → `profundidade = NULL` (aresta desconhecida).
- RN029: Parametrizar a navegabilidade por tramo da hidrovia (fonte: DNIT/ANTAQ). Calado de projeto por tramo:
  - Amazonas (Manaus–Belém, ~1.650 km): 10 m (navios marítimos até 60.000 TPB)
  - Solimões (Tabatinga–Manaus, ~1.600 km): 6 m (mínimo; com pontos críticos na seca)
  - Madeira (Porto Velho–Itacoatiara, ~1.450 km): >13 m na cheia (navios oceânicos até Porto Velho); na seca forma praias e restringe a navegação de grande porte
  - Negro (Porto de Manaus): recebe navios de qualquer calado mesmo nas vazantes
  - Exceção: o calado efetivo de cada rota é o `calado_m` informado pelo piloto (RN009); o calado de referência é o teto de navegabilidade do tramo, não um limite fixo por rota.

### 3.4 Entidade: Nível

| ID | Regra | Tipo | Descrição |
|----|-------|------|-----------|
| RN013 | Série temporal | Cálculo | Cota mínima histórica = menor `nivel_cm` do período disponível da estação. |
| RN014 | Deduplicação | Validação | Uma leitura por `(codigo_estacao, data_hora)` — upsert. |
| RN015 | Janela de consulta | Validação | `data_fim ≥ data_inicio`; intervalo máximo de 90 dias por requisição. |
| RN019 | Limiar de variação | Cálculo | Variação de nível calculada por estação como `|nivel_atual − nivel_anterior|` na janela monitorada. |
| RN020 | Recomputação automática | Fluxo | Rota em monitoramento é recalculada se variação ≥ 30 cm em estação influente do trecho. |
| RN021 | Cooldown de recálculo | Fluxo | Após recomputar, aguardar no mínimo 30 min antes de nova recomputação da mesma rota. |

**Detalhamento**
- RN020: Dada rota com `monitorar = true` e nova leitura de nível chegando em estação do trecho, se `|nivel_atual − nivel_anterior| ≥ 30 cm`, então roda IDW novamente, revalida transitabilidade e recalcula a rota; se o traçado mudar, notifica o piloto. Exceção: variação < 30 cm não aciona recálculo; apenas atualiza o nível exibido.
- RN021: Toda recomputação automática da mesma rota registra `ultima_recomputacao`; novas variações só recalculam após 30 min. Exceção: variação ≥ 100 cm (evento extremo) ignora cooldown e recalcula imediatamente.

### 3.5 Entidade: Batimetria e Correnteza

| ID | Regra | Tipo | Descrição |
|----|-------|------|-----------|
| RN024 | Cota de fundo | Cálculo | `cota_fundo_batimetria` por aresta = IDW sobre os pontos batimétricos conhecidos. |
| RN025 | Correnteza derivada | Cálculo | `Velocidade_correnteza` por aresta é derivada da vazão e seção transversal: `V = Q / A`, onde `A` = largura × profundidade estimada. |
| RN028 | Vazão padrão | Validação | Aresta sem estação com vazão usa `Q` da estação influente mais próxima; se nenhuma, `V = 0` (sem correnteza). |

**Detalhamento**
- RN024: Para toda aresta com pontos batimétricos conhecidos no raio de 50 km, o IDW pondera os pontos por `1/d²`; resultado = cota de fundo da aresta. Exceção: sem pontos no raio → `cota_fundo = NULL` → aresta desconhecida (RN022).
- RN025: Toda aresta transitável ao calcular custo (RN011): `Velocidade_correnteza (m/s) = Vazão (m³/s) / Seção (m²)`; `Seção = Largura_do_canal × Profundidade_estimada`. Exceção: largura desconhecida → usa largura média do trecho (constante por segmento de rio).

### 3.6 Entidade: Sincronização

| ID | Regra | Tipo | Descrição |
|----|-------|------|-----------|
| RN016 | Snapshot offline | Fluxo | Snapshot local deve conter o grafo completo (nós/arestas com cota de fundo), níveis, profundidades e rotas da última sincronização. |
| RN017 | Merge sem perda | Fluxo | Push local nunca sobrescreve dados do servidor mais recentes; usa timestamp. |
| RN018 | Sincronização automática | Fluxo | Ao detectar conexão, dispara pull (dados) e push (logs/rotas locais). |
| RN026 | Cálculo offline | Fluxo | Offline recalcula rota localmente (A* embarcado) usando o grafo e profundidades do snapshot; nunca consulta o backend. |
| RN027 | Notificação em tempo real | Fluxo | Alterações de rotas monitoradas são entregues via WebSocket (ou SSE) apenas quando o app está online. |

**Detalhamento**
- RN016: Toda sincronização bem-sucedida grava no IndexedDB: grafo (nós, arestas, cota de fundo, largura), últimas profundidades, últimos níveis e rotas recentes. Exceção: grafo muito grande (> X MB) → baixa apenas o subgrafo do trecho ativo + rotas favoritas.
- RN026: Piloto solicita rota sem conexão; o front-end executa um A* local (JS) sobre o grafo do snapshot; usa calado e margem salvos, aplicando as mesmas RN010/RN011/RN022. Exceção: origem/destino fora do subgrafo local → erro "rota indisponível offline".
- RN027: Recomputação muda o traçado de uma rota monitorada (RN020); o backend publica evento no canal WebSocket do usuário; o app exibe toast e, se não houver conexão, aplica na próxima sincronização. Exceção: WebSocket indisponível (rede bloqueada) → fallback para polling de `GET /rotas/{id}/alteracoes` a cada 5 min.

---

## 4. Critérios de Aceite de Qualidade (ISO/IEC 25010)

| Característica | Estratégia de Avaliação | Critério de Aceitação |
|----------------|--------------------------|------------------------|
| Adequação Funcional | Testes de caixa-preta (pytest) para roteamento, interpolação e sincronização; testes de interface com Cypress (front-end) | 100% dos casos de uso executados com sucesso, incluindo offline e sincronização |
| Confiabilidade | Simulação de falhas de rede no front-end (offline) e no backend (APIs externas); verificação da recuperação | O aplicativo deve funcionar com dados locais por ≥ 24h; ao recuperar a rede, a sincronização deve ser completada sem perda de dados |
| Usabilidade | Teste com usuários reais (pilotos, operadores) utilizando o aplicativo em campo; coleta de feedback | Taxa de sucesso na primeira utilização ≥ 90%; tempo médio para encontrar uma rota ≤ 1 minuto |
| Eficiência de Desempenho | Medição do tempo de carregamento do mapa e da rota (Lighthouse); tempo de resposta do backend (cProfile) | Front-end: First Contentful Paint < 2s; Backend: rota em ≤ 5s para 10k nós |
| Manutenibilidade | Análise estática (Ruff/Pylint para Python, ESLint para Vue); cobertura de testes | Cobertura ≥ 80% para módulos críticos; baixa complexidade ciclomática |
| Portabilidade | Teste do PWA em diferentes navegadores e dispositivos; teste do app empacotado (Capacitor) em Android e iOS | O aplicativo deve funcionar em todas as plataformas alvo sem ajustes manuais |
| Segurança | Testes de autenticação, injeção de dados maliciosos (backend), verificação de criptografia local (front-end) | 100% dos endpoints protegidos; dados locais criptografados; vulnerabilidades críticas zeradas (Bandit/Safety) |
| Compatibilidade | Verificação da integração com PostGIS, APIs da ANA/CPRM e com os principais navegadores | Integração plena; front-end responsivo e consistente em todos os navegadores |
