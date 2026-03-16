# Windows Git Bootstrap Launcher Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Añadir un lanzador Windows que clone el repo público en `%LOCALAPPDATA%\WebVTES`, prepare el entorno local, cree un usuario normal inicial si no existe ninguno y abra la app en el navegador.

**Architecture:** La solución se apoya en un `.bat` mínimo que delega en un script PowerShell principal. Ese script PowerShell resuelve la carpeta de instalación, clona el repo si hace falta, prepara `.venv`, aplica migraciones y llama a un helper Python reutilizable para crear el primer usuario. El arranque del servidor y la apertura del navegador se mantienen locales y sin actualizaciones automáticas del repo.

**Tech Stack:** PowerShell, batch de Windows, Python, Django, unittest de Django.

---

### Task 1: Añadir helper Python para bootstrap del primer usuario normal

**Files:**
- Create: `scripts/bootstrap_local_user.py`
- Modify: `apps/layouts/tests.py`

**Step 1: Write the failing test**

Añadir tests como:

```python
def test_bootstrap_local_user_creates_normal_user(self):
    result = bootstrap_local_user("compa", "clave123")
    self.assertTrue(result["created"])
    user = get_user_model().objects.get(username="compa")
    self.assertFalse(user.is_superuser)
    self.assertFalse(user.is_staff)

def test_bootstrap_local_user_is_idempotent(self):
    bootstrap_local_user("compa", "clave123")
    result = bootstrap_local_user("compa", "otra")
    self.assertFalse(result["created"])
    self.assertEqual(get_user_model().objects.filter(username="compa").count(), 1)
```

**Step 2: Run test to verify it fails**

Run:

```bash
/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.layouts.tests -v 1
```

Expected: FAIL porque el helper aún no existe.

**Step 3: Write minimal implementation**

Crear `scripts/bootstrap_local_user.py` con una función reutilizable y un entrypoint CLI:

- crear usuario normal si no existe
- no recrearlo si ya existe
- devolver estado legible

**Step 4: Run test to verify it passes**

Run:

```bash
/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.layouts.tests -v 1
```

Expected: PASS.

**Step 5: Commit**

```bash
git add scripts/bootstrap_local_user.py apps/layouts/tests.py
git commit -m "feat: add bootstrap helper for first local user"
```

### Task 2: Añadir scripts Windows de clone-and-run

**Files:**
- Create: `run_windows_clone.bat`
- Create: `scripts/windows/clone_and_run.ps1`
- Modify: `apps/layouts/tests.py`

**Step 1: Write the failing test**

Añadir tests de contrato como:

```python
def test_clone_and_run_script_uses_localappdata_install_dir(self):
    script = Path(settings.BASE_DIR, "scripts", "windows", "clone_and_run.ps1").read_text(encoding="utf-8")
    self.assertIn("$env:LOCALAPPDATA", script)
    self.assertIn("WebVTES", script)

def test_clone_and_run_script_clones_repo_and_bootstraps_user(self):
    script = Path(settings.BASE_DIR, "scripts", "windows", "clone_and_run.ps1").read_text(encoding="utf-8")
    self.assertIn("git clone", script)
    self.assertIn("bootstrap_local_user.py", script)
    self.assertNotIn("git pull", script)
```

**Step 2: Run test to verify it fails**

Run:

```bash
/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.layouts.tests -v 1
```

Expected: FAIL porque los scripts aún no existen.

**Step 3: Write minimal implementation**

Crear:

- `run_windows_clone.bat`
  - invoca PowerShell con el script principal
- `scripts/windows/clone_and_run.ps1`
  - resuelve `%LOCALAPPDATA%\WebVTES`
  - clona repo si falta
  - crea `.venv`
  - instala requirements
  - corre migraciones
  - pregunta por usuario/clave si no hay usuarios
  - llama a `scripts/bootstrap_local_user.py`
  - arranca la app y abre navegador

**Step 4: Run test to verify it passes**

Run:

```bash
/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.layouts.tests -v 1
```

Expected: PASS.

**Step 5: Commit**

```bash
git add run_windows_clone.bat scripts/windows/clone_and_run.ps1 apps/layouts/tests.py
git commit -m "feat: add windows clone-and-run launcher"
```

### Task 3: Documentar el flujo de arranque desde git

**Files:**
- Modify: `README.md`
- Modify: `docs/plans/2026-03-16-windows-git-bootstrap-design.md`

**Step 1: Update docs**

Añadir una sección nueva en `README.md` explicando:

- que el repo es público
- que el compañero puede ejecutar `run_windows_clone.bat`
- que el repo se clona en `%LOCALAPPDATA%\WebVTES`
- que el primer arranque pide username/password
- que no hace `git pull` automáticamente en ejecuciones posteriores

**Step 2: Verify docs are clear**

Revisar manualmente que la documentación menciona también que los usuarios nuevos reciben layouts default automáticamente.

**Step 3: Commit**

```bash
git add README.md docs/plans/2026-03-16-windows-git-bootstrap-design.md
git commit -m "docs: explain windows clone-and-run workflow"
```

### Task 4: Verificación final

**Files:**
- Modify: `apps/layouts/tests.py`
- Modify: `scripts/windows/clone_and_run.ps1`
- Modify: `scripts/bootstrap_local_user.py`

**Step 1: Run focused tests**

Run:

```bash
/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.layouts.tests apps.mis_cartas.tests apps.srv_textos.tests -v 1
```

Expected: PASS.

**Step 2: Run Django checks**

Run:

```bash
/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py check
```

Expected: `System check identified no issues`.

**Step 3: Run Python syntax checks**

Run:

```bash
/home/juanrrafdez/VtesProxi/.venv/bin/python -m py_compile scripts/bootstrap_local_user.py
```

Expected: no output, exit code `0`.

**Step 4: Final note**

Dejar claro al cerrar que la validación real del `.bat`/PowerShell completo sigue requiriendo Windows.

**Step 5: Commit**

```bash
git add README.md scripts apps/layouts/tests.py
git commit -m "feat: add windows git bootstrap launcher"
```
