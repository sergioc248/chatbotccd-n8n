# 🎓 TuNaveganteCCD — Asistente Virtual del Centro de Competencias Digitales UNAB

> Chatbot conversacional de IA que guía a los estudiantes de la Universidad Autónoma de Bucaramanga (UNAB) a través de su Ruta de Competencias Digitales. Combina un **agente inteligente con memoria, herramientas y RAG** orquestado en **n8n Cloud**, con un **frontend web FastAPI + Gradio (PWA)** desplegado en una **máquina virtual de Azure**.

---

## 📋 Tabla de Contenidos

- [Descripción del Problema](#-descripción-del-problema)
- [Solución Propuesta](#-solución-propuesta)
- [Arquitectura del Sistema](#-arquitectura-del-sistema)
- [Stack Tecnológico](#-stack-tecnológico)
- [Frontend FastAPI + Gradio (Azure VM)](#-frontend-fastapi--gradio-azure-vm)
- [Workflow n8n: `CCD Bot IngenioTIC`](#-workflow-n8n-ccd-bot-ingeniotic)
- [Sub-workflow: `CCD - Consulta Base de Datos`](#-sub-workflow-ccd---consulta-base-de-datos)
- [Bases de Datos (Neon)](#-bases-de-datos-neon)
- [Sistema RAG](#-sistema-rag)
- [Comandos del Bot](#-comandos-del-bot)
- [Variables de Entorno y Credenciales](#-variables-de-entorno-y-credenciales)
- [Despliegue](#-despliegue)
- [Limitaciones Conocidas](#-limitaciones-conocidas)
- [Contribución](#-contribución)

---

## 🎯 Descripción del Problema

El Centro de Competencias Digitales (CCD) de la UNAB gestiona la **Ruta de Competencias Digitales**, un programa que certifica a estudiantes en tres pilares de habilidades digitales. Los estudiantes frecuentemente necesitan consultar:

- Su estado de avance en la ruta (pilares cumplidos / pendientes)
- Cursos completados (aprobados ✅ / reprobados ❌)
- Reglamentos, instructivos y documentos institucionales
- Fechas del calendario académico del CCD
- Requisitos para obtener la Insignia de Competencias Digitales

Esta información estaba dispersa entre el portal web, documentos PDF y el sistema de gestión académica, generando carga operativa al personal del CCD y fricción para los estudiantes.

---

## 💡 Solución Propuesta

**TuNaveganteCCD** es un chatbot basado en IA Generativa + Agente Inteligente que:

1. **Autentica** al estudiante por su código UNAB, sin contraseñas y persistiendo la sesión.
2. **Consulta en tiempo real** la base de datos institucional (Cosmos) para datos personalizados.
3. **Busca semánticamente** en documentos vectorizados (RAG) para reglamentos y contenidos.
4. **Recuerda el contexto** de la conversación con memoria persistente en PostgreSQL.
5. **Consulta el calendario** institucional de Google Calendar para eventos y fechas 2026.
6. **Responde en lenguaje natural** en español, con tono amigable y emojis.

El estudiante interactúa a través de una **web app FastAPI + Gradio** (con soporte PWA "instalable") o del **widget de Chat Trigger** propio de n8n.

---

## 🏗️ Arquitectura del Sistema

```
┌───────────────────────────────────────────────────────────────────────────┐
│  FRONTEND — FastAPI + Gradio (PWA)        ☁️ Azure Virtual Machine          │
│  main.py · uvicorn :8000 · service worker · autocompletado de comandos       │
└───────────────────────────────┬─────────────────────────────────────────────┘
                                │  POST JSON  { action, sessionId, chatInput, metadata }
                                ▼
┌───────────────────────────────────────────────────────────────────────────┐
│  n8n CLOUD  ·  Workflow: "CCD Bot IngenioTIC"                                │
│                                                                              │
│  Chat Trigger ─▶ Init DB ─▶ Verificar Sesión ─▶ Merge Sesion ─▶ ¿Autenticado?│
│                                                          ┌────────┴────────┐  │
│                                                    NO ▼          ▼ SÍ        │
│                                         Es Código Estudiante   Switch Comandos│
│                                                │                   │          │
│                                       Validar Estudiante   Prompt: /…  (11)  │
│                                                │                   │          │
│                                       Guardar Sesión        ┌──────▼───────┐  │
│                                                │            │   AI AGENT    │  │
│                                       Bienvenida Auth       │ (Tools Agent) │  │
│                                                             └──┬───┬───┬────┘  │
│   ┌──────────── sub-nodos del AI Agent ───────────────────────┘   │   │       │
│   │  • LLM:    OpenCode API  (deepseek-v4-flash)                  │   │       │
│   │  • Memory: Postgres Chat Memory (n8n_ccd)                      │   │       │
│   │  • Tools:  CCD_DB_Tool · Documentos_CCD_Tool · Calendario_CCD_Tool      │
│   └──────────────────────────────────────────────────────────────┘          │
│        │                         │                          │                 │
│        ▼                         ▼                          ▼                 │
│  Sub-workflow SQL        PGVector + Embeddings        Google Calendar          │
│  "Consulta BD"           (RAG, OpenRouter QA)         (eventos 2026)            │
└────────┬─────────────────────────┬───────────────────────────────────────────┘
         │                         │
         ▼                         ▼
┌──────────────────────┐  ┌──────────────────────────────────────────────┐
│  NEON · Cosmos DB     │  │  NEON · n8n_ccd DB                            │
│  (datos institucional)│  │  (datos del chatbot)                          │
│  • estudiante         │  │  • ccd_sesiones      (autenticación)          │
│  • registro_nota      │  │  • n8n_chat_histories(memoria conversación)   │
│  • catalogo_materias  │  │  • ccd_documentos    (vector store / RAG)     │
│  • oferta_vigente     │  │                                              │
│  • progreso_estudiante│  │                                              │
└──────────────────────┘  └──────────────────────────────────────────────┘
```

**Componentes principales**

| Capa | Implementación | Hosting |
|---|---|---|
| Frontend | FastAPI + Gradio (PWA), `main.py` | Azure Virtual Machine |
| Orquestación / Agente | Workflow `CCD Bot IngenioTIC` + sub-workflow `CCD - Consulta Base de Datos` | n8n Cloud |
| Bases de datos | PostgreSQL `cosmos` (institucional) y `n8n_ccd` (chatbot + RAG) | Neon (serverless Postgres) |

---

## 🛠️ Stack Tecnológico

| Componente | Tecnología | Rol |
|---|---|---|
| **Orquestación** | n8n Cloud | Motor de workflow, agente y herramientas |
| **Frontend** | FastAPI + Gradio (PWA) | Interfaz web del chat, hospedada en Azure VM |
| **LLM del agente** | OpenCode API — `deepseek-v4-flash` | Razonamiento del Tools Agent y generación de respuestas |
| **LLM del RAG** | OpenRouter `poolside/laguna-xs.2:free` ("Laguna") | QA sobre documentos recuperados del vector store |
| **Embeddings** | OpenAI Embeddings | Vectorización de documentos y consultas (RAG) |
| **Vector Store** | PostgreSQL + `pgvector` (`ccd_documentos`) | Búsqueda semántica de documentos |
| **Base de datos institucional** | Neon Postgres (`cosmos`) | Estudiantes, notas, catálogo, oferta, progreso |
| **Base de datos del chatbot** | Neon Postgres (`n8n_ccd`) | Sesiones, memoria de chat y vector store |
| **Memoria conversacional** | Postgres Chat Memory (n8n LangChain) | Historial persistente (ventana de contexto = 2) |
| **Calendario** | Google Calendar Tool | Eventos y fechas académicas del CCD (2026) |
| **Punto de entrada** | n8n Chat Trigger (webhook) | Recibe mensajes del frontend / widget |

> **Modelos alternos.** El workflow incluye nodos de modelo adicionales desconectados (Groq, NVIDIA Nemotron, OpenRouter) que sirven como reemplazos rápidos del LLM; solo los conectados arriba están activos.

---

## 🖥️ Frontend FastAPI + Gradio (Azure VM)

El archivo [`main.py`](./main.py) levanta un servidor **FastAPI** que monta una interfaz **Gradio** en la raíz `/`. Se ejecuta con `uvicorn` en el puerto `8000` dentro de una **máquina virtual de Azure** (normalmente detrás de Nginx con TLS).

### Características

- **Interfaz de chat** con la identidad visual de la UNAB (tema claro forzado, tipografías IBM Plex / Fraunces, paleta institucional).
- **PWA instalable**: `manifest.webmanifest`, `service-worker.js`, iconos SVG generados en runtime y botón "Descargar app".
- **Autocompletado de comandos**: al escribir `/` aparece un desplegable con los comandos disponibles (definidos en `SLASH_COMMANDS`).
- **Mensaje de bienvenida** y ejemplos de comandos precargados.

### Contrato hacia n8n

Cada mensaje enviado por el usuario realiza un `POST` JSON al webhook del Chat Trigger (`N8N_WEBHOOK_URL`):

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

El `sessionId` proviene del `session_hash` de Gradio (o un UUID de respaldo) y es la **clave de sesión** que n8n usa para autenticación y memoria. La app lee la respuesta de n8n desde cualquiera de las claves: `output`, `text`, `response`, `message` o `answer`.

### Endpoints

| Ruta | Descripción |
|---|---|
| `/` | Interfaz Gradio del chatbot |
| `/api/health` | Estado del servicio y confirmación de `N8N_WEBHOOK_URL` |
| `/docs` | Documentación OpenAPI de FastAPI |
| `/manifest.webmanifest`, `/service-worker.js`, `/pwa-icon-*.svg` | Activos de la PWA |

### Ejecución local

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # define N8N_WEBHOOK_URL

uvicorn main:app --host 0.0.0.0 --port 8000 --reload
# o bien:  python main.py
```

Abre `http://localhost:8000`.

---

## 🧩 Workflow n8n: `CCD Bot IngenioTIC`

Workflow principal (activo) en n8n Cloud, con **43 nodos**. Recibe el mensaje, autentica, enruta comandos y ejecuta el agente.

### Flujo de ejecución

```
Chat Trigger ─▶ Init DB ─▶ Verificar Sesión ─▶ Merge Sesion ─▶ ¿Autenticado?
                                                                   │
        ┌──────────────────────── SÍ ◀────────────────┴──────▶ NO ───────────────┐
        ▼                                                                          ▼
  Switch Comandos                                                       Es Codigo Estudiante
        │ (11 salidas)                                                   │            │
        ├─ /inicio, /ayuda, /ruta, /cursos,                       (parece código) (no)
        │  /documentos, /perfil, /insignia, /siguiente ─▶ Prompt: /…       │            └─▶ Pedir Código
        ├─ /calendario ─▶ Get many events ─▶ Prompt: /calendario           ▼
        ├─ chat libre (regex ^[^/]) ─▶ Prompt: Chat Libre          Validar Estudiante
        └─ desconocido (^/) ─▶ Prompt: Comando Desconocido                 │
                       │                                          ¿Estudiante Existe?
                       ▼                                            │            │
                   AI AGENT ─▶ Respuesta Agente                 (sí)│        (no)│
                                                          Guardar Sesión   Codigo No Encontrado
                                                                 │
                                                          Bienvenida Auth ─▶ Error Amigable
```

> El `Chat Trigger` también conecta a `Prompt: Error → AI Agent` como ruta de respaldo ante fallos.

### Secciones y nodos clave

**Entrada y sesión**
- `Chat Trigger` — recibe el mensaje vía webhook.
- `Init DB` — `CREATE TABLE IF NOT EXISTS ccd_sesiones (...)` en `n8n_ccd` (idempotente).
- `Verificar Sesión` — busca el `sessionId` en `ccd_sesiones` (devuelve `id_estudiante`, `nombre_completo`, `plan`).
- `Merge Sesion` — unifica el estado de sesión y normaliza el contexto para los nodos siguientes.

**Autenticación**
- `¿Autenticado?` — bifurca según exista sesión con código.
- `Es Codigo Estudiante` → `Validar Estudiante` (consulta `estudiante`, `activo = TRUE`; deriva el plan con `anio_ingreso >= 2025 → 'Nuevo'`, si no `'Antiguo'`).
- `¿Estudiante Existe?` → `Guardar Sesión` (UPSERT en `ccd_sesiones`) → `Bienvenida Auth`, o `Codigo No Encontrado`.
- `Pedir Código` — solicita el código cuando aún no hay sesión.

**Router de comandos** — `Switch Comandos` con 11 salidas (ver tabla de [Comandos](#-comandos-del-bot)). Cada salida arma el `chatInput` enriquecido en un nodo `Prompt: /…` (Set o Code) y lo pasa al agente. `/calendario` primero ejecuta `Get many events` (Google Calendar) para inyectar los eventos en el prompt.

**Núcleo de IA** — `AI Agent` (Tools Agent) con:
- **LLM:** nodo OpenAI Chat Model (API compatible con OpenAI) apuntando a la **API de OpenCode** → modelo `deepseek-v4-flash`.
- **Memoria:** `Postgres Chat Memory` (clave = `session_id`, ventana de contexto = 2).
- **Herramientas:** `CCD_DB_Tool`, `Documentos_CCD_Tool`, `Calendario_CCD_Tool`.
- **System message:** identidad de TuNaveganteCCD; inyecta `id_estudiante`, `nombre_completo` y `plan` de la sesión vía expresión n8n.

**Salida** — `Respuesta Agente` formatea la respuesta final que se devuelve al frontend.

### Herramientas del agente

| Herramienta | Tipo | Función |
|---|---|---|
| `CCD_DB_Tool` | `toolWorkflow` | Ejecuta SQL crudo contra **Cosmos** llamando al sub-workflow `CCD - Consulta Base de Datos`. |
| `Documentos_CCD_Tool` | `toolVectorStore` (`topK = 3`) | RAG sobre documentos institucionales (vector store `ccd_documentos`). QA con OpenRouter "Laguna". |
| `Calendario_CCD_Tool` | `googleCalendarTool` | Lee el calendario `CCD Calendario n8n` (eventos 2026, zona `America/Bogota`). |

---

## 🔁 Sub-workflow: `CCD - Consulta Base de Datos`

Workflow auxiliar invocado por `CCD_DB_Tool`. Aísla el acceso SQL a **Cosmos** y **comprime** el resultado antes de devolverlo al agente (clave para reducir tokens).

```
Execute Workflow Trigger ─▶ Consultar Postgres ─▶ Comprimir Resultado
       (recibe `query`)        (executeQuery,         (Code node)
                                contra Cosmos)
```

- **`Consultar Postgres`** — `operation: executeQuery`, `query: {{ $json.query ?? $json.input }}`. Ejecuta el SQL que el agente envía como texto plano.
- **`Comprimir Resultado`** — nodo Code que:
  - Elimina campos `null`, `undefined` o vacíos de cada fila.
  - Limita a **`MAX_ROWS = 50`** filas y anota cuántas se omitieron.
  - Devuelve un único `result` con el JSON compactado.

> 💡 **Optimización de tokens.** Como el resultado se comprime aquí, conviene que el SQL de cada prompt seleccione **solo las columnas necesarias** y use `LIMIT` explícito (p. ej. `/cursos` ya no trae `observacion`/`tipo_registro` y limita a 100 filas). Esto reduce el tamaño en origen, antes de la compresión.

---

## 🗄️ Bases de Datos (Neon)

Ambas bases corren en **Neon** (PostgreSQL serverless). Se separan por responsabilidad:

### 1. `cosmos` — datos institucionales (solo lectura para el bot)

Accedida exclusivamente vía `CCD_DB_Tool` → sub-workflow SQL.

| Tabla | Columnas relevantes |
|---|---|
| `estudiante` | `id_estudiante`, `nombre_completo`, `programa_academico`, `facultad`, `anio_ingreso`, `semestre_actual`, `email`, `telefono`, `activo` |
| `registro_nota` | `id_estudiante`, `codigo_materia`, `nota` (`A`=aprobado, `R`=reprobado), `fecha_registro`, `tipo_registro`, `observacion` |
| `catalogo_materias_ccd` | `codigo_materia`, `codigo_curso`, `nombre_materia`, `pilar` |
| `oferta_vigente` | `id_oferta`, `codigo_curso`, `nombre_curso`, `pilar`, `modalidad`, `cupos_disponibles`, `fecha_inicio/fin`, `fecha_inicio/fin_matricula`, `aula`, `docente` |
| `progreso_estudiante` | `id_estudiante`, `nombre_completo`, `plan`, `pilar1/2/3_cumplido`, `cursos_aprobados`, `cursos_faltantes` |

> El plan **no** se almacena en `estudiante`: se deriva en `Validar Estudiante` (`anio_ingreso >= 2025 → Nuevo`, de lo contrario `Antiguo`) y se propaga en la sesión.

### 2. `n8n_ccd` — datos del chatbot

| Tabla | Rol |
|---|---|
| `ccd_sesiones` | Sesiones autenticadas (creada por `Init DB`). |
| `n8n_chat_histories` | Memoria de conversación gestionada por `Postgres Chat Memory`. |
| `ccd_documentos` | Vector store del RAG (`pgvector`). |

```sql
-- ccd_sesiones (n8n_ccd) — creada por el nodo "Init DB"
CREATE TABLE IF NOT EXISTS ccd_sesiones (
    session_id    TEXT PRIMARY KEY,
    id_estudiante TEXT,
    nombre_completo TEXT,
    plan          TEXT,
    updated_at    TIMESTAMPTZ DEFAULT NOW()
);

-- ccd_documentos (n8n_ccd) — vector store del RAG
CREATE EXTENSION IF NOT EXISTS vector;
CREATE TABLE IF NOT EXISTS ccd_documentos (
    id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    text      TEXT,
    embedding VECTOR(1536),      -- dimensión de los embeddings de OpenAI
    metadata  JSONB
);
CREATE INDEX ON ccd_documentos USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
```

---

## 📚 Sistema RAG

El RAG permite responder con información precisa de documentos institucionales sin reentrenar el modelo.

**Documentos indexados:** ruta de competencias digitales y su transición, cursos intensivos, pruebas de validación, prueba diagnóstica, reglamentos y preguntas frecuentes.

**Búsqueda en runtime:**

```
Pregunta ─▶ Embeddings OpenAI ─▶ pgvector (top-K = 3, similitud coseno, ccd_documentos)
        ─▶ QA con OpenRouter (poolside/laguna-xs.2:free) ─▶ respuesta fundamentada
```

El nodo `Documentos_CCD_Tool` (Vector Store QA) combina los 3 chunks recuperados con la pregunta y deja que su LLM dedicado genere la respuesta, que el agente integra en la conversación.

---

## 💬 Comandos del Bot

Detectados por `Switch Comandos` (coincidencia exacta del comando; texto libre vía regex `^[^/]`):

| Comando | Descripción |
|---|---|
| `/inicio` | Bienvenida e información general del CCD |
| `/ayuda` | Lista completa de comandos con ejemplos |
| `/ruta` | Estado de avance en los 3 pilares de la ruta |
| `/cursos` | Cursos del estudiante con nota (✅/❌), pilar y fecha |
| `/calendario` | Próximos eventos y fechas académicas (Google Calendar) |
| `/documentos` | Búsqueda en reglamentos y documentos institucionales (RAG) |
| `/perfil` | Datos del estudiante (programa, facultad, semestre, contacto) |
| `/insignia` | Estado y requisitos para la insignia digital + oferta vigente |
| `/siguiente` | Próximo curso recomendado según el pilar pendiente |
| *(texto libre)* | Pregunta abierta respondida por el agente (RAG + BD + calendario) |
| *(comando `/` no reconocido)* | Respuesta de comando desconocido |

---

## 🔐 Variables de Entorno y Credenciales

### Frontend (`main.py`, en la Azure VM)

| Variable | Descripción | Ejemplo |
|---|---|---|
| `N8N_WEBHOOK_URL` | URL pública del Chat Trigger de n8n Cloud | `https://<tenant>.app.n8n.cloud/webhook/<id>` |
| `N8N_TIMEOUT_SECONDS` | Tiempo máximo de espera para n8n (def. `60`) | `60` |
| `UNAB_LOGO_URL` | URL del logo institucional | `https://.../LogoUnab.png` |

### Credenciales en n8n Cloud

| Credencial | Uso |
|---|---|
| **Postgres — Cosmos** | Sub-workflow SQL (`Consultar Postgres`) → base institucional en Neon |
| **Postgres — n8n_ccd** | `Init DB`, `Verificar/Guardar/Validar`, `Postgres Chat Memory`, `PGVector Store` |
| **OpenCode API** | LLM del agente (`deepseek-v4-flash`), vía nodo OpenAI Chat Model con base URL de OpenCode |
| **OpenAI API** | `Embeddings OpenAI` (vectorización del RAG) |
| **OpenRouter API** | QA del RAG — modelo "Laguna" (`poolside/laguna-xs.2:free`) |
| **Google Calendar OAuth2** | `Calendario_CCD_Tool` y `Get many events` |

> Los hosts de Neon usan el sufijo `…neon.tech` y requieren `SSL: require`.

---

## 🚀 Despliegue

### Frontend en Azure Virtual Machine

La interfaz FastAPI + Gradio se publica directamente desde la VM en el puerto `8000`. Acceso actual:

`http://130.107.49.127:8000/?__theme=light`

No es necesario Nginx: basta con configurar las reglas del **Network Security Group** de la VM para permitir el tráfico entrante/saliente en el puerto expuesto (por ejemplo `8000` o `80`). El parámetro `?__theme=light` fuerza el tema claro institucional.

```bash
# En la VM (Ubuntu)
git clone <repo> && cd chatbotccd-n8n
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # define N8N_WEBHOOK_URL al webhook de n8n Cloud

# Ejecución directa (pruebas)
uvicorn main:app --host 0.0.0.0 --port 8000
```

Para endurecer producción (opcional), ejecutar `uvicorn`/Gunicorn como servicio `systemd`, o usar Docker:

```bash
docker compose up -d --build      # publica :8000
```

Si más adelante quieres TLS, puedes añadir **Nginx** como proxy inverso: enlaza la app solo a localhost (`127.0.0.1:8000:8000`) y expón HTTPS en el proxy, ajustando las reglas del **Network Security Group**.

### Backend en n8n Cloud

1. Importar/abrir los workflows en n8n Cloud:
   - `CCD - Consulta Base de Datos` (sub-workflow SQL)
   - `CCD Bot IngenioTIC` (workflow principal)
2. Configurar las credenciales de la tabla anterior (Cosmos, n8n_ccd, OpenAI, OpenRouter, Google Calendar).
3. Activar `CCD Bot IngenioTIC` y copiar la URL del `Chat Trigger`.
4. Colocar esa URL en `N8N_WEBHOOK_URL` del frontend.

### Bases de datos en Neon

1. Crear dos proyectos/bases: `cosmos` (institucional) y `n8n_ccd` (chatbot).
2. En `n8n_ccd`, habilitar `pgvector` y crear `ccd_documentos` (ver SQL arriba). `ccd_sesiones` se crea sola vía `Init DB`.
3. Cargar las tablas institucionales en `cosmos`.

---

## ⚠️ Limitaciones Conocidas

- **Ventana de memoria corta:** `Postgres Chat Memory` usa `contextWindowLength = 2`; conversaciones largas pueden perder contexto previo.
- **Compresión de resultados SQL:** el sub-workflow limita a 50 filas y descarta campos vacíos. Consultas que devuelvan más filas se truncan: usar `LIMIT` y proyecciones específicas en los prompts.
- **Sesiones persistentes:** `ccd_sesiones` no expira automáticamente. Conviene un job de limpieza para sesiones inactivas.
- **Idioma:** optimizado para español; otros idiomas no están garantizados.
- **Calendario:** la herramienta consulta el rango 2026 del calendario `CCD Calendario n8n`; eventos fuera de ese rango no se devuelven.
- **Disponibilidad de modelos:** los LLM compartidos/gratuitos (OpenCode `deepseek-v4-flash`, OpenRouter "Laguna") pueden tener límites de cuota o contexto. Existen modelos alternos desconectados (Groq, NVIDIA Nemotron, OpenRouter) listos para sustituir el principal.

---

## 🤝 Contribución

Proyecto desarrollado en el marco de **IngenioTIC — UNAB**.

1. Crear un fork del repositorio.
2. Exportar el workflow modificado desde n8n (`···` → `Download`).
3. Abrir un Pull Request con descripción del cambio y capturas del workflow.

---

## 📄 Licencia

Uso interno UNAB — Centro de Competencias Digitales. Todos los derechos reservados.

---

*Construido con ❤️ para la Ruta de Competencias Digitales de la UNAB.*
