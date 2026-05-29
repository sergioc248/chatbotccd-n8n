from __future__ import annotations

import json
import os
import uuid
from typing import Any

import gradio as gr
import httpx
import uvicorn
from fastapi import FastAPI
from fastapi.responses import JSONResponse, Response
from dotenv import load_dotenv
from pydantic import BaseModel


load_dotenv()

APP_TITLE = "TuNaveganteCCD"
APP_SUBTITLE = "Asistente Virtual del Centro de Competencias Digitales UNAB"
N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL", "").strip()
N8N_TIMEOUT_SECONDS = float(os.getenv("N8N_TIMEOUT_SECONDS", "60"))
PWA_THEME_COLOR = "#c41e24"
PWA_BACKGROUND_COLOR = "#edf0f4"

UNAB_LOGO_URL = os.getenv(
    "UNAB_LOGO_URL",
    "https://upload.wikimedia.org/wikipedia/commons/d/de/LogoUnab.png",
)

RESOURCES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resources")


def _load_resource_bytes(filename: str) -> bytes:
    with open(os.path.join(RESOURCES_DIR, filename), "rb") as handle:
        return handle.read()


PWA_ICON_192_PNG = _load_resource_bytes("logo_unab_192.png")
PWA_ICON_512_PNG = _load_resource_bytes("logo_unab_512.png")

SLASH_COMMANDS: list[dict[str, str]] = [
    {"cmd": "/inicio", "desc": "Bienvenida e información general del CCD"},
    {"cmd": "/ayuda", "desc": "Lista completa de comandos con ejemplos"},
    {"cmd": "/ruta", "desc": "Avance en los 3 pilares de la ruta"},
    {"cmd": "/cursos", "desc": "Cursos completados con fecha y pilar"},
    {"cmd": "/calendario", "desc": "Próximos eventos y fechas académicas"},
    {"cmd": "/documentos", "desc": "Reglamentos y documentos institucionales"},
    {"cmd": "/perfil", "desc": "Datos del estudiante (programa, semestre)"},
    {"cmd": "/insignia", "desc": "Estado y requisitos de la insignia digital"},
    {"cmd": "/siguiente", "desc": "Próximo curso recomendado"},
]


class HealthResponse(BaseModel):
    status: str
    n8n_configured: bool


app = FastAPI(
    title=APP_TITLE,
    description="Frontend Gradio para el chatbot CCD de la UNAB alojado en n8n.",
    version="0.1.0",
)


@app.get("/api/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok", n8n_configured=bool(N8N_WEBHOOK_URL))


@app.get("/manifest.webmanifest", include_in_schema=False)
async def pwa_manifest() -> JSONResponse:
    return JSONResponse(
        content={
            "name": APP_TITLE,
            "short_name": "TuNaveganteCCD",
            "description": APP_SUBTITLE,
            "start_url": "/",
            "scope": "/",
            "display": "standalone",
            "background_color": PWA_BACKGROUND_COLOR,
            "theme_color": PWA_THEME_COLOR,
            "orientation": "portrait-primary",
            "categories": ["education", "productivity"],
            "icons": [
                {
                    "src": "/pwa-icon-192.png",
                    "sizes": "192x192",
                    "type": "image/png",
                    "purpose": "any",
                },
                {
                    "src": "/pwa-icon-512.png",
                    "sizes": "512x512",
                    "type": "image/png",
                    "purpose": "any",
                },
                {
                    "src": "/pwa-icon-192.png",
                    "sizes": "192x192",
                    "type": "image/png",
                    "purpose": "maskable",
                },
                {
                    "src": "/pwa-icon-512.png",
                    "sizes": "512x512",
                    "type": "image/png",
                    "purpose": "maskable",
                },
            ],
        },
        headers={"Cache-Control": "public, max-age=3600"},
        media_type="application/manifest+json",
    )


@app.get("/pwa-icon-192.png", include_in_schema=False)
async def pwa_icon_192() -> Response:
    return Response(
        content=PWA_ICON_192_PNG,
        headers={"Cache-Control": "public, max-age=86400"},
        media_type="image/png",
    )


@app.get("/pwa-icon-512.png", include_in_schema=False)
async def pwa_icon_512() -> Response:
    return Response(
        content=PWA_ICON_512_PNG,
        headers={"Cache-Control": "public, max-age=86400"},
        media_type="image/png",
    )


@app.get("/service-worker.js", include_in_schema=False)
async def service_worker() -> Response:
    return Response(
        content=f"""
const CACHE_NAME = '{APP_TITLE.lower()}-pwa-v3';
const APP_SHELL = ['/', '/manifest.webmanifest', '/pwa-icon-192.png', '/pwa-icon-512.png'];

self.addEventListener('install', function (event) {{
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(function (cache) {{ return cache.addAll(APP_SHELL); }})
      .then(function () {{ return self.skipWaiting(); }})
  );
}});

self.addEventListener('activate', function (event) {{
  event.waitUntil(
    caches.keys()
      .then(function (keys) {{
        return Promise.all(keys.filter(function (key) {{
          return key !== CACHE_NAME;
        }}).map(function (key) {{
          return caches.delete(key);
        }}));
      }})
      .then(function () {{ return self.clients.claim(); }})
  );
}});

self.addEventListener('fetch', function (event) {{
  const request = event.request;
  const url = new URL(request.url);

  if (request.method !== 'GET' || url.origin !== self.location.origin) {{
    return;
  }}

  if (request.mode === 'navigate') {{
    event.respondWith(
      fetch(request)
        .then(function (response) {{
          const copy = response.clone();
          caches.open(CACHE_NAME).then(function (cache) {{
            cache.put('/', copy);
          }});
          return response;
        }})
        .catch(function () {{ return caches.match('/'); }})
    );
    return;
  }}

  if (APP_SHELL.includes(url.pathname)) {{
    event.respondWith(
      caches.match(request).then(function (cached) {{
        return cached || fetch(request);
      }})
    );
  }}
}});
""".strip(),
        headers={"Cache-Control": "no-cache"},
        media_type="text/javascript",
    )


def _extract_n8n_reply(payload: Any) -> str:
    if isinstance(payload, str):
        return payload

    if isinstance(payload, list) and payload:
        return _extract_n8n_reply(payload[0])

    if isinstance(payload, dict):
        for key in ("output", "text", "response", "message", "answer"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value

        nested = payload.get("data")
        if nested is not None:
            return _extract_n8n_reply(nested)

    return "Recibí una respuesta de n8n, pero no pude leer el texto del mensaje."


async def send_message_to_n8n(
    message: str,
    history: list[dict[str, str]] | None = None,
    request: gr.Request | None = None,
) -> str:
    if not N8N_WEBHOOK_URL:
        return (
            "Aún no está configurada la variable `N8N_WEBHOOK_URL`. "
            "Configúrala con la URL pública del Chat Trigger de n8n para conectar el bot."
        )

    session_hash = getattr(request, "session_hash", None) if request else None
    session_id = session_hash or f"gradio-{uuid.uuid4()}"

    payload = {
        "action": "sendMessage",
        "sessionId": session_id,
        "chatInput": message,
        "metadata": {
            "source": "gradio-fastapi",
            "app": APP_TITLE,
            "institution": "UNAB",
            "unit": "CCD",
            "historyLength": len(history or []),
        },
    }

    try:
        async with httpx.AsyncClient(timeout=N8N_TIMEOUT_SECONDS) as client:
            response = await client.post(N8N_WEBHOOK_URL, json=payload)
            response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        return (
            "n8n respondió con un error al procesar tu mensaje. "
            f"Código HTTP: {exc.response.status_code}."
        )
    except httpx.RequestError:
        return (
            "No pude conectarme con n8n en este momento. "
            "Verifica la URL del webhook y que el workflow esté activo."
        )

    try:
        data = response.json()
    except ValueError:
        data = response.text

    return _extract_n8n_reply(data)


UNAB_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,500;9..144,600;9..144,700&family=IBM+Plex+Sans:ital,wght@0,300;0,400;0,500;0,600;1,400&family=IBM+Plex+Mono:wght@400;500&display=swap');

/* ─── Design tokens ─── */
:root {
  --page:    #edf0f4;
  --card:    #ffffff;
  --inset:   #f5f7fa;
  --red:     #c41e24;
  --red-dk:  #a11820;
  --blue:    #0058a8;
  --yellow:  #b8720a;
  --green:   #1c7a3e;
  --navy:    #0e2140;
  --text-1:  #0e2140;
  --text-2:  #4a5568;
  --text-3:  #8896a6;
  --border:  #d4d9e0;
  --border-strong: #b0b9c4;
  --font-d: 'Fraunces', Georgia, serif;
  --font-b: 'IBM Plex Sans', system-ui, sans-serif;
  --font-m: 'IBM Plex Mono', 'Courier New', monospace;
  --r:    8px;
  --r-lg: 12px;
  --shadow-sm: 0 1px 3px rgba(14,33,64,0.07), 0 1px 2px rgba(14,33,64,0.04);
  --shadow:    0 2px 8px rgba(14,33,64,0.07), 0 1px 3px rgba(14,33,64,0.04);
}

/* ─── Base ─── */
*, *::before, *::after { box-sizing: border-box; }

body, .gradio-container {
  background-color: var(--page) !important;
  color: var(--text-1) !important;
  font-family: var(--font-b) !important;
}

.gradio-container {
  min-height: 100vh !important;
}

/* Strip all decorative Gradio block chrome; we style explicitly */
.block, .form, .gap, .wrap, .contain, .panel {
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
}

/* ═══════════════════════════════════════
   HERO BANNER
═══════════════════════════════════════ */
.unab-hero {
  background: var(--card);
  border: 1px solid var(--border);
  border-top: 3px solid var(--red);
  border-radius: var(--r-lg);
  box-shadow: var(--shadow);
  padding: 0;
  overflow: hidden;
}

/* Top strip: logo + institution identity */
.hero-brand {
  display: flex;
  align-items: center;
  gap: 0;
  padding: 20px 28px;
  border-bottom: 1px solid var(--border);
}

.hero-logo {
  height: 44px;
  width: auto;
  max-width: min(180px, 38vw);
  object-fit: contain;
  object-position: left center;
  display: block;
  flex-shrink: 0;
}

.hero-divider {
  width: 1px;
  height: 36px;
  background: var(--border);
  margin: 0 20px;
  flex-shrink: 0;
}

.hero-id {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.pwa-install-button {
  margin-left: auto;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 38px;
  padding: 9px 16px;
  border-radius: var(--r);
  border: 1px solid var(--red);
  background: var(--red);
  color: #ffffff;
  font-family: 'IBM Plex Sans', sans-serif !important;
  font-size: 0.78rem;
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  cursor: pointer;
  transition: background 0.15s, border-color 0.15s, color 0.15s;
  box-shadow: var(--shadow-sm);
}

.pwa-install-button:hover {
  background: var(--red-dk);
  border-color: var(--red-dk);
}

.pwa-install-button.is-installed,
.pwa-install-button:disabled {
  background: var(--inset);
  border-color: var(--border);
  color: var(--green);
  cursor: default;
}

.pwa-install-overlay {
  position: fixed;
  inset: 0;
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  background: rgba(14, 33, 64, 0.55);
}

.pwa-install-dialog {
  width: min(420px, 100%);
  max-height: 90vh;
  overflow-y: auto;
  background: #ffffff;
  border: 1px solid var(--border);
  border-radius: var(--r);
  box-shadow: 0 18px 48px rgba(14, 33, 64, 0.28);
  padding: 24px;
}

.pwa-install-dialog-title {
  margin: 0 0 16px;
  font-family: 'IBM Plex Sans', sans-serif !important;
  font-size: 1.05rem;
  font-weight: 700;
  color: var(--red);
}

.pwa-install-dialog-steps {
  margin: 0 0 20px;
  padding-left: 20px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  font-size: 0.9rem;
  line-height: 1.45;
  color: var(--text-1);
}

.pwa-install-dialog-close {
  width: 100%;
  min-height: 42px;
  border-radius: var(--r);
  border: 1px solid var(--red);
  background: var(--red);
  color: #ffffff;
  font-family: 'IBM Plex Sans', sans-serif !important;
  font-size: 0.82rem;
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  cursor: pointer;
}

.pwa-install-dialog-close:hover {
  background: var(--red-dk);
  border-color: var(--red-dk);
}

.hero-unit {
  font-family: 'IBM Plex Sans', sans-serif !important;
  font-size: 0.72rem;
  font-weight: 600;
  letter-spacing: 0.10em;
  text-transform: uppercase;
  color: var(--red);
  line-height: 1;
}

.hero-institution {
  font-family: 'IBM Plex Sans', sans-serif !important;
  font-size: 0.82rem;
  font-weight: 400;
  color: var(--text-2);
  line-height: 1.2;
}

/* Body section: title, description, tags */
.hero-body {
  padding: 24px 28px 26px;
}

.hero-title {
  font-family: 'Fraunces', Georgia, serif !important;
  font-size: clamp(2rem, 3.8vw, 3rem);
  font-weight: 600;
  font-style: italic;
  letter-spacing: -0.02em;
  line-height: 1.05;
  color: var(--navy);
  margin: 0 0 10px;
}

.hero-desc {
  font-family: 'IBM Plex Sans', sans-serif !important;
  font-size: 0.92rem;
  font-weight: 400;
  line-height: 1.72;
  color: var(--text-2);
  margin: 0;
  max-width: 680px;
}

/* Tags */
.hero-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 7px;
  margin-top: 18px;
}

.tag {
  font-family: 'IBM Plex Sans', sans-serif !important;
  font-size: 0.70rem;
  font-weight: 500;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  padding: 4px 10px;
  border-radius: 4px;
  border: 1px solid;
  cursor: default;
  transition: background 0.15s;
}

.tag.red   { color: var(--red);    border-color: rgba(196, 30, 36, 0.35);  background: rgba(196, 30, 36, 0.06); }
.tag.amber { color: var(--yellow); border-color: rgba(184,114, 10, 0.35);  background: rgba(184,114, 10, 0.06); }
.tag.blue  { color: var(--blue);   border-color: rgba(  0, 88,168, 0.32);  background: rgba(  0, 88,168, 0.06); }
.tag.green { color: var(--green);  border-color: rgba( 28,122, 62, 0.32);  background: rgba( 28,122, 62, 0.06); }

.tag.red:hover   { background: rgba(196,  30,  36, 0.12); }
.tag.amber:hover { background: rgba(184, 114,  10, 0.12); }
.tag.blue:hover  { background: rgba(  0,  88, 168, 0.12); }
.tag.green:hover { background: rgba( 28, 122,  62, 0.12); }

/* ═══════════════════════════════════════
   CHATBOT
═══════════════════════════════════════ */
#chatbot {
  background: var(--card) !important;
  border: 1px solid var(--border) !important;
  border-radius: var(--r-lg) !important;
  box-shadow: var(--shadow) !important;
  overflow: hidden !important;
}

/* All inner containers — reset any dark backgrounds Gradio may inject */
#chatbot .wrapper,
#chatbot .bubble-wrap,
#chatbot .message-wrap {
  background: var(--card) !important;
}

/* Header label */
#chatbot label[data-testid="block-label"] {
  display: flex !important;
  align-items: center !important;
  gap: 7px !important;
  background: var(--inset) !important;
  border-bottom: 1px solid var(--border) !important;
  padding: 9px 16px !important;
  color: var(--text-3) !important;
  font-family: 'IBM Plex Sans', sans-serif !important;
  font-size: 0.70rem !important;
  font-weight: 600 !important;
  letter-spacing: 0.10em !important;
  text-transform: uppercase !important;
}

#chatbot label[data-testid="block-label"] svg {
  width: 13px !important;
  height: 13px !important;
  opacity: 0.5 !important;
}

/* Keep the wide UNAB logo readable when Gradio renders it inside avatar slots */
#chatbot .avatar-container,
#chatbot .avatar-image {
  background: #ffffff !important;
}

#chatbot .avatar-container img,
#chatbot img.avatar-image {
  object-fit: contain !important;
  padding: 3px !important;
}

/* Message area padding */
#chatbot .message-wrap {
  padding: 14px 16px !important;
}

/* Individual message bubbles */
#chatbot .message {
  font-family: 'IBM Plex Sans', sans-serif !important;
  font-size: 0.92rem !important;
  line-height: 1.68 !important;
  border-radius: var(--r) !important;
  padding: 10px 14px !important;
  border: none !important;
}

#chatbot .message.user,
#chatbot [data-testid="user"] .message {
  background: #dbeafe !important;
  color: #1e3a5f !important;
}

#chatbot .message.user p,
#chatbot .message.user li,
#chatbot .message.user strong,
#chatbot .message.user em,
#chatbot .message.user .prose,
#chatbot .message.user .prose * {
  color: #1e3a5f !important;
}

/* Gradio's temporary typing/loading indicators can inherit low-contrast colors */
#chatbot .message.user .typing,
#chatbot .message.user .loading,
#chatbot .message.user .generating,
#chatbot .message.user.pending,
#chatbot .message.user .pending,
#chatbot .message.user .dot,
#chatbot .message.user [class*="typing"],
#chatbot .message.user [class*="loading"],
#chatbot .message.user [class*="generating"],
#chatbot .message.user [class*="pending"],
#chatbot .message.user [class*="dot"],
#chatbot [data-testid="user"] .message .typing,
#chatbot [data-testid="user"] .message .loading,
#chatbot [data-testid="user"] .message .generating,
#chatbot [data-testid="user"] .message.pending,
#chatbot [data-testid="user"] .message .pending,
#chatbot [data-testid="user"] .message .dot,
#chatbot [data-testid="user"] .message [class*="typing"],
#chatbot [data-testid="user"] .message [class*="loading"],
#chatbot [data-testid="user"] .message [class*="generating"],
#chatbot [data-testid="user"] .message [class*="pending"],
#chatbot [data-testid="user"] .message [class*="dot"] {
  color: #1e3a5f !important;
  opacity: 1 !important;
}

#chatbot .message.user .typing *,
#chatbot .message.user .loading *,
#chatbot .message.user .generating *,
#chatbot .message.user.pending *,
#chatbot .message.user .pending *,
#chatbot .message.user .dot,
#chatbot .message.user [class*="typing"] *,
#chatbot .message.user [class*="loading"] *,
#chatbot .message.user [class*="generating"] *,
#chatbot .message.user [class*="pending"] *,
#chatbot .message.user [class*="dot"],
#chatbot [data-testid="user"] .message .typing *,
#chatbot [data-testid="user"] .message .loading *,
#chatbot [data-testid="user"] .message .generating *,
#chatbot [data-testid="user"] .message.pending *,
#chatbot [data-testid="user"] .message .pending *,
#chatbot [data-testid="user"] .message .dot,
#chatbot [data-testid="user"] .message [class*="typing"] *,
#chatbot [data-testid="user"] .message [class*="loading"] *,
#chatbot [data-testid="user"] .message [class*="generating"] *,
#chatbot [data-testid="user"] .message [class*="pending"] *,
#chatbot [data-testid="user"] .message [class*="dot"] {
  background-color: #1e3a5f !important;
  color: #1e3a5f !important;
  opacity: 1 !important;
}

#chatbot .message.user .typing::before,
#chatbot .message.user .typing::after,
#chatbot .message.user .loading::before,
#chatbot .message.user .loading::after,
#chatbot .message.user .generating::before,
#chatbot .message.user .generating::after,
#chatbot .message.user.pending::before,
#chatbot .message.user.pending::after,
#chatbot .message.user .pending::before,
#chatbot .message.user .pending::after,
#chatbot .message.user .dot::before,
#chatbot .message.user .dot::after,
#chatbot .message.user [class*="dot"]::before,
#chatbot .message.user [class*="dot"]::after,
#chatbot [data-testid="user"] .message .typing::before,
#chatbot [data-testid="user"] .message .typing::after,
#chatbot [data-testid="user"] .message .loading::before,
#chatbot [data-testid="user"] .message .loading::after,
#chatbot [data-testid="user"] .message .generating::before,
#chatbot [data-testid="user"] .message .generating::after,
#chatbot [data-testid="user"] .message.pending::before,
#chatbot [data-testid="user"] .message.pending::after,
#chatbot [data-testid="user"] .message .pending::before,
#chatbot [data-testid="user"] .message .pending::after,
#chatbot [data-testid="user"] .message .dot::before,
#chatbot [data-testid="user"] .message .dot::after,
#chatbot [data-testid="user"] .message [class*="dot"]::before,
#chatbot [data-testid="user"] .message [class*="dot"]::after {
  background-color: #1e3a5f !important;
  color: #1e3a5f !important;
  opacity: 1 !important;
}

#chatbot .message.bot,
#chatbot [data-testid="bot"] .message {
  background: var(--inset) !important;
  color: #0e2140 !important;
  border: 1px solid var(--border) !important;
}

/* Explicitly override Gradio's prose renderer which may inherit light theme vars */
#chatbot .message.bot p,
#chatbot .message.bot li,
#chatbot .message.bot strong,
#chatbot .message.bot em,
#chatbot .message.bot a,
#chatbot .message.bot .prose,
#chatbot .message.bot .prose * {
  color: #0e2140 !important;
}

/* ─── Message & toolbar action buttons (copy / retry / undo / delete) ───
   These render via Gradio's .icon-button-wrapper which defaults to
   var(--block-background-fill)/var(--body-text-color); under dark mode those
   resolve dark, leaving floating black squares over the light chat. Pin them
   to the light brand surface explicitly. */
#chatbot .icon-button-wrapper {
  background: var(--card) !important;
  border: 1px solid var(--border) !important;
  box-shadow: var(--shadow-sm) !important;
  border-radius: var(--r) !important;
}

#chatbot .icon-button-wrapper.no-background {
  background: none !important;
  border: none !important;
  box-shadow: none !important;
}

#chatbot .icon-button {
  color: var(--text-3) !important;
  background: transparent !important;
}

#chatbot .icon-button svg {
  color: var(--text-3) !important;
}

#chatbot .icon-button:hover:not(:disabled) {
  background: var(--inset) !important;
  color: var(--blue) !important;
}

#chatbot .icon-button:hover:not(:disabled) svg {
  color: var(--blue) !important;
}

/* Hairline separators between grouped icon buttons */
#chatbot .icon-button-wrapper button:not(:last-child)::after,
#chatbot .icon-button-wrapper a.download-link:not(:last-child)::after {
  background-color: var(--border) !important;
}

/* ─── Agent "writing" typing indicator ───
   The pulsing dots use background-color: var(--body-text-color); under dark
   mode that is near-white and disappears on the light bubble. Pin to brand. */
#chatbot .pending {
  background: transparent !important;
}

#chatbot .dots {
  gap: 6px !important;
}

#chatbot .dot {
  background-color: var(--blue) !important;
  opacity: 0.45 !important;
}

/* ═══════════════════════════════════════
   INPUT ROW
═══════════════════════════════════════ */
#message_box {
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
  overflow: visible !important;
}

#message_box .input-container {
  display: flex !important;
  align-items: center !important;
  gap: 8px !important;
  background: var(--card) !important;
  border: 1.5px solid var(--border) !important;
  border-radius: 10px !important;
  padding: 5px 5px 5px 14px !important;
  transition: border-color 0.18s, box-shadow 0.18s !important;
  position: relative !important;
  overflow: visible !important;
  box-shadow: var(--shadow-sm) !important;
}

#message_box .input-container:focus-within {
  border-color: var(--blue) !important;
  box-shadow: 0 0 0 3px rgba(0, 88, 168, 0.12), var(--shadow-sm) !important;
}

textarea[data-testid="textbox"] {
  background: transparent !important;
  border: none !important;
  outline: none !important;
  box-shadow: none !important;
  color: var(--text-1) !important;
  font-family: 'IBM Plex Sans', sans-serif !important;
  font-size: 0.93rem !important;
  line-height: 1.5 !important;
  caret-color: var(--blue) !important;
  padding: 8px 0 !important;
  resize: none !important;
  flex: 1 !important;
}

textarea[data-testid="textbox"]::placeholder {
  color: var(--text-3) !important;
  font-style: normal !important;
  font-weight: 400 !important;
}

/* ─── Submit button ─── */
button[data-testid="submit-button"] {
  background: var(--red) !important;
  border: none !important;
  border-radius: var(--r) !important;
  color: #ffffff !important;
  font-family: 'IBM Plex Sans', sans-serif !important;
  font-weight: 600 !important;
  font-size: 0.85rem !important;
  letter-spacing: 0.02em !important;
  padding: 9px 18px !important;
  cursor: pointer !important;
  flex-shrink: 0 !important;
  transition: background 0.15s !important;
  box-shadow: none !important;
}

button[data-testid="submit-button"]:hover {
  background: var(--red-dk) !important;
}

/* ═══════════════════════════════════════
   COMMAND AUTOCOMPLETE DROPDOWN
═══════════════════════════════════════ */
#ccd-cmd-drop {
  background: var(--card) !important;
  border: 1px solid var(--border) !important;
  border-radius: var(--r-lg) !important;
  overflow-x: hidden !important;
  overflow-y: auto !important;
  max-height: min(320px, 42vh) !important;
  box-shadow: 0 -4px 24px rgba(14,33,64,0.12), 0 -1px 6px rgba(14,33,64,0.06) !important;
}

.ccd-item {
  display: flex !important;
  align-items: center !important;
  gap: 14px !important;
  padding: 9px 16px !important;
  cursor: pointer !important;
  border-bottom: 1px solid var(--border) !important;
  transition: background 0.12s !important;
}

.ccd-item:last-of-type { border-bottom: none !important; }

.ccd-item:hover,
.ccd-item.ccd-active {
  background: #eff4fb !important;
}

.ccd-item code {
  font-family: 'IBM Plex Mono', monospace !important;
  font-size: 0.80rem !important;
  font-weight: 500 !important;
  color: var(--blue) !important;
  min-width: 108px !important;
  background: none !important;
  padding: 0 !important;
}

.ccd-item span {
  font-family: 'IBM Plex Sans', sans-serif !important;
  font-size: 0.80rem !important;
  color: var(--text-2) !important;
}

.ccd-hint {
  padding: 5px 16px 7px !important;
  font-family: 'IBM Plex Sans', sans-serif !important;
  font-size: 0.67rem !important;
  color: var(--text-3) !important;
  letter-spacing: 0.04em !important;
  border-top: 1px solid var(--border) !important;
  background: var(--inset) !important;
}

/* ═══════════════════════════════════════
   EXAMPLES
═══════════════════════════════════════ */
.gr-examples, .examples-holder {
  background: transparent !important;
}

.gr-examples button, .example {
  background: var(--card) !important;
  border: 1px solid var(--border) !important;
  border-radius: 6px !important;
  color: var(--text-2) !important;
  font-family: 'IBM Plex Sans', sans-serif !important;
  font-size: 0.78rem !important;
  padding: 5px 12px !important;
  transition: border-color 0.15s, color 0.15s !important;
  box-shadow: var(--shadow-sm) !important;
}

.gr-examples button:hover, .example:hover {
  border-color: var(--blue) !important;
  color: var(--blue) !important;
  background: var(--card) !important;
}

/* ═══════════════════════════════════════
   TYPOGRAPHY & MISC
═══════════════════════════════════════ */
p, span, div, li, td, th, button, input, textarea, select {
  font-family: 'IBM Plex Sans', sans-serif !important;
}

h1, h2, h3, h4, h5, h6 {
  font-family: 'Fraunces', Georgia, serif !important;
  color: var(--navy) !important;
}

label > span, .label-wrap span {
  font-family: 'IBM Plex Sans', sans-serif !important;
  font-size: 0.70rem !important;
  font-weight: 600 !important;
  letter-spacing: 0.08em !important;
  text-transform: uppercase !important;
  color: var(--text-3) !important;
}

/* Code blocks in messages */
code, pre {
  font-family: 'IBM Plex Mono', monospace !important;
  background: var(--inset) !important;
  border: 1px solid var(--border) !important;
  border-radius: 4px !important;
  font-size: 0.85em !important;
  color: var(--navy) !important;
}

/* Scrollbar */
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb {
  background: var(--border-strong);
  border-radius: 99px;
}
::-webkit-scrollbar-thumb:hover {
  background: #9aa5b4;
}

/* Footer */
footer { display: none !important; }

@media (max-width: 720px) {
  .hero-brand {
    flex-wrap: wrap;
  }

  .pwa-install-button {
    width: 100%;
    margin-left: 0;
    margin-top: 12px;
  }
}
"""

_PWA_HEAD = f"""
<link rel="manifest" href="/manifest.webmanifest">
<meta name="theme-color" content="{PWA_THEME_COLOR}">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="{APP_TITLE}">
<meta name="apple-mobile-web-app-status-bar-style" content="default">
<link rel="apple-touch-icon" href="/pwa-icon-192.png">
"""

_HERO_HTML = f"""
<section class="unab-hero" aria-label="Encabezado TuNaveganteCCD">
  <div class="hero-brand">
    <img class="hero-logo" src="{UNAB_LOGO_URL}" alt="Logo UNAB" />
    <div class="hero-divider" aria-hidden="true"></div>
    <div class="hero-id">
      <span class="hero-unit">Centro de Competencias Digitales</span>
      <span class="hero-institution">Universidad Autónoma de Bucaramanga</span>
    </div>
    <button
      id="pwa-install-button"
      class="pwa-install-button"
      type="button"
      aria-label="Descargar {APP_TITLE} como aplicación"
    >
      Descargar app
    </button>
  </div>
  <div class="hero-body">
    <h1 class="hero-title">{APP_TITLE}</h1>
    <p class="hero-desc">
      Asistente virtual del CCD para orientarte en tu Ruta de Competencias Digitales,
      cursos disponibles, documentos institucionales e Insignia Digital.
    </p>
    <nav class="hero-tags" aria-label="Áreas de consulta">
      <span class="tag red">Ruta CCD</span>
      <span class="tag amber">Cursos</span>
      <span class="tag blue">RAG documental</span>
      <span class="tag green">Insignia digital</span>
    </nav>
  </div>
</section>
"""

_THEME = gr.themes.Base(
    primary_hue=gr.themes.colors.red,
    secondary_hue=gr.themes.colors.blue,
    neutral_hue=gr.themes.colors.slate,
    font=[
        gr.themes.GoogleFont("IBM Plex Sans"),
        "system-ui",
        "sans-serif",
    ],
    font_mono=[gr.themes.GoogleFont("IBM Plex Mono"), "monospace"],
).set(
    body_background_fill="#edf0f4",
    body_text_color="#0e2140",
    background_fill_primary="#ffffff",
    background_fill_secondary="#f5f7fa",
    border_color_primary="#d4d9e0",
    border_color_accent="#c41e24",
    block_background_fill="#ffffff",
    block_border_color="#d4d9e0",
    block_border_width="1px",
    input_background_fill="#ffffff",
    input_background_fill_focus="#ffffff",
    input_border_color="#d4d9e0",
    input_border_color_focus="#0058a8",
    input_shadow_focus="0 0 0 3px rgba(0, 88, 168, 0.12)",
    input_placeholder_color="#8896a6",
    button_primary_background_fill="#c41e24",
    button_primary_background_fill_hover="#a11820",
    button_primary_text_color="#ffffff",
    button_primary_text_color_hover="#ffffff",
    button_secondary_background_fill="#ffffff",
    button_secondary_background_fill_hover="#f5f7fa",
    button_secondary_text_color="#0e2140",
    button_secondary_border_color="#d4d9e0",
    shadow_drop="0 1px 3px rgba(14,33,64,0.07), 0 1px 2px rgba(14,33,64,0.04)",
    shadow_drop_lg="0 2px 8px rgba(14,33,64,0.07), 0 1px 3px rgba(14,33,64,0.04)",
)


def build_gradio_app() -> gr.Blocks:
    with gr.Blocks(
        title=APP_TITLE,
        fill_height=True,
    ) as demo:
        gr.HTML(_HERO_HTML)

        chatbot = gr.Chatbot(
            label="Chat con TuNaveganteCCD",
            height=520,
            elem_id="chatbot",
            buttons=["copy", "copy_all"],
            avatar_images=(None, UNAB_LOGO_URL),
            value=[
                {
                    "role": "assistant",
                    "content": (
                        "¡Hola! Soy **TuNaveganteCCD**. Para iniciar, escribe tu código UNAB "
                        "o usa `/ayuda` para ver todo lo que puedo hacer por ti."
                    ),
                }
            ],
        )

        gr.ChatInterface(
            fn=send_message_to_n8n,
            chatbot=chatbot,
            textbox=gr.Textbox(
                placeholder="Escribe tu código UNAB o un comando (escribe / para ver la lista)",
                container=False,
                scale=7,
                elem_id="message_box",
                submit_btn="Enviar",
            ),
            examples=[cmd["cmd"] for cmd in SLASH_COMMANDS]
            + [
                "¿Qué necesito para completar la Ruta de Competencias Digitales?",
            ],
        )

    return demo


_FORCE_LIGHT_THEME_JS = """
(function () {
  // The UNAB theme is a light theme, but Gradio honours the visitor's system
  // colour scheme by default and falls into dark mode — which leaves the CSS
  // variables (block backgrounds, borders, icon buttons, typing dots) resolving
  // to dark values. Lock the app to light so the configured theme applies.
  try {
    var params = new URLSearchParams(window.location.search);
    if (params.get('__theme') !== 'light') {
      params.set('__theme', 'light');
      window.location.search = params.toString();
    }
  } catch (error) {
    document.documentElement.classList.remove('dark');
    document.body.classList.remove('dark');
  }
}());
"""

_CMD_AUTOCOMPLETE_JS = f"""
(function () {{
  const COMMANDS = {json.dumps(SLASH_COMMANDS, ensure_ascii=False)};

  let drop = null;
  let activeIdx = -1;
  let attachedTo = null;

  function findTextInput() {{
    return (
      document.querySelector('#message_box textarea') ||
      document.querySelector('#message_box input[type="text"]') ||
      document.querySelector('textarea[data-testid="textbox"]') ||
      document.querySelector('input[data-testid="textbox"]')
    );
  }}

  function getQuery(ta) {{
    const val = (ta.value || '').trimStart();
    if (val.startsWith('/') && !val.includes(' ')) return val;
    return null;
  }}

  function filterCommands(q) {{
    if (q === '/') return COMMANDS.slice();
    return COMMANDS.filter(function (c) {{ return c.cmd.indexOf(q) === 0; }});
  }}

  function ensureDrop(container) {{
    if (drop && container.contains(drop)) return;
    drop = document.createElement('div');
    drop.id = 'ccd-cmd-drop';
    Object.assign(drop.style, {{
      position: 'absolute',
      bottom: 'calc(100% + 10px)',
      left: '0',
      right: '0',
      zIndex: '9999',
      display: 'none',
    }});
    container.appendChild(drop);
  }}

  function render(items) {{
    drop.innerHTML =
      items.map(function (c, i) {{
        var cls = 'ccd-item' + (i === activeIdx ? ' ccd-active' : '');
        return '<div class="' + cls + '" data-i="' + i + '">' +
          '<code>' + c.cmd + '</code>' +
          '<span>' + c.desc + '</span>' +
          '</div>';
      }}).join('') +
      '<div class="ccd-hint">↑↓ navegar &nbsp;·&nbsp; Enter / Tab seleccionar &nbsp;·&nbsp; Esc cerrar</div>';

    drop.querySelectorAll('.ccd-item').forEach(function (el) {{
      el.addEventListener('mousedown', function (e) {{
        e.preventDefault();
        selectCmd(attachedTo, parseInt(el.getAttribute('data-i'), 10));
      }});
    }});
  }}

  function showDrop(ta) {{
    var q = getQuery(ta);
    if (!q) {{ hideDrop(); return; }}
    var filtered = filterCommands(q);
    if (!filtered.length) {{ hideDrop(); return; }}

    var container = ta.closest('.input-container') || ta.parentElement;
    container.style.position = 'relative';
    ensureDrop(container);

    activeIdx = -1;
    drop._items = filtered;
    render(filtered);
    drop.style.display = 'block';
  }}

  function hideDrop() {{
    if (drop) drop.style.display = 'none';
    activeIdx = -1;
  }}

  function selectCmd(ta, idx) {{
    if (!drop || !drop._items) return;
    var cmd = drop._items[idx].cmd;
    var proto = ta.tagName === 'INPUT'
      ? HTMLInputElement.prototype
      : HTMLTextAreaElement.prototype;
    var nativeSetter = Object.getOwnPropertyDescriptor(proto, 'value').set;
    nativeSetter.call(ta, cmd + ' ');
    ta.dispatchEvent(new Event('input', {{ bubbles: true }}));
    hideDrop();
    ta.focus();
  }}

  function attachTo(ta) {{
    if (ta._ccdAttached) return;
    ta._ccdAttached = true;
    attachedTo = ta;

    ta.addEventListener('input', function () {{ showDrop(ta); }});
    ta.addEventListener('focus', function () {{ showDrop(ta); }});

    ta.addEventListener('keydown', function (e) {{
      if (!drop || drop.style.display === 'none') return;
      var items = drop._items || [];
      if (e.key === 'ArrowDown') {{
        e.preventDefault();
        activeIdx = Math.min(activeIdx + 1, items.length - 1);
        render(items);
      }} else if (e.key === 'ArrowUp') {{
        e.preventDefault();
        activeIdx = Math.max(activeIdx - 1, 0);
        render(items);
      }} else if ((e.key === 'Enter' || e.key === 'Tab') && activeIdx >= 0) {{
        e.preventDefault();
        e.stopPropagation();
        selectCmd(ta, activeIdx);
      }} else if (e.key === 'Escape') {{
        hideDrop();
      }}
    }});

    ta.addEventListener('blur', function () {{
      setTimeout(hideDrop, 160);
    }});
  }}

  function tryAttach() {{
    var ta = findTextInput();
    if (ta && !ta._ccdAttached) attachTo(ta);
  }}

  tryAttach();
  var observer = new MutationObserver(tryAttach);
  observer.observe(document.body, {{ childList: true, subtree: true }});
}})();
"""

_PWA_INSTALL_JS = """
(function () {
  let deferredInstallPrompt = null;
  let installButton = null;

  function isStandalone() {
    return window.matchMedia('(display-mode: standalone)').matches ||
      window.navigator.standalone === true;
  }

  function isIOS() {
    const ua = window.navigator.userAgent || '';
    const iOSDevice = /iPad|iPhone|iPod/.test(ua);
    // iPadOS 13+ reports as Mac but exposes touch support.
    const iPadOS = navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1;
    return iOSDevice || iPadOS;
  }

  function setInstalledState() {
    if (!installButton) return;
    installButton.textContent = 'App instalada';
    installButton.disabled = true;
    installButton.classList.add('is-installed');
    installButton.setAttribute('aria-label', 'TuNaveganteCCD ya está instalada');
  }

  function setReadyState() {
    if (!installButton) return;
    installButton.textContent = 'Descargar app';
    installButton.disabled = false;
    installButton.classList.remove('is-installed');
    installButton.setAttribute('aria-label', 'Descargar TuNaveganteCCD como aplicación');
  }

  function buildInstructions() {
    if (isIOS()) {
      return {
        title: 'Instalar en iPhone o iPad',
        steps: [
          'Abre esta página en Safari (no en otra app).',
          'Toca el botón Compartir (el cuadro con la flecha hacia arriba).',
          'Elige "Añadir a pantalla de inicio".',
          'Confirma con "Añadir" y abre TuNaveganteCCD desde tu pantalla de inicio.'
        ]
      };
    }
    return {
      title: 'Instalar la app',
      steps: [
        'Abre el menú del navegador (los tres puntos ⋮).',
        'Elige "Instalar app" o "Añadir a pantalla de inicio".',
        'Confirma la instalación y abre TuNaveganteCCD como aplicación.'
      ]
    };
  }

  function closeInstructions() {
    const overlay = document.getElementById('pwa-install-overlay');
    if (overlay) overlay.remove();
  }

  function showInstructions() {
    closeInstructions();

    const info = buildInstructions();

    const overlay = document.createElement('div');
    overlay.id = 'pwa-install-overlay';
    overlay.className = 'pwa-install-overlay';
    overlay.setAttribute('role', 'dialog');
    overlay.setAttribute('aria-modal', 'true');
    overlay.setAttribute('aria-label', info.title);

    const dialog = document.createElement('div');
    dialog.className = 'pwa-install-dialog';

    const heading = document.createElement('h2');
    heading.className = 'pwa-install-dialog-title';
    heading.textContent = info.title;

    const list = document.createElement('ol');
    list.className = 'pwa-install-dialog-steps';
    info.steps.forEach(function (step) {
      const item = document.createElement('li');
      item.textContent = step;
      list.appendChild(item);
    });

    const close = document.createElement('button');
    close.type = 'button';
    close.className = 'pwa-install-dialog-close';
    close.textContent = 'Entendido';
    close.addEventListener('click', closeInstructions);

    dialog.appendChild(heading);
    dialog.appendChild(list);
    dialog.appendChild(close);
    overlay.appendChild(dialog);

    overlay.addEventListener('click', function (event) {
      if (event.target === overlay) closeInstructions();
    });
    document.addEventListener('keydown', function onKey(event) {
      if (event.key === 'Escape') {
        closeInstructions();
        document.removeEventListener('keydown', onKey);
      }
    });

    document.body.appendChild(overlay);
    close.focus();
  }

  function attachInstallButton() {
    const button = document.getElementById('pwa-install-button');
    if (!button || button._pwaInstallAttached) return;

    installButton = button;
    button._pwaInstallAttached = true;

    if (isStandalone()) {
      setInstalledState();
      return;
    }

    setReadyState();

    button.addEventListener('click', async function () {
      if (isStandalone()) {
        setInstalledState();
        return;
      }

      // The native prompt is only available on Chromium browsers that fired
      // `beforeinstallprompt`. iOS and any browser without it get clear
      // step-by-step instructions instead of a dead button.
      if (!deferredInstallPrompt) {
        showInstructions();
        return;
      }

      deferredInstallPrompt.prompt();
      await deferredInstallPrompt.userChoice.catch(function () { return null; });
      deferredInstallPrompt = null;
      setReadyState();
    });
  }

  if ('serviceWorker' in navigator) {
    window.addEventListener('load', function () {
      navigator.serviceWorker.register('/service-worker.js', { scope: '/' })
        .catch(function (error) {
          console.warn('No se pudo registrar el service worker de la PWA.', error);
        });
    });
  }

  window.addEventListener('beforeinstallprompt', function (event) {
    event.preventDefault();
    deferredInstallPrompt = event;
    setReadyState();
  });

  window.addEventListener('appinstalled', function () {
    deferredInstallPrompt = null;
    setInstalledState();
  });

  attachInstallButton();

  const observer = new MutationObserver(attachInstallButton);
  observer.observe(document.body, { childList: true, subtree: true });
}());
"""

_CHATBOT_LOADING_CLEANUP_JS = """
(function () {
  const LOADING_SELECTOR = [
    '[class*="pending"]',
    '[class*="loading"]',
    '[class*="generating"]',
    '[class*="typing"]',
    '[class*="dot"]'
  ].join(',');

  function isChatBusy() {
    const submitButton = document.querySelector('button[data-testid="submit-button"]');
    const stopButton = document.querySelector('button[data-testid="stop-button"]');

    return Boolean(
      stopButton ||
      (submitButton && (
        submitButton.disabled ||
        submitButton.getAttribute('aria-disabled') === 'true'
      ))
    );
  }

  function looksLikeLoadingOnly(el) {
    const text = (el.textContent || '').trim();
    return text === '' || /^[.\\u2022\\u2026]+$/.test(text);
  }

  function clearStaleUserLoading() {
    if (isChatBusy()) return;

    const chatbot = document.getElementById('chatbot');
    if (!chatbot) return;

    chatbot.querySelectorAll('[data-testid="user"] .message, .message.user').forEach(function (message) {
      message.classList.remove('pending', 'loading', 'generating', 'typing');

      message.querySelectorAll(LOADING_SELECTOR).forEach(function (el) {
        if (looksLikeLoadingOnly(el)) {
          el.remove();
          return;
        }

        el.classList.remove('pending', 'loading', 'generating', 'typing', 'dot');
      });
    });
  }

  let cleanupTimer = null;

  function scheduleCleanup() {
    window.clearTimeout(cleanupTimer);
    cleanupTimer = window.setTimeout(clearStaleUserLoading, 400);
  }

  window.addEventListener('load', scheduleCleanup);

  const observer = new MutationObserver(scheduleCleanup);
  observer.observe(document.body, {
    childList: true,
    subtree: true,
    attributes: true,
    attributeFilter: ['class', 'disabled', 'aria-disabled']
  });
}());
"""


gradio_app = build_gradio_app()
app = gr.mount_gradio_app(
    app,
    gradio_app,
    path="/",
    css=UNAB_CSS,
    theme=_THEME,
    js=_FORCE_LIGHT_THEME_JS
    + _CMD_AUTOCOMPLETE_JS
    + _PWA_INSTALL_JS
    + _CHATBOT_LOADING_CLEANUP_JS,
    head=_PWA_HEAD,
    pwa=True,
)


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("APP_PORT", "8000")),
        reload=True,
    )
