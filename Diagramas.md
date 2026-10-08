# Modelagem do Sistema Ygapé

### 3.1. Fluxo de Cálculo de Rota

```mermaid
sequenceDiagram
    actor C as Comandante
    participant F as Frontend
    participant B as Backend (API + Motor)
    participant E as APIs Externas

    C->>F: Insere origem, destino e calado  
    F->>B: POST /calcular
    B->>E: Busca níveis e profundidades
    E-->>B: Retorna dados
    B->>B: Interpola profundidades + Executa A*
    B-->>F: Retorna GeoJSON da rota
    F-->>C: Exibe mapa e perfil
```

### 3.2. Fluxo de Geração de Relatório

```mermaid
sequenceDiagram
    actor C as Comandante
    participant F as Frontend
    participant B as Backend
    participant D as Banco de Dados

    C->>F: Clica em "Gerar Relatório"
    F->>B: GET /relatorio/{id}
    B->>D: Busca dados da rota e embarcação
    D-->>B: Retorna dados
    
    B->>B: Valida critérios legais
    alt Aprovado
        B->>B: Gera PDF + Calcula Hash
        B->>D: Salva Hash e status "Confirmada"
        B-->>F: PDF para download
        F-->>C: Inicia download
    else Reprovado
        B-->>F: Erro 422 com justificativa
        F-->>C: Exibe motivo
    end
```

### 3.3. Fluxo de Atualização Automática

```mermaid
sequenceDiagram
    participant S as Agendador (a cada 1h)
    participant E as APIs (ANA/CPRM)
    participant Sis as Sistema (BD + Grafos)
    actor C as Comandantes

    S->>E: Consulta dados em lote
    E-->>S: Retorna medições
    S->>Sis: Atualiza dados e recalcula grafo
    
    opt Trecho ficou intransitável
        Sis->>C: Envia alerta (Email/Push)
        Note over Sis,C: Rotas em navegação são <br>desviadas automaticamente
    end
```

### 5. Visão de Estados: Ciclo de Vida da Rota

```mermaid
stateDiagram-v2
    [*] --> Rascunho: Criada
    
    Rascunho --> Calculada: Rota viável
    Rascunho --> Arquivada: Inválida ou cancelada
    
    Calculada --> Confirmada: Aprovada legalmente
    Calculada --> Bloqueada: Atualização inviabilizou
    Calculada --> Rascunho: Usuário altera dados
    
    Confirmada --> Navegando: Iniciada
    Confirmada --> Bloqueada: Atualização inviabilizou
    
    Navegando --> Arquivada: Concluída ou interrompida
    Navegando --> Desviando: Alerta de bloqueio à frente
    Desviando --> Navegando: Desvio encontrado
    Desviando --> Arquivada: Sem desvio viável
    
    Bloqueada --> Arquivada
    Arquivada --> [*]
```

## 1. Diagrama de Classes

```mermaid
%%{init: { 'class': { 'minWidth': 250 } } }%%
classDiagram
    class Usuario {
        -int id
        -string nome
        -string email
        -string senha
        -string tipo
        -datetime dataCadastro
        +login()
        +logout()
        +atualizarPerfil()
    }
    
    class Embarcacao {
        -int id
        -string nome
        -double calado
        -double comprimento
        -double boca
        -string tipo
        -int usuarioId
        +getCaladoSeguro()
        +validarDimensoes()
        +atualizarCalado()
    }
    
    class Rota {
        -int id
        -int origemId
        -int destinoId
        -datetime dataCalculo
        -double distanciaTotal
        -double tempoEstimado
        -double custoTotal
        -string status
        +calcularCusto()
        +validarSeguranca()
        +gerarGeoJSON()
    }
    
    class NoHidrografico {
        -int id
        -double latitude
        -double longitude
        -double profundidadeEstimada
        -double profundidadeMinima
        -bool navegavel
        +calcularProfundidade()
        +verificarNavegabilidade()
    }
    
    class ArestaFluvial {
        -int id
        -int origemNoId
        -int destinoNoId
        -double distancia
        -double peso
        -double velocidadeCorrenteza
        -bool transitavel
        +calcularPesoDinamico()
        +verificarTransitabilidade()
    }
    
    class GrafoRotas {
        -List~NoHidrografico~ nos
        -List~ArestaFluvial~ arestas
        +adicionarNo()
        +adicionarAresta()
        +buscarRotaAEstrela()
        +atualizarPesos()
    }
    
    class AlgoritmoRoteamento {
        -GrafoRotas grafo
        +calcularRotaMinima()
        +aplicarIDW()
        +simplificarPolilinha()
    }
    
    class IDWInterpolador {
        -List~PontoMedicao~ pontos
        -double potencia
        +interpolar()
        +calcularDistancia()
        +buscarVizinhos()
    }
    
    class PontoMedicao {
        -int id
        -double latitude
        -double longitude
        -double profundidade
        -double nivelAgua
        -datetime dataMedicao
        +getValorInterpolado()
    }
    
    class DadosHidrologicos {
        -string estacao
        -double nivel
        -double vazao
        -double velocidade
        -datetime timestamp
        +carregarAPI_ANA()
        +carregarAPI_CPRM()
        +atualizarDados()
    }
    
    class RelatorioNavegacao {
        -int id
        -int rotaId
        -datetime dataEmissao
        -string validacaoLegal
        +gerarPDF()
        +validarANTAQ()
        +validarMarinha()
    }
    
    Usuario "1" --> "*" Embarcacao : possui
    Usuario "1" --> "*" Rota : planeja
    Rota "1" --> "2" NoHidrografico : conecta
    Rota "1" --> "1" RelatorioNavegacao : gera
    Rota "1" --> "1" Embarcacao : executada_por
    GrafoRotas "1" --> "*" NoHidrografico : contém
    GrafoRotas "1" --> "*" ArestaFluvial : contém
    AlgoritmoRoteamento "1" --> "1" GrafoRotas : utiliza
    AlgoritmoRoteamento "1" --> "1" IDWInterpolador : utiliza
    IDWInterpolador "1" --> "*" PontoMedicao : utiliza
    PontoMedicao "1" --> "*" DadosHidrologicos : baseadoEm
```

## 1. Diagrama de Sequência
```mermaid

sequenceDiagram
    participant Comandante
    participant FrontendWeb
    participant ServicoAPIRotas
    participant AlgoritmoRoteamento
    participant IDWInterpolador
    participant GrafoRotas
    participant API_ANA
    participant API_CPRM

    Comandante->>FrontendWeb: 1. Seleciona origem/destino + calado
    FrontendWeb->>ServicoAPIRotas: 2. POST /api/rota/calcular
    ServicoAPIRotas->>API_ANA: 3. GET (nível e vazão)
    ServicoAPIRotas->>API_CPRM: 4. GET (profundidade e correnteza)
    API_ANA-->>ServicoAPIRotas: 5. Dados brutos recebidos
    API_CPRM-->>ServicoAPIRotas: 6. Dados brutos recebidos
    ServicoAPIRotas->>IDWInterpolador: 7. interpolar(pontos)
    IDWInterpolador->>IDWInterpolador: 8. Calcula distâncias
    IDWInterpolador-->>ServicoAPIRotas: 9. Matriz de profundidades
    ServicoAPIRotas->>GrafoRotas: 10. atualizarPesos()
    GrafoRotas->>GrafoRotas: 11. Verifica transitabilidade
    GrafoRotas->>GrafoRotas: 12. Calcula peso dinâmico
    ServicoAPIRotas->>AlgoritmoRoteamento: 13. executarAEstrela()
    AlgoritmoRoteamento->>AlgoritmoRoteamento: 14. Busca caminho
    AlgoritmoRoteamento-->>ServicoAPIRotas: 15. Rota encontrada
    ServicoAPIRotas->>ServicoAPIRotas: 16. Monta GeoJSON
    ServicoAPIRotas-->>FrontendWeb: 17. 200 OK (GeoJSON)
    FrontendWeb->>FrontendWeb: 18. Renderiza mapa
    FrontendWeb-->>Comandante: 19. Exibe rota
```