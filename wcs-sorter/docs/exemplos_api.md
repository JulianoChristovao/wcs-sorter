# Exemplos de Chamadas à API

## 1. Autenticação (Interface)

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"Admin@123"}'
```

Use o `access_token` retornado como `Authorization: Bearer <token>` nas rotas da interface.

---

## 2. WMS → WCS: criar pedido

**Sem autenticação JWT** (entrada de integração no protótipo acadêmico).

O WMS envia **uma** etiqueta de rastreio por pedido. O pedido é gravado com status **`pendente`**.

```bash
curl -X POST http://localhost:8000/api/v1/pedidos \
  -H "Content-Type: application/json" \
  -d '{
    "codigo_externo": "NF-111111111111111",
    "etiqueta": "FFFF45678",
    "rota_codigo": "SAO",
    "sigla": "SAO",
    "uf": "SP"
  }'
```

| Campo | Significado |
|-------|-------------|
| `codigo_externo` | ID no WMS (NF, pedido, etc.) |
| `etiqueta` | Única etiqueta de rastreio do volume |
| `rota_codigo` / `sigla` / `uf` / `filial` | Destino conforme o critério do mapa ONLINE |

### Reenvio (idempotência por `codigo_externo`)

| Situação | HTTP | Efeito |
|----------|------|--------|
| Mesmo `codigo_externo` e status `recebido` ou `pendente` | **200** | Atualiza `sigla`, `uf`, `filial`, `rota_codigo`, `dados_originais` e `prioridade` |
| Mesmo `codigo_externo` e status `em_processamento`, `separado`, `enviado_wms`, `erro` ou `cancelado` | **409** | Rejeita; motivo em `detail` e em `log_integracao_wms` (`tipo=rejeitado`, `sucesso=false`) |
| Sem `codigo_externo` | **201** | Sempre cria um novo pedido |

```bash
# Primeiro envio → 201
curl -i -X POST http://localhost:8000/api/v1/pedidos \
  -H "Content-Type: application/json" \
  -d '{"codigo_externo":"NF-111","etiqueta":"FFFF45678","sigla":"SAO"}'

# Reenvio enquanto pendente → 200 (atualiza sigla)
curl -i -X POST http://localhost:8000/api/v1/pedidos \
  -H "Content-Type: application/json" \
  -d '{"codigo_externo":"NF-111","etiqueta":"FFFF45678","sigla":"CWB"}'

# Reenvio após separado/enviado_wms → 409
curl -i -X POST http://localhost:8000/api/v1/pedidos \
  -H "Content-Type: application/json" \
  -d '{"codigo_externo":"NF-111","etiqueta":"FFFF45678","sigla":"FLN"}'
```

---

## 3. Excluir pedido (RF-12) — somente admin

```bash
# Pendente: sem force
curl -X DELETE "http://localhost:8000/api/v1/pedidos/{id}" \
  -H "Authorization: Bearer <token-admin>"

# Já separado/enviado_wms: exige force=true
curl -X DELETE "http://localhost:8000/api/v1/pedidos/{id}?force=true" \
  -H "Authorization: Bearer <token-admin>"
```

Remove o pedido, as etiquetas e as confirmações. Os registros de `log_integracao_wms` **são mantidos** (`pedido_id` fica nulo por `ON DELETE SET NULL`).

---

## 4. Sorter → WCS: consultar

O sorter envia **todos** os códigos da caixa separados por `;`.  
O domínio (`decidir_rota`) identifica a etiqueta válida e a saída do mapa ONLINE.

```bash
curl -X POST http://localhost:8000/api/v1/sorter/consultar \
  -H "Content-Type: application/json" \
  -H "X-API-Key: sorter-api-key-change-me" \
  -d '{"etiqueta":"ABC1234;FFFF45678;123456789"}'
```

**Sucesso (1 etiqueta conhecida):**
```json
{ "codigo": "FFFF45678", "saida": 1 }
```

**Erro — nenhum código conhecido:** HTTP 404  

**Erro — múltiplos destinos:** HTTP 409

---

## 5. Sorter → WCS: confirmar separação

```bash
curl -X POST http://localhost:8000/api/v1/sorter/confirmar \
  -H "Content-Type: application/json" \
  -H "X-API-Key: sorter-api-key-change-me" \
  -d '{
    "codigo": "FFFF45678",
    "altura": 15.2,
    "largura": 21.5,
    "comprimento": 25.4,
    "peso": 2.23,
    "saida": 1
  }'
```

Após gravar a confirmação, o WCS tenta o webhook (`WMS_WEBHOOK_URL`). Cada tentativa é registrada em `log_integracao_wms`.  
Se a URL estiver vazia, a notificação é marcada como simulada com sucesso e o pedido pode ir para `enviado_wms`.

---

## 6. Habilitar mapa (operador, gestor ou admin)

```bash
curl -X POST http://localhost:8000/api/v1/mapeamento/mapas/1/habilitar \
  -H "Authorization: Bearer <token>"
```

Desabilita os demais mapas na mesma operação. Apenas **gestor/admin** desabilitam explicitamente; gestor e admin excluem mapa OFFLINE.
