# Visão Geral: RotaRios — Roteamento Fluvial Dinâmico do Amazonas

## Propósito

Sistema web responsivo (PWA/app híbrido) que calcula **rotas fluviais de menor tempo** nas hidrovias da bacia amazônica (prioridade para a área brasileira), considerando o **calado da embarcação**, a **velocidade própria da embarcação**,
a **correnteza** e a **cota atual dos rios** (seca/cheia). O sistema consome dados telemétricos da ANA
em tempo real, combina a **batimetria interpolada (IDW)** com o nível atual para estimar a profundidade
por trecho e retorna a rota de menor tempo. Funciona **offline** usando a última sincronização
armazenada no dispositivo, sendo direcionado a pilotos, operadores logísticos e instituições que
navegam no Amazonas.

## Pipeline de Cálculo (Profundidade → Custo)

```mermaid
graph LR
    B[Pontos batimetricos] -->|IDW| CF[Cota de fundo por aresta]
    E[Estacao influente RN023] -->|Nivel atual| P[Profundidade = nivel - cota fundo]
    CF --> P
    P --> T{Profundidade >= calado + margem?}
    T -->|Nao| I[Transitavel = FALSE]
    T -->|Sim| C[Transitavel = TRUE]
    V[Vazao / Secao] -->|V = Q/A| COR[Velocidade correnteza]
    C --> CUSTO[Tempo = Distancia / Vel. liquida]
    COR --> CUSTO
    CUSTO --> A[A* minimiza tempo total]
    I --> A


## Stack Definida

| Camada | Tecnologia | Justificativa |
|--------|-----------|---------------|
| Frontend | Vue.js 3 (Composition API) + Vite | SPA leve e reativa; ecossistema maduro |
| Mapa | Leaflet (MapLibre opcional) | Visualização cartográfica interativa leve |
| Backend | Python 3.10+ / FastAPI | Alta performance, tipagem, Swagger automático |
| Geoespacial | GeoPandas, Shapely, NetworkX, PostGIS | Grafo, IDW e operações espaciais nativas |
| Banco | PostgreSQL + PostGIS | Geometrias e consultas espaciais |
| Offline | PWA (Service Worker) + IndexedDB/Dexie.js | Cache e operação sem conexão |
| Empacotamento | Capacitor (Android/iOS) | Distribuição em lojas (opcional) |
| Auth | JWT (roles: admin, piloto) | Segurança de endpoints |
| Fontes de dados | API SOAP telemetria ANA + Shapefile ANA | Cotas em tempo real + rede hidrográfica |

## Diagrama de Arquitetura

```mermaid
graph TD
    subgraph Frontend
        A[Vue.js 3 PWA] --> M[Leaflet Map]
        A --> D[IndexedDB - Dexie.js]
    end
    A -->|HTTP/REST JSON| B[FastAPI]
    B -->|SQLAlchemy + GeoAlchemy2| C[(PostgreSQL + PostGIS)]
    B --> R[Motor de Roteamento]
    R --> G[GeoPandas + NetworkX]
    R --> I[Interpolação IDW]
    B -->|SOAP/XML| ANA[Telemetria ANA]
    B -->|Sincronização| D
```

## Estrutura de Pastas Prevista

```
/
├── backend/
│   ├── app/
│   │   ├── api/v1/          # Endpoints (rotas, niveis, auth, sync)
│   │   ├── core/            # Config, segurança, DB
│   │   ├── models/          # ORM (SQLAlchemy)
│   │   ├── schemas/         # Pydantic
│   │   ├── services/        # Roteador, IDW, coleta ANA
│   │   └── main.py
│   ├── scripts/             # Importação de shapefile, seed
│   └── tests/
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── views/
│   │   ├── stores/
│   │   ├── services/
│   │   └── db/              # Dexie.js
│   └── public/sw.js
├── docs/
│   └── specs/
├── data/                    # Shapefiles, estacoes_am.csv
└── .env.example
```

## Escopo do MVP

- **Área**: bacia amazônica completa (drenagem internacional), priorizando a área brasileira — hidrovias como Solimões/Amazonas e afluentes.
- **Usuários**: admin (gerencia dados) e piloto (consulta rotas).
- **Funcionalidades centrais**: cálculo de rota por calado, níveis em tempo real, modo offline e
  sincronização automática.
