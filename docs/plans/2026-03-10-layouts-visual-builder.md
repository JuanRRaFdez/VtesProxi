# Visual Layouts Builder Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implementar una app `layouts` para crear/editar layouts visuales privados por usuario (Cripta y Librería), con drag & resize, guardado en BD y default por tipo.

**Architecture:** Se añade `apps.layouts` con modelo `UserLayout` (`JSONField`) y API autenticada para CRUD/config/default. El frontend del editor usa Interact.js para mover/redimensionar capas y previsualiza vía endpoints de render existentes con `layout_override`. `srv_textos` resuelve layout por prioridad (`override -> layout_id -> default usuario -> fallback classic`).

**Tech Stack:** Django 6, SQLite (dev), Django TestCase, JavaScript vanilla + Interact.js (CDN), templates Django.

---

**Execution rules:** aplicar @test-driven-development en cada tarea, validar resultados con @verification-before-completion antes de afirmar éxito, y mantener commits pequeños.

### Task 1: Crear app `layouts` y modelo `UserLayout`

**Files:**
- Create: `apps/layouts/__init__.py`
- Create: `apps/layouts/apps.py`
- Create: `apps/layouts/models.py`
- Create: `apps/layouts/migrations/0001_initial.py`
- Create: `apps/layouts/migrations/__init__.py`
- Create: `apps/layouts/tests.py`
- Modify: `webvtes/settings.py`

**Step 1: Write the failing test**

```python
class UserLayoutModelTests(TestCase):
    def test_unique_name_per_user_and_card_type(self):
        ...

    def test_only_one_default_per_user_and_card_type(self):
        ...
```

**Step 2: Run test to verify it fails**

Run: `python manage.py test apps.layouts.tests.UserLayoutModelTests -v 2`
Expected: FAIL (`ModuleNotFoundError` o modelo no definido).

**Step 3: Write minimal implementation**

```python
class UserLayout(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    name = models.CharField(max_length=80)
    card_type = models.CharField(max_length=16, choices=[('cripta','cripta'), ('libreria','libreria')])
    config = models.JSONField(default=dict)
    is_default = models.BooleanField(default=False)
```

Añadir constraints para unicidad de nombre y default único condicional.

**Step 4: Run test to verify it passes**

Run: `python manage.py test apps.layouts.tests.UserLayoutModelTests -v 2`
Expected: PASS.

**Step 5: Commit**

```bash
git add apps/layouts webvtes/settings.py
git commit -m "feat: add user layout model with constraints"
```

### Task 2: Montar rutas base de `layouts` y vista protegida

**Files:**
- Create: `apps/layouts/urls.py`
- Create: `apps/layouts/views.py`
- Create: `apps/layouts/templates/layouts/editor.html`
- Modify: `webvtes/urls.py`
- Modify: `apps/cripta/templates/base.html`
- Test: `apps/layouts/tests.py`

**Step 1: Write the failing test**

```python
class LayoutEditorAccessTests(TestCase):
    def test_editor_requires_login(self):
        response = self.client.get('/layouts/')
        self.assertEqual(response.status_code, 302)
```

**Step 2: Run test to verify it fails**

Run: `python manage.py test apps.layouts.tests.LayoutEditorAccessTests -v 2`
Expected: FAIL (ruta no existe).

**Step 3: Write minimal implementation**

```python
@login_required
def editor(request):
    return render(request, 'layouts/editor.html')
```

Registrar `path('layouts/', include('apps.layouts.urls'))` y añadir enlace en sidebar.

**Step 4: Run test to verify it passes**

Run: `python manage.py test apps.layouts.tests.LayoutEditorAccessTests -v 2`
Expected: PASS.

**Step 5: Commit**

```bash
git add apps/layouts webvtes/urls.py apps/cripta/templates/base.html
git commit -m "feat: add authenticated layouts editor route"
```

### Task 3: API `list/create/detail` con ownership

**Files:**
- Modify: `apps/layouts/views.py`
- Modify: `apps/layouts/urls.py`
- Modify: `apps/layouts/tests.py`
- Create: `apps/layouts/services.py`

**Step 1: Write the failing test**

```python
class LayoutApiListCreateTests(TestCase):
    def test_list_returns_only_current_user_layouts(self): ...
    def test_create_builds_layout_from_classic_seed(self): ...
    def test_detail_rejects_other_user_layout(self): ...
```

**Step 2: Run test to verify it fails**

Run: `python manage.py test apps.layouts.tests.LayoutApiListCreateTests -v 2`
Expected: FAIL (endpoints sin implementar).

**Step 3: Write minimal implementation**

```python
@login_required
def api_list(request): ...
@login_required
def api_create(request): ...
@login_required
def api_detail(request, layout_id): ...
```

En `services.py`, helper `load_classic_seed(card_type)` leyendo `apps/srv_textos/layouts.json`.

**Step 4: Run test to verify it passes**

Run: `python manage.py test apps.layouts.tests.LayoutApiListCreateTests -v 2`
Expected: PASS.

**Step 5: Commit**

```bash
git add apps/layouts
git commit -m "feat: add list/create/detail layout api endpoints"
```

### Task 4: API `update-config` con validación de schema/rangos

**Files:**
- Modify: `apps/layouts/services.py`
- Modify: `apps/layouts/views.py`
- Modify: `apps/layouts/urls.py`
- Modify: `apps/layouts/tests.py`

**Step 1: Write the failing test**

```python
class LayoutConfigValidationTests(TestCase):
    def test_update_config_rejects_invalid_payload(self): ...
    def test_update_config_accepts_valid_payload(self): ...
```

**Step 2: Run test to verify it fails**

Run: `python manage.py test apps.layouts.tests.LayoutConfigValidationTests -v 2`
Expected: FAIL.

**Step 3: Write minimal implementation**

```python
def validate_layout_config(card_type, config):
    # required keys + numeric ranges
    return normalized_config
```

Endpoint `api_update_config` persiste solo si validación pasa.

**Step 4: Run test to verify it passes**

Run: `python manage.py test apps.layouts.tests.LayoutConfigValidationTests -v 2`
Expected: PASS.

**Step 5: Commit**

```bash
git add apps/layouts
git commit -m "feat: validate and persist layout config updates"
```

### Task 5: API `rename/delete/set-default`

**Files:**
- Modify: `apps/layouts/views.py`
- Modify: `apps/layouts/urls.py`
- Modify: `apps/layouts/tests.py`

**Step 1: Write the failing test**

```python
class LayoutManagementApiTests(TestCase):
    def test_rename_layout(self): ...
    def test_delete_layout(self): ...
    def test_set_default_switches_previous_default_off(self): ...
```

**Step 2: Run test to verify it fails**

Run: `python manage.py test apps.layouts.tests.LayoutManagementApiTests -v 2`
Expected: FAIL.

**Step 3: Write minimal implementation**

```python
@login_required
def api_rename(request): ...
@login_required
def api_delete(request): ...
@login_required
def api_set_default(request): ...
```

`api_set_default`: transaction + update atomico por `user` y `card_type`.

**Step 4: Run test to verify it passes**

Run: `python manage.py test apps.layouts.tests.LayoutManagementApiTests -v 2`
Expected: PASS.

**Step 5: Commit**

```bash
git add apps/layouts
git commit -m "feat: add rename delete and set-default layout endpoints"
```

### Task 6: Resolver de layout en `srv_textos` (override/id/default/fallback)

**Files:**
- Modify: `apps/srv_textos/views.py`
- Modify: `apps/srv_textos/tests.py`
- Modify: `apps/layouts/services.py`

**Step 1: Write the failing test**

```python
class LayoutResolverPriorityTests(TestCase):
    def test_render_uses_layout_override_first(self): ...
    def test_render_uses_layout_id_when_provided(self): ...
    def test_render_rejects_layout_id_from_other_user(self): ...
```

**Step 2: Run test to verify it fails**

Run: `python manage.py test apps.srv_textos.tests.LayoutResolverPriorityTests -v 2`
Expected: FAIL.

**Step 3: Write minimal implementation**

```python
def _resolve_layout_config(request_user, card_type, layout_id=None, layout_name=None, layout_override=None):
    ...
```

Inyectar `request.user` en endpoints `render-*` y usar resolver central.

**Step 4: Run test to verify it passes**

Run: `python manage.py test apps.srv_textos.tests.LayoutResolverPriorityTests -v 2`
Expected: PASS.

**Step 5: Commit**

```bash
git add apps/srv_textos apps/layouts
git commit -m "feat: resolve render layout from user config with priority"
```

### Task 7: Integrar selector de layouts en Cripta y Librería

**Files:**
- Modify: `apps/cripta/views.py`
- Modify: `apps/libreria/views.py`
- Modify: `apps/cripta/templates/cripta/importar_imagen.html`
- Modify: `apps/srv_textos/tests.py`

**Step 1: Write the failing test**

```python
class ImportViewsLayoutContextTests(TestCase):
    def test_cripta_view_uses_user_layout_options(self): ...
    def test_libreria_view_uses_user_layout_options(self): ...
```

**Step 2: Run test to verify it fails**

Run: `python manage.py test apps.srv_textos.tests.ImportViewsLayoutContextTests -v 2`
Expected: FAIL.

**Step 3: Write minimal implementation**

- Context con `layout_options` desde BD del usuario.
- `active_layout_id` por default del tipo.
- JS del template envía `layout_id` en cada `fetch` de render.

**Step 4: Run test to verify it passes**

Run: `python manage.py test apps.srv_textos.tests.ImportViewsLayoutContextTests -v 2`
Expected: PASS.

**Step 5: Commit**

```bash
git add apps/cripta apps/libreria apps/srv_textos
git commit -m "feat: wire import views to user-scoped layouts"
```

### Task 8: Implementar editor visual drag/resize con Interact.js

**Files:**
- Modify: `apps/layouts/templates/layouts/editor.html`
- Create: `static/layouts/editor.css`
- Create: `static/layouts/editor.js`
- Modify: `apps/layouts/views.py`
- Modify: `apps/layouts/tests.py`

**Step 1: Write the failing test**

```python
class LayoutEditorTemplateTests(TestCase):
    def test_editor_template_contains_required_mount_points(self):
        response = self.client.get('/layouts/')
        self.assertContains(response, 'id="layout-stage"')
        self.assertContains(response, 'id="layout-properties"')
```

**Step 2: Run test to verify it fails**

Run: `python manage.py test apps.layouts.tests.LayoutEditorTemplateTests -v 2`
Expected: FAIL.

**Step 3: Write minimal implementation**

- Añadir stage + handles de elementos.
- Cargar Interact.js por CDN.
- En `editor.js`: estado local de config, drag/resize, debounce de preview, guardar en `api/update-config`.

**Step 4: Run test to verify it passes**

Run: `python manage.py test apps.layouts.tests.LayoutEditorTemplateTests -v 2`
Expected: PASS.

**Step 5: Commit**

```bash
git add apps/layouts static/layouts
git commit -m "feat: add visual drag-resize layout editor ui"
```

### Task 9: Regresión de APIs y flujo completo

**Files:**
- Modify: `apps/layouts/tests.py`
- Modify: `apps/srv_textos/tests.py`
- Modify: `docs/plans/2026-03-10-layouts-visual-builder-design.md` (si hay cambios de alcance)

**Step 1: Write the failing test**

```python
class EndToEndLayoutFlowTests(TestCase):
    def test_user_can_create_edit_set_default_and_render_with_layout(self): ...
```

**Step 2: Run test to verify it fails**

Run: `python manage.py test apps.layouts.tests.EndToEndLayoutFlowTests -v 2`
Expected: FAIL.

**Step 3: Write minimal implementation**

Ajustes puntuales detectados por test E2E (sin añadir scope nuevo).

**Step 4: Run test to verify it passes**

Run:
- `python manage.py test apps.layouts.tests -v 2`
- `python manage.py test apps.srv_textos.tests -v 2`

Expected: PASS en ambos.

**Step 5: Commit**

```bash
git add apps/layouts apps/srv_textos docs/plans
git commit -m "test: cover end-to-end user layout flow"
```

### Task 10: Verificación final y limpieza

**Files:**
- Modify: `README.md` (si existe sección de uso de layouts)
- Modify: `apps/cripta/templates/base.html` (verificar navegación final)

**Step 1: Write the failing test**

No aplica nuevo test funcional; usar suite completa relevante.

**Step 2: Run verification command set**

Run:
- `python manage.py test apps.layouts.tests -v 2`
- `python manage.py test apps.srv_textos.tests -v 2`
- `python manage.py check`

Expected: todo PASS, sin system check errors.

**Step 3: Write minimal implementation**

Ajustes de documentación y pequeños fixes de integración si aparecen en verificación.

**Step 4: Run verification again**

Run mismos comandos.
Expected: PASS estable.

**Step 5: Commit**

```bash
git add README.md apps/cripta/templates/base.html
git commit -m "docs: document layouts editor workflow"
```
