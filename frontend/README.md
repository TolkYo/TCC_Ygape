# Ygapé — Web App (Vue 3 + Vite + TypeScript)

Frontend do sistema de roteamento fluvial dinâmico da bacia amazônica (TCC HidroWize).
Consome a API FastAPI em `backend/`.

## Requisitos

- Node.js 20+ e npm

## Desenvolvimento

```powershell
npm install
Copy-Item .env.example .env
npm run dev
```

O app sobe em `http://localhost:5173`. A URL da API é configurada por
`VITE_API_BASE_URL` no `.env` (padrão: `http://localhost:8000/api/v1`).

Subir a API antes (a partir de `backend/`, ver README da raiz):

```powershell
..\.venv\Scripts\python.exe -m uvicorn main:app --reload
```

## Scripts

| Comando                           | Descrição                             |
| --------------------------------- | ------------------------------------- |
| `npm run dev`                     | Servidor de desenvolvimento           |
| `npm run build`                   | Checagem de tipos + build de produção |
| `npm run preview`                 | Pré-visualiza o build                 |
| `npm run typecheck`               | Apenas checagem de tipos (`vue-tsc`)  |
| `npm run lint` / `lint:fix`       | ESLint                                |
| `npm run format` / `format:check` | Prettier                              |
| `npm run test` / `test:run`       | Vitest (watch / execução única)       |

## Estrutura

```text
frontend/
├── src/
│   ├── app/            # configuração e router
│   ├── components/ui/  # componentes base (Button, Badge)
│   ├── composables/    # useConnectivity
│   ├── layouts/        # AppLayout (cabeçalho, navegação, rodapé)
│   ├── services/       # cliente HTTP tipado e endpoints da API
│   ├── stores/         # Pinia: sessão e preferências de UI
│   ├── types/          # contratos TypeScript da API
│   └── views/          # telas (login, mapa, rota, histórico, configurações)
├── prototipos/         # protótipos estáticos anteriores (legado)
└── vite.config.ts
```

## Estado (Fase 0 — Fundação)

- [x] Vue 3 + TypeScript + Vite, router e Pinia
- [x] Tailwind CSS com tokens semânticos e temas claro/escuro/alto contraste
- [x] Cliente HTTP tipado e contratos da API
- [x] ESLint + Prettier + Vitest
- [ ] Mapa interativo (Fase 2)
- [ ] Planejamento de rota (Fase 3)
- [ ] Offline/PWA (Fase 5)
