# 📧 Mail Watchdog (Nova-2 Capability)

Mail Watchdog es un servicio ligero y autónomo del ecosistema **Nova-2** encargado de enviar correos electrónicos de forma asíncrona a través de SMTP.

Forma parte del sistema de *capabilities watchdog-based* de Nova, donde los plugins no ejecutan acciones externas directamente, sino que generan artefactos que son consumidos por servicios especializados.

---

## 🧠 Rol dentro del ecosistema Nova

En Nova-2, la arquitectura se basa en separación estricta de responsabilidades:

```text
Plugin → genera intención estructurada
        ↓
Filesystem (outbox)
        ↓
Watchdog especializado
        ↓
Servicio externo (SMTP)
```

El Mail Watchdog es el componente responsable de:

* Consumir solicitudes de envío de email
* Ejecutar el envío real vía SMTP
* Garantizar entrega (best effort con reintentos)
* Borrar el email / registrar resultado fallido

No interactúa con el usuario ni con el orchestrator directamente.

---

## 📦 Responsabilidad del servicio

El servicio:

* Escucha una carpeta de entrada (`/shared/mail/pending`)
* Procesa archivos `.json`
* Envía emails mediante SMTP
* Si el envío fue correcto, borra el mail.
* Si el envío falló y no hay más reintentos, mueve el mail a `/failed`.
* Implementa reintentos con backoff configurable

---

## 📜 Contrato de entrada

El Mail Watchdog consume archivos JSON con el siguiente formato:

```json
{
  "id": "mail-12345",
  "to": "user@example.com",
  "subject": "Título del correo",
  "body": "Contenido del mensaje",
  "content_type": "text/plain"
}
```

### Campos obligatorios

* `id`: identificador único del mensaje
* `to`: destinatario
* `subject`: asunto del email
* `body`: contenido del email

### Campos opcionales

* `content_type`: `"text/plain"` o `"text/html"` (default: `text/plain`)

---

## 📤 Comportamiento del sistema

### Flujo de procesamiento

```text
1. Detectar archivo en /pending
2. Bloquear / mover a processing (opcional)
3. Parsear JSON
4. Enviar email vía SMTP
5. Si éxito → borrar archivo
6. Si fallo → retry con backoff
7. Si agotado → /failed
```

---

## 🔁 Política de reintentos

* Número de reintentos configurable (ej: 3–5)
* Backoff exponencial calculado con la fórmula `MAIL_BACKOFF_BASE ** (attempts - 1)` (en segundos). Con los valores por defecto (`MAIL_BACKOFF_BASE=2.0` y `MAIL_MAX_RETRIES=3`):
  * Reintento 1: 1.0s
  * Reintento 2: 2.0s
  * Reintento 3: Límite de reintentos alcanzado (fallo definitivo tras 3 intentos en total)
* Fallo definitivo tras agotamiento de intentos

---

## 📁 Estructura de directorios

```text
/shared/mail/
    pending/
    processing/
    failed/
```

---

## ⚙️ Configuración (variables de entorno)

El servicio se configura completamente mediante variables de entorno:

```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_user@gmail.com
SMTP_PASSWORD=your_password
SMTP_FROM="Nova <your_user@gmail.com>"

MAIL_POLL_INTERVAL=2
MAIL_MAX_RETRIES=3
MAIL_BACKOFF_BASE=2

# Directorio compartido para buzones de correo y nivel de logs (opcionales)
MAIL_SHARED_DIR=/shared/mail
LOG_LEVEL=INFO
```

---

## 🚀 Instalación

### 1. Clonar repositorio

```bash
git clone <repo-url>
cd mail-watchdog
```

---

### 2. Construir Docker

```bash
docker build -t nova-mail-watchdog .
```

---

### 3. Ejecutar contenedor

```bash
docker run -d \
  --name mail-watchdog \
  -v /shared/mail:/shared/mail \
  --env-file .env \
  nova-mail-watchdog
```

---

## 🧪 Modo desarrollo

Ejecutar directamente en Python:

```bash
python main.py
```

Requiere:

```bash
pip install -r requirements.txt
```

---

## 📡 Observabilidad

El servicio debe registrar:

* envío iniciado
* envío exitoso
* fallo SMTP
* número de reintentos

Ejemplo de log:

```text
2026-06-30 00:53:40,123 [INFO] processor: Processing mail mail-12345
2026-06-30 00:53:40,124 [INFO] processor: Sending to user@example.com
2026-06-30 00:53:41,125 [WARNING] processor: SMTP retry 1/3 failed for ID mail-12345: [SMTP connection error]
2026-06-30 00:53:43,126 [ERROR] processor: Mail failed after retries
2026-06-30 00:53:43,127 [INFO] processor: Moved to /shared/mail/failed/mail-12345.json
```

---

## 🧱 Arquitectura

```text
                ┌──────────────┐
                │   Nova Plugin │
                └──────┬───────┘
                       │ JSON artifact
                       ↓
              ┌──────────────────┐
              │ /shared/mail     │
              │   /pending       │
              └────────┬─────────┘
                       ↓
           ┌───────────────────────┐
           │ Mail Watchdog         │
           │ (Python service)      │
           └────────┬──────────────┘
                    ↓
              SMTP Provider
                    ↓
              Email delivered
```

---

## 🔒 Seguridad (importante)

* No loggear credenciales SMTP
* No almacenar emails enviados
* Usar variables de entorno para secretos
* Recomendar App Passwords (Gmail)

---

## 🧩 Diseño filosófico

Este servicio sigue el principio:

> “Watchdogs no deciden, solo ejecutan”

No existe:

* lógica de conversación
* lógica de orquestación
* lógica de composición de mensajes

Solo ejecución fiable de un contrato.

---

## 📁 Estructura de carpetas del proyecto

El Mail Watchdog opera sobre un directorio compartido (`/shared/mail`) que actúa como interfaz de entrada y estado del sistema.

```text id="m7k2qv"
mail-watchdog/
├── src/
│   ├── main.py
│   ├── watcher.py
│   ├── processor.py
│   ├── smtp_client.py
│   ├── retry.py
│   ├── models.py
│   ├── config.py
│   └── utils.py
│
├── shared/
│   └── mail/
│       ├── pending/
│       │   ├── mail-12345.json
│       │   ├── mail-12346.json
│       │   └── ...
│       │
│       ├── processing/
│       │   └── mail-12345.json   (estado temporal de procesamiento)
│       │
│       ├── failed/
│       │   ├── mail-12340.json
│       │   └── ...
│       │
│       └── logs/
│           └── mail.log         (opcional, logs estructurados)
│
├── tests/
│   ├── test_processor.py
│   ├── test_smtp.py
│   └── test_retry.py
│
├── Dockerfile
├── requirements.txt
├── README.md
└── .env.example
```

---

## 🧠 Descripción de directorios

### `src/`

Contiene la lógica del servicio watchdog.

* `main.py`: entrypoint del daemon
* `watcher.py`: polling del filesystem (`/pending`)
* `processor.py`: orquestación del envío de un mail
* `smtp_client.py`: wrapper de envío SMTP
* `retry.py`: lógica de reintentos con backoff
* `models.py`: estructura del JSON de entrada
* `config.py`: carga de variables de entorno
* `utils.py`: helpers (filesystem, parsing, etc.)

---

### `shared/mail/`

Interfaz del sistema con Nova.

#### `pending/`

* Entrada de mensajes de correo
* Archivos `.json` generados por plugins

#### `processing/`

* Estado transitorio obligatorio mientras se envía (evita duplicados o pérdidas si el proceso se interrumpe)

#### `failed/`

* Mensajes que han fallado definitivamente
* Útil para debugging y trazabilidad

#### `logs/` (opcional)

* Logs por mail o logs agregados del sistema

---

### `tests/`

Tests unitarios y de integración del watchdog:

* parsing de mensajes
* simulación SMTP
* comportamiento de reintentos
* movimientos de archivos

---

### Archivos raíz

* `Dockerfile`: contenedor del servicio
* `requirements.txt`: dependencias Python
* `.env.example`: configuración SMTP y runtime
* `README.md`: documentación del sistema

---

## 📌 Nota de diseño

Esta estructura está optimizada para:

* ejecución simple en Docker
* observabilidad basada en filesystem
* bajo acoplamiento con Nova
* implementación directa por agente (sin decisiones ambiguas)

---

## 🧭 Evolución futura (no implementado)

Posibles extensiones:

* HTML templating avanzado
* Attachments
* Tracking de estado
* Callback file para confirmaciones
* Integración con event bus (Nova-3)

---

## 🧪 Compatibilidad con Nova

Este servicio es compatible con:

* speaker-watchdog
* future telegram-watchdog
* cualquier watchdog basado en filesystem

---

## 📌 Decisión de diseño clave

* ✔ Asíncrono por diseño
* ✔ Fire-and-forget desde Nova
* ✔ Entrega garantizada a nivel servicio
* ❌ Sin API REST
* ❌ Sin callbacks obligatorios
* ❌ Sin acoplamiento con orchestrator

---

## 🧠 Nota para implementación con agente (Antigravity)

El agente debe implementar:

* polling de directorio
* parsing JSON robusto
* cliente SMTP con retry
* movimiento atómico de archivos
* logging estructurado
* ejecución en loop continuo

