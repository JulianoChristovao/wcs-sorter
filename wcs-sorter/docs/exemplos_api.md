# Exemplos de Chamadas à API

## 1. Autenticação (Interface)

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"Admin@123"}'
```

---

## 2. WMS → WCS: criar pedido

O WMS envia **uma** etiqueta de rastreio por pedido:

```bash
curl -X POST http://localhost:8000/api/v1/pedidos \
  -H "Content-Type: application/json" \
  -d '{
    "codigo_externo": "NF-111111111111111",
    "etiqueta": "FFFF45678",
    "rota_codigo": "SAO"
  }'
```

| Campo | Significado |
|-------|-------------|
| `codigo_externo` | ID no WMS (NF, pedido, etc.) |
| `etiqueta` | Única etiqueta de rastreio do volume |
| `rota_codigo` | Destino lógico (ex: SAO) |

---

## 3. Sorter → WCS: consultar (leitura de todos os códigos da caixa)

O sorter lê **todos** os códigos que encontrar na caixa e envia separados por `;`.
O WCS identifica qual deles é a etiqueta de rastreio conhecida.

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
```json
{
  "detail": "Múltiplos destinos encontrados nos códigos lidos: etiquetas=[...], rotas=[...]"
}
```

---

## 4. Sorter → WCS: confirmar separação

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
