# Arquitetura do WCS Sorter

## Visão Geral

O **WCS (Warehouse Control System)** atua como camada intermediária entre o **WMS** (Warehouse Management System) do cliente e o equipamento de automação (**Sorter**).

```
┌─────────────┐         REST API          ┌──────────────────────┐
│    WMS      │ ─────────────────────────► │                      │
│  (Cliente)  │ ◄───────────────────────── │   WCS (este sistema) │
└─────────────┘   Confirmação separação    │                      │
                                           │  ┌────────────────┐  │
                                           │  │  PostgreSQL    │  │
                                           │  └────────────────┘  │
                                           │                      │
┌─────────────┐   POST /consultar          │                      │
│   SORTER    │ ─────────────────────────► │                      │
│ (Automação) │ ◄───────────────────────── │                      │
│             │   { codigo, saida }        │                      │
│             │                            │                      │
│             │   POST /confirmar          │                      │
│             │ ─────────────────────────► │                      │
└─────────────┘                            └──────────────────────┘
```

## Camadas

| Camada              | Tecnologia              | Responsabilidade                                      |
|---------------------|-------------------------|-------------------------------------------------------|
| API REST            | FastAPI + Uvicorn       | Endpoints síncronos de baixa latência                 |
| Regras de negócio   | Services (Python)       | Decisão de roteamento, confirmação, notificação WMS |
| Persistência        | SQLAlchemy 2 + asyncpg  | Modelagem e acesso ao PostgreSQL                      |
| Banco de dados      | PostgreSQL 16           | Dados transacionais + JSONB                           |
| Autenticação        | JWT (python-jose)       | Controle de acesso por papéis (RBAC)                  |
| Integração WMS      | httpx (async)           | Webhook de confirmação                                |

## Fluxo Principal do Sorter

1. **Indução / Leitura**  
   O sorter lê todos os códigos de barras da caixa e envia:
   ```json
   { "etiqueta": "ABC1234;FFFF45678;123456789" }
   ```

2. **Consulta ao WCS** (`POST /api/v1/sorter/consultar`)  
   - O WCS busca nos pedidos pendentes qual código é conhecido.  
   - Resolve a **rota** do pedido (ex: `SAO`).  
   - Consulta o **mapeamento** rota → saída.  
   - Retorna:
     ```json
     { "codigo": "FFFF45678", "saida": 1 }
     ```

3. **Separação física**  
   O sorter desvia a caixa para a rampa indicada.

4. **Confirmação** (`POST /api/v1/sorter/confirmar`)  
   ```json
   {
     "codigo": "FFFF45678",
     "altura": 15.2,
     "largura": 21.5,
     "comprimento": 25.4,
     "peso": 2.23,
     "saida": 1
   }
   ```
   - Grava a confirmação com as medidas.  
   - Atualiza o status do pedido para `separado`.  
   - Dispara notificação assíncrona ao WMS.

## Papéis de Usuário (RBAC)

| Papel      | Permissões principais                                                                 |
|------------|----------------------------------------------------------------------------------------|
| **Admin**  | Acesso total: configurações, APIs, usuários, logs, mapeamento                         |
| **Gestor** | Gestão de usuários, dashboard, mapeamento, consulta de pedidos + tudo do Operador     |
| **Operador** | Ajuste de mapas (rota → saída), consulta de códigos pendentes e processados         |

## Mapeamento de Saídas

O gestor/operador configura:

1. Quantidade de saídas físicas do sorter (1–100).  
2. Cadastro de rotas (ex: SAO, CWB, RIO).  
3. Associação **Rota → Número da Saída** (com prioridade).

A interface deve apresentar um mapa intuitivo para facilitar a programação das rotas.

## Segurança

- Endpoints de interface protegidos por **JWT Bearer Token**.  
- Endpoints do sorter protegidos por **API Key** (`X-API-Key`).  
- Senhas armazenadas com **bcrypt**.  
- Logs de auditoria e de integração com o WMS.

## Escalabilidade e Boas Práticas

- Código tipado (Pydantic + type hints).  
- Separação clara de responsabilidades (routers → services → models).  
- Logs estruturados de todas as operações do sorter.  
- Schema PostgreSQL com índices nas colunas de busca frequente.  
- Pronto para containerização (Docker Compose).