# Layout Habilidad Box Clamp Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Hacer que el editor de layouts no genere `habilidad.box.y` negativo al guardar desde el panel derecho.

**Architecture:** El fix vive en el frontend del editor, en `static/layouts/editor.js`, dentro de la ruta común que traduce un frame del canvas a la configuración persistida. El backend mantiene su validación actual; nosotros hacemos que el editor deje de fabricar payloads inválidos. La cobertura se añade en `apps/layouts/tests.py`.

**Tech Stack:** Django, JavaScript vanilla, unittest de Django.

---

### Task 1: Fijar por test el clamp de coordenadas en la ruta común del editor

**Files:**
- Modify: `apps/layouts/tests.py`
- Modify: `static/layouts/editor.js`

**Step 1: Write the failing test**

Añadir un test de asset como:

```python
def test_editor_script_clamps_common_frame_coordinates_before_persisting_box(self):
    script = Path(settings.BASE_DIR, 'static', 'layouts', 'editor.js').read_text(encoding='utf-8')
    self.assertIn('Math.max(0, Math.round(normalizedFrame.x))', script)
    self.assertIn('Math.max(0, Math.round(normalizedFrame.y))', script)
```

Y fijar que ese clamp ocurre en la ruta común, no solo en el drag.

**Step 2: Run test to verify it fails**

Run:

```bash
/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.layouts.tests.LayoutEditorStaticAssetTests -v 2
```

Expected: FAIL porque hoy `applyFrameToSection()` persiste `normalizedFrame.y` tal cual.

**Step 3: Write minimal implementation**

En `static/layouts/editor.js`:

- introducir coordenadas clamped en la ruta común de `applyFrameToSection()`
- usarlas para `section.x`, `section.y` y `section.box`
- dejar intactas las ramas especiales de `disciplinas` y `habilidad` de `libreria`

**Step 4: Run test to verify it passes**

Run:

```bash
/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.layouts.tests.LayoutEditorStaticAssetTests -v 2
```

Expected: PASS.

**Step 5: Commit**

```bash
git add apps/layouts/tests.py static/layouts/editor.js
git commit -m "fix: clamp common layout frame coordinates"
```

### Task 2: Fijar por test el caso de `habilidad.box.y` negativo

**Files:**
- Modify: `apps/layouts/tests.py`
- Modify: `static/layouts/editor.js`

**Step 1: Write the failing test**

Añadir un test de integración ligera o de script que fije el caso concreto de `habilidad`:

```python
def test_editor_script_prevents_negative_habilidad_box_y(self):
    script = Path(settings.BASE_DIR, 'static', 'layouts', 'editor.js').read_text(encoding='utf-8')
    self.assertIn("layerName === 'habilidad'", script)
    self.assertIn('Math.max(0, Math.round(normalizedFrame.y))', script)
```

**Step 2: Run test to verify it fails**

Run:

```bash
/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.layouts.tests.LayoutEditorStaticAssetTests -v 2
```

Expected: FAIL o cobertura insuficiente antes del cambio.

**Step 3: Write minimal implementation**

Si hace falta, ajustar `applySelectedProperties()` o la rama común de `applyFrameToSection()` para que el panel derecho no pueda enviar un `frame.y` negativo persistible a `habilidad.box`.

**Step 4: Run test to verify it passes**

Run:

```bash
/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.layouts.tests.LayoutEditorStaticAssetTests -v 2
```

Expected: PASS.

**Step 5: Commit**

```bash
git add apps/layouts/tests.py static/layouts/editor.js
git commit -m "fix: prevent negative habilidad box coordinates from editor"
```

### Task 3: Verificación final

**Files:**
- Modify: `static/layouts/editor.js`
- Modify: `apps/layouts/tests.py`

**Step 1: Run focused suite**

Run:

```bash
/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.layouts.tests -v 1
```

Expected: PASS.

**Step 2: Run checks**

Run:

```bash
/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py check
node --check static/layouts/editor.js
```

Expected: OK.

**Step 3: Run broader regression**

Run:

```bash
/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.layouts.tests apps.srv_textos.tests -v 1
```

Expected: PASS.

**Step 4: Review diff**

Run:

```bash
git status --short
git diff -- static/layouts/editor.js apps/layouts/tests.py docs/plans/2026-03-16-layout-habilidad-box-clamp-design.md docs/plans/2026-03-16-layout-habilidad-box-clamp.md
```

Expected: solo cambios del clamp de coordenadas y la documentación asociada.

**Step 5: Commit**

```bash
git add static/layouts/editor.js apps/layouts/tests.py docs/plans/2026-03-16-layout-habilidad-box-clamp-design.md docs/plans/2026-03-16-layout-habilidad-box-clamp.md
git commit -m "docs: add plan for habilidad box clamp fix"
```
