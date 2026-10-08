# Regras de Negocio

## Entidade: Usuario

| ID | Regra | Tipo | Descricao |
|----|-------|------|-----------|
| RN001 | Papel obrigatorio | Validacao | Todo usuario deve ter papel `admin` ou `piloto`. |
| RN002 | Email unico | Validacao | Nao pode haver dois usuarios com o mesmo email. |
| RN003 | Senha forte | Validacao | Senha minima de 8 caracteres com letras e numeros. |
| RN004 | Auto-registro bloqueado | Fluxo | Registro publico nao permitido; apenas admin cria usuarios. |
| RN005 | Token JWT | Seguranca | Token expira em 8h; logout invalida sessao no cliente. |

### Detalhamento

**RN004 - Auto-registro bloqueado**
- **Condicao**: Qualquer requisicao `POST /auth/register` sem papel de admin
- **Comportamento**: Retorna 403; apenas admin autenticado cria usuarios
- **Excecao**: Seed inicial cria o primeiro admin via script

## Entidade: Estacao

| ID | Regra | Tipo | Descricao |
|----|-------|------|-----------|
| RN006 | Codigo unico | Validacao | `codigo_estacao` e unico (identificador ANA). |
| RN007 | Coleta padronizada | Validacao | Registro de nivel exige `codigo_estacao`, `data_hora` e `nivel_cm` nao nulos. |
| RN008 | Formato de dados | Validacao | Datas no formato `dd/MM/yyyy` na entrada da API ANA; armazenar UTC. |

### Detalhamento

**RN007 - Coleta padronizada**
- **Condicao**: Cada leitura vinda da telemetria ANA
- **Comportamento**: Grava `nivel_cm`, `chuva_mm`, `vazao` e timestamp; nulos viram NULL
- **Excecao**: Se `nivel` ausente, nao grava; registra falha no log de coleta

## Entidade: Rota

| ID | Regra | Tipo | Descricao |
|----|-------|------|-----------|
| RN009 | Calado obrigatorio | Validacao | Rota exige `calado_m` > 0; maximo 20 m. |
| RN010 | Transitabilidade | Calculo | Aresta intransitavel se `profundidade_estimada < calado`. |
| RN011 | Custo da aresta (tempo) | Calculo | `Custo (h) = Distancia_km / Velocidade_liquida_kmh`. |
| RN012 | Cota limite | Calculo | Aresta transitavel exige margem minima de 0.5 m sobre o calado. |
| RN022 | Profundidade da aresta | Calculo | `profundidade = cota_nivel_atual - cota_fundo_batimetria` (nao e interpolado diretamente). |
| RN023 | Estacao influente | Calculo | Aresta usa o nivel da estacao mais proxima ao longo da rede (raio de 50 km). |
| RN029 | Calado de referencia | Parametro | Calado de projeto do DNIT/ANTAQ por tramo (ver detalhamento). |

### Detalhamento

**RN010 - Transitabilidade**
- **Condicao**: No calculo da rota, para cada aresta
- **Comportamento**: Se `profundidade < calado`, peso = infinito (aresta removida do A*)
- **Excecao**: Sem aresta viavel → erro 404 "rota nao encontrada"

**RN011 - Custo da aresta (tempo)**
- **Condicao**: Sempre que se calcula o peso de uma aresta
- **Comportamento**: `Velocidade_liquida = Velocidade_embarcacao + Velocidade_correnteza`
  - `Velocidade_correnteza > 0` quando a navegacao e a favor da corrente (descendo o rio)
  - `Velocidade_correnteza < 0` quando contra a corrente (subindo o rio)
  - `Custo (h) = Distancia_km / Velocidade_liquida_kmh`
- **Excecao**: Se `Velocidade_liquida <= 0`, peso = infinito (trecho nao percorrivel)

**RN012 - Cota limite (margem de seguranca)**
- **Condicao**: Sempre que for calcular transitabilidade
- **Comportamento**: Considera navegavel apenas se `profundidade >= calado + 0.5m`
- **Excecao**: Piloto pode optar por "modo arriscado" desativando a margem (preferencia do perfil)

**RN022 - Profundidade da aresta (batimetria + nivel)**
- **Condicao**: Toda vez que se estima a profundidade de uma aresta
- **Comportamento**: IDW interpola a **cota do fundo do rio** a partir dos pontos batimetricos (RF013);
  a **cota do nivel** da aresta vem da estacao influente (RN023);
  `profundidade = cota_nivel_atual - cota_fundo_batimetria`
- **Excecao**: Aresta sem cota de fundo (sem pontos batimetricos no raio) → `profundidade = NULL`
  e a aresta e tratada como **desconhecida** (exige revisao manual)

**RN023 - Estacao influente**
- **Condicao**: Para associar nivel a uma aresta
- **Comportamento**: Seleciona a estacao com menor distancia ao longo da rede hidrografica
  (nao distancia euclidiana) dentro de um raio de 50 km; se nenhuma, aresta fica sem nivel
- **Excecao**: Estacao fora do raio → `profundidade = NULL` (aresta desconhecida)

**RN029 - Calado de referencia (tramo DNIT/ANTAQ)**
- **Condicao**: Parametrizar a navegabilidade por tramo da hidrovia (fonte: DNIT/ANTAQ)
- **Comportamento**: calado de projeto por tramo:
  - Amazonas (Manaus–Belém, ~1.650 km): **10 m** (navios marítimos até 60.000 TPB)
  - Solimões (Tabatinga–Manaus, ~1.600 km): **6 m** (mínimo; com pontos críticos na seca)
  - Madeira (Porto Velho–Itacoatiara, ~1.450 km): **>13 m na cheia** (navios oceânicos até
    Porto Velho); na seca forma praias e restringe a navegação de grande porte
  - Negro (Porto de Manaus): recebe navios de qualquer calado mesmo nas vazantes
- **Excecao**: o calado efetivo de cada rota é o `calado_m` informado pelo piloto (RN009);
  o calado de referência é o teto de navegabilidade do tramo, não um limite fixo por rota

## Entidade: Nivel

| ID | Regra | Tipo | Descricao |
|----|-------|------|-----------|
| RN013 | Serie temporal | Calculo | Cota minima historica = menor `nivel_cm` do periodo disponivel da estacao. |
| RN014 | Deduplicacao | Validacao | Uma leitura por `(codigo_estacao, data_hora)` — upsert. |
| RN015 | Janela de consulta | Validacao | `data_fim >= data_inicio`; intervalo maximo de 90 dias por requisicao. |
| RN019 | Limiar de variacao | Calculo | Variacao de nivel calculada por estacao como `|nivel_atual - nivel_anterior|` na janela monitorada. |
| RN020 | Recomputacao automatica | Fluxo | Rota em monitoramento e recalculada se variacao >= 30 cm em estacao influente do trecho. |
| RN021 | Cooldown de recalculo | Fluxo | Apos recomputar, aguardar no minimo 30 min antes de nova recomputacao da mesma rota. |

### Detalhamento

**RN020 - Recomputacao automatica**
- **Condicao**: Rota com `monitorar = true` e nova leitura de nivel chegando em estacao do trecho
- **Comportamento**: Se `|nivel_atual - nivel_anterior| >= 30 cm`, roda IDW novamente, revalida transitabilidade e recalcula a rota; se o tracado mudar, notifica o piloto
- **Excecao**: Variacao < 30 cm nao aciona recalculo; apenas atualiza o nivel exibido

**RN021 - Cooldown de recalculo**
- **Condicao**: Toda recomputacao automatica da mesma rota
- **Comportamento**: Registra `ultima_recomputacao`; novas variacoes so recalcular apos 30 min
- **Excecao**: Variacao >= 100 cm (evento extremo) ignora cooldown e recalcula imediatamente

## Entidade: Batimetria e Correnteza

| ID | Regra | Tipo | Descricao |
|----|-------|------|-----------|
| RN024 | Cota de fundo | Calculo | `cota_fundo_batimetria` por aresta = IDW sobre os pontos batimetricos conhecidos. |
| RN025 | Correnteza derivada | Calculo | `Velocidade_correnteza` por aresta e derivada da vazao e secao transversal: `V = Q / A`, onde `A` = largura x profundidade estimada. |
| RN028 | Vazao padrao | Validacao | Aresta sem estacao com vazao usa `Q` da estacao influente mais proxima; se nenhuma, `V = 0` (sem correnteza). |

### Detalhamento

**RN024 - Cota de fundo (batimetria)**
- **Condicao**: Para toda aresta com pontos batimetricos conhecidos no raio de 50 km
- **Comportamento**: IDW pondera os pontos por `1/d^2`; resultado = cota de fundo da aresta
- **Excecao**: Sem pontos no raio → `cota_fundo = NULL` → aresta desconhecida (RN022)

**RN025 - Correnteza derivada**
- **Condicao**: Toda aresta transitavel ao calcular custo (RN011)
- **Comportamento**: `Velocidade_correnteza (m/s) = Vazao (m3/s) / Secao (m2)`;
  `Secao = Largura_do_canal x Profundidade_estimada`
- **Excecao**: Largura desconhecida → usa largura media do trecho (constante por segmento de rio)

## Entidade: Sincronizacao

| ID | Regra | Tipo | Descricao |
|----|-------|------|-----------|
| RN016 | Snapshot offline | Fluxo | Snapshot local deve conter o **grafo completo** (nos/arestas com cota de fundo), niveis, profundidades e rotas da ultima sincronizacao. |
| RN017 | Merge sem perda | Fluxo | Push local nunca sobrescreve dados do servidor mais recentes; usa timestamp. |
| RN018 | Sincronizacao automatica | Fluxo | Ao detectar conexao, dispara pull (dados) e push (logs/rotas locais). |
| RN026 | Calculo offline | Fluxo | Offline recalcula rota localmente (A* embarcado) usando o grafo e profundidades do snapshot; nunca consulta o backend. |
| RN027 | Notificacao em tempo real | Fluxo | Alteracoes de rotas monitoradas sao entregues via WebSocket (ou SSE) apenas quando o app esta online. |

### Detalhamento

**RN016 - Snapshot offline (com grafo)**
- **Condicao**: Toda sincronizacao bem-sucedida
- **Comportamento**: Grava no IndexedDB: grafo (nos, arestas, cota de fundo, largura), ultimas profundidades, ultimos niveis e rotas recentes
- **Excecao**: Grafo muito grande (> X MB) → baixa apenas o subgrafo do trecho ativo + rotas favoritas

**RN026 - Calculo offline**
- **Condicao**: Piloto solicita rota sem conexao
- **Comportamento**: O front-end executa um A* local (JS) sobre o grafo do snapshot; usa calado e margem salvos, aplicando as mesmas RN010/RN011/RN022
- **Excecao**: Origem/destino fora do subgrafo local → erro "rota indisponivel offline"

**RN027 - Notificacao em tempo real**
- **Condicao**: Recomputacao muda o tracado de uma rota monitorada (RN020)
- **Comportamento**: Backend publica evento no canal WebSocket do usuario; app exibe toast e, se nao houver conexao, aplica na proxima sincronizacao
- **Excecao**: WebSocket indisponivel (rede bloqueada) → fallback para polling de `GET /rotas/{id}/alteracoes` a cada 5 min
