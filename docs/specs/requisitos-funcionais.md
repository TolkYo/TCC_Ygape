# Requisitos Funcionais

## Modulos do Sistema

### Modulo: Autenticacao e Usuarios
**Descricao**: Registro, login e gestao de usuarios com papeis (admin/piloto).

| ID | Historia de Usuario | Prioridade | Dependencias |
|----|-------------------|------------|--------------|
| RF001 | Como piloto, quero fazer login para acessar o sistema | Alta | Nenhuma |
| RF002 | Como admin, quero cadastrar usuarios para conceder acesso a equipe | Alta | Nenhuma |
| RF003 | Como admin, quero listar/editar/desativar usuarios para controlar acesso | Media | RF002 |
| RF004 | Como piloto, quero atualizar meu perfil (nome, senha) | Baixa | RF001 |

**Criterios de Aceitacao**:
- [ ] Dado um usuario com credenciais validas, quando ele faz login, entao recebe um token JWT com papel correto
- [ ] Dado um admin logado, quando cadastra um piloto, entao o piloto consegue logar
- [ ] Dado um usuario desativado, quando tenta logar, entao recebe erro 401

### Modulo: Rede Hidrografica e Grafo
**Descricao**: Importacao e gestao do grafo de navegacao (nodos/arestas) a partir do shapefile ANA.

| ID | Historia de Usuario | Prioridade | Dependencias |
|----|-------------------|------------|--------------|
| RF005 | Como admin, quero importar o shapefile da rede hidrografica para popular o PostGIS | Alta | Nenhuma |
| RF033 | Como admin, quero importar os pontos batimetricos da area ativa (cota de fundo) | Alta | RF005 |
| RF006 | Como admin, quero reconstruir o grafo (NetworkX) para validar conectividade | Alta | RF005 |
| RF007 | Como admin, quero definir a bacia amazonica (priorizando a area brasileira) como area ativa do MVP | Alta | RF005 |
| RF008 | Como admin, quero listar nodos e arestas para auditar a malha | Media | RF006 |

**Criterios de Aceitacao**:
- [ ] Dado um shapefile valido, quando importado, entao a geometria aparece como LINESTRING no PostGIS
- [ ] Dado um grafo reconstruido, quando validado, entao todos os nodos do trecho estao conectados
- [ ] Dado o trecho definido, quando o roteador consulta, entao usa apenas nodos/arestas do trecho

### Modulo: Cotas e Niveis (Dados ANA)
**Descricao**: Coleta e armazenamento de niveis telemétricos das estacoes da area ativa.

| ID | Historia de Usuario | Prioridade | Dependencias |
|----|-------------------|------------|--------------|
| RF009 | Como sistema, quero coletar cotas das estacoes ANA da area ativa a cada 60 min | Alta | Nenhuma |
| RF010 | Como admin, quero forcar uma coleta manual para atualizar dados | Media | RF009 |
| RF011 | Como piloto, quero visualizar o nivel atual de uma estacao no mapa | Alta | RF009 |
| RF012 | Como sistema, quero armazenar minimos historicos por estacao para a regra de navegabilidade | Media | RF009 |

**Criterios de Aceitacao**:
- [ ] Dado um codigo de estacao valido, quando o coletor roda, entao grava nivel, chuva e vazao com timestamp
- [ ] Dado um endpoint de coleta manual, quando admin aciona, entao retorna o resumo da coleta
- [ ] Dado dados historicos, quando calculada a minima, entao a cota minima da estacao fica disponivel

### Modulo: Batimetria e Estimativa de Profundidade (IDW)
**Descricao**: Modelagem do fundo do rio e derivacao da profundidade por trecho.

| ID | Historia de Usuario | Prioridade | Dependencias |
|----|-------------------|------------|--------------|
| RF013 | Como admin, quero importar pontos batimetricos (cota de fundo) para basear a estimativa | Alta | RF005 |
| RF031 | Como sistema, quero interpolar a cota de fundo por aresta usando IDW (SciPy) sobre os pontos batimetricos | Alta | RF013 |
| RF014 | Como sistema, quero recalcular profundidades quando novos niveis chegam | Alta | RF031, RF009 |
| RF015 | Como admin, quero visualizar o mapa de profundidades estimadas | Media | RF014 |

**Criterios de Aceitacao**:
- [ ] Dado um conjunto de pontos batimetricos, quando o IDW roda, entao cada aresta ganha `cota_fundo_batimetria`
- [ ] Dada uma aresta com cota de fundo e nivel atual, quando calculada, entao a profundidade = nivel - cota_fundo
- [ ] Dado novos niveis, quando recalcula, entao a profundidade muda sem refazer o IDW (cota de fundo e estatica)
- [ ] Dada uma aresta sem pontos batimetricos no raio, quando processada, entao fica marcada como desconhecida

### Modulo: Motor de Roteamento
**Descricao**: Calculo da rota de menor tempo considerando calado, correnteza e profundidade.

| ID | Historia de Usuario | Prioridade | Dependencias |
|----|-------------------|------------|--------------|
| RF016 | Como piloto, quero calcular uma rota informando origem, destino, calado e velocidade da embarcacao | Alta | RF006, RF014 |
| RF017 | Como piloto, quero receber a rota em GeoJSON para exibir no mapa | Alta | RF016 |
| RF018 | Como sistema, quero marcar arestas intransitaveis (profundidade < calado) | Alta | RF014 |
| RF032 | Como sistema, quero derivar a velocidade da correnteza por aresta a partir da vazao e secao | Alta | RF014 |
| RF019 | Como sistema, quero aplicar o algoritmo A* minimizando o tempo total (custo = distancia / velocidade) | Alta | RF018, RF032 |
| RF020 | Como piloto, quero ver o resumo da rota (distancia, tempo estimado, trechos criticos) | Media | RF016 |

**Criterios de Aceitacao**:
- [ ] Dado origem e destino validos, quando calculado, entao retorna rota, distancia e tempo total
- [ ] Dado calado maior que profundidade de um trecho, quando calculado, entao o trecho e desviado
- [ ] Dado um trecho a favor da correnteza, quando o custo e calculado, entao o tempo e menor que contra a corrente
- [ ] Dado origem e destino desconectados, quando calculado, entao retorna erro 404 (rota nao encontrada)

### Modulo: Modo Offline e Sincronizacao
**Descricao**: Persistencia local (incluindo o grafo) e sincronizacao com o backend.

| ID | Historia de Usuario | Prioridade | Dependencias |
|----|-------------------|------------|--------------|
| RF021 | Como piloto, quero que o app armazene localmente a ultima rota, niveis e o grafo da area ativa | Alta | RF009, RF016 |
| RF022 | Como piloto, quero calcular rota offline recalculando localmente sobre o grafo do snapshot | Alta | RF021 |
| RF023 | Como sistema, quero sincronizar automaticamente ao voltar online (pull/push) | Alta | RF021 |
| RF024 | Como sistema, quero logar sucessos e falhas de sincronizacao | Media | RF023 |

**Criterios de Aceitacao**:
- [ ] Dado o app sem conexao, quando piloto calcula rota, entao o A* local recalcula sobre o grafo do snapshot
- [ ] Dado o snapshot completo, quando offline, entao o app recalcula com os mesmos resultados do backend (para mesmo grafo)
- [ ] Dado o app offline por 24h, quando consulta dados, entao mantem funcionalidade basica
- [ ] Dado retorno da conexao, quando online, entao o app sincroniza sem perder dados locais

### Modulo: Monitoramento de Rota (Nivel do Rio)
**Descricao**: Acompanhamento da rota ativa e recomputacao automatica quando o nivel do rio varia.

| ID | Historia de Usuario | Prioridade | Dependencias |
|----|-------------------|------------|--------------|
| RF027 | Como piloto, quero ativar o monitoramento de uma rota para ser avisado se ela mudar | Alta | RF016 |
| RF028 | Como sistema, quero recalcular automaticamente a rota monitorada quando o nivel variar >= 30 cm | Alta | RF014, RF027 |
| RF029 | Como piloto, quero receber notificacao em tempo real quando a rota monitorada mudar | Alta | RF028 |
| RF034 | Como sistema, quero manter um canal WebSocket/SSE por usuario para entrega de eventos | Alta | RF029 |
| RF030 | Como piloto, quero ver o historico de alteracoes de uma rota monitorada | Media | RF028 |

**Criterios de Aceitacao**:
- [ ] Dado uma rota com monitoramento ativo, quando nova leitura ANA chega, entao o sistema compara a variacao de nivel
- [ ] Dado variacao >= 30 cm em estacao do trecho, quando validada, entao a rota e recalculada e o piloto e notificado
- [ ] Dado o app online, quando o backend publica o evento, entao o WebSocket entrega em < 2s
- [ ] Dado o app offline, quando a rota muda, entao a notificacao e entregue na proxima sincronizacao
- [ ] Dado variacao < 30 cm, quando nova leitura chega, entao apenas o nivel e atualizado sem recalcular
- [ ] Dado recalculo com mudanca de tracado, quando concluido, entao o novo tracado fica disponivel e o antigo e versionado

### Modulo: Relatorios e Auditoria
**Descricao**: Historico de rotas e logs para auditoria.

| ID | Historia de Usuario | Prioridade | Dependencias |
|----|-------------------|------------|--------------|
| RF025 | Como piloto, quero ver o historico das minhas rotas calculadas | Media | RF016 |
| RF026 | Como admin, quero visualizar logs de coleta e sincronizacao | Baixa | RF024 |

**Criterios de Aceitacao**:
- [ ] Dado um piloto logado, quando abre historico, entao ve rotas com data, origem, destino e calado
- [ ] Dado um admin logado, quando abre logs, entao ve status e erros de coletas/sincronizacoes

### Modulo: Inteligencia de Dados (Satelite + ML)
**Descricao**: Aplicacao dos dados satelitais (altimetria, batimetria SICFLOW, vazao SWOT) e de modelos de Machine Learning para preencher lacunas de batimetria, nivel, vazao e navegabilidade.

| ID | Historia de Usuario | Prioridade | Dependencias |
|----|-------------------|------------|--------------|
| RF035 | Como sistema, quero estimar a cota de fundo dos trechos sem batimetria usando um modelo treinado com os nos do SICFLOW e os atributos AHGN | Alta | RF005, RF033 |
| RF036 | Como sistema, quero interpolar o nivel d'agua da bacia com ML (em substituicao ao IDW simples) usando as estacoes virtuais e as estacoes ANA | Media | RF009 |
| RF037 | Como sistema, quero estimar a vazao em trechos sem medicao a partir do nivel e da geometria do canal (rating curve) | Media | RF032 |
| RF038 | Como sistema, quero classificar a navegabilidade (navegavel/restrito/critico) com ML a partir de nivel, fundo, largura e vazao | Baixa | RF014, RF018 |
| RF039 | Como piloto, quero ver a previsao de nivel/vazao (cheia/estiagem) para planejar a navegacao | Baixa | RF009 |

**Criterios de Aceitacao**:
- [x] Dado os 1,3 mi nos do SICFLOW com cota de fundo, quando o modelo RF035 e treinado com os atributos AHGN, entao os trechos sem batimetria recebem cota de fundo estimada (implementado: `treinar_cota_fundo.py`, previsoes em `cota_fundo_trecho`)
- [x] Dada a validacao com separacao treino/teste por trecho ou periodo, quando avaliada, entao a metrica e registrada sem inflacao por leakage espacial/temporal (MAE 6,9 m vs baseline 8,6 m; viés zerado; ver `mapeamento_fontes.md` 12.3/12.4)
- [x] Dada a rede de estacoes virtuais e ANA, quando a interpolacao ML (RF036) roda, entao cada aresta recebe nivel estimado comparavel ou melhor que o IDW (implementado: `interpolar_nivel.py`; ML supera IDW em ~20-30% no regime esparso de ~75 reguas; ver `mapeamento_fontes.md` 12.5)
- [x] Dados nivel, largura, profundidade e declividade, quando a rating curve (RF037) roda, entao a vazao estimada e comparada a vazao observada (ANA/SWOT) (implementado: `rating_curve.py`; curva-chave e quase deterministica por estacao R2=1,0, mas a regionalizacao falha R2=0,04 → vazao vem da estacao influente; ver `mapeamento_fontes.md` 12.6)
- [x] Dadas as features de nivel, fundo, largura e vazao, quando o classificador (RF038) roda, entao retorna a classe de navegabilidade com metrica de acuracia/recall (implementado: `classificar_navegabilidade.py`; rotulos derivados da regra RF018 → ML nao supera a regra; ver `mapeamento_fontes.md` 12.7)
- [x] Dada a serie historica, quando a previsao (RF039) roda, entao gera previsao de cheia/estiagem com horizonte definido (implementado: `prever_nivel.py`; climatologia mensal captura o ciclo com MAE 1-2 m; ML sazonal nao supera; ver `mapeamento_fontes.md` 12.8)
- [x] Dado o calado de referencia (RF018) ainda indefinido, quando a classificacao (RF038) e treinada, entao as labels sao derivadas de decretos (Legisla.AM) e Defesa Civil, nao de limiar fixo (constatado: decretos municipais/mistos sao insuficientes como ground truth → RF038 bloqueado por falta de rotulo independente)
