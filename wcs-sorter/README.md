# WCS Sorter – Warehouse Control System

Sistema de Controle de Armazém (WCS) desenvolvido como Trabalho de Conclusão de Curso (TCC).

O WCS conecta a automação de **Sorter** logístico ao **WMS** do cliente, realizando:

- Recebimento de pedidos via API (JSON)
- Decisão de roteamento em tempo real para o sorter (domínio puro + adaptadores)
- Confirmação de separação com dados aferidos (dimensões e peso)
- Notificação de conclusão ao WMS (webhook; cada tentativa em log)
- Interface de mapeamento de rotas → saídas
- Controle de acesso por papéis (Admin, Gestor, Operador)

---

## Arquitetura Rápida

```
WMS  ──(REST)──►  WCS (FastAPI + PostgreSQL)  ◄──(REST + API Key)──  Sorter
                      │
                      ▼
               Interface Web (RBAC)
```

Dependências: `routers → services → domain ← infrastructure`.  
O domínio (`app/domain`) não importa ORM nem HTTP. A decisão de roteamento é a função pura `decidir_rota`.

Documentação: [`docs/arquitetura.md`](docs/arquitetura.md) · [`docs/exemplos_api.md`](docs/exemplos_api.md)

---

## Stack Tecnológica

| Camada          | Tecnologia                          |
|-----------------|-------------------------------------|
| Backend         | Python 3.12 + FastAPI               |
| Domínio         | Pacote puro (sem SQLAlchemy/FastAPI)|
| ORM             | SQLAlchemy 2 (async) + asyncpg      |
| Banco de dados  | PostgreSQL 16                       |
| Autenticação    | JWT (python-jose) + bcrypt; sorter com API Key |
| Validação       | Pydantic v2                         |
| Testes domínio  | pytest                              |
| Containerização | Docker + Docker Compose             |

---

## Como Executar

### Pré-requisitos
- Docker e Docker Compose

### Subir o ambiente

```bash
cd wcs-sorter
docker compose up --build -d
```

Após os containers subirem, crie o usuário administrador:

```bash
docker compose exec api python -m scripts.seed_admin
```

A API estará disponível em: **http://localhost:8000**

- Documentação interativa (Swagger): http://localhost:8000/docs  
- ReDoc: http://localhost:8000/redoc  
- Health check: http://localhost:8000/health  

### Credenciais padrão

| Usuário | Senha      | Papel  |
|---------|------------|--------|
| admin   | Admin@123  | Admin  |

> **Importante:** Altere a senha e as chaves secretas em produção.

---

## APIs do Sorter (Machine-to-Machine)

Todas as rotas do sorter exigem o header:

```
X-API-Key: sorter-api-key-change-me
```

### 1. Consultar código e rampa

```http
POST /api/v1/sorter/consultar
Content-Type: application/json
X-API-Key: sorter-api-key-change-me

{
  "etiqueta": "ABC1234;FFFF45678;123456789"
}
```

**Resposta de sucesso:**
```json
{
  "codigo": "FFFF45678",
  "saida": 1
}
```

### 2. Confirmar separação

```http
POST /api/v1/sorter/confirmar
Content-Type: application/json
X-API-Key: sorter-api-key-change-me

{
  "codigo": "FFFF45678",
  "altura": 15.2,
  "largura": 21.5,
  "comprimento": 25.4,
  "peso": 2.23,
  "saida": 1
}
```

---

## Pedidos — reenvio por `codigo_externo`

`POST /api/v1/pedidos` é idempotente quando `codigo_externo` vem preenchido:

- Status `recebido` ou `pendente` → **HTTP 200** e atualização de `sigla`, `uf`, `filial`, `rota_codigo`, `dados_originais` e `prioridade`.
- Demais estados (`em_processamento`, `separado`, `enviado_wms`, `erro`, `cancelado`) → **HTTP 409** com o motivo (log `tipo=rejeitado` permanece gravado).
- Sem `codigo_externo` → sempre cria um novo pedido (**HTTP 201**).

```bash
curl -i -X POST http://localhost:8000/api/v1/pedidos \
  -H "Content-Type: application/json" \
  -d '{"codigo_externo":"NF-111","etiqueta":"FFFF45678","sigla":"SAO"}'
```

## Interface de Usuário – Papéis

Fonte: `backend/app/routers/*.py` e `frontend/src/components/Layout.tsx`.

| Funcionalidade | Admin | Gestor | Operador | Evidência |
|----------------|:-----:|:------:|:--------:|-----------|
| Gestão de usuários | ✓ | ✓ | | `routers/usuarios.py` → `require_gestor` |
| Dashboard (KPIs) | ✓ | ✓ | ✓ | `routers/dashboard.py` → `require_operador` |
| Configurar quantidade de saídas | ✓ | ✓ | | `PUT /mapeamento/config` → `require_gestor` |
| Criar/editar mapas e mapear valor → saída | ✓ | ✓ | | `POST/PATCH mapas`, `POST mapeamentos` → `require_gestor` |
| Habilitar (selecionar) o mapa em uso | ✓ | ✓ | ✓ | `POST .../habilitar` → `require_operador` |
| Desabilitar mapa | ✓ | ✓ | | `POST .../desabilitar` → `require_gestor` |
| Excluir mapa (somente OFFLINE) | ✓ | ✓ | | `DELETE /mapas/{id}` → `require_gestor` |
| Consultar pedidos pendentes/processados | ✓ | ✓ | ✓ | `GET /pedidos` → `require_operador` |
| Excluir pedido (`force=true` se processado) | ✓ | | | `DELETE /pedidos/{id}` → `require_admin` |
| Logs do sorter e do WMS | ✓ | | | `routers/logs.py` → `require_admin`; menu Logs só `admin` |

**Mapas (resumo):** gestor/admin criam, editam e desabilitam mapas; operador, gestor e admin **habilitam** (selecionam o mapa ONLINE); gestor e admin excluem mapa, e só se estiver OFFLINE.

---

## Estrutura do Projeto

```
wcs-sorter/
├── backend/
│   ├── app/
│   │   ├── core/              # Config, DB, Security (JWT, API Key)
│   │   ├── domain/            # Entidades, Criterio, decidir_rota, porta PedidoRepository (sem ORM)
│   │   ├── infrastructure/    # Adaptador em memória (MemoryPedidoRepository) para testes
│   │   ├── models/            # SQLAlchemy (PostgreSQL)
│   │   ├── schemas/           # Pydantic (HTTP)
│   │   ├── routers/           # Endpoints FastAPI
│   │   ├── services/          # Orquestração; SorterService delega a domain.decidir_rota
│   │   └── main.py
│   ├── tests/
│   │   └── domain/            # test_routing.py — regras sem banco
│   ├── scripts/
│   ├── requirements.txt
│   └── Dockerfile
├── database/
│   ├── init.sql               # Schema instalação limpa
│   └── migrate_*.sql          # Scripts pontuais (sem pasta alembic/)
├── docs/
│   ├── arquitetura.md
│   └── exemplos_api.md
├── frontend/                  # React + Vite
├── docker-compose.yml
└── README.md
```

Schema: criado por `database/init.sql` (+ scripts `migrate_*.sql`). Alembic consta no `requirements.txt`, mas **não há** pasta `alembic/` — migrações versionadas ainda planejadas.

---

## Testes

Regras de roteamento (domínio) sem PostgreSQL e sem container:

```bash
cd backend
pip install -r requirements.txt
PYTHONPATH=. pytest tests/domain -q
```

Saída esperada (executada neste ambiente):

```
.........                                                                [100%]
10 passed in ~2.5s
```

Os dez testes cobrem etiqueta válida, conflito de destinos, ausência de rota, remapeamento (mesmo objeto), unicidade de valor→saída, um mapa ONLINE, critério sigla/uf/filial, roteamento por UF e o repositório em memória.

---

## Frontend (Interface Web)

```bash
cd frontend
npm install
npm run dev
```

Abra **http://localhost:5173** (API na porta 8000).

Login: `admin` / `Admin@123`

Telas: Dashboard, Pedidos, Mapeamento, Logs (admin), Usuários (admin/gestor).

---

## Variáveis de ambiente relevantes

| Variável | Uso |
|----------|-----|
| `SORTER_API_KEY` | Header `X-API-Key` nas rotas do sorter |
| `WMS_WEBHOOK_URL` | URL do webhook de confirmação **WCS → WMS** (vazio = notificação simulada com sucesso). Repassada ao container via `docker-compose.yml`. |
| `WMS_API_KEY` | Chave que o **WCS envia ao WMS** no header `X-API-Key` do webhook. **Não** autentica o `POST /api/v1/pedidos`. |
| `WMS_TIMEOUT_SECONDS` | Timeout do webhook em segundos (padrão **10**, em `core/config.py`). |
| `SECRET_KEY` | Assinatura JWT |

Exemplo para apontar a um mock no host (SoapUI na porta 8089). No Docker Desktop, `host.docker.internal` resolve o host; no Linux descomente `extra_hosts` no compose.

```bash
WMS_WEBHOOK_URL=http://host.docker.internal:8089/wms/separacao WMS_API_KEY=wms-api-key-change-me docker compose up -d --build api
```

Excluir pedido (`DELETE /pedidos/{id}`): remove o pedido, as etiquetas e as confirmações. Os logs de integração **são mantidos** (`pedido_id` fica nulo por `ON DELETE SET NULL`).

---

## Código-fonte

https://github.com/JulianoChristovao/wcs-sorter
