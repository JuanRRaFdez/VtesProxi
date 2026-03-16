# Layout Cripta Y Gap Range Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Alinear el editor de layouts de `cripta` con la validacion backend para que `y_gap` no provoque errores de guardado al crear o editar layouts.

**Architecture:** El ajuste se divide en dos capas. Primero, `apps/layouts/services.py` ampliara el rango permitido de `cripta.y_gap` a un valor coherente con el canvas real. Segundo, `static/layouts/editor.js` clampetara la capa `cripta` para no producir nunca un `y_gap` fuera de ese rango. La cobertura se fijara en `apps/layouts/tests.py`.

**Tech Stack:** Django, Python, JavaScript vanilla, unittest de Django.

---

### Task 1: Fijar por test el nuevo rango permitido de `cripta.y_gap`

**Files:**
- Modify: `apps/layouts/tests.py`
- Modify: `apps/layouts/services.py`

**Step 1: Write the failing test**

Anadir un test tipo:

```python
def test_validate_accepts_large_cripta_y_gap_within_canvas_range(self):
    config = normalize_layout_config('cripta', load_classic_seed('cripta'))
    config['cripta']['y_gap'] = 420
    validate_layout_config('cripta', config)
```

**Step 2: Run test to verify it fails**

Run:

```bash
/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.layouts.tests.LayoutConfigBoxSchemaTests -v 2
```

Expected: FAIL con `y_gap fuera de rango`.

**Step 3: Write minimal implementation**

En `apps/layouts/services.py`:

- cambiar la validacion de `cripta.y_gap` desde `0..200` a un rango amplio coherente con el resto del layout, por ejemplo `0..3000`

**Step 4: Run test to verify it passes**

Run:

```bash
/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.layouts.tests.LayoutConfigBoxSchemaTests -v 2
```

Expected: PASS.

**Step 5: Commit**

```bash
git add apps/layouts/tests.py apps/layouts/services.py
git commit -m "fix: widen allowed cripta y gap range"
```

### Task 2: Fijar por test el clamp de la capa `cripta` en el editor

**Files:**
- Modify: `apps/layouts/tests.py`
- Modify: `static/layouts/editor.js`

**Step 1: Write the failing test**

Anadir un test de script que fije:

```python
def test_editor_script_clamps_cripta_layer_to_valid_y_gap_range(self):
    response = self.client.get('/layouts/')
    script = Path(settings.BASE_DIR / 'static' / 'layouts' / 'editor.js').read_text(encoding='utf-8')
    self.assertIn(\"layerName === 'cripta'\", script)
    self.assertIn('section.y_gap = Math.max(0', script)
    self.assertIn('normalizeFrameForLayer', script)
```

Y ajustar el test para que exija una referencia explicita al limite de `y_gap` o a un helper dedicado de clamp.

**Step 2: Run test to verify it fails**

Run:

```bash
/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.layouts.tests.LayoutEditorUiTests -v 2
```

Expected: FAIL porque el editor aun no fija ese clamp explicito para la capa `cripta`.

**Step 3: Write minimal implementation**

En `static/layouts/editor.js`:

- introducir un helper de clamp para la capa `cripta`
- aplicarlo en `frameFromSection()` y/o `applyFrameToSection()` al calcular la geometria y `section.y_gap`
- asegurar que el frame nunca produzca un `y_gap` superior al rango valido del backend

**Step 4: Run test to verify it passes**

Run:

```bash
/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.layouts.tests.LayoutEditorUiTests -v 2
```

Expected: PASS.

**Step 5: Commit**

```bash
git add apps/layouts/tests.py static/layouts/editor.js
git commit -m "fix: clamp cripta layer to valid y gap range"
```

### Task 3: Verificacion final

**Files:**
- Modify: `apps/layouts/services.py`
- Modify: `static/layouts/editor.js`
- Modify: `apps/layouts/tests.py`

**Step 1: Run focused suite**

Run:

```bash
/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.layouts.tests -v 1
```

Expected: PASS.

**Step 2: Run broader regression**

Run:

```bash
/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.layouts.tests apps.srv_textos.tests -v 1
```

Expected: PASS.

**Step 3: Run checks**

Run:

```bash
/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py check
```

Expected: OK.

**Step 4: Review diff**

Run:

```bash
git status --short
git diff -- apps/layouts/services.py static/layouts/editor.js apps/layouts/tests.py docs/plans/2026-03-16-layout-cripta-y-gap-range-design.md docs/plans/2026-03-16-layout-cripta-y-gap-range.md
```

Expected: solo cambios del rango/clamp de `cripta.y_gap` y la documentacion asociada.

**Step 5: Commit**

```bash
git add apps/layouts/services.py static/layouts/editor.js apps/layouts/tests.py docs/plans/2026-03-16-layout-cripta-y-gap-range-design.md docs/plans/2026-03-16-layout-cripta-y-gap-range.md
git commit -m "docs: add plan for cripta y gap range fix"
```
