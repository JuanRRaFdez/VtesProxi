# Disciplinas Fixed Bottom Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a fixed-bottom mode for the disciplinas layer so its lowest icon can be positioned independently from the habilidad box, with a dedicated checkbox in the layout editor.

**Architecture:** The layout model already persists per-section rules and the renderer already computes disciplina metrics from a box. This change adds a new `disciplinas.rules.anchor_mode = 'fixed_bottom'`, keeps the current responsive behavior as default, and teaches the editor to toggle that mode with a dedicated checkbox while leaving the icon stack rendering logic unchanged.

**Tech Stack:** Django, Python, JavaScript, Django test runner

---

### Task 1: Add Failing Backend Regression Tests

**Files:**
- Modify: `apps/srv_textos/tests.py`
- Modify: `apps/layouts/services.py`

**Step 1: Write the failing tests**

Add focused tests for:

```python
def test_disciplinas_fixed_bottom_preserves_box_bottom():
    ...

def test_validate_layout_accepts_fixed_bottom_for_disciplinas():
    ...
```

The first test should assert that `metrics['disciplinas']['box']['y'] + metrics['disciplinas']['box']['height']` stays equal to the configured bottom edge when `anchor_mode == 'fixed_bottom'`.

The second test should assert that layout validation accepts `disciplinas.rules.anchor_mode = 'fixed_bottom'`.

**Step 2: Run tests to verify they fail**

Run:

```bash
/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.srv_textos.tests.GlobalCollisionResolverTests apps.srv_textos.tests.SymbolsDiscBoxSizingTests apps.layouts.tests.LayoutValidationTests -v 2
```

Expected: FAIL because validation rejects `fixed_bottom` and metrics still re-anchor disciplinas to habilidad.

**Step 3: Commit**

```bash
git add apps/srv_textos/tests.py apps/layouts/tests.py apps/layouts/services.py
git commit -m "test: cover fixed bottom disciplinas mode"
```

### Task 2: Implement Backend Fixed-Bottom Mode

**Files:**
- Modify: `apps/layouts/services.py`
- Modify: `apps/srv_textos/views.py`

**Step 1: Write minimal implementation**

- Extend rule validation to accept `fixed_bottom`.
- In `_compute_layout_metrics()`, only re-anchor `disc_box['y']` from `used_hab_box` when the disciplinas anchor mode is not `fixed_bottom`.

**Step 2: Run focused tests to verify they pass**

Run:

```bash
/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.srv_textos.tests.SymbolsDiscBoxSizingTests apps.layouts.tests.LayoutValidationTests -v 2
```

Expected: PASS.

**Step 3: Commit**

```bash
git add apps/layouts/services.py apps/srv_textos/views.py apps/srv_textos/tests.py apps/layouts/tests.py
git commit -m "feat: add fixed bottom disciplinas mode"
```

### Task 3: Add Failing Editor UI Tests

**Files:**
- Modify: `apps/layouts/tests.py`
- Modify: `apps/layouts/templates/layouts/editor.html`
- Modify: `static/layouts/editor.js`

**Step 1: Write the failing tests**

Add assertions that the editor template exposes a dedicated checkbox for fixed disciplinas symbols and that existing preview/editor tests still mount correctly.

**Step 2: Run tests to verify they fail**

Run:

```bash
/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.layouts.tests.LayoutEditorTemplateTests -v 2
```

Expected: FAIL because the checkbox does not exist yet.

**Step 3: Commit**

```bash
git add apps/layouts/tests.py
git commit -m "test: cover disciplinas fixed checkbox"
```

### Task 4: Implement Editor Toggle

**Files:**
- Modify: `apps/layouts/templates/layouts/editor.html`
- Modify: `static/layouts/editor.js`

**Step 1: Write minimal implementation**

- Add the checkbox to the properties panel.
- Enable it only for `disciplinas`.
- Map checked to `section.rules.anchor_mode = 'fixed_bottom'` and unchecked to `free`.
- Keep the generic anchor selector disabled for `disciplinas`.

**Step 2: Run focused tests to verify they pass**

Run:

```bash
/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.layouts.tests.LayoutEditorTemplateTests -v 2
```

Expected: PASS.

**Step 3: Commit**

```bash
git add apps/layouts/templates/layouts/editor.html static/layouts/editor.js apps/layouts/tests.py
git commit -m "feat: add disciplinas fixed toggle to editor"
```

### Task 5: Run Regression Verification

**Files:**
- Modify: `apps/layouts/services.py` (only if needed)
- Modify: `apps/srv_textos/views.py` (only if needed)
- Modify: `apps/layouts/templates/layouts/editor.html` (only if needed)
- Modify: `static/layouts/editor.js` (only if needed)
- Modify: `apps/layouts/tests.py` (only if needed)
- Modify: `apps/srv_textos/tests.py` (only if needed)

**Step 1: Run relevant suites**

Run:

```bash
/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.layouts.tests apps.srv_textos.tests -v 1
/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py check
```

Expected: PASS with no regressions.

**Step 2: Fix any failing regression minimally**

If needed, patch only the disciplinas metrics path, validation, or editor property handling and rerun the same verification.
