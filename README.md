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
* Procesa archivos `.msg.json`
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
* Backoff exponencial simple recomendado:

  * 1s → 5s → 15s → 30s
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
[INFO] Processing mail mail-12345
[INFO] Sending to user@example.com
[WARN] SMTP retry 1/3
[ERROR] Mail failed after retries
[INFO] Moved to /failed/mail-12345.json
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

