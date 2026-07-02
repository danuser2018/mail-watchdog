# Registro de cambios

Todos los cambios notables de este proyecto se documentan en este fichero.

El formato está basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/)
y este proyecto adhiere a [Versionado Semántico](https://semver.org/lang/es/).

## Guía de uso

Cada versión se documenta bajo su número de versión y fecha de publicación.
Los cambios se agrupan en las siguientes categorías:

- **Añadido** — nuevas funcionalidades.
- **Cambiado** — cambios en funcionalidades existentes.
- **Obsoleto** — funcionalidades que serán eliminadas en versiones futuras.
- **Eliminado** — funcionalidades eliminadas en esta versión.
- **Corregido** — corrección de errores.
- **Seguridad** — correcciones de vulnerabilidades.

---

## [1.1.0] - 2026-07-02

### Añadido

- Nueva carpeta `.agent/skills` con información relevante para la IA.
- Variable de configuración `identity_service_base_url` cargada desde `IDENTITY_SERVICE_BASE_URL` (por defecto `http://identity-service:8000`) en `src/config.py`.
- Método privado `_resolve_recipient()` en `MailProcessor` (`src/processor.py`) que consulta `GET /v1/identity/email` en `identity-service` usando `urllib.request` estándar con timeout de 5 segundos.
- Nuevos tests en `tests/test_processor.py` que cubren los escenarios de fallo de `identity-service` (reintento por backoff, agotamiento de reintentos, email vacío) y compatibilidad con campo `to` legado ignorado por Pydantic.
- Nuevo test en `tests/test_smtp.py` que verifica que `sendmail` usa el destinatario explícito pasado como argumento.

### Cambiado

- Eliminado el campo obligatorio `to` del modelo `MailMessage` en `src/models.py`. El destinatario ahora se resuelve dinámicamente vía REST desde `identity-service`.
- Modificada la firma de `SMTPClient.send()` en `src/smtp_client.py` para aceptar el parámetro explícito `recipient: str`, desacoplando el cliente SMTP del modelo de datos.
- Actualizado `src/processor.py` para resolver el destinatario llamando a `_resolve_recipient()` antes del envío SMTP, tratando los fallos de `identity-service` como fallos temporales sujetos a la política de backoff exponencial.

### Corregido

- Alineación y corrección de discrepancias de la documentación técnica en `README.md` respecto a la extensión de archivos (`.json`), la obligatoriedad del directorio `processing/`, el cálculo del backoff exponencial (`MAIL_BACKOFF_BASE ** (attempts - 1)`), las variables de entorno `MAIL_SHARED_DIR`/`LOG_LEVEL` y la estructura exacta de logs generados por el daemon.

## [1.0.0] - 2026-06-27

### Añadido

- Fichero `CONTRIBUTING.md` con el flujo de trabajo Trunk Based Development,
  convenciones de commits, guía de Pull Requests y buenas prácticas para
  desarrollo asistido con IA.
- Fichero `CHANGELOG.md` con el formato Keep a Changelog v1.1.0 en castellano.
- Fichero `README.md` con la descripción del servicio.
- Implementación del servicio daemon `mail-watchdog` (módulos de configuración, modelos, cliente SMTP, reintentos, procesador y watcher).
- Pruebas unitarias para la lógica de reintento, cliente SMTP y procesador (`tests/`).
- Archivo `Dockerfile` para el empaquetado del servicio en contenedor.
- Configuración de integración continua (CI) en GitHub Actions (`.github/workflows/ci.yml`) para la validación automática en Pull Requests.

---

<!-- Plantilla para nuevas versiones:

## [X.Y.Z] - AAAA-MM-DD

### Añadido
-

### Cambiado
-

### Obsoleto
-

### Eliminado
-

### Corregido
-

### Seguridad
-

-->

[Sin publicar]: https://github.com/danuser2018/tts-capability/compare/HEAD...HEAD
