# 🎓 TuNaveganteCCD — Asistente Virtual del Centro de Competencias Digitales UNAB

> Chatbot de IA conversacional que guía a los estudiantes de la Universidad Autónoma de Bucaramanga (UNAB) a través de su Ruta de Competencias Digitales, respondiendo preguntas institucionales en tiempo real mediante un agente inteligente con memoria, herramientas y búsqueda semántica de documentos (RAG).

---

## 📋 Tabla de Contenidos

- [Descripción del Problema](#-descripción-del-problema)
- [Solución Propuesta](#-solución-propuesta)
- [Arquitectura del Sistema](#-arquitectura-del-sistema)
- [Stack Tecnológico](#-stack-tecnológico)
- [Flujo de Funcionamiento](#-flujo-de-funcionamiento)
- [Estructura del Workflow n8n](#-estructura-del-workflow-n8n)
- [Base de Datos](#-base-de-datos)
- [Sistema RAG](#-sistema-rag)
- [Comandos del Bot](#-comandos-del-bot)
- [Guía de Construcción Paso a Paso](#-guía-de-construcción-paso-a-paso)
- [Variables de Entorno y Credenciales](#-variables-de-entorno-y-credenciales)
- [Carga de Documentos al Vector Store](#-carga-de-documentos-al-vector-store)
- [Despliegue](#-despliegue)
- [Limitaciones Conocidas](#-limitaciones-conocidas)
- [Contribución](#-contribución)

---

## 🎯 Descripción del Problema

El Centro de Competencias Digitales (CCD) de la UNAB gestiona la **Ruta de Competencias Digitales**, un programa que certifica a estudiantes en tres pilares fundamentales de habilidades digitales. Los estudiantes frecuentemente necesitan consultar:

- Su estado de avance en la ruta
- Cursos completados y pendientes
- Reglamentos e instructivos institucionales
- Fechas de calendarios académicos
- Información sobre la Insignia de Competencias Digitales

Toda esta información estaba dispersa en múltiples fuentes (portal web, documentos PDF, sistema de gestión académica), lo que generaba carga operativa al personal del CCD y frustración en los estudiantes que no sabían dónde consultar.

---

## 💡 Solución Propuesta

**TuNaveganteCCD** es un chatbot basado en IA Generativa + Agente Inteligente que:

1. **Autentica** al estudiante por su código UNAB sin necesidad de contraseñas
2. **Consulta en tiempo real** la base de datos institucional para datos personalizados
3. **Busca semánticamente** en documentos vectorizados para responder preguntas sobre reglamentos y contenidos
4. **Recuerda el contexto** de la conversación usando memoria persistente en PostgreSQL
5. **Responde en lenguaje natural** en español, con tono amigable y uso de emojis

---

## 🏗️ Arquitectura del Sistema

```
┌─────────────────────────────────────────────────────────────────────┐
│                        USUARIO (WhatsApp / Web Chat)                 │
└─────────────────────────┬───────────────────────────────────────────┘
                          │ mensaje de chat
                          ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     n8n WORKFLOW ENGINE                              │
│                                                                      │
│  ┌─────────────┐    ┌──────────────┐    ┌────────────────────────┐  │
│  │ Chat Trigger│───▶│   Init DB    │───▶│  Verificar Sesión      │  │
│  └─────────────┘    └──────────────┘    └──────────┬─────────────┘  │
│                                                    │                 │
│                          ┌─────────────────────────▼──────────────┐ │
│                          │         ¿Autenticado?                   │ │
│                          └──────┬──────────────────┬──────────────┘ │
│                       SÍ        │                  │ NO              │
│                    ┌────────────▼──┐      ┌────────▼──────────────┐ │
│                    │ Switch Comandos│      │  Es Código Estudiante │ │
│                    └──────┬────────┘      └────────┬──────────────┘ │
│                           │                        │                 │
│              ┌────────────▼───────────┐   ┌────────▼───────────┐   │
│              │   Prompt Builder       │   │  Validar Estudiante │   │
│              │ (/inicio, /ruta, etc.) │   └────────┬───────────┘   │
│              └────────────┬───────────┘            │                │
│                           │                        │                │
│                    ┌──────▼──────────────────────────────────────┐  │
│                    │              AI AGENT (n8n LangChain)        │  │
│                    │                                              │  │
│                    │  ┌─────────────────┐  ┌──────────────────┐  │  │
│                    │  │  NVIDIA NIM LLM │  │ Postgres Memory  │  │  │
│                    │  │  (Llama 4)      │  │  (Chat History)  │  │  │
│                    │  └─────────────────┘  └──────────────────┘  │  │
│                    │                                              │  │
│                    │  ┌───────────────────────────────────────┐  │  │
│                    │  │               TOOLS                    │  │  │
│                    │  │                                        │  │  │
│                    │  │  ┌──────────────┐  ┌───────────────┐  │  │  │
│                    │  │  │  Vector Store │  │  Postgres DB  │  │  │  │
│                    │  │  │  QA Tool     │  │  Query Tool   │  │  │  │
│                    │  │  │  (RAG docs)  │  │  (SQL data)   │  │  │  │
│                    │  │  └──────┬───────┘  └───────────────┘  │  │  │
│                    │  └─────────│──────────────────────────────┘  │  │
│                    └───────────-│─────────────────────────────────┘  │
└────────────────────────────────│────────────────────────────────────┘
                                 │
          ┌──────────────────────▼─────────────────────┐
          │           PostgreSQL + pgvector              │
          │                                              │
          │  ┌─────────────────┐  ┌──────────────────┐  │
          │  │  ccd_documentos  │  │  Tablas          │  │
          │  │  (Vector Store)  │  │  Institucionales  │  │
          │  │  - id            │  │  - estudiantes    │  │
          │  │  - text          │  │  - cursos         │  │
          │  │  - embedding     │  │  - sesiones_bot   │  │
          │  │  - metadata      │  │  - ...            │  │
          │  └─────────────────┘  └──────────────────┘  │
          └──────────────────────────────────────────────┘
```

---

## 🛠️ Stack Tecnológico

| Componente | Tecnología | Rol |
|---|---|---|
| **Orquestación** | n8n (self-hosted) | Motor de workflow y automatización |
| **LLM** | NVIDIA NIM `llama-4-maverick-17b-128e-instruct` | Generación de respuestas en lenguaje natural |
| **Embeddings** | OpenAI `text-embedding-small-3` | Vectorización de documentos para RAG |
| **Vector Store** | PostgreSQL + pgvector | Almacenamiento y búsqueda semántica |
| **Base de Datos** | PostgreSQL | Datos de estudiantes, sesiones y cursos |
| **Memoria** | Postgres Chat Memory (n8n LangChain) | Historial de conversación persistente |
| **Framework IA** | LangChain (via n8n nodes) | Cadena de RAG, agente y herramientas |
| **Chat Interface** | n8n Chat Trigger (Widget / API) | Punto de entrada de mensajes |

---

## 🔄 Flujo de Funcionamiento

### 1. Autenticación del Estudiante

```
Usuario envía mensaje
        │
        ▼
¿Tiene sesión activa en BD? ──SÍ──▶ Continúa al Switch de Comandos
        │
        NO
        ▼
¿El mensaje parece un código de estudiante?
        │
    SÍ  │  NO
        │   └──▶ Pide el código
        ▼
Consulta la BD de estudiantes
        │
¿Existe? ──NO──▶ "Código no encontrado"
        │
       SÍ
        ▼
Guarda sesión en BD ──▶ Mensaje de bienvenida personalizado
```

El sistema utiliza una tabla `sesiones_bot` para persistir el estado de autenticación entre mensajes, evitando que el estudiante tenga que identificarse en cada interacción.

### 2. Procesamiento de Comandos

Una vez autenticado, el estudiante puede enviar comandos específicos (`/ruta`, `/cursos`, etc.) o hacer preguntas en lenguaje natural. El nodo **Switch Comandos** detecta el prefijo del mensaje y redirige a un **Prompt Builder** específico que prepara el contexto adecuado antes de pasar al agente.

### 3. Razonamiento del Agente

El **AI Agent** recibe el prompt enriquecido con contexto del estudiante y decide autónomamente qué herramientas usar:

- Si la pregunta es sobre **datos personales** (cursos, progreso, perfil) → usa `Postgres DB Tool`
- Si la pregunta es sobre **documentos institucionales** (reglamentos, guías, insignia) → usa `Documentos CCD Tool` (RAG)
- Si puede responder con **conocimiento propio + contexto** → responde directamente

### 4. RAG (Retrieval Augmented Generation)

```
Pregunta del usuario
        │
        ▼
OpenAI Embeddings vectoriza la pregunta
        │
        ▼
Búsqueda de similitud coseno en pgvector (top-K=4 chunks)
        │
        ▼
VectorDBQAChain combina los documentos recuperados
        │
        ▼
LLM genera respuesta basada en los documentos + pregunta
        │
        ▼
Respuesta fundamentada en documentos reales
```

---

## 🧩 Estructura del Workflow n8n

El workflow `CCD Bot IngenioTIC` contiene **32 nodos** organizados en las siguientes secciones:

### Sección 1: Entry Point y Sesión
| Nodo | Tipo | Función |
|---|---|---|
| `Chat Trigger` | ChatTrigger | Recibe mensajes del usuario vía webhook |
| `Init DB` | Postgres | Crea las tablas necesarias si no existen |
| `Verificar Sesión` | Postgres | Consulta si el `sessionId` tiene sesión activa |
| `Merge Sesion` | Merge | Unifica el flujo de sesión nueva vs. existente |

### Sección 2: Autenticación
| Nodo | Tipo | Función |
|---|---|---|
| `¿Autenticado?` | If | Verifica si la sesión tiene un código de estudiante |
| `Es Codigo Estudiante` | If | Detecta si el mensaje tiene formato de código UNAB |
| `Validar Estudiante` | Postgres | Busca el código en la tabla de estudiantes |
| `¿Estudiante Existe?` | If | Bifurca entre estudiante encontrado y no encontrado |
| `Guardar Sesión` | Postgres | Persiste la sesión autenticada |
| `Pedir Código` | Set | Mensaje solicitando el código de estudiante |
| `Codigo No Encontrado` | Set | Mensaje de error de código inválido |
| `Bienvenida Auth` | Set | Mensaje de bienvenida personalizado post-autenticación |

### Sección 3: Router de Comandos
| Nodo | Tipo | Función |
|---|---|---|
| `Switch Comandos` | Switch | Detecta el comando enviado por el usuario |
| `Prompt: /inicio` | Set | Construye prompt para el comando de inicio |
| `Prompt: /ayuda` | Set | Construye prompt listando capacidades del bot |
| `Prompt: /ruta` | Set | Construye prompt para mostrar progreso en la ruta |
| `Prompt: /cursos` | Set | Construye prompt para listar cursos del estudiante |
| `Prompt: /calendario` | Set | Construye prompt para fechas académicas |
| `Prompt: /documentos` | Set | Construye prompt para buscar en documentos |
| `Prompt: /perfil` | Set | Construye prompt para datos del perfil |
| `Prompt: /insignia` | Set | Construye prompt sobre la insignia digital |
| `Prompt: /siguiente` | Set | Construye prompt para el próximo curso recomendado |
| `Prompt: Chat Libre` | Set | Prompt genérico para preguntas sin comando |
| `Prompt: Comando Desconocido` | Set | Responde a comandos no reconocidos |

### Sección 4: Núcleo de IA
| Nodo | Tipo | Función |
|---|---|---|
| `Agent CCD` | LangChain Agent | Agente principal con razonamiento ReAct |
| `NVIDIA NIM Llama 4 Maverick` | LangChain LLM | Modelo de lenguaje vía NVIDIA NIM API |
| `Postgres Chat Memory` | LangChain Memory | Memoria de conversación en PostgreSQL |
| `Documentos CCD Tool` | toolVectorStore | Herramienta RAG para documentos institucionales |
| `PGVector Store` | vectorStorePGVector | Conexión al vector store en PostgreSQL |
| `Embeddings OpenAI` | embeddingsOpenAi | Modelo de embeddings para búsqueda semántica |
| `Postgres DB Tool` | toolPostgresDB | Herramienta de consulta SQL para datos de estudiantes |

### Sección 5: Manejo de Errores
| Nodo | Tipo | Función |
|---|---|---|
| `Error Amigable` | Set | Transforma errores técnicos en mensajes amigables |

---

## 🗄️ Base de Datos

### Tabla: `sesiones_bot`
```sql
CREATE TABLE IF NOT EXISTS sesiones_bot (
    session_id    VARCHAR(255) PRIMARY KEY,  -- ID único del chat
    codigo        VARCHAR(50),               -- Código de estudiante UNAB
    nombre        VARCHAR(255),              -- Nombre del estudiante
    creado_en     TIMESTAMP DEFAULT NOW(),
    actualizado_en TIMESTAMP DEFAULT NOW()
);
```

### Tabla: `ccd_documentos` (Vector Store)
```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS ccd_documentos (
    id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    text      TEXT,                          -- Contenido del chunk de documento
    embedding VECTOR(1536),                  -- Embedding OpenAI text-embedding-small-3
    metadata  JSONB                          -- Fuente, página, nombre del archivo
);

CREATE INDEX ON ccd_documentos
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);
```

### Tablas Institucionales (consultadas por `Postgres DB Tool`)
El agente tiene acceso de solo lectura a tablas de la institución que contienen:
- Datos del estudiante (nombre, programa, semestre)
- Cursos completados por pilar (Pilar 1, 2, 3)
- Fechas del calendario académico
- Estado de la insignia de competencias digitales

---

## 📚 Sistema RAG

El RAG (Retrieval Augmented Generation) permite al bot responder con información precisa de documentos institucionales sin necesidad de re-entrenar el modelo.

### Documentos Indexados
- Reglamento del CCD y la Ruta de Competencias Digitales
- Guías de inscripción por curso
- Instructivo para obtención de la Insignia Digital
- Contenidos y requisitos de cada curso por pilar
- Preguntas frecuentes institucionales

### Pipeline de Carga de Documentos

El workflow `CCD RAG - Cargar Documentos` procesa cada archivo así:

```
Formulario de carga (PDF/DOCX)
          │
          ▼
Fix MimeType (normaliza el tipo de archivo)
          │
          ▼
Document Loader (extrae texto del archivo)
          │
          ▼
RecursiveCharacterTextSplitter
  - chunkSize: 1000 caracteres
  - chunkOverlap: 200 caracteres
          │
          ▼
OpenAI Embeddings (text-embedding-small-3)
  - Dimensión: 1536
          │
          ▼
PGVector Store → tabla ccd_documentos
          │
          ▼
Confirmación en formulario
```

### Búsqueda en Runtime

```
Pregunta del usuario
          │
          ▼
Vectorización con OpenAI Embeddings
          │
          ▼
Búsqueda por similitud coseno (top-K = 4)
          │
          ▼
VectorDBQAChain (LangChain Classic)
  - Combina los 4 chunks recuperados
  - Construye prompt con contexto
          │
          ▼
LLM genera respuesta fundamentada
```

---

## 💬 Comandos del Bot

| Comando | Descripción |
|---|---|
| `/inicio` | Bienvenida e información general del CCD |
| `/ayuda` | Lista completa de comandos con ejemplos de uso |
| `/ruta` | Estado de avance en los 3 pilares de la ruta |
| `/cursos` | Lista de cursos completados con fecha y pilar |
| `/calendario` | Próximos eventos y fechas académicas del CCD |
| `/documentos` | Busca en reglamentos y documentos institucionales |
| `/perfil` | Información del estudiante (nombre, programa, semestre) |
| `/insignia` | Estado y requisitos para obtener la insignia digital |
| `/siguiente` | Recomendación del próximo curso a tomar |
| *(texto libre)* | Pregunta abierta respondida por el agente con RAG + BD |

---

## 🏗️ Guía de Construcción Paso a Paso

### Prerrequisitos

- n8n versión 1.70+ (self-hosted con Docker o npm)
- PostgreSQL 14+ con extensión `pgvector` instalada
- Cuenta en [NVIDIA NIM](https://build.nvidia.com/) con acceso al modelo
- API Key de OpenAI (para embeddings)
- Acceso a la base de datos institucional de la UNAB

---

### Paso 1: Preparar PostgreSQL con pgvector

```bash
# En el servidor de PostgreSQL
psql -U postgres

-- Crear base de datos
CREATE DATABASE ccd_bot;
\c ccd_bot

-- Instalar extensión pgvector
CREATE EXTENSION IF NOT EXISTS vector;

-- Crear tabla de sesiones
CREATE TABLE sesiones_bot (
    session_id     VARCHAR(255) PRIMARY KEY,
    codigo         VARCHAR(50),
    nombre         VARCHAR(255),
    creado_en      TIMESTAMP DEFAULT NOW(),
    actualizado_en TIMESTAMP DEFAULT NOW()
);

-- Crear tabla del vector store
CREATE TABLE ccd_documentos (
    id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    text      TEXT,
    embedding VECTOR(1536),
    metadata  JSONB
);

-- Índice para búsqueda eficiente
CREATE INDEX ON ccd_documentos
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);
```

### Paso 2: Instalar y Configurar n8n

```bash
# Opción A: Docker (recomendado)
docker run -d \
  --name n8n \
  -p 5678:5678 \
  -e N8N_BASIC_AUTH_ACTIVE=true \
  -e N8N_BASIC_AUTH_USER=admin \
  -e N8N_BASIC_AUTH_PASSWORD=TuPassword \
  -e DB_TYPE=postgresdb \
  -e DB_POSTGRESDB_HOST=tu-postgres-host \
  -e DB_POSTGRESDB_DATABASE=n8n \
  -e DB_POSTGRESDB_USER=n8n_user \
  -e DB_POSTGRESDB_PASSWORD=n8n_pass \
  -v ~/.n8n:/home/node/.n8n \
  n8nio/n8n

# Opción B: npm
npm install -g n8n
n8n start
```

### Paso 3: Configurar Credenciales en n8n

En `Settings > Credentials`, crear las siguientes:

**PostgreSQL (BD Institucional + Vector Store):**
```
Host:     tu-servidor-postgres
Port:     5432
Database: ccd_bot
User:     ccd_user
Password: ***
SSL:      desactivado (o configurar según servidor)
```

**OpenAI API:**
```
API Key: sk-...
```

**NVIDIA NIM API:**
```
Base URL: https://integrate.api.nvidia.com/v1
API Key:  nvapi-...
```

### Paso 4: Importar los Workflows

Importar en este orden:

1. **`CCD RAG - Cargar Documentos`** — workflow de ingesta de documentos
2. **`CCD Bot IngenioTIC`** — workflow principal del bot

Desde n8n: `Workflows > Import from File > seleccionar JSON`

### Paso 5: Configurar el Nodo `Init DB`

Este nodo crea la tabla `sesiones_bot` al recibir el primer mensaje. Verificar que tenga el SQL correcto:

```sql
CREATE TABLE IF NOT EXISTS sesiones_bot (
    session_id     VARCHAR(255) PRIMARY KEY,
    codigo         VARCHAR(50),
    nombre         VARCHAR(255),
    creado_en      TIMESTAMP DEFAULT NOW(),
    actualizado_en TIMESTAMP DEFAULT NOW()
);
```

### Paso 6: Configurar el Agente (`Agent CCD`)

En el nodo `Agent CCD`:

- **Type:** Tools Agent
- **System Message:** Prompt del sistema con la identidad de TuNaveganteCCD
- **Prompt Type:** Define (usar el campo `text` del nodo anterior)

En el system message, incluir:
```
Eres TuNaveganteCCD, el asistente virtual oficial del Centro de Competencias
Digitales (CCD) de la Universidad Autónoma de Bucaramanga (UNAB). SIEMPRE
respondes en ESPAÑOL, eres conciso, amigable y usas emojis apropiados.

El estudiante autenticado es: {{ $json.nombre }} ({{ $json.codigo }})
Programa: {{ $json.programa }}

Usa las herramientas disponibles para responder con información precisa y
actualizada. No inventes datos. Si no tienes la información, dilo claramente.
```

### Paso 7: Configurar `Documentos CCD Tool`

- **Tipo de nodo:** `toolVectorStore` (Vector Store Question Answer Tool)
- **Descripción:** Descripción clara de qué contiene el vector store
- **Conexiones requeridas:**
  - `PGVector Store` → input `ai_vectorStore`
  - `NVIDIA NIM Llama 4 Maverick` → input `ai_languageModel` *(requerido por VectorDBQAChain)*


### Paso 8: Configurar el `Switch Comandos`

El nodo Switch debe detectar el inicio de cada mensaje:

| Output | Condición |
|---|---|
| 0 → `/inicio` | `{{ $json.chatInput }}.startsWith('/inicio')` |
| 1 → `/ayuda` | `{{ $json.chatInput }}.startsWith('/ayuda')` |
| 2 → `/ruta` | `{{ $json.chatInput }}.startsWith('/ruta')` |
| 3 → `/cursos` | `{{ $json.chatInput }}.startsWith('/cursos')` |
| 4 → `/calendario` | `{{ $json.chatInput }}.startsWith('/calendario')` |
| 5 → `/documentos` | `{{ $json.chatInput }}.startsWith('/documentos')` |
| 6 → `/perfil` | `{{ $json.chatInput }}.startsWith('/perfil')` |
| 7 → `/insignia` | `{{ $json.chatInput }}.startsWith('/insignia')` |
| 8 → `/siguiente` | `{{ $json.chatInput }}.startsWith('/siguiente')` |
| 9 → Desconocido | Cualquier `/` no reconocido |
| 10 → Chat Libre | Sin `/` (pregunta libre) |

### Paso 9: Cargar Documentos al Vector Store

Activar el workflow `CCD RAG - Cargar Documentos` e ir a la URL del formulario que genera n8n. Subir cada documento institucional en formato PDF o DOCX. El workflow automáticamente:

1. Extrae el texto
2. Lo divide en chunks de 1000 caracteres
3. Genera embeddings con OpenAI
4. Almacena en `ccd_documentos` con metadatos del archivo

### Paso 10: Activar el Bot

1. En n8n, activar el workflow `CCD Bot IngenioTIC` (toggle superior derecho)
2. Copiar la URL del `Chat Trigger` webhook
3. Integrar con WhatsApp Business, Telegram, o usar el widget de chat de n8n

---

## 🔐 Variables de Entorno y Credenciales

| Variable | Descripción | Ejemplo |
|---|---|---|
| `POSTGRES_HOST` | Host de PostgreSQL | `db.ejemplo.com` |
| `POSTGRES_DB` | Nombre de la base de datos | `ccd_bot` |
| `POSTGRES_USER` | Usuario de la BD | `ccd_user` |
| `POSTGRES_PASSWORD` | Contraseña de la BD | `***` |
| `OPENAI_API_KEY` | API key de OpenAI (embeddings) | `sk-...` |
| `NVIDIA_NIM_API_KEY` | API key de NVIDIA NIM (LLM) | `nvapi-...` |
| `N8N_WEBHOOK_URL` | URL pública de n8n | `https://n8n.tudominio.com` |

---

## 📤 Carga de Documentos al Vector Store

Para agregar nuevos documentos institucionales al sistema RAG:

1. Ir a la URL del formulario de carga (generada por n8n al activar `CCD RAG - Cargar Documentos`)
2. Subir el archivo (PDF, DOCX, TXT)
3. El sistema procesará automáticamente y confirmará la carga
4. Los nuevos documentos estarán disponibles inmediatamente para el bot

Para **eliminar o actualizar** un documento, borrar los registros de `ccd_documentos` filtrando por `metadata->>'source'` y volver a cargar el archivo actualizado.

```sql
-- Eliminar chunks de un documento específico
DELETE FROM ccd_documentos
WHERE metadata->>'source' = 'reglamento_ccd_2024.pdf';
```

---

## 🚀 Despliegue

### FastAPI + Gradio en Azure

Si estás publicando la interfaz FastAPI + Gradio en Azure, puedes abrirla en:

`http://130.107.49.127:8000/?__theme=light`

No necesitas Nginx; solo asegúrate de configurar las reglas de red para permitir el tráfico entrante y saliente en el puerto expuesto por la app (por ejemplo, `8000` o `80`).

### Opción A: Servidor Propio (VPS)

```bash
# docker-compose.yml
version: '3.8'
services:
  postgres:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_DB: ccd_bot
      POSTGRES_USER: ccd_user
      POSTGRES_PASSWORD: secure_password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  n8n:
    image: n8nio/n8n
    ports:
      - "5678:5678"
    environment:
      - DB_TYPE=postgresdb
      - DB_POSTGRESDB_HOST=postgres
      - DB_POSTGRESDB_DATABASE=n8n
      - DB_POSTGRESDB_USER=ccd_user
      - DB_POSTGRESDB_PASSWORD=secure_password
      - N8N_HOST=0.0.0.0
      - WEBHOOK_URL=https://n8n.tudominio.com
    depends_on:
      - postgres
    volumes:
      - n8n_data:/home/node/.n8n

volumes:
  postgres_data:
  n8n_data:
```

```bash
docker-compose up -d
```

### Opción B: n8n Cloud + PostgreSQL Externo

Usar [n8n Cloud](https://n8n.io/cloud/) y un PostgreSQL en Supabase, Railway o Neon (todos soportan `pgvector`).

---

## ⚠️ Limitaciones Conocidas


- **Modelos de NVIDIA NIM:** Algunos modelos pueden tener límites de contexto o disponibilidad según la cuenta y configuración. Si los documentos recuperados superan el límite, el LLM puede fallar. Usar modelos con al menos 8K tokens de contexto.

- **Sesiones:** La autenticación persiste en la tabla `sesiones_bot` indefinidamente. Implementar un job de limpieza para sesiones inactivas mayores a N días.

- **Idioma:** El bot está optimizado para español. Respuestas en otros idiomas no están garantizadas.

- **Documentos binarios:** El cargador de documentos soporta PDF y DOCX. Archivos escaneados sin OCR no serán procesados correctamente.

---

## 🤝 Contribución

Este proyecto fue desarrollado en el marco de **IngenioTIC — UNAB**.

Para contribuir:

1. Crear un fork del repositorio
2. Exportar el workflow modificado desde n8n (`...` > `Export`)
3. Abrir un Pull Request con descripción del cambio y capturas del workflow

---

## 📄 Licencia

Uso interno UNAB — Centro de Competencias Digitales. Todos los derechos reservados.

---

*Construido con ❤️*
