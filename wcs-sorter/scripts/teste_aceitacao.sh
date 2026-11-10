#!/usr/bin/env bash
# =============================================================================
# Roteiro de testes de aceitação — WCS Sorter (TCC)
# =============================================================================
# Para a banca: cada passo imprime o que está sendo testado e o resultado
# esperado. [OK] = passou; [FALHA] = não passou.
#
# Pré-requisitos:
#   - API em http://localhost:8000 (docker compose up -d)
#   - Usuário admin semeado (docker compose exec api python -m scripts.seed_admin)
#   - API Key do sorter: sorter-api-key-change-me
#
# Comportamento: a cada execução cria e habilita um mapa novo (nome com
# timestamp). Pode ser rodado várias vezes seguidas.
#
# O que o roteiro cobre:
#   1  API no ar
#   2  Login admin (JWT)
#   3–6  Criar mapa, cadastrar sigla, mapear, habilitar (mapa ONLINE)
#   7  WMS cria pedido (status pendente)
#   7b Reenvio do mesmo codigo_externo atualiza uf sem trocar a sigla (HTTP 200)
#   8  Sorter consulta e recebe a saída mapeada
#   9  Código inexistente → 404
#   10 Sorter confirma a separação
#   10b Reenvio após separado → 409 (pedido não editável)
#   10c Admin exclui o pedido (force); logs de integração permanecem no banco
#   11 Dashboard de KPIs responde
# =============================================================================
set -euo pipefail

BASE="${WCS_BASE_URL:-http://localhost:8000}"
API="$BASE/api/v1"
SORTER_KEY="${SORTER_API_KEY:-sorter-api-key-change-me}"
PASS=0
FAIL=0

# Git Bash no Windows costuma ter só "python"; Linux/macOS usam "python3"
if command -v python3 >/dev/null 2>&1; then
  PY=python3
elif command -v python >/dev/null 2>&1; then
  PY=python
else
  echo "ERRO: python3 ou python não encontrado no PATH." >&2
  exit 1
fi

ok()  { echo "  [OK] $1"; PASS=$((PASS+1)); }
fail(){ echo "  [FALHA] $1"; FAIL=$((FAIL+1)); }

echo "=== WCS Sorter – Testes de Aceitação ==="
echo "API: $API"
echo

echo "1. Health check"
echo "   Testa: a API está no ar."
echo "   Esperado: GET /health responde 200."
if curl -sf "$BASE/health" >/dev/null; then ok "GET /health"; else fail "GET /health"; fi

echo "2. Autenticação admin"
echo "   Testa: login com admin / Admin@123 devolve JWT."
echo "   Esperado: access_token presente (sem token os passos seguintes falham)."
LOGIN=$(curl -sf -X POST "$API/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"Admin@123"}' || true)
TOKEN=$(echo "$LOGIN" | $PY -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))" 2>/dev/null || true)
if [ -n "$TOKEN" ]; then ok "POST /auth/login"; else fail "POST /auth/login"; fi
AUTH="Authorization: Bearer $TOKEN"

echo "3. Criar mapa"
echo "   Testa: admin cria um mapa novo (critério sigla, 8 saídas), ainda offline."
echo "   Esperado: HTTP 200/201 e um id de mapa."
MAPA_NOME="Mapa Teste Aceitacao $(date +%s)"
MAPA=$(curl -sf -X POST "$API/mapeamento/mapas" \
  -H "$AUTH" -H "Content-Type: application/json" \
  -d "{\"nome\":\"$MAPA_NOME\",\"quantidade_saidas\":8,\"criterio_roteamento\":\"sigla\",\"habilitado\":false}" || true)
MAPA_ID=$(echo "$MAPA" | $PY -c "import sys,json; print(json.load(sys.stdin).get('id',''))" 2>/dev/null || true)
if [ -n "$MAPA_ID" ]; then ok "POST /mapeamento/mapas id=$MAPA_ID"; else fail "POST /mapeamento/mapas"; fi

echo "4. Cadastro de sigla TST"
echo "   Testa: cadastrar a sigla TST no catálogo (necessária para mapear)."
echo "   Esperado: sigla criada ou já existente (não pode falhar o roteiro)."
curl -sf -X POST "$API/mapeamento/rotas" \
  -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"codigo":"TST","descricao":"Teste Aceitacao"}' >/dev/null 2>&1 || true
ok "POST /mapeamento/rotas (TST)"

echo "5. Mapear TST -> saída 2"
echo "   Testa: associar a sigla TST à saída física 2 neste mapa."
echo "   Esperado: mapeamento gravado com saida_numero = 2."
MAP=$(curl -sf -X POST "$API/mapeamento" \
  -H "$AUTH" -H "Content-Type: application/json" \
  -d "{\"mapa_id\":$MAPA_ID,\"valor\":\"TST\",\"saida_numero\":2}" || true)
if echo "$MAP" | grep -qE '"saida_numero": ?2'; then ok "POST /mapeamento TST->2"; else fail "POST /mapeamento"; fi

echo "6. Habilitar mapa"
echo "   Testa: marcar este mapa como ONLINE (só ele direciona o sorter)."
echo "   Esperado: mapa habilitado; os demais ficam offline."
curl -sf -X POST "$API/mapeamento/mapas/$MAPA_ID/habilitar" -H "$AUTH" >/dev/null \
  && ok "habilitar mapa" || fail "habilitar mapa"

echo "7. Receber pedido (WMS)"
echo "   Testa: POST /pedidos com codigo_externo, etiqueta e sigla TST."
echo "   Esperado: pedido criado com status pendente (HTTP 201)."
ETQ="ETQ$(date +%s)"
EXT="NF-TEST-$ETQ"
PED=$(curl -sf -X POST "$API/pedidos" \
  -H "Content-Type: application/json" \
  -d "{\"codigo_externo\":\"$EXT\",\"etiqueta\":\"$ETQ\",\"sigla\":\"TST\"}" || true)
STATUS=$(echo "$PED" | $PY -c "import sys,json; print(json.load(sys.stdin).get('status',''))" 2>/dev/null || true)
if [ "$STATUS" = "pendente" ]; then ok "POST /pedidos status=pendente"; else fail "POST /pedidos ($STATUS)"; fi

echo "7b. Idempotência do pedido ainda pendente"
echo "   Testa: reenviar o mesmo codigo_externo com sigla TST e uf SP."
echo "   Esperado: HTTP 200, sigla continua TST (roteável) e uf = SP."
echo "   Não troca a sigla: senão o passo 8 não acharia mapeamento."
PED2=$(curl -sf -w "\n%{http_code}" -X POST "$API/pedidos" \
  -H "Content-Type: application/json" \
  -d "{\"codigo_externo\":\"$EXT\",\"etiqueta\":\"$ETQ\",\"sigla\":\"TST\",\"uf\":\"SP\"}" || true)
CODE2=$(echo "$PED2" | tail -1)
BODY2=$(echo "$PED2" | head -n -1)
UF2=$(echo "$BODY2" | $PY -c "import sys,json; print(json.load(sys.stdin).get('uf',''))" 2>/dev/null || true)
SIGLA2=$(echo "$BODY2" | $PY -c "import sys,json; print(json.load(sys.stdin).get('sigla',''))" 2>/dev/null || true)
if [ "$CODE2" = "200" ] && [ "$UF2" = "SP" ] && [ "$SIGLA2" = "TST" ]; then
  ok "idempotência atualizou (200, sigla=TST, uf=SP)"
else
  fail "idempotência (code=$CODE2 sigla=$SIGLA2 uf=$UF2)"
fi

echo "8. Sorter consultar (sucesso)"
echo "   Testa: POST /sorter/consultar com vários códigos (só um é a etiqueta)."
echo "   Esperado: { codigo: a etiqueta, saida: 2 } — a saída do mapa ONLINE."
CONS=$(curl -sf -X POST "$API/sorter/consultar" \
  -H "X-API-Key: $SORTER_KEY" -H "Content-Type: application/json" \
  -d "{\"etiqueta\":\"XYZ;$ETQ;999\"}" || true)
COD=$(echo "$CONS" | $PY -c "import sys,json; print(json.load(sys.stdin).get('codigo',''))" 2>/dev/null || true)
SAI=$(echo "$CONS" | $PY -c "import sys,json; print(json.load(sys.stdin).get('saida',''))" 2>/dev/null || true)
if [ "$COD" = "$ETQ" ] && [ "$SAI" = "2" ]; then ok "consultar codigo=$COD saida=$SAI"; else fail "consultar ($CONS)"; fi

echo "9. Sorter consultar (código inexistente)"
echo "   Testa: consulta de um código que não está na base."
echo "   Esperado: HTTP 404 (erro de roteamento, não 200)."
CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$API/sorter/consultar" \
  -H "X-API-Key: $SORTER_KEY" -H "Content-Type: application/json" \
  -d '{"etiqueta":"CODIGO-QUE-NAO-EXISTE"}')
if [ "$CODE" = "404" ]; then ok "consultar inexistente -> 404"; else fail "esperava 404 obteve $CODE"; fi

echo "10. Sorter confirmar"
echo "   Testa: POST /sorter/confirmar com medidas e saída 2."
echo "   Esperado: confirmação aceita; pedido segue para separado/enviado_wms."
CONF=$(curl -sf -X POST "$API/sorter/confirmar" \
  -H "X-API-Key: $SORTER_KEY" -H "Content-Type: application/json" \
  -d "{\"codigo\":\"$ETQ\",\"altura\":10,\"largura\":20,\"comprimento\":30,\"peso\":1.5,\"saida\":2}" || true)
if [ -n "$CONF" ]; then ok "POST /sorter/confirmar"; else fail "confirmar"; fi

echo "10b. Reenvio após a separação"
echo "   Testa: reenviar o mesmo codigo_externo depois de confirmado."
echo "   Esperado: HTTP 409 (pedido não editável). O log tipo=rejeitado permanece."
CODE409=$(curl -s -o /tmp/wcs_409.json -w "%{http_code}" -X POST "$API/pedidos" \
  -H "Content-Type: application/json" \
  -d "{\"codigo_externo\":\"$EXT\",\"etiqueta\":\"$ETQ\",\"sigla\":\"FLN\"}")
if [ "$CODE409" = "409" ]; then ok "reenvio após separado → 409"; else fail "esperava 409 obteve $CODE409 ($(cat /tmp/wcs_409.json 2>/dev/null))"; fi

echo "10c. Excluir pedido já processado"
echo "   Testa: DELETE /pedidos/{id}?force=true com o token admin."
echo "   Esperado: HTTP 204. Pedido, etiquetas e confirmações saem;"
echo "             logs de integração ficam (pedido_id nulo no banco)."
PED_ID=$(echo "$PED" | $PY -c "import sys,json; print(json.load(sys.stdin).get('id',''))" 2>/dev/null || true)
if [ -z "$PED_ID" ]; then
  fail "sem id do pedido para excluir"
else
  CODEDEL=$(curl -s -o /tmp/wcs_del.json -w "%{http_code}" -X DELETE "$API/pedidos/$PED_ID?force=true" -H "$AUTH")
  if [ "$CODEDEL" = "204" ]; then ok "DELETE /pedidos/$PED_ID?force=true → 204"; else fail "DELETE pedido esperava 204 obteve $CODEDEL ($(cat /tmp/wcs_del.json 2>/dev/null))"; fi
fi

echo "11. Dashboard KPIs"
echo "   Testa: GET /dashboard/kpis com o token admin."
echo "   Esperado: JSON com consultas e taxa de sucesso."
KPI=$(curl -sf "$API/dashboard/kpis" -H "$AUTH" || true)
if echo "$KPI" | grep -qE "consultas_24h|taxa_sucesso"; then ok "GET /dashboard/kpis"; else fail "dashboard"; fi

echo
echo "=== Resultado: $PASS ok, $FAIL falha(s) ==="
[ "$FAIL" -eq 0 ] && exit 0 || exit 1
