"""Interfaz web simple para conversar con el agente.

Instrucciones:
- Mantener esta UI solo para diagnostico y pruebas.
- No exponer razonamiento interno del modelo.
- Mostrar trazas tecnicas de herramientas.
- Incluye campos como match_type, dominio_label y label_pages si existen.
"""

from fastapi import APIRouter
from fastapi.responses import HTMLResponse


router = APIRouter()


_HTML = r"""<!doctype html>
<html lang="es">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Agente de Patentes - UI</title>
    <style>
      body { font-family: Arial, sans-serif; margin: 24px; background: #f7f7f7; color: #222; }
      .container { max-width: 980px; margin: 0 auto; }
      .row { display: flex; gap: 16px; flex-wrap: wrap; }
      .panel { background: #fff; border: 1px solid #ddd; border-radius: 8px; padding: 16px; flex: 1 1 460px; }
      .panel h2 { margin-top: 0; font-size: 18px; }
      textarea { width: 100%; min-height: 120px; }
      input, textarea, button { font-size: 14px; }
      button { padding: 8px 12px; cursor: pointer; }
      .log { white-space: pre-wrap; background: #fafafa; border: 1px dashed #ccc; padding: 12px; border-radius: 6px; }
      .msg { margin: 8px 0; }
      .msg strong { display: inline-block; min-width: 90px; }
    </style>
  </head>
  <body>
    <div class="container">
      <h1>Agente de Patentes</h1>
      <p>UI de prueba para conversar con el agente y ver trazas tecnicas.</p>

      <div class="panel">
        <div class="msg"><strong>user_id</strong> <input id="userId" value="test" /></div>
        <div class="msg"><strong>session_id</strong> <input id="sessionId" value="test1" /></div>
        <div class="msg"><strong>mensaje</strong></div>
        <textarea id="message">AUT011</textarea>
        <button id="sendBtn" type="button">Enviar</button>
      </div>

      <div class="row" style="margin-top: 16px;">
        <div class="panel">
          <h2>Respuesta</h2>
          <div id="response" class="log"></div>
        </div>
        <div class="panel">
          <h2>Debug (herramientas)</h2>
          <div id="debug" class="log"></div>
        </div>
      </div>
    </div>

    <script>
      const sendBtn = document.getElementById("sendBtn");
      const responseEl = document.getElementById("response");
      const debugEl = document.getElementById("debug");

      function pretty(obj) {
        return JSON.stringify(obj, null, 2);
      }

      function escapeHtml(text) {
        return String(text || "")
          .replace(/&/g, "&amp;")
          .replace(/</g, "&lt;")
          .replace(/>/g, "&gt;")
          .replace(/"/g, "&quot;")
          .replace(/'/g, "&#39;");
      }

      function renderMarkdownLinks(text) {
        const escaped = escapeHtml(text);
        const withLinks = escaped.replace(
          /\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g,
          '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>'
        );
        return withLinks.replace(/\n/g, "<br>");
      }

      sendBtn.addEventListener("click", async () => {
        responseEl.innerHTML = "Enviando...";
        debugEl.textContent = "";

        const payload = {
          user_id: document.getElementById("userId").value.trim(),
          session_id: document.getElementById("sessionId").value.trim(),
          message: document.getElementById("message").value.trim()
        };

        try {
          const res = await fetch("/chat_debug", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
          });

          const raw = await res.text();
          let data = {};
          try {
            data = raw ? JSON.parse(raw) : {};
          } catch {
            data = { text: raw || "" };
          }

          if (!res.ok) {
            responseEl.textContent = "Error HTTP: " + res.status + (data.text ? " - " + data.text : "");
            return;
          }

          responseEl.innerHTML = renderMarkdownLinks(data.text || "");
          debugEl.textContent = pretty(data.debug || {});
        } catch (error) {
          responseEl.textContent = "No se pudo enviar la consulta: " + (error?.message || error);
        }
      });
    </script>
  </body>
</html>
"""


@router.get("/ui", response_class=HTMLResponse)
def ui() -> HTMLResponse:
    """Devuelve la pagina HTML de la interfaz de pruebas."""
    return HTMLResponse(_HTML)
