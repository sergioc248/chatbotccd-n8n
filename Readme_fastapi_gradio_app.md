# TuNaveganteCCD FastAPI + Gradio

Frontend web para el chatbot del Centro de Competencias Digitales (CCD) de la UNAB. La aplicación expone un servidor FastAPI y monta una interfaz Gradio en la ruta principal `/`, pensada para conectarse con un workflow de n8n mediante el nodo Chat Trigger.

## Ejecución local

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edita `.env` y configura `N8N_WEBHOOK_URL` con la URL pública del Chat Trigger de n8n.

```bash
export $(grep -v '^#' .env | xargs)
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Abre `http://localhost:8000`.

También puedes ejecutarlo directamente:

```bash
python main.py
```

## Variables de entorno

| Variable | Descripción |
|---|---|
| `N8N_WEBHOOK_URL` | URL pública del webhook del Chat Trigger de n8n. |
| `N8N_TIMEOUT_SECONDS` | Tiempo máximo de espera para n8n. Por defecto: `45`. |
| `UNAB_LOGO_URL` | URL del logo mostrado en la interfaz. Reemplázala por el activo oficial de MiPortalU cuando esté disponible. |

## Contrato enviado a n8n

Cada mensaje del chat envía un `POST` JSON al webhook:

```json
{
  "action": "sendMessage",
  "sessionId": "session-hash-de-gradio",
  "chatInput": "mensaje del estudiante",
  "metadata": {
    "source": "gradio-fastapi",
    "app": "TuNaveganteCCD",
    "institution": "UNAB",
    "unit": "CCD",
    "historyLength": 2
  }
}
```

La app intenta leer la respuesta de n8n desde cualquiera de estas claves comunes: `output`, `text`, `response`, `message` o `answer`.

## Docker

### Docker Compose (recomendado)

```bash
cp .env.example .env
# Edita .env y define N8N_WEBHOOK_URL

docker compose up -d --build
docker compose logs -f app
```

Abre `http://localhost:8000`. Para detener: `docker compose down`.

En un VPS detrás de Nginx, enlaza solo en localhost editando `docker-compose.yml`:

```yaml
ports:
  - "127.0.0.1:8000:8000"
```

### Docker sin Compose

```bash
docker build -t tunavegante-ccd .
docker run --rm -p 8000:8000 \
  -e N8N_WEBHOOK_URL="https://n8n.tudominio.com/webhook/tu-chat-trigger" \
  tunavegante-ccd
```

## Endpoints

- `/`: interfaz Gradio del chatbot.
- `/api/health`: estado del servicio y confirmación de configuración del webhook.
- `/docs`: documentación OpenAPI de FastAPI.
