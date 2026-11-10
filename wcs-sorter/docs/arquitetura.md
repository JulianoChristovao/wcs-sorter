# Arquitetura do WCS Sorter

Documento resumido no repositório. A entrega acadêmica completa está na E2 (Arquitetura, Domínio e Dados).

## Visão geral

O **WCS (Warehouse Control System)** é a camada intermediária entre o WMS (origem dos pedidos) e o sorter (automação física). Não controla PLC nem substitui o WMS.

```
WMS  --POST /api/v1/pedidos-->  WCS  <--POST /api/v1/sorter/consultar--  Sorter
WMS  <--webhook confirmação--   WCS  <--POST /api/v1/sorter/confirmar--  Sorter
```

## Camadas e dependências

```
routers (FastAPI) --> services --> domain <-- infrastructure (memória / futuro SQL)
                                      ^
                    entidades, decidir_rota, porta PedidoRepository
                    (sem ORM, sem HTTP, sem Pydantic)
```

| Camada | Pacote | Responsabilidade |
|--------|--------|------------------|
| HTTP | `app/routers` | Validação de entrada, auth, status HTTP |
| Aplicação | `app/services` | Orquestra: DTO → persistência → domínio → logs / webhook |
| Domínio | `app/domain` | `Pedido`, `Mapa`, `Criterio`, `decidir_rota`, erros, porta `PedidoRepository` |
| Persistência | `app/models` + `app/infrastructure` | SQLAlchemy em `models`; adaptador em memória em `infrastructure/memory_repository.py` (testes). **Não há** repositório SQL da porta ainda: o `SorterService` consulta o banco e converte para entidades de domínio antes de `decidir_rota`. |
| Core | `app/core` | Sessão async, JWT, API Key, config |

## Domínio (implementado)

- `app/domain/entities.py` — Pedido, Mapa, Criterio, Decisao, `habilitar_mapa`
- `app/domain/routing.py` — `decidir_rota` / `consultar` (função pura)
- `app/domain/ports.py` — `PedidoRepository` (Protocol)
- `app/domain/errors.py` — erros de negócio
- Testes: `backend/tests/domain/test_routing.py` (9 testes; `pytest tests/domain -q`)

## Estados do pedido

Enum: `recebido`, `pendente`, `em_processamento`, `separado`, `enviado_wms`, `erro`, `cancelado`.

Fluxo principal: pedido criado pelo WMS entra como **`pendente`** (`WmsService.receber_pedido`) → `em_processamento` (após consulta) → `separado` (após confirmação) → `enviado_wms` (após notificação com sucesso).  
`recebido` existe no enum e é aceito na consulta do sorter junto com `pendente` e `em_processamento`.

## Modelo de dados (resumo)

- **Pedido**: codigo_principal, sigla, uf, filial, status
- **Mapa**: criterio_roteamento (sigla \| uf \| filial), habilitado, quantidade_saidas
- **MapeamentoRotaSaida**: UNIQUE (mapa_id, valor) → saida
- **ConfirmacaoSorter**: dimensões, peso, saída
- **Usuario**: roles admin \| gestor \| operador

Schema: `database/init.sql` (+ `migrate_*.sql`). Alembic no `requirements.txt`, **sem** pasta `alembic/` (planejado).

## Fluxo sorter

1. `POST /api/v1/sorter/consultar` com códigos separados por `;` (header `X-API-Key`)
2. Service carrega pedidos e mapa ONLINE, monta entidades de domínio, chama `decidir_rota`
3. Sucesso: `{ codigo, saida }`; conflito → 409; sem rota → 404
4. `POST /api/v1/sorter/confirmar` grava aferição e notifica WMS (log de cada tentativa)

## Segurança e papéis

| Ação | Papel mínimo | Onde |
|------|--------------|------|
| Login JWT | — | `POST /api/v1/auth/login` |
| Habilitar mapa ONLINE | operador | `POST /mapeamento/mapas/{id}/habilitar` |
| Criar/editar mapa, mapeamento, desabilitar, config saídas | gestor | routers/mapeamento |
| Excluir mapa OFFLINE | gestor/admin | `DELETE /mapeamento/mapas/{id}` |
| Excluir pedido (`?force=`) | admin | `DELETE /api/v1/pedidos/{id}` |
| Logs sorter / WMS | admin | `GET /api/v1/logs/...` |
| Sorter consultar/confirmar | API Key | header `X-API-Key` |
| Criar pedido (WMS) | **sem JWT** (protótipo) | `POST /api/v1/pedidos` |

## Desempenho (referência acadêmica)

Meta: consulta ≤ 1.000 ms (RNF-01); p95 ≤ 200 ms sob carga (RNF-07 / CA-09, Fase 5).  
Índices em etiqueta e mapeamento; ver Decisões Técnicas Fase 2.
