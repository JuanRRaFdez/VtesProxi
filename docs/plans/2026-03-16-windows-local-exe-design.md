# Windows Local EXE Launcher Design

## Goal

Entregar una versión Windows de la app que el compañero pueda ejecutar en local con doble clic, abriendo automáticamente el navegador, conservando el usuario exportado, los layouts y las cartas ya existentes.

## Constraints

- El proyecto no se va a publicar en red.
- El compañero ejecutará la app sólo en su propio PC Windows.
- El paquete debe conservar el estado actual:
  - `db.sqlite3`
  - `media/`
  - usuarios actuales
  - layouts actuales
  - cartas guardadas
- Los usuarios nuevos deben recibir automáticamente dos layouts por defecto:
  - `classic` para `cripta`
  - `classic` para `libreria`

## Decision

Usaremos un bundle portable para Windows con un único `.exe` visible como lanzador. Ese lanzador arrancará un servidor Django local, esperará a que responda y abrirá el navegador automáticamente.

El estado persistente no vivirá dentro del binario, sino en archivos portables junto al paquete:

- `db.sqlite3`
- `media/`

Eso permite que:

- el usuario exportado viaje con el paquete
- las cartas y layouts persistan entre ejecuciones
- el binario no tenga que reescribir sus propios recursos internos

## Runtime Architecture

### Launcher

Crearemos un lanzador Windows en Python congelado con PyInstaller.

El lanzador tendrá dos modos:

- modo supervisor:
  - prepara rutas portables
  - copia semillas iniciales (`db.sqlite3`, `media/`) si faltan
  - elige puerto local
  - arranca un proceso hijo para servir Django
  - espera a que la URL responda
  - abre el navegador
- modo servidor:
  - configura variables de entorno para rutas portables
  - arranca Django en `127.0.0.1:<puerto>`

### Desktop Settings

Añadiremos un settings específico para escritorio, derivado del settings actual.

Ese settings resolverá:

- `DATABASES['default']['NAME']` desde un directorio portable
- `MEDIA_ROOT` desde ese mismo directorio portable
- `ALLOWED_HOSTS = ['127.0.0.1', 'localhost']`
- modo local compatible con servir estáticos y media

## User Bootstrap

El comportamiento de layouts por defecto debe vivir en la aplicación, no en el lanzador.

Añadiremos una utilidad idempotente, algo como `ensure_default_layouts_for_user(user)`, que:

- cree un layout `classic` de `cripta` si el usuario no tiene default para ese tipo
- cree un layout `classic` de `libreria` si el usuario no tiene default para ese tipo
- no duplique layouts existentes
- no pise defaults ya elegidos por el usuario

Esa utilidad se enganchará a la creación de usuarios mediante una señal `post_save` del modelo `User`.

## Packaging

El repo incorporará los ingredientes para construir el bundle Windows, aunque el build final del `.exe` deberá ejecutarse en Windows.

Se añadirán:

- script del lanzador
- settings de escritorio
- spec de PyInstaller
- script de build para Windows
- carpeta semilla para empaquetar:
  - `db.sqlite3`
  - `media/`

## Testing

La cobertura debe fijar tres áreas:

1. Layouts por defecto en usuarios nuevos
- usuario nuevo recibe default de `cripta`
- usuario nuevo recibe default de `libreria`
- no se duplican defaults al re-guardar usuario

2. Runtime portable
- settings de escritorio resuelven rutas externas para DB y media
- la lógica de seed copia `db.sqlite3` y `media/` sólo si faltan

3. Packaging contract
- el spec o script de build referencia los recursos requeridos
- el lanzador expone el flujo supervisor/servidor esperado

## Important Note

Podemos implementar y verificar la lógica Python y Django desde Linux, pero el binario `.exe` final tendrá que generarse y probarse en Windows con PyInstaller.
