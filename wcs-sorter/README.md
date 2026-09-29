# WCS Sorter – Warehouse Control System

Sistema de Controle de Armazém (WCS) desenvolvido como Trabalho de Conclusão de Curso (TCC).

O WCS conecta a automação de **Sorter** logístico ao **WMS** do cliente, realizando:

- Recebimento de pedidos via API (JSON)
- Decisão de roteamento em tempo real para o sorter
- Confirmação de separação com dados aferidos (dimensões e peso)
- Notificação de conclusão ao WMS
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

Documentação completa da arquitetura: [`docs/arquitetura.md`](docs/arquitetura.md)

---

## Stack Tecnológica

| Camada          | Tecnologia                          |
|-----------------|-------------------------------------|
| Backend         | Python 3.12 + FastAPI               |
| ORM             | SQLAlchemy 2 (async) + asyncpg      |
| Banco de dados  | PostgreSQL 16                       |
| Autenticação    | JWT (python-jose) + bcrypt          |
| Validação       | Pydantic v2                         |
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

## Recebimento de Pedidos do WMS

```http
POST /api/v1/pedidos
Content-Type: application/json

{
  "codigo_externo": "PED-2026-001234",
  "codigo_principal": "FFFF45678",
  "rota_codigo": "SAO",
  "etiquetas": ["ABC1234", "FFFF45678", "123456789"],
  "prioridade": 3,
  "dados_extras": {
    "cliente": "Cliente XYZ",
    "transportadora": "Transp ABC"
  }
}
```

---

## Interface de Usuário – Papéis

| Funcionalidade                    | Admin | Gestor | Operador |
|-----------------------------------|:-----:|:------:|:--------:|
| Configurações gerais / APIs       |  ✓    |        |          |
| Gestão de usuários                |  ✓    |   ✓    |          |
| Dashboard (KPIs)                  |  ✓    |   ✓    |    ✓     |
| Configurar quantidade de saídas   |  ✓    |   ✓    |          |
| Mapear rota → saída               |  ✓    |   ✓    |    ✓     |
| Consultar pedidos pendentes/processados | ✓ | ✓ | ✓ |

---

## Estrutura do Projeto

```
wcs-sorter/
├── backend/
│   ├── app/
│   │   ├── core/           # Config, DB, Security
│   │   ├── models/         # SQLAlchemy models
│   │   ├── schemas/        # Pydantic schemas
│   │   ├── routers/        # Endpoints
│   │   ├── services/       # Regras de negócio
│   │   └── main.py
│   ├── requirements.txt
│   └── Dockerfile
├── database/
│   └── init.sql            # Schema + dados iniciais
├── docs/
│   └── arquitetura.md
├── docker-compose.yml
└── README.md
```

---

## Regras de Código Adotadas

- Tipagem estática com type hints
- Separação clara: Router → Service → Model
- Validação de entrada com Pydantic
- Logs de todas as operações do sorter e integração WMS
- Índices no banco nas colunas de busca frequente
- Uso de UUID para entidades principais
- Enums para status e papéis
- Configuração via variáveis de ambiente
- Código em português nas mensagens de negócio e documentação

---

## Frontend (Interface Web)

```bash
cd frontend
npm install
npm run dev
```

Abra **http://localhost:5173** (a API precisa estar rodando na porta 8000).

Login: `admin` / `Admin@123`

Telas: Dashboard, Pedidos, Mapeamento de rotas→saídas, Usuários.

---

## Próximos Passos Sugeridos (TCC)

1. Desenvolver a interface frontend (React + TypeScript + Tailwind)
2. Tela de mapa visual de saídas (drag-and-drop de rotas)
3. Dashboard com gráficos em tempo real
4. Testes automatizados (pytest + httpx)
5. CI/CD básico
6. Documentação de casos de uso e diagramas UML/BPMN

---

## Licença

Projeto acadêmico – uso livre para fins educacionais.


---

## Mapas (N configurações)

O WCS permite cadastrar **vários mapas** de roteamento (rota → saída).  
Apenas **um mapa habilitado (ONLINE)** direciona o sorter.

| Estado   | Efeito                                      |
|----------|---------------------------------------------|
| ONLINE   | Usado pelo sorter em `/sorter/consultar`    |
| OFFLINE  | Editável, sem efeito na operação do sorter  |

- **Gestor/Admin:** criar, habilitar e desabilitar mapas  
- **Admin:** excluir mapa (somente se estiver OFFLINE)

---

## Frontend

```bash
cd frontend
npm install
npm run dev
```

Acesse: **http://localhost:5173**

Login padrão: `admin` / `Admin@123`

### Dados de demonstração (opcional)

```bash
docker compose exec api python -m scripts.seed_demo
```

Cria mapa "Turno noite", mapeamentos alternativos e 3 pedidos de exemplo.
