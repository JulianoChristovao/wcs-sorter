# WCS Sorter — Funcionamento

Guia para instalar e testar em outro computador. Siga na ordem.

## 0. O que instalar antes

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) instalado e **em execução**
- [Node.js 18+](https://nodejs.org/) (só para a interface)
- Git Bash ou WSL, se for rodar o script `.sh` (o PowerShell puro não executa esse arquivo)

Não é preciso instalar Python nem PostgreSQL no Windows. Eles sobem dentro do Docker.

## 1. Entrar na pasta certa

Extraia o ZIP e entre na pasta que **contém** o arquivo `docker-compose.yml`.

```powershell
cd C:\caminho\wcs-sorter
dir
```

Tem que aparecer `docker-compose.yml`, `backend`, `frontend`, `database` e `scripts`.

Se o `dir` mostrar só outra pasta `wcs-sorter`, entre nela:

```powershell
cd wcs-sorter
dir
```

Todos os comandos abaixo partem dessa pasta.

## 2. Subir API e banco

```powershell
docker compose down -v
docker compose up --build -d
docker compose ps
```

Espere o `wcs_postgres` ficar **healthy** e o `wcs_api` **Up**. Se o `ps` ainda mostrar starting, espere uns 20 segundos e rode `docker compose ps` de novo.

## 3. Criar o admin

```powershell
docker compose exec api python -m scripts.seed_admin
```

Tem que aparecer `Usuário admin criado` ou `atualizado` e `Login: admin / Admin@123`.

O aviso do bcrypt (`__about__`) pode aparecer. Se o admin foi criado, ignore.

Login da interface: `admin` / `Admin@123`

## 4. Interface

Abra **outro** terminal, ainda na pasta do `docker-compose.yml`:

```powershell
cd frontend
Remove-Item -Recurse -Force node_modules -ErrorAction SilentlyContinue
Remove-Item -Force package-lock.json -ErrorAction SilentlyContinue
npm cache clean --force
npm install
npm run dev
```

Se ainda aparecer `Exit handler never called` (comum em pasta do OneDrive):

```powershell
npm install --no-audit --no-fund
```

Se continuar, copie a pasta do projeto para fora do OneDrive (por exemplo `C:\wcs-sorter`) e repita a partir do passo 1.

Deixe esse terminal aberto. A tela fica em http://localhost:5173/login

## 5. Endereços

| O quê | URL |
|-------|-----|
| Interface | http://localhost:5173/login |
| Swagger | http://localhost:8000/docs |
| Health | http://localhost:8000/health |

Confira o health no PowerShell:

```powershell
curl http://localhost:8000/health
```

## 6. Autenticação

### Interface (JWT)

Login na tela ou:

`POST http://localhost:8000/api/v1/auth/login`

```json
{ "username": "admin", "password": "Admin@123" }
```

Use o `access_token` como `Authorization: Bearer <token>` nas rotas da tela.

Usuário ou senha incorretos permanecem na tela de login. Não entram no sistema.

### Sorter (API Key)

Rotas `/api/v1/sorter/*` exigem o header `X-API-Key`. Não use o JWT nessas rotas.

Valor: `sorter-api-key-change-me`

**Swagger**

1. Abra http://localhost:8000/docs
2. Clique em **Authorize**
3. Em **X-API-Key**, cole exatamente:

```text
sorter-api-key-change-me
```

**SoapUI**

| Campo | Valor |
|-------|--------|
| Header | `X-API-Key` |
| Value | `sorter-api-key-change-me` |

## 7. Teste rápido do fluxo

### Pedido (WMS → WCS)

`POST http://localhost:8000/api/v1/pedidos` — sem JWT nesta versão.

Antes, na interface: crie um mapa por **sigla**, cadastre `SAO`, mapeie para a saída 1 e **habilite** o mapa.

```json
{
  "codigo_externo": "NF-111111111111111",
  "etiqueta": "FFFF45678",
  "sigla": "SAO"
}
```

Esperado: HTTP **201**, status `pendente`.

### Consultar (sorter)

`POST http://localhost:8000/api/v1/sorter/consultar`  
Header: `X-API-Key: sorter-api-key-change-me`

```json
{ "etiqueta": "ABC1234;FFFF45678;123456789" }
```

Esperado: `{ "codigo": "FFFF45678", "saida": 1 }`

Só consulta pedido ainda aberto (`pendente` ou `em_processamento`). Pedido `enviado_wms` devolve “etiqueta não conhecida”.

### Confirmar (sorter)

`POST http://localhost:8000/api/v1/sorter/confirmar`  
Mesmo header `X-API-Key`.

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

## 8. Script automático (Git Bash)

Na pasta do `docker-compose.yml`, no **Git Bash** (não no PowerShell):

```bash
bash scripts/teste_aceitacao.sh
```

O script escolhe sozinho um Python que funciona. No Windows, ignore o `python3` da Microsoft Store.

Esperado: **14 ok e 0 falhas**. Pode rodar de novo: cada execução cria um mapa novo.

Prova dos logs após a exclusão:

```powershell
docker compose exec db psql -U wcs_user -d wcs_db -c "SELECT tipo, pedido_id, sucesso FROM log_integracao_wms ORDER BY created_at DESC LIMIT 10;"
```

As linhas do pedido excluído continuam, com `pedido_id` vazio.

## 9. Webhook do WMS (opcional)

Vazio = notificação simulada e o pedido vai para `enviado_wms`.

Para uma tentativa real (mock no PC, porta 8089), na pasta do `docker-compose.yml`:

No **PowerShell**:

```powershell
$env:WMS_WEBHOOK_URL="http://host.docker.internal:8089/wms/separacao"
$env:WMS_API_KEY="wms-api-key-change-me"
docker compose up -d api
docker compose exec api env | findstr WMS
```

No **Git Bash** (não use `$env:`):

```bash
export WMS_WEBHOOK_URL="http://host.docker.internal:8089/wms/separacao"
export WMS_API_KEY="wms-api-key-change-me"
docker compose up -d api
docker compose exec api env | grep WMS
```

`WMS_API_KEY` é a chave que o **WCS envia ao WMS**. Não autentica o `POST /pedidos`.

No Docker Desktop, `host.docker.internal` aponta para o PC. No Linux, descomente `extra_hosts` no `docker-compose.yml`.

Para simular WMS fora do ar na apresentação:

PowerShell:

```powershell
$env:WMS_WEBHOOK_URL="http://host.docker.internal:9/wms"
docker compose up -d api
```

Git Bash:

```bash
export WMS_WEBHOOK_URL="http://host.docker.internal:9/wms"
docker compose up -d api
```

## 10. Se algo falhar

| Sintoma | O que fazer |
|---------|-------------|
| `no configuration file provided` | Você não está na pasta do `docker-compose.yml`. Veja o passo 1. |
| Porta 8000 ocupada | `netstat -ano \| findstr :8000` e encerre o processo, ou pare o compose antigo |
| Seed falha | Espere o `wcs_api` ficar Up e rode o seed de novo |
| Tela não abre | Confirme que o terminal do `npm run dev` continua aberto e use http://localhost:5173 |
| Consulta 404 com etiqueta que existe | O pedido já está `enviado_wms`. Crie um pedido novo ainda pendente e deixe o mapa ONLINE |
| Script falha no login | No Git Bash, use `python`, não `python3` (passo 8) |
