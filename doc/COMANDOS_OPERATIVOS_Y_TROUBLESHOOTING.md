<!-- NOTA: Guia de comandos operativos y de troubleshooting desde terminal. -->
# Comandos operativos y troubleshooting

Esta guia concentra los comandos utiles para operar, diagnosticar y seguir el
proyecto desde terminal en entorno local. Los ejemplos estan escritos para
PowerShell y asumen que el working directory es:

```powershell
cd C:\Users\fnrivarola\Desktop\Celula\Patentes\patentes_agent
```

## Entorno y dependencias

Activar el entorno virtual:

```powershell
..\venv_patentes_agent\Scripts\Activate.ps1
```

Reinstalar el proyecto en editable:

```powershell
..\venv_patentes_agent\Scripts\python.exe -m pip install -e .
```

Ver paquete y dependencias clave:

```powershell
..\venv_patentes_agent\Scripts\python.exe -m pip show patentes-agent
..\venv_patentes_agent\Scripts\python.exe -m pip show msal
..\venv_patentes_agent\Scripts\python.exe -m pip show pypdf
```

## Verificacion de configuracion

Ver valores no sensibles del `.env`:

```powershell
Get-Content .env | Select-String "PATENTES_SOURCE_MODE|PATENTES_INDEX_DB|DOCS_BASE_URL|SHAREPOINT_SITE_URL|SHAREPOINT_LIBRARY_NAME|SHAREPOINT_FOLDER_PATH|SHAREPOINT_SYNC_"
```

Confirmar que el certificado exista:

```powershell
Test-Path .\Certificado\arcor_agente_patentes2026.pfx
```

## SharePoint: smoke tests

Resolver site:

```powershell
..\venv_patentes_agent\Scripts\python.exe scripts\sharepoint_probe.py --site-info
```

Listar drives:

```powershell
..\venv_patentes_agent\Scripts\python.exe scripts\sharepoint_probe.py --list-drives
```

Listar carpeta objetivo:

```powershell
..\venv_patentes_agent\Scripts\python.exe scripts\sharepoint_probe.py --list-folder
```

Listar PDFs:

```powershell
..\venv_patentes_agent\Scripts\python.exe scripts\sharepoint_probe.py --list-pdfs --limit 5
```

Descargar un PDF:

```powershell
..\venv_patentes_agent\Scripts\python.exe scripts\sharepoint_probe.py --download-one
```

Sync incremental corto con telemetria:

```powershell
..\venv_patentes_agent\Scripts\python.exe scripts\sharepoint_probe.py --sync --limit 1
```

Sync completo:

```powershell
..\venv_patentes_agent\Scripts\python.exe scripts\sharepoint_probe.py --sync
```

## SharePoint: scheduler incremental

Evaluar el slot actual una sola vez:

```powershell
..\venv_patentes_agent\Scripts\python.exe scripts\sharepoint_scheduler.py --once
```

Forzar una corrida inmediata:

```powershell
..\venv_patentes_agent\Scripts\python.exe scripts\sharepoint_scheduler.py --run-now
```

Modo continuo:

```powershell
..\venv_patentes_agent\Scripts\python.exe scripts\sharepoint_scheduler.py
```

Cambiar frecuencia de chequeo del daemon:

```powershell
..\venv_patentes_agent\Scripts\python.exe scripts\sharepoint_scheduler.py --poll-seconds 60
```

## Indexado e inspeccion

Reindexado completo:

```powershell
..\venv_patentes_agent\Scripts\python.exe scripts\index_patentes.py --force
```

Solo sync SharePoint sin indexar:

```powershell
..\venv_patentes_agent\Scripts\python.exe scripts\index_patentes.py --sync-only
```

Indexado limitado para pruebas:

```powershell
..\venv_patentes_agent\Scripts\python.exe scripts\index_patentes.py --force --limit 3 --max-pages-per-pdf 20
```

Estadisticas del indice:

```powershell
..\venv_patentes_agent\Scripts\python.exe scripts\inspect_db.py --stats
```

Buscar una patente exacta:

```powershell
..\venv_patentes_agent\Scripts\python.exe scripts\inspect_db.py --plate AUT230 --mode exacto
```

Buscar por prefijo:

```powershell
..\venv_patentes_agent\Scripts\python.exe scripts\inspect_db.py --plate AD --mode prefijo
```

Buscar por contiene:

```powershell
..\venv_patentes_agent\Scripts\python.exe scripts\inspect_db.py --plate 70 --mode contiene
```

## Backend y UI local

Levantar backend:

```powershell
..\venv_patentes_agent\Scripts\python.exe -m uvicorn api.main:app --host 127.0.0.1 --port 8000
```

Levantar backend con autoreload:

```powershell
..\venv_patentes_agent\Scripts\python.exe -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

Abrir UI:

```powershell
Start-Process "http://localhost:8000/ui"
```

Consultar `/chat` manualmente:

```powershell
$body = @{
  user_id = "smoke"
  session_id = "smoke"
  message = "Dame informacion de la patente AUT230"
  channel = "manual"
} | ConvertTo-Json

Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/chat" -ContentType "application/json" -Body $body
```

## Webex adapter

Levantar adaptador:

```powershell
..\venv_patentes_agent\Scripts\python.exe -m uvicorn webex_adapter.main:app --host 0.0.0.0 --port 8010 --reload
```

Health del adaptador:

```powershell
Invoke-RestMethod -Method Get -Uri "http://localhost:8010/webex/health"
```

Abrir tunel temporal con `localhost.run`:

```powershell
ssh -o StrictHostKeyChecking=no -o ServerAliveInterval=60 -o ExitOnForwardFailure=yes -R 80:localhost:8010 nokey@localhost.run
```

Listar webhooks en Webex:

```powershell
$token = (Get-Content .env | Where-Object { $_ -match '^WEBEX_BOT_TOKEN=' } | ForEach-Object { ($_ -split '=', 2)[1] })
Invoke-RestMethod -Method Get -Uri "https://webexapis.com/v1/webhooks" -Headers @{ Authorization = "Bearer $token" }
```

Crear webhook por API:

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

## Logs y seguimiento

Seguir log principal:

```powershell
Get-Content ..\data\logs\patentes_agent.log -Wait -Tail 50
```

Seguir errores:

```powershell
Get-Content ..\data\logs\patentes_agent.error.log -Wait -Tail 50
```

Seguir errores de indexado:

```powershell
Get-Content ..\data\logs\patentes_agent.index_errors.log -Wait -Tail 50
```

Ver ultimo transcript:

```powershell
Get-Content ..\data\conversations.jsonl -Tail 20
```

Ver logs del adaptador si fueron redirigidos:

```powershell
Get-Content ..\data\logs\webex_adapter.local.log -Wait -Tail 50
Get-Content ..\data\logs\webex_adapter.local.err.log -Wait -Tail 50
```

## Procesos y puertos

Ver procesos Python:

```powershell
Get-Process python -ErrorAction SilentlyContinue
```

Ver quien escucha en 8000:

```powershell
Get-NetTCPConnection -LocalPort 8000 -State Listen
```

Ver quien escucha en 8010:

```powershell
Get-NetTCPConnection -LocalPort 8010 -State Listen
```

Matar procesos Python:

```powershell
Get-Process python -ErrorAction SilentlyContinue | Stop-Process -Force
```

## Git

Estado rapido:

```powershell
git status --short --branch
```

Ver ramas con tracking:

```powershell
git branch -vv
```

Ver remotos:

```powershell
git remote -v
```

Ver historial resumido:

```powershell
git log --oneline --decorate --graph -20
```

Comparar `main` contra `test`:

```powershell
git log --oneline --left-right main...test
```

## Validacion de sintaxis

Compilar archivos Python relevantes:

```powershell
..\venv_patentes_agent\Scripts\python.exe -m py_compile scripts\sharepoint_probe.py scripts\sharepoint_scheduler.py scripts\index_patentes.py src\agent\config.py src\agent\sources\sharepoint_client.py
```

## Referencias

- `doc/LOGS_Y_OBSERVABILIDAD.md`
- `doc/PRUEBA_END_TO_END.md`
- `doc/SHAREPOINT_INTEGRACION.md`
- `doc/SHAREPOINT_OPERACION_Y_COSTOS.md`
- `doc/WEBEX_WEBHOOK.md`
