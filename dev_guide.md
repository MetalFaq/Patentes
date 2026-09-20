<!-- NOTA: Guia rapida para desarrolladores con comandos utiles del proyecto. -->
# Developer Guide

Guia rapida para programadores que trabajan sobre `Patentes`.
Los comandos estan pensados para PowerShell y asumen este directorio:

```powershell
cd patentes_agent
```

Para la version extendida y con contexto operativo, ver tambien:
- `doc/COMANDOS_OPERATIVOS_Y_TROUBLESHOOTING.md`

## Que le falta a un desarrollador despues de hacer `pull`

El repositorio queda utilizable a nivel de codigo y documentacion, pero no queda
operativo al 100%. Para correr el proyecto completo faltan estos insumos
sensibles o locales:

- `.env` real, o al menos estos secretos:
  - `GOOGLE_API_KEY`
  - `WEBEX_BOT_TOKEN`
  - `WEBEX_WEBHOOK_SECRET`
  - `SHAREPOINT_CERT_PFX_PASSWORD`
- certificado SharePoint:
  - `.\Certificado\agente_patentes_cert.pfx`
- opcionalmente, artefactos runtime ya generados:
  - `data/index/patentes.sqlite`
  - `data/sharepoint_cache/*`
  - `data/webex_adapter/webex_events.sqlite`
  - `data/session_store.json`
  - `data/conversations.jsonl`

Sin esos elementos:
- el backend no puede hablar con Gemini
- SharePoint no puede autenticarse
- Webex no puede operar con el bot real
- el indice local debe reconstruirse desde cero

Referencia rapida:
- `.env.example` define la estructura completa esperada
- el archivo `.env` real y el `.pfx` deben entregarse por canal seguro

## Entorno

Activar el entorno virtual:

```powershell
.venv\Scripts\Activate.ps1
```

Reinstalar el proyecto:

```powershell
python -m pip install -e .
```

Ver dependencias clave:

```powershell
python -m pip show patentes-agent
python -m pip show msal
python -m pip show pypdf
```

## Configuracion

Ver variables no sensibles:

```powershell
Get-Content .env | Select-String "PATENTES_SOURCE_MODE|PATENTES_INDEX_DB|DOCS_BASE_URL|SHAREPOINT_SITE_URL|SHAREPOINT_LIBRARY_NAME|SHAREPOINT_FOLDER_PATH|SHAREPOINT_SYNC_"
```

Verificar certificado SharePoint:

```powershell
Test-Path .\Certificado\agente_patentes_cert.pfx
```

## SharePoint

Resolver site:

```powershell
python scripts\sharepoint_probe.py --site-info
```

Listar drives:

```powershell
python scripts\sharepoint_probe.py --list-drives
```

Listar carpeta:

```powershell
python scripts\sharepoint_probe.py --list-folder
```

Listar PDFs:

```powershell
python scripts\sharepoint_probe.py --list-pdfs --limit 5
```

Descargar uno:

```powershell
python scripts\sharepoint_probe.py --download-one
```

Sync corto con telemetria:

```powershell
python scripts\sharepoint_probe.py --sync --limit 1
```

Sync completo:

```powershell
python scripts\sharepoint_probe.py --sync
```

Scheduler: una sola evaluacion:

```powershell
python scripts\sharepoint_scheduler.py --once
```

Scheduler: forzar corrida:

```powershell
python scripts\sharepoint_scheduler.py --run-now
```

Scheduler continuo:

```powershell
python scripts\sharepoint_scheduler.py
```

## Indexado e inspeccion

Reindexado completo:

```powershell
python scripts\index_patentes.py --force
```

Solo sync SharePoint:

```powershell
python scripts\index_patentes.py --sync-only
```

Indexado limitado:

```powershell
python scripts\index_patentes.py --force --limit 3 --max-pages-per-pdf 20
```

Stats del indice:

```powershell
python scripts\inspect_db.py --stats
```

Busqueda exacta:

```powershell
python scripts\inspect_db.py --plate AUT230 --mode exacto
```

Busqueda por prefijo:

```powershell
python scripts\inspect_db.py --plate AD --mode prefijo
```

Busqueda por contiene:

```powershell
python scripts\inspect_db.py --plate 70 --mode contiene
```

## Backend y UI

Levantar backend:

```powershell
python -m uvicorn api.main:app --host 127.0.0.1 --port 8000
```

Levantar backend con reload:

```powershell
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

Abrir UI:

```powershell
Start-Process "http://localhost:8000/ui"
```

Consulta manual a `/chat`:

```powershell
$body = @{
  user_id = "smoke"
  session_id = "smoke"
  message = "Dame informacion de la patente AUT230"
  channel = "manual"
} | ConvertTo-Json

Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/chat" -ContentType "application/json" -Body $body
```

## Webex

Levantar adaptador:

```powershell
python -m uvicorn webex_adapter.main:app --host 0.0.0.0 --port 8010 --reload
```

Health del adaptador:

```powershell
Invoke-RestMethod -Method Get -Uri "http://localhost:8010/webex/health"
```

Abrir tunel:

```powershell
ssh -o StrictHostKeyChecking=no -o ServerAliveInterval=60 -o ExitOnForwardFailure=yes -R 80:localhost:8010 nokey@localhost.run
```

Listar webhooks:

```powershell
$token = (Get-Content .env | Where-Object { $_ -match '^WEBEX_BOT_TOKEN=' } | ForEach-Object { ($_ -split '=', 2)[1] })
Invoke-RestMethod -Method Get -Uri "https://webexapis.com/v1/webhooks" -Headers @{ Authorization = "Bearer $token" }
```

Crear webhook:

```powershell
$token = (Get-Content .env | Where-Object { $_ -match '^WEBEX_BOT_TOKEN=' } | ForEach-Object { ($_ -split '=', 2)[1] })
$secret = (Get-Content .env | Where-Object { $_ -match '^WEBEX_WEBHOOK_SECRET=' } | ForEach-Object { ($_ -split '=', 2)[1] })
$targetUrl = "https://<url-publica>/webex/webhook"

$body = @{
  name = "patentes-webhook"
  targetUrl = $targetUrl
  resource = "messages"
  event = "created"
  secret = $secret
} | ConvertTo-Json

Invoke-RestMethod -Method Post -Uri "https://webexapis.com/v1/webhooks" -Headers @{ Authorization = "Bearer $token" } -ContentType "application/json" -Body $body
```

## Logs

Tail del log principal:

```powershell
Get-Content ..\data\logs\patentes_agent.log -Wait -Tail 50
```

Tail de errores:

```powershell
Get-Content ..\data\logs\patentes_agent.error.log -Wait -Tail 50
```

Tail de errores de indexado:

```powershell
Get-Content ..\data\logs\patentes_agent.index_errors.log -Wait -Tail 50
```

Ver transcripts:

```powershell
Get-Content ..\data\conversations.jsonl -Tail 20
```

## Procesos y puertos

Procesos Python:

```powershell
Get-Process python -ErrorAction SilentlyContinue
```

Puerto 8000:

```powershell
Get-NetTCPConnection -LocalPort 8000 -State Listen
```

Puerto 8010:

```powershell
Get-NetTCPConnection -LocalPort 8010 -State Listen
```

Matar procesos Python:

```powershell
Get-Process python -ErrorAction SilentlyContinue | Stop-Process -Force
```

## Git

Estado:

```powershell
git status --short --branch
```

Ramas:

```powershell
git branch -vv
```

Remotos:

```powershell
git remote -v
```

Historial:

```powershell
git log --oneline --decorate --graph -20
```

Comparar `main` y `test`:

```powershell
git log --oneline --left-right main...test
```

## Validacion rapida

Compilar scripts/modulos clave:

```powershell
python -m py_compile scripts\sharepoint_probe.py scripts\sharepoint_scheduler.py scripts\index_patentes.py src\agent\config.py src\agent\sources\sharepoint_client.py
```
