# Instalacion en Windows

Guia verificada para levantar `VtesProxi` en Windows como entorno local de desarrollo.

## 1. Prerrequisitos

Antes de empezar, asegurate de tener instalado:

1. `git`
2. Python `3.12`
3. El lanzador `py` disponible en `PATH`

Evidencia del repositorio:

- CI fija Python `3.12` en `.github/workflows/quality.yml`.
- `pyproject.toml` fija `py312` para Ruff y `python_version = "3.12"` para MyPy.
- El flujo Windows del repo usa `py -m venv .venv` en `scripts/windows/clone_and_run.ps1`.

## 2. Clonar el repositorio

Abre PowerShell y ejecuta:

```powershell
git clone https://github.com/JuanRRaFdez/VtesProxi.git
cd VtesProxi
```

## 3. Crear el entorno virtual

Desde la raiz del proyecto:

```powershell
py -3.12 -m venv .venv
```

## 4. Activar el entorno virtual

En PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Si prefieres no activar el entorno, puedes ejecutar siempre el interprete del entorno virtual directamente:

```powershell
.\.venv\Scripts\python.exe --version
```

## 5. Instalar dependencias

El workflow de CI instala dependencias con estos ficheros:

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt -r requirements-dev.txt
```

## 6. Variables de entorno locales

El `README.md` y `webvtes/settings.py` documentan este contrato:

- `DJANGO_ENV=local`
- `DJANGO_ALLOW_LOCAL_SECRET_FALLBACK=1`
- `DJANGO_SECRET_KEY` es opcional en local, pero recomendable si quieres fijar una clave propia

En PowerShell:

```powershell
$env:DJANGO_ENV = "local"
$env:DJANGO_ALLOW_LOCAL_SECRET_FALLBACK = "1"
$env:DJANGO_SECRET_KEY = "dev-secret-opcional"
```

Notas:

- Si no defines `DJANGO_SECRET_KEY`, el proyecto permite una clave local de desarrollo cuando `DJANGO_ENV` es `local`, `desktop` o `dev` y el fallback esta habilitado.
- Fuera de esos entornos, Django falla al arrancar con `ImproperlyConfigured`.

## 7. Aplicar migraciones

```powershell
python manage.py migrate
```

## 8. Crear un usuario administrador

```powershell
python manage.py createsuperuser
```

## 9. Arrancar el servidor local

```powershell
python manage.py runserver
```

Con la configuracion por defecto de Django, la aplicacion quedara disponible en:

```text
http://127.0.0.1:8000/
```

## 10. Pruebas recomendadas

### Suite completa

```powershell
python manage.py test
```

### Pruebas concretas del repositorio

```powershell
python manage.py test apps.layouts.tests -v 2
python manage.py test apps.srv_textos.tests -v 2
python manage.py test webvtes.tests.test_settings_secret_key.SecretKeySettingsTests -v 2
python manage.py check
```

Estas rutas de prueba estan documentadas en `README.md` y en la configuracion del proyecto.

## 11. Lint y typecheck

El contrato del repositorio esta en `Makefile`, `pyproject.toml` y `.github/workflows/quality.yml`.

### Si tienes `make` disponible

```powershell
make lint
make typecheck
make check
make test
make quality
```

### Equivalentes directos desde Windows

```powershell
.\.venv\Scripts\ruff.exe check webvtes scripts desktop
.\.venv\Scripts\mypy.exe --config-file pyproject.toml
python manage.py check
python manage.py test
```

### Pre-commit opcional

```powershell
.\.venv\Scripts\pre-commit.exe run --all-files
```

## 12. Problemas habituales en Windows

### `py` no existe o no esta en `PATH`

El propio flujo Windows del repo (`scripts/windows/clone_and_run.ps1`) depende de `py`. Si falla `py -3.12 -m venv .venv`, instala Python para Windows asegurandote de exponer el lanzador `py` en `PATH`.

### Error de `DJANGO_SECRET_KEY`

Si aparece un error parecido a este:

```text
DJANGO_SECRET_KEY is required outside local development mode.
```

revisa que tu terminal tenga:

```powershell
$env:DJANGO_ENV = "local"
$env:DJANGO_ALLOW_LOCAL_SECRET_FALLBACK = "1"
```

o define explicitamente `DJANGO_SECRET_KEY`.

### `make` no esta disponible

Es normal en Windows nativo. Usa los comandos equivalentes del apartado de lint/typecheck con `ruff`, `mypy` y `python manage.py ...`.

### PowerShell bloquea scripts

El repositorio ya incluye un lanzador Windows (`run_windows_clone.bat`) que ejecuta PowerShell con `-ExecutionPolicy Bypass`. Si tu sesion bloquea la activacion del entorno virtual, puedes evitar ese paso y usar directamente `python` o `.\.venv\Scripts\python.exe` en todos los comandos.

## 13. Resumen rapido

```powershell
git clone https://github.com/JuanRRaFdez/VtesProxi.git
cd VtesProxi
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt -r requirements-dev.txt
$env:DJANGO_ENV = "local"
$env:DJANGO_ALLOW_LOCAL_SECRET_FALLBACK = "1"
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```
