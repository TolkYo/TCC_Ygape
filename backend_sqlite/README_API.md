# API HidroWize

Instale as dependências e inicie o servidor a partir da pasta `backend`:

```powershell
pip install -r requirements.txt
$env:HIDROWIZE_TOKEN_SECRET = "gere-um-segredo-longo"
python criar_admin.py --nome "Administrador" --email admin@hidrowize.local
uvicorn main:app --reload
```

A documentação interativa fica em `http://localhost:8000/api/v1/docs`.

O banco de dados hidrográfico é somente leitura (`data/hidrowize.db`). Usuários
da aplicação ficam em `data/hidrowize_api.db`; o comando `criar_admin.py` cria
ou atualiza o primeiro administrador. O motor monta em memória o grafo da
malha BHAE a partir de `trechos_navegaveis` e retorna GeoJSON para o menor
caminho navegável pelo calado informado. A primeira consulta pode levar mais
tempo enquanto a malha é carregada; as seguintes usam o grafo em cache.
