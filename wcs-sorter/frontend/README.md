# WCS Sorter — Frontend

Interface web do Warehouse Control System.

## Stack

- React 19 + TypeScript
- Vite 8
- Tailwind CSS 4
- React Router 7
- Axios

## Como rodar

### Pré-requisito
A API deve estar rodando em `http://localhost:8000` (`docker compose up -d` na raiz do projeto).

### Desenvolvimento

```bash
cd frontend
npm install
npm run dev
```

Abra: **http://localhost:5173**

O Vite faz proxy automático de `/api` → `http://localhost:8000`.

### Login padrão

- Usuário: `admin`
- Senha: `Admin@123`

## Telas

| Rota            | Descrição                                      | Papéis              |
|-----------------|------------------------------------------------|---------------------|
| `/login`        | Autenticação                                   | —                   |
| `/`             | Dashboard com KPIs                             | todos               |
| `/pedidos`      | Consulta e criação de pedidos (simular WMS)    | todos               |
| `/mapeamento`   | Mapa visual de saídas + configuração de rotas  | todos (config: gestor+) |
| `/usuarios`     | Gestão de usuários                             | admin, gestor       |

## Build de produção

```bash
npm run build
```

Arquivos gerados em `dist/`.
