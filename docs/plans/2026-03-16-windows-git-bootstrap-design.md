# Windows Git Bootstrap Launcher Design

## Goal

Entregar un archivo de arranque para Windows que permita a otro usuario clonar el repositorio público, preparar el entorno local y abrir la app en el navegador con el menor número posible de pasos manuales.

## Constraints

- El repositorio es público.
- El arranque debe funcionar desde Windows.
- El archivo de arranque debe clonar el repo si todavía no existe en la máquina destino.
- El repo se instalará en una ruta estable bajo `%LOCALAPPDATA%\WebVTES`.
- En ejecuciones posteriores no debe hacer `git pull`; sólo debe reutilizar la copia local y arrancar la app.
- La primera vez debe pedir:
  - nombre de usuario
  - contraseña
- Ese usuario debe ser un usuario normal, no superusuario.
- Ese usuario debe poder usar toda la app salvo admin.

## Decision

Añadiremos un flujo `clone-and-run` para Windows basado en PowerShell y un `.bat` lanzador fino.

El `.bat` será el punto de entrada visible y delegará en un script PowerShell más robusto.

## Runtime Flow

### First run

1. Resolver directorio de instalación:
   - `%LOCALAPPDATA%\WebVTES`
2. Si no existe el repo:
   - hacer `git clone` del repositorio público
3. Crear `.venv` si falta
4. Instalar `requirements.txt`
5. Ejecutar migraciones
6. Comprobar si existen usuarios en la base de datos
7. Si no existen:
   - pedir username
   - pedir password
   - crear usuario normal
8. Arrancar Django en local
9. Abrir el navegador en la URL local

### Subsequent runs

1. Reutilizar la carpeta ya clonada
2. No actualizar con `git pull`
3. Verificar `.venv`
4. Arrancar la app
5. Abrir navegador

## App Integration

No meteremos la creación interactiva del primer usuario dentro de una vista.

La forma limpia es añadir un comando o script Python reutilizable, algo como:

- `scripts/bootstrap_local_user.py`

Ese helper debe:

- recibir `username` y `password`
- crear usuario normal si no existe
- no tocar usuarios ya existentes

Los layouts por defecto ya quedan cubiertos por el bootstrap automático introducido en `apps.layouts`.

## Files

La solución debería quedar repartida así:

- `run_windows_clone.bat`
- `scripts/windows/clone_and_run.ps1`
- `scripts/bootstrap_local_user.py`
- `README.md`
- tests en `apps/layouts/tests.py` o donde mejor encaje el contrato de los scripts

## Testing

La cobertura debe fijar:

1. El helper Python de bootstrap de usuario
- crea usuario normal
- no duplica si ya existe

2. El contrato del script PowerShell
- usa `%LOCALAPPDATA%\WebVTES`
- clona el repo público
- crea `.venv`
- ejecuta migraciones
- llama al helper de creación de usuario
- no hace `git pull` en cada arranque

3. El contrato del `.bat`
- delega en el PowerShell correcto

## Important Note

Podemos preparar y verificar el contrato de scripts desde Linux, pero la prueba real del flujo final tendrá que hacerse en Windows.
