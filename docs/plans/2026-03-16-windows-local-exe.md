# Windows Local EXE Launcher Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Preparar un bundle portable para Windows con un `.exe` lanzador que abra la app localmente en el navegador, conserve el estado actual del proyecto y garantice layouts `classic` por defecto para usuarios nuevos.

**Architecture:** El trabajo se divide en dos piezas coordinadas. Primero, la app Django gana un bootstrap idempotente de layouts por defecto para cada usuario nuevo. Después, añadimos una capa desktop para Windows con settings portables, lanzador supervisor/servidor, semillas de `db.sqlite3` y `media`, y assets de build para PyInstaller. El build final del `.exe` se hará en Windows, pero la lógica se dejará preparada y testeada desde el repo.

**Tech Stack:** Django, SQLite, señales de Django, Python estándar, PyInstaller, unittest de Django.

---

### Task 1: Añadir bootstrap idempotente de layouts por defecto para usuarios nuevos

**Files:**
- Create: `apps/layouts/bootstrap.py`
- Modify: `apps/layouts/apps.py`
- Create: `apps/layouts/signals.py`
- Modify: `apps/layouts/tests.py`

**Step 1: Write the failing test**

Añadir tests como:

```python
def test_new_user_gets_default_classic_layouts_for_both_card_types(self):
    user = get_user_model().objects.create_user(username="fresh", password="secret")
    defaults = UserLayout.objects.filter(user=user, is_default=True).order_by("card_type")
    self.assertEqual(
        [(layout.card_type, layout.name) for layout in defaults],
        [("cripta", "classic"), ("libreria", "classic")],
    )

def test_re_saving_user_does_not_duplicate_default_layouts(self):
    user = get_user_model().objects.create_user(username="stable", password="secret")
    user.first_name = "Stable"
    user.save()
    self.assertEqual(UserLayout.objects.filter(user=user, card_type="cripta").count(), 1)
    self.assertEqual(UserLayout.objects.filter(user=user, card_type="libreria").count(), 1)
```

**Step 2: Run test to verify it fails**

Run:

```bash
/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.layouts.tests.LayoutUserBootstrapTests -v 2
```

Expected: FAIL porque hoy no se crean layouts automáticamente al crear usuarios.

**Step 3: Write minimal implementation**

- Crear `ensure_default_layouts_for_user(user)` en `apps/layouts/bootstrap.py`.
- Reutilizar `load_classic_seed()` y `validate_layout_config()` para construir layouts válidos.
- Enganchar una señal `post_save` del modelo `User` en `apps/layouts/signals.py`.
- Importar señales en `apps/layouts/apps.py.ready()`.

**Step 4: Run test to verify it passes**

Run:

```bash
/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.layouts.tests.LayoutUserBootstrapTests -v 2
```

Expected: PASS.

**Step 5: Commit**

```bash
git add apps/layouts/bootstrap.py apps/layouts/apps.py apps/layouts/signals.py apps/layouts/tests.py
git commit -m "feat: bootstrap default layouts for new users"
```

### Task 2: Añadir settings portables para escritorio Windows

**Files:**
- Create: `webvtes/settings_desktop.py`
- Modify: `webvtes/settings.py`
- Modify: `apps/srv_textos/tests.py`

**Step 1: Write the failing test**

Añadir tests unitarios para el settings de escritorio, por ejemplo:

```python
def test_desktop_settings_use_portable_database_and_media_paths(self):
    env = {"WEBVTES_PORTABLE_DIR": "/tmp/webvtes-portable"}
    settings_module = import_desktop_settings(env)
    self.assertTrue(str(settings_module.DATABASES["default"]["NAME"]).endswith("db.sqlite3"))
    self.assertTrue(str(settings_module.MEDIA_ROOT).endswith("media"))
```

Si hace falta, crear helpers de test en `apps/srv_textos/tests.py` o en `apps/layouts/tests.py` según el mejor encaje.

**Step 2: Run test to verify it fails**

Run:

```bash
/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.layouts.tests apps.srv_textos.tests -v 1
```

Expected: FAIL porque `settings_desktop.py` aún no existe.

**Step 3: Write minimal implementation**

- Crear `webvtes/settings_desktop.py` importando desde `webvtes.settings`.
- Resolver `WEBVTES_PORTABLE_DIR` para `db.sqlite3` y `media/`.
- Fijar `ALLOWED_HOSTS = ["127.0.0.1", "localhost"]`.
- Mantener compatibilidad con static y media en local.

**Step 4: Run test to verify it passes**

Run:

```bash
/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.layouts.tests apps.srv_textos.tests -v 1
```

Expected: PASS.

**Step 5: Commit**

```bash
git add webvtes/settings_desktop.py webvtes/settings.py apps/srv_textos/tests.py apps/layouts/tests.py
git commit -m "feat: add portable desktop settings"
```

### Task 3: Implementar el lanzador Windows supervisor/servidor

**Files:**
- Create: `desktop/windows_launcher.py`
- Create: `desktop/runtime.py`
- Modify: `apps/layouts/tests.py`

**Step 1: Write the failing test**

Añadir tests de helpers, por ejemplo:

```python
def test_seed_copy_only_copies_db_and_media_when_missing(self):
    portable_dir = tmp_path / "portable"
    seed_dir = tmp_path / "seed"
    prepare_seed(seed_dir)
    ensure_seeded_runtime(portable_dir, seed_dir)
    ensure_seeded_runtime(portable_dir, seed_dir)
    assert (portable_dir / "db.sqlite3").exists()
    assert (portable_dir / "media").exists()
```

```python
def test_launcher_parses_supervisor_and_serve_modes(self):
    args = parse_args(["--serve", "--port", "8123"])
    assert args.serve is True
    assert args.port == 8123
```

**Step 2: Run test to verify it fails**

Run:

```bash
/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.layouts.tests -v 1
```

Expected: FAIL porque aún no existen `desktop/windows_launcher.py` ni los helpers.

**Step 3: Write minimal implementation**

- Crear lógica de runtime portable en `desktop/runtime.py`.
- Crear `desktop/windows_launcher.py` con:
  - parseo de argumentos
  - modo supervisor
  - modo servidor
  - espera activa a `http://127.0.0.1:<puerto>/login/`
  - apertura de navegador
- Mantener la implementación suficientemente desacoplada como para testear helpers sin necesitar Windows real.

**Step 4: Run test to verify it passes**

Run:

```bash
/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.layouts.tests -v 1
```

Expected: PASS.

**Step 5: Commit**

```bash
git add desktop/windows_launcher.py desktop/runtime.py apps/layouts/tests.py
git commit -m "feat: add portable windows launcher runtime"
```

### Task 4: Añadir assets de build para PyInstaller y semillas del paquete

**Files:**
- Create: `desktop/windows_launcher.spec`
- Create: `scripts/windows/build_windows_bundle.bat`
- Create: `scripts/windows/build_windows_bundle.ps1`
- Create: `desktop/seed/README.md`
- Modify: `.gitignore`

**Step 1: Write the failing test**

Añadir tests de contrato ligero sobre assets, por ejemplo:

```python
def test_windows_build_assets_reference_required_seed_resources(self):
    spec = Path(settings.BASE_DIR, "desktop", "windows_launcher.spec").read_text(encoding="utf-8")
    self.assertIn("db.sqlite3", spec)
    self.assertIn("media", spec)
    self.assertIn("desktop/windows_launcher.py", spec)
```

**Step 2: Run test to verify it fails**

Run:

```bash
/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.layouts.tests.LayoutDesktopPackagingTests -v 2
```

Expected: FAIL porque los assets de build aún no existen.

**Step 3: Write minimal implementation**

- Crear spec de PyInstaller para bundle one-dir.
- Crear scripts de build Windows.
- Documentar en `desktop/seed/README.md` que el bundle se construye incluyendo el `db.sqlite3` y `media/` actuales del repo.
- Ignorar directorios de salida de build si hace falta.

**Step 4: Run test to verify it passes**

Run:

```bash
/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.layouts.tests.LayoutDesktopPackagingTests -v 2
```

Expected: PASS.

**Step 5: Commit**

```bash
git add desktop/windows_launcher.spec scripts/windows/build_windows_bundle.bat scripts/windows/build_windows_bundle.ps1 desktop/seed/README.md .gitignore apps/layouts/tests.py
git commit -m "build: add windows bundle packaging assets"
```

### Task 5: Documentar uso y limitaciones del build Windows

**Files:**
- Modify: `README.md`
- Modify: `docs/plans/2026-03-16-windows-local-exe-design.md`

**Step 1: Write the failing doc check**

No hace falta test automatizado; fijar por revisión que `README.md` explique:

- cómo construir el bundle Windows
- que el build final del `.exe` debe hacerse en Windows
- qué estado local viaja en el paquete
- cómo actualizar semillas (`db.sqlite3`, `media/`)

**Step 2: Add documentation**

Añadir una sección tipo:

```md
## Windows Portable Bundle

1. Copia o actualiza `db.sqlite3` y `media/`.
2. Ejecuta `scripts/windows/build_windows_bundle.ps1` en Windows.
3. Entrega la carpeta `dist/...` a tu compañero.
4. El usuario exportado, layouts y cartas viajarán dentro del bundle inicial.
```

**Step 3: Verify docs are clear**

Revisar manualmente que la documentación explique también que los usuarios nuevos reciben layouts `classic` por defecto para `cripta` y `libreria`.

**Step 4: Commit**

```bash
git add README.md docs/plans/2026-03-16-windows-local-exe-design.md
git commit -m "docs: explain windows portable bundle workflow"
```

### Task 6: Verificación final

**Files:**
- Modify: `apps/layouts/tests.py`
- Modify: `desktop/windows_launcher.py`
- Modify: `webvtes/settings_desktop.py`

**Step 1: Run focused Django suite**

Run:

```bash
/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.layouts.tests apps.mis_cartas.tests apps.srv_textos.tests -v 1
```

Expected: PASS.

**Step 2: Run framework checks**

Run:

```bash
/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py check
```

Expected: `System check identified no issues`.

**Step 3: Run Python syntax checks for desktop files**

Run:

```bash
python -m py_compile desktop/windows_launcher.py desktop/runtime.py webvtes/settings_desktop.py
```

Expected: no output, exit code `0`.

**Step 4: Optional build note**

Anotar explícitamente en el cierre que el `.exe` final no se puede validar desde Linux y debe generarse/probarse en Windows.

**Step 5: Final commit**

```bash
git add desktop apps/layouts README.md webvtes
git commit -m "feat: add windows local launcher bundle support"
```
