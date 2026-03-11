# Cripta Habilidad Bottom Anchor Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Restrict dynamic habilidad top recalculation to the cripta creation/preview flow while using only the persisted bottom edge of `habilidad.box`.

**Architecture:** The cripta UI will send an explicit render-context flag to the shared render endpoint. The backend will propagate that flag through `_render_carta()` into `_compute_layout_metrics()` and only then reinterpret `habilidad.box` as a bottom anchor for cripta. Other callers keep the normal fixed-box behavior.

**Tech Stack:** Django, Python, Pillow, Django templates, Django test runner

---

### Task 1: Add Failing Backend Tests For Render Context

**Files:**
- Modify: `apps/srv_textos/tests.py`
- Modify: `apps/srv_textos/views.py`

**Step 1: Write the failing test**

Add tests in `apps/srv_textos/tests.py` that verify:

```python
def test_cripta_dynamic_habilidad_from_bottom_uses_only_bottom_edge():
    ...

def test_habilidad_box_without_flag_remains_fixed():
    ...
```

**Step 2: Run test to verify it fails**

Run: `/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.srv_textos.tests.HabilidadDynamicHeightTests -v 2`
Expected: FAIL because the current logic still applies the dynamic recalc globally.

**Step 3: Write minimal implementation**

Propagate a boolean flag into `_compute_layout_metrics()` and gate the dynamic bottom-anchor behavior behind:

```python
is_dynamic_bottom_anchor = (
    dynamic_habilidad_from_bottom
    and normalized_card_type == "cripta"
    and has_habilidad_box
)
```

**Step 4: Run test to verify it passes**

Run: `/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.srv_textos.tests.HabilidadDynamicHeightTests -v 2`
Expected: PASS

**Step 5: Commit**

```bash
git add apps/srv_textos/tests.py apps/srv_textos/views.py
git commit -m "feat: scope habilidad bottom anchor to cripta context"
```

### Task 2: Propagate Render Context From Cripta UI

**Files:**
- Modify: `apps/cripta/templates/cripta/importar_imagen.html`
- Modify: `apps/srv_textos/views.py`
- Modify: `apps/srv_textos/tests.py`

**Step 1: Write the failing test**

Add a test covering endpoint propagation, for example through `render_clan`, asserting the flag reaches `_render_carta()`.

```python
def test_render_clan_propagates_dynamic_habilidad_from_bottom():
    ...
```

**Step 2: Run test to verify it fails**

Run: `/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.srv_textos.tests.LayoutResolverPriorityTests apps.srv_textos.tests.HabilidadDynamicHeightTests -v 2`
Expected: FAIL because the request payload is not propagated yet.

**Step 3: Write minimal implementation**

Pass `dynamic_habilidad_from_bottom: true` from the cripta template fetches that render the card preview and thread it through the Django endpoints into `_render_carta()`.

**Step 4: Run test to verify it passes**

Run: `/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.srv_textos.tests.LayoutResolverPriorityTests apps.srv_textos.tests.HabilidadDynamicHeightTests -v 2`
Expected: PASS

**Step 5: Commit**

```bash
git add apps/cripta/templates/cripta/importar_imagen.html apps/srv_textos/tests.py apps/srv_textos/views.py
git commit -m "feat: send cripta habilidad bottom-anchor render context"
```

### Task 3: Run Focused Regression Verification

**Files:**
- Modify: `apps/srv_textos/tests.py` (only if a gap appears)
- Modify: `apps/srv_textos/views.py` (only if needed)

**Step 1: Run focused regression suite**

Run:

```bash
/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.srv_textos.tests apps.layouts.tests -v 1
```

Expected: PASS with no regressions in cripta, layout rendering, or preview flow.

**Step 2: Fix any failing regression minimally**

Only if needed, patch the smallest code path and rerun the same suite.

**Step 3: Commit**

```bash
git add apps/cripta/templates/cripta/importar_imagen.html apps/srv_textos/tests.py apps/srv_textos/views.py
git commit -m "test: verify cripta habilidad bottom-anchor regressions"
```
