# Roteiro da apresentação — WCS Sorter (12 minutos)

Antes de começar. API e banco no ar, admin criado, mapa ONLINE com siglas mapeadas, SoapUI aberto, interface logada em outra aba.

## 0. Preparação (antes da banca)

Siga `docs/funcionamento.md` do passo 0 ao 4. Resumo, na pasta do `docker-compose.yml`:

```powershell
docker compose down -v
docker compose up --build -d
docker compose ps
```

Espere `healthy` / `Up`. Depois:

```powershell
docker compose exec api python -m scripts.seed_admin
```

Outro terminal, mesma pasta:

```powershell
cd frontend
npm install
npm run dev
```

Endereços:

- Interface: http://localhost:5173/login
- Swagger: http://localhost:8000/docs
- Health: http://localhost:8000/health

Credenciais:

- Interface: `admin` / `Admin@123`
- Sorter (SoapUI / Swagger): header `X-API-Key` = `sorter-api-key-change-me`

Deixe pronto:

1. Mapa por **sigla**, 8 saídas, **ONLINE**.
2. Siglas cadastradas: `SAO` → saída 1 e `CWB` → saída 3.
3. Usuários `gestor` e `operador` criados (senha com 6+ caracteres).
4. SoapUI com as requisições abaixo.
5. Aba da interface já logada como admin.

Para a falha do WMS (slide do webhook), suba a API assim:

```powershell
$env:WMS_WEBHOOK_URL="http://host.docker.internal:9/wms"
docker compose up -d api
```

Porta 9 fechada = receptor fora do ar. Sem essa variável, a notificação é simulada e o pedido vai para `enviado_wms`.

## 1. Problema e objetivo (0–4 min)

Falar, sem demonstrar código:

- 5.000 volumes/hora, 10% de erro na separação manual, R$ 18 por ocorrência.
- A caixa tem vários códigos; só um é a etiqueta válida.
- Objetivo: decidir a etiqueta e a rampa em até 1.000 ms e registrar a confirmação.
- Fora do escopo: CLP, estoque/picking, app mobile, vários WMS, BI, reenvio automático.

## 2. Caminho feliz no SoapUI (6–8 min)

### 2.1 WMS envia o pedido

`POST http://localhost:8000/api/v1/pedidos`

```json
{
  "codigo_externo": "NF-DEMO-1",
  "etiqueta": "FFFF45678",
  "sigla": "SAO"
}
```

Esperado: HTTP **201**, status **pendente**.

Na tela Pedidos: a linha aparece como pendente.

### 2.2 Sorter consulta

Header: `X-API-Key: sorter-api-key-change-me`

`POST http://localhost:8000/api/v1/sorter/consultar`

```json
{ "etiqueta": "ABC1234;FFFF45678;123456789" }
```

Esperado:

```json
{ "codigo": "FFFF45678", "saida": 1 }
```

Na tela: status **em_processamento**.

### 2.3 Sorter confirma

`POST http://localhost:8000/api/v1/sorter/confirmar`

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

Esperado: HTTP 200. Na tela, altura/largura/comprimento/peso preenchidos.

- Com webhook vazio: status **enviado_wms** (notificação simulada).
- Com URL apontando para porta fechada: status **separado** e log `confirmacao_erro`.

## 3. Regras em ação

### 3.1 Conflito de destinos (RN-03)

Crie um segundo pedido:

```json
{
  "codigo_externo": "NF-DEMO-2",
  "etiqueta": "CCCC99999",
  "sigla": "CWB"
}
```

Consulte os dois códigos juntos:

```json
{ "etiqueta": "FFFF45678;CCCC99999" }
```

Só funciona se os dois pedidos ainda estiverem abertos (pendente ou em_processamento). Se o primeiro já foi confirmado, use duas etiquetas novas.

Esperado: HTTP **409**, sem saída. O volume iria para a rampa de exceção.

### 3.2 Remapeamento vale na hora (CA-06)

Na interface, como gestor ou admin, mude `SAO` da saída 1 para a saída 5. Sem reiniciar, consulte de novo um pedido novo com sigla SAO.

Esperado: `saida: 5`.

### 3.3 Papéis (CA-07)

- Entre como **operador**: consegue habilitar o mapa do turno. Não vê botões de criar mapa, mapear ou excluir.
- Entre como **gestor**: mapeia e exclui mapa OFFLINE. Não vê o menu Logs. Não desativa o admin.
- Entre como **admin**: vê Logs e exclui pedido.

## 4. Quando o WMS está fora (CA-05)

Com `WMS_WEBHOOK_URL` apontando para porta fechada, confirme um pedido.

Mostre:

- O sorter recebe 200 (a separação foi aceita).
- Na tela Pedidos: **separado**, ainda não enviado.
- Em Logs (admin): `confirmacao_erro`, `sucesso=false`, mensagem de conexão.

Não há reenvio automático. A falha fica no log.

## 5. Se sobrar tempo

Reenviar o mesmo `codigo_externo` depois de separado:

```json
{
  "codigo_externo": "NF-DEMO-1",
  "etiqueta": "FFFF45678",
  "sigla": "FLN"
}
```

Esperado: HTTP **409**. Em Logs: tipo `rejeitado`.

Script de reserva (Git Bash, na pasta do projeto):

```bash
bash scripts/teste_aceitacao.sh
```

Esperado: 14 ok e 0 falhas.

## 6. Fechamento

- Rota decidida em 32,6 ms com 10.000 pedidos (limite 1.000 ms).
- 40 de 40 testes aprovados (10 unidade, 14 sistema, 13 integração, 3 desempenho).
- Único requisito parcial: criação de pedido sem autenticação.
- Código: github.com/JulianoChristovao/wcs-sorter
