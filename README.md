# VtesProxi

Aplicacion Django para generar proxies de cartas (Cripta y Libreria), con recorte, render de texto/simbolos y gestion de cartas guardadas.

## Editor de Layouts

La app `apps.layouts` permite crear y mantener layouts privados por usuario para `cripta` y `libreria`.

### Acceso
- URL: `/layouts/`
- Requiere login.
- Entrada de menu disponible en la barra lateral como `Layouts`.

### Flujo recomendado
1. Entrar en `Layouts`.
2. Elegir tipo de carta (`cripta` o `libreria`).
3. Crear o seleccionar un layout.
4. Mover/redimensionar capas en el editor visual.
5. Guardar configuracion.
6. (Opcional) Marcar layout como default.
7. Ir a `/cripta/importar-imagen/` o `/libreria/importar-imagen/` y usar el selector de layout.

### Prioridad de resolucion en render
Los endpoints de `srv_textos` resuelven el layout en este orden:
1. `layout_override`
2. `layout_id`
3. layout default del usuario para el tipo de carta
4. fallback `classic` desde `apps/srv_textos/layouts.json`

## Layout Box Engine v2

El motor de render usa un schema v2 compatible con layouts legacy.

### Campos principales por elemento
- `box`: `{x, y, width, height}`
- `rules.align`: `left | center | right` (texto)
- `rules.anchor_mode`: `free | top_locked | bottom_locked`
- `rules.autoshrink`: `true | false`
- `rules.min_font_size`: entero
- `rules.ellipsis_enabled`: `true | false`
- `shadow.enabled`: sombra de texto on/off

### Compatibilidad
- Los layouts antiguos se normalizan automaticamente con `normalize_layout_config`.
- `validate_layout_config` acepta legacy y v2, validando rangos/enums de `box` y `rules`.

### Comportamiento de render
- `nombre` e `ilustrador` se ajustan al `box` con alineacion configurable.
- Si el texto no cabe: reduce fuente hasta `min_font_size`; si sigue sin caber y hay ellipsis, truncado con `...`.
- `disciplinas` y `simbolos` escalan tamano/espaciado a partir del `box`.
- `habilidad` calcula altura dinamica por contenido y el resolver global mueve elementos anclables para evitar solapes.

### Editor visual
En `/layouts/`, ademas de `x/y/width/height`, el panel permite editar:
- `align`
- `anchor_mode`
- `min_font_size`
- `autoshrink`
- `ellipsis_enabled`
- `shadow.enabled`

## Verificacion rapida

Usar el interprete del entorno virtual:

```bash
/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.layouts.tests -v 2
/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.srv_textos.tests -v 2
/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py check
```

## Windows Portable Bundle

La app puede empaquetarse como bundle portable de Windows con un `.exe` lanzador local.

### Qué viaja en el paquete inicial
- el `db.sqlite3` actual
- la carpeta `media/` actual
- usuarios existentes
- layouts existentes
- cartas guardadas

### Qué pasa al arrancar
- el lanzador levanta Django en `127.0.0.1`
- espera a que el servidor responda
- abre el navegador automáticamente en la app local

### Usuarios nuevos
- cualquier usuario nuevo recibe automáticamente dos layouts por defecto:
  - `classic` para `cripta`
  - `classic` para `libreria`

### Cómo construir el bundle
El build final del `.exe` debe ejecutarse en Windows.

Archivos relevantes:
- spec de PyInstaller: `desktop/windows_launcher.spec`
- script PowerShell: `scripts/windows/build_windows_bundle.ps1`
- script `.bat`: `scripts/windows/build_windows_bundle.bat`

Flujo recomendado en Windows:

```powershell
cd C:\ruta\al\repo
scripts\windows\build_windows_bundle.ps1
```

Ese script:
- copia `db.sqlite3` a `desktop/seed/db.sqlite3`
- copia `media/` a `desktop/seed/media/`
- ejecuta PyInstaller con `desktop/windows_launcher.spec`

El resultado esperado es una carpeta en `dist/` lista para entregar a tu compañero.

## Windows Clone-And-Run

Si prefieres no pasar un bundle, también puedes pasar un único archivo Windows que clone el repo público y arranque la app localmente.

### Archivo de entrada
- `run_windows_clone.bat`

### Qué hace
- clona el repo en `%LOCALAPPDATA%\WebVTES\repo` si no existe
- crea `.venv`
- instala dependencias
- corre migraciones con `webvtes.settings_desktop`
- si no hay usuarios, pide `nombre` y `clave`
- crea un usuario normal inicial
- arranca la app local
- abre el navegador

### Comportamiento posterior
- no hace `git pull` automáticamente
- reutiliza la instalación local existente
- no vuelve a crear usuarios si ya existe alguno

### Archivos relacionados
- lanzador único: `run_windows_clone.bat`
- script principal: `scripts/windows/clone_and_run.ps1`
- helper de alta inicial: `scripts/bootstrap_local_user.py`

### Nota
Este flujo requiere que la máquina Windows tenga:
- `git`
- `py` o Python para Windows en PATH

Los layouts `classic` de `cripta` y `libreria` se crean automáticamente para el usuario nuevo gracias al bootstrap de layouts de la aplicación.
