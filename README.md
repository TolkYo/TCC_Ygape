# MOTO HELP — Sistema de Gestão Web para o Mercado de Serviços para Motociclistas em Manaus

Plataforma web interativa desenvolvida para auxiliar motociclistas, com sistema completo de
autenticação e gerenciamento de anúncios. Utiliza **Supabase** para autenticação e gerenciamento
de dados em tempo real.

- **Demonstração:** https://moto-help-1.onrender.com
- **Vídeo de apresentação:** https://www.youtube.com/watch?v=gtCFli9_CrI
- **Repositório:** https://github.com/GeorgeLucas1/MOTO-HELP

## Funcionalidades

- Cadastro e login de usuários com Supabase Auth
- Validação de e-mails e tratamento de erros
- Sistema de autenticação seguro
- Páginas dinâmicas e interativas
- Design responsivo com CSS personalizado
- Integração completa com Supabase (Authentication + Database)
- Gerenciamento de sessões de usuário
- Proteção de rotas autenticadas
- Chat-bot de atendimento
- Gerenciamento de anúncios

## Tecnologias Utilizadas

| Tecnologia | Descrição |
| --- | --- |
| HTML5 | Estrutura das páginas |
| CSS3 | Estilização e responsividade |
| JavaScript (ES6+) | Lógica e interatividade |
| Supabase | Backend as a Service (Authentication + Database) |

Distribuição das linguagens no repositório: JavaScript 41,6%, CSS 29,0%, HTML 21,3%, EJS 7,5%, Nix 0,6%.

## Capturas de Tela

- Tela Inicial
- Tela de Login e Tela de Cadastro
- Portal Principal e Menu de Navegação
- Chat-bot
- Gerenciar Anúncios

## Estrutura do Projeto

```text
MOTO-HELP/
├── public/
│   └── assets/              # Recursos estáticos (imagens, ícones)
├── home/
│   ├── index.html           # Página inicial
│   ├── script.js            # Scripts da página inicial
│   ├── styles.css           # Estilos da página inicial
│   └── gemini-config.js     # Configurações adicionais
├── login/
│   ├── index.html           # Página de login
│   ├── script.js            # Lógica de autenticação
│   └── styles.css           # Estilos da tela de login
├── config/                  # Configurações da aplicação
├── controllers/             # Controladores
├── models/                  # Modelos de dados
├── routes/                  # Gerenciamento de rotas
├── views/                   # Views adicionais
├── index.js                 # Entrada do servidor
├── package.json             # Dependências e scripts
├── GEMINI.md                # Instruções do workspace
├── .env                     # Variáveis de ambiente (não versionado)
└── README.md                # Este arquivo
```

## Pré-requisitos

- Navegador web moderno
- Conta no Supabase
- Editor de código (recomendado: VS Code)
- Node.js instalado (opcional, para servidor local)

## Configuração

1. Crie o projeto no [Supabase](https://supabase.com) e configure as tabelas necessárias no
   Supabase Dashboard.
2. Obtenha a URL do projeto e a chave anônima (anon key) em **Project Settings → API**.
3. Preencha o arquivo `.env` (não versionado) com as credenciais do Supabase.

## Como Executar o Projeto

### Opção 1: Diretamente no Navegador

```bash
# Clone o repositório
git clone https://github.com/GeorgeLucas1/MOTO-HELP

# Navegue até a pasta
cd moto-help

# Abra o arquivo index.html no navegador
```

### Opção 2: Com Servidor Local

```bash
# Clone o repositório
git clone https://github.com/GeorgeLucas1/MOTO-HELP

# Navegue até a pasta
cd moto-help

# Inicie um servidor local (Python)
python -m http.server 8000

# Ou usando Node.js com live-server
npx live-server
```

Acesse **http://localhost:8000** no navegador.

## Funcionalidades Detalhadas

### Autenticação

- Cadastro de novos usuários com validação de e-mail
- Login seguro com Supabase Auth
- Logout e gerenciamento de sessão
- Proteção de rotas autenticadas

### Anúncios

- Criação e gerenciamento de anúncios pelos usuários autenticados
- Integração com o banco de dados Supabase em tempo real

## Deploy

O projeto está publicado no Render em **https://moto-help-1.onrender.com**.

## Autor

George Lucas — [GitHub](https://github.com/GeorgeLucas1)
