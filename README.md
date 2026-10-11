# TCC Ygape

Cópia enxuta e operacional do projeto HidroWize/Ygape.

## Conteúdo incluído

- `backend/`: API FastAPI, motor de roteamento e rotinas de manutenção de dados.
- `frontend/`: web app Vue 3 + Vite + TypeScript (aplicação principal).
- `frontend/prototipos/hidrowaze/`: protótipos estáticos anteriores (legado).
- `data/hidrowize.db`: base hidrográfica consolidada gerada pela coleta; espelhada no PostGIS pelo ETL.
- `data/hidrowize_api.db`: base SQLite legada de usuários/rotas (a aplicação agora usa o Postgres).
- `docs/` e arquivos Markdown na raiz: planejamento, requisitos, arquitetura, diagramas e relatórios.

## Preparar o ambiente e executar a API

Crie o ambiente virtual e instale as dependências, na raiz do repositório (PowerShell):

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
Copy-Item .env.example .env
```

Gere um segredo e preencha `HIDROWIZE_TOKEN_SECRET` no `.env`:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Crie o primeiro acesso administrativo e suba a API, a partir de `backend`:

```powershell
cd backend
..\.venv\Scripts\python.exe criar_admin.py --nome "Administrador" --email admin@ygape.local
..\.venv\Scripts\python.exe -m uvicorn main:app --reload
```

A API estará disponível em `http://localhost:8000/api/v1/docs`. O backend carrega o `.env`
da raiz (segredo JWT, CORS, tempo de vida do token e caminhos dos bancos).

## Executar o frontend

Com a API no ar, em outro terminal:

```powershell
cd frontend
npm install
Copy-Item .env.example .env   # ajuste VITE_API_BASE_URL se necessário
npm run dev                   # http://localhost:5173
```

Comandos úteis: `npm run build`, `npm run typecheck`, `npm run lint`, `npm run test:run`.

## Banco (PostgreSQL + PostGIS)

O backend usa **PostgreSQL/PostGIS** (container Docker `ygape-db` na VPS). Os dados hidrográficos
(estações, trechos, telemetria, satélite) e os dados da aplicação (usuários, rotas, logs) ficam no
mesmo banco `ygape`, alimentado pelo ETL `backend/carregar_postgis.py` a partir do `data/hidrowize.db`
(que continua sendo o armazenamento da coleta).

O banco fica exposto apenas em `127.0.0.1:5432` na VPS (não público). As credenciais estão nas chaves
`HIDROWIZE_PG_*` do `.env` (não versionado).

Para rodar a API localmente, abra um túnel SSH para o banco da VPS (o IP está no `.env`):

```powershell
ssh -L 5432:127.0.0.1:5432 root@<IP_DA_VPS>
```

> Diferente de versões anteriores, a API **não lê mais SQLite** — `data/hidrowize.db` é usado apenas
> pelos coletores e pelo ETL. As tabelas grandes de satélite/batimetria só entram no PostGIS com
> `python backend/carregar_postgis.py --todas`.

## Itens deliberadamente removidos

Ambientes locais, caches, tokens, logs, protótipos alternativos e fontes brutas regeneráveis (GeoPackages e dados satelitais). O banco consolidado já contém os dados necessários para a aplicação funcionar.
