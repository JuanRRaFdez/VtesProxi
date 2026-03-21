# VtesProxi

Aplicacion Django para generar proxies de cartas (Cripta y Libreria), con recorte, render de texto/simbolos y gestion de cartas guardadas.

## Baseline de seguridad y calidad

### Onboarding de entorno (`SECRET_KEY`)

Variables soportadas por `webvtes/settings.py`:

| Variable | Uso | Valor por defecto |
| --- | --- | --- |
| `DJANGO_SECRET_KEY` | Clave principal de Django (recomendada siempre) | sin valor |
| `DJANGO_ENV` | Modo de ejecucion (`local`, `desktop`, `dev`, `prod`, etc.) | `local` |
| `DJANGO_ALLOW_LOCAL_SECRET_FALLBACK` | Permite fallback local de clave solo en `local/desktop/dev` (`1/0`, `true/false`) | `1` |

Regla efectiva:
- Si `DJANGO_SECRET_KEY` existe, se usa siempre.
- Si no existe y el entorno es `local/desktop/dev` con fallback habilitado, se usa clave local de desarrollo.
- Si no existe fuera de local, Django falla en arranque con `ImproperlyConfigured`.

Ejemplo local:

```bash
export DJANGO_ENV=local
export DJANGO_ALLOW_LOCAL_SECRET_FALLBACK=1
export DJANGO_SECRET_KEY="dev-secret-opcional"
.venv/bin/python manage.py runserver
```

Ejemplo desktop portable:

```bash
export DJANGO_ENV=desktop
export DJANGO_ALLOW_LOCAL_SECRET_FALLBACK=1
export WEBVTES_PORTABLE_DIR="/tmp/webvtes-portable"
.venv/bin/python manage.py check --settings=webvtes.settings_desktop
```

Troubleshooting fail-fast:
- Error: `DJANGO_SECRET_KEY is required outside local development mode...`
- Causa: estas en un entorno no local (por ejemplo `prod`) sin `DJANGO_SECRET_KEY`.
- Solucion: define `DJANGO_SECRET_KEY` o vuelve a `DJANGO_ENV=local|desktop|dev` con fallback habilitado.

### Verificacion en un comando

Comando base del repo:

```bash
make quality
```

`make quality` ejecuta en orden: `make lint` -> `make typecheck` -> `make check` -> `make test`.

Paridad esperada:
- Local antes de push: `make quality`
- Pre-commit antes de commit: `.venv/bin/pre-commit run --all-files`
- CI (`quality-gate`): mismo contrato en dos jobs (`static`: lint+typecheck, `runtime`: check+test)
- Nota: `--all-files` revisa todo el repositorio; si aparece deuda historica no relacionada, corrige esos ficheros o ejecuta pre-commit sobre staged para validar solo tu cambio antes del commit.

Si CI falla y local no, revisar primero versiones/dependencias de `.venv` y que hayas ejecutado exactamente los comandos anteriores desde la raiz del repo.

### Ownership del quality gate

- Politica de runtime/seguridad: `webvtes/settings.py` (secret key y fail-fast)
- Portabilidad desktop: `webvtes/settings_desktop.py` (paths/entorno local desktop)
- Contrato y tooling de calidad: `Makefile`, `pyproject.toml`, `.pre-commit-config.yaml`, `.github/workflows/quality.yml`

### Contrato de evidencia CI para verify/archive

- La evidencia valida del `quality-gate` debe incluir siempre `run_url` y `run_id`, y deberia incluir `commit_sha` para evitar ambiguedad entre reruns.
- Capturas de pantalla o texto narrativo sin IDs estables no cuentan como prueba primaria.
- Antes de cerrar verify/archive, valida el run con:

```bash
gh run view <run_id> --json headSha,workflowName,jobs,conclusion,url
```

- Aserciones minimas de ingestion:
  - `workflowName == "quality-gate"`
  - `headSha` coincide con el commit evaluado
  - los jobs `static` y `runtime` concluyen `success`
- Si `gh` no esta disponible (CLI/API), se permite bloque manual `ci_evidence` solo como `pass_with_warnings`; no se permite cierre sin warning.
- Referencia completa y plantilla: `docs/quality/ci-evidence.md`

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

## Plan incremental de MyPy

Matriz de rollout con alcance y responsables:

| Fase | Alcance | Responsable |
| --- | --- | --- |
| A (activa) | `webvtes/`, `scripts/`, `desktop/` | Core platform maintainers |
| B (adopcion) | `apps/layouts/`, `apps/srv_textos/` | Maintainers de cada dominio |
| C (endurecimiento) | activar flags estrictos por modulo (`disallow_untyped_defs`, `warn_return_any`) y retirar ignores temporales | Quality gate maintainers |

Checklist por fase:
- [ ] Alcance documentado y validado en `pyproject.toml`
- [ ] Owner asignado para seguimiento de fixes
- [ ] `make typecheck` en verde sin regresiones del baseline

Politica de promocion en CI para ampliar alcance MyPy:
- La ampliacion de alcance solo pasa a gate requerido tras **2 merges consecutivos en verde** con `make typecheck` en la rama principal.
- Si una ampliacion rompe baseline, se revierte al alcance anterior y se reintenta con overrides por modulo.

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
