# Cripta Habilidad Effective Font Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make the habilidad background box in cripta resize from the actual rendered font size instead of the fixed layout font size.

**Architecture:** The dynamic bottom-anchor flow already exists and is correctly scoped to cripta. The change will thread `hab_font_size` into `_compute_layout_metrics()` and use it as the effective font size for dynamic height calculation when `dynamic_habilidad_from_bottom` is active.

**Tech Stack:** Django, Python, Pillow, Django test runner

---

### Task 1: Add Failing Regression Test For Effective Font Size

**Files:**
- Modify: `apps/srv_textos/tests.py`
- Modify: `apps/srv_textos/views.py`

**Step 1: Write the failing test**

Add a test that compares two cripta renders with the same text and layout box but different `hab_font_size` values while `dynamic_habilidad_from_bottom=True`.

```python
def test_cripta_dynamic_habilidad_uses_effective_render_font_size():
    ...
```

**Step 2: Run test to verify it fails**

Run: `/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.srv_textos.tests.HabilidadDynamicHeightTests -v 2`
Expected: FAIL because the box height is still calculated from `lh['font_size']`.

**Step 3: Write minimal implementation**

Update `_compute_layout_metrics()` to accept `hab_font_size=None`, derive `effective_hab_font_size`, and use that value in `_compute_habilidad_dynamic_height()` when the cripta dynamic-bottom-anchor flow is active.

**Step 4: Run test to verify it passes**

Run: `/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.srv_textos.tests.HabilidadDynamicHeightTests -v 2`
Expected: PASS

**Step 5: Commit**

```bash
git add apps/srv_textos/tests.py apps/srv_textos/views.py
git commit -m "feat: size cripta habilidad box from effective font"
```

### Task 2: Run Focused Regression Verification

**Files:**
- Modify: `apps/srv_textos/tests.py` (only if needed)
- Modify: `apps/srv_textos/views.py` (only if needed)

**Step 1: Run focused suite**

Run:

```bash
/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.srv_textos.tests apps.layouts.tests -v 1
```

Expected: PASS with no regressions.

**Step 2: Fix any failing regression minimally**

Only if needed, patch the smallest code path and rerun the same suite.

**Step 3: Commit**

```bash
git add apps/srv_textos/tests.py apps/srv_textos/views.py
git commit -m "test: verify effective font habilidad regressions"
```
