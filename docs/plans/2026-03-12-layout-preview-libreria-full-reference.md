# Layout Preview Libreria Full Reference Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make the fixed layout editor preview for libreria render a full reference card with all major visible layers.

**Architecture:** The layout editor preview already supports preview-only overrides through `FIXED_LAYOUT_PREVIEWS`. This change expands the libreria preview entry into a full reference payload and teaches `api_preview()` to prefer those explicit preview fields over autocomplete data, while leaving the real card render path untouched.

**Tech Stack:** Django, Python, Django test runner

---

### Task 1: Add Failing Preview Regression Test

**Files:**
- Modify: `apps/layouts/tests.py`

**Step 1: Write the failing test**

Extend the libreria preview test so it asserts `_render_carta_from_path()` receives a full reference payload:

```python
nombre == 'Muestra de Libreria'
clan == 'gangrel.png'
coste == 'pool2'
disciplinas == [...]
simbolos == ['action', 'equipment']
habilidad == '...'
ilustrador == 'Crafted with AI'
```

Use a deliberately different autocomplete payload so the test proves the preview override is really taking precedence.

**Step 2: Run test to verify it fails**

Run:

```bash
/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.layouts.tests.LayoutPreviewApiTests.test_preview_for_libreria_uses_fixed_44_magnum_payload -v 2
```

Expected: FAIL because the current preview still depends on autocomplete values for `nombre`, `coste`, `habilidad`, and `simbolos`.

### Task 2: Implement Full Preview Overrides

**Files:**
- Modify: `apps/layouts/views.py`

**Step 1: Write minimal implementation**

Add the fixed libreria reference payload to `FIXED_LAYOUT_PREVIEWS['libreria']` and update `api_preview()` so it resolves preview overrides for:

- `nombre`
- `clan`
- `senda`
- `disciplinas`
- `simbolos`
- `habilidad`
- `coste`
- `ilustrador`

**Step 2: Run targeted test to verify it passes**

Run:

```bash
/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.layouts.tests.LayoutPreviewApiTests.test_preview_for_libreria_uses_fixed_44_magnum_payload -v 2
```

Expected: PASS.

### Task 3: Run Regression Verification

**Files:**
- Modify: `apps/layouts/views.py` (only if needed)
- Modify: `apps/layouts/tests.py` (only if needed)

**Step 1: Run relevant suites**

Run:

```bash
/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.layouts.tests apps.srv_textos.tests -v 1
/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py check
```

Expected: PASS with no regressions.
