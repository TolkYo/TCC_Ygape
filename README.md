# TCC Ygape

Cópia enxuta e operacional do projeto HidroWize/Ygape.

## Conteúdo incluído

- `backend/`: API FastAPI, motor de roteamento e rotinas de manutenção de dados.
- `frontend/prototipos/hidrowaze/`: interface web principal.
- `data/hidrowize.db`: base hidrográfica consolidada, utilizada em leitura pela API.
- `data/hidrowize_api.db`: base local de usuários e sessões.
- `docs/` e arquivos Markdown na raiz: planejamento, requisitos, arquitetura, diagramas e relatórios.

## Executar a API

No PowerShell:

```powershell
cd backend
pip install -r requirements.txt
$env:HIDROWIZE_TOKEN_SECRET = "defina-um-segredo-seguro"
uvicorn main:app --reload
```

A API estará disponível em `http://localhost:8000/api/v1/docs`.

Para criar o primeiro acesso administrativo:

```powershell
python criar_admin.py --nome "Administrador" --email admin@ygape.local
```

## Itens deliberadamente removidos

Ambientes locais, caches, tokens, logs, protótipos alternativos e fontes brutas regeneráveis (GeoPackages e dados satelitais). O banco consolidado já contém os dados necessários para a aplicação funcionar.
