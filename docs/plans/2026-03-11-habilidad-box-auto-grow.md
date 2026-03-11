# Habilidad Box Auto Grow Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make `habilidad.box` grow upward with a fixed bottom edge and vertically centered text for any layout that defines that box.

**Architecture:** The render engine in `apps/srv_textos/views.py` already computes a dynamic habilidad height and a `used_box`. The change will reinterpret `habilidad.box` as a persisted base box whose bottom edge remains fixed while `used_box` becomes the real render box sized from content, clamped to the card top, and consumed by downstream collision logic and text rendering helpers.

**Tech Stack:** Django, Python, Pillow, Django test runner

---

### Task 1: Lock Bottom Edge And Auto-Grow Used Box

**Files:**
- Modify: `apps/srv_textos/tests.py`
- Modify: `apps/srv_textos/views.py`

**Step 1: Write the failing test**

Add focused tests in `apps/srv_textos/tests.py` that verify:

```python
def test_habilidad_box_keeps_bottom_edge_and_grows_upward():
    ...

def test_habilidad_box_is_clamped_to_card_top():
    ...
```

**Step 2: Run test to verify it fails**

Run: `python manage.py test apps.srv_textos.tests.HabilidadDynamicHeightTests -v 2`
Expected: FAIL because `used_box` is still limited by `box.height` and/or does not clamp as specified.

**Step 3: Write minimal implementation**

Update `apps/srv_textos/views.py` so that when `habilidad.box` exists:

```python
bottom = habilidad_box["y"] + habilidad_box["height"]
used_height = dynamic_hab_box_h
used_y = max(0, bottom - used_height)
used_height = bottom - used_y
used_hab_box = {
    "x": habilidad_box["x"],
    "y": used_y,
    "width": habilidad_box["width"],
    "height": used_height,
}
```

Keep legacy behavior unchanged when `habilidad.box` is absent.

**Step 4: Run test to verify it passes**

Run: `python manage.py test apps.srv_textos.tests.HabilidadDynamicHeightTests -v 2`
Expected: PASS

**Step 5: Commit**

```bash
git add apps/srv_textos/tests.py apps/srv_textos/views.py
git commit -m "feat: auto grow habilidad box upward"
```

### Task 2: Vertically Center Habilidad Text Inside Effective Box

**Files:**
- Modify: `apps/srv_textos/tests.py`
- Modify: `apps/srv_textos/views.py`

**Step 1: Write the failing test**

Add render-level tests that verify the text block is centered vertically inside the provided `box_height` for both cripta and libreria helpers.

```python
def test_render_habilidad_centers_text_vertically_inside_box():
    ...

def test_render_habilidad_libreria_centers_text_vertically_inside_box():
    ...
```

**Step 2: Run test to verify it fails**

Run: `python manage.py test apps.srv_textos.tests.HabilidadRenderAlignmentTests -v 2`
Expected: FAIL because the current helper draws from the top padding, not the vertical center of the effective box.

**Step 3: Write minimal implementation**

Adjust `_render_habilidad_text()` and `_render_habilidad_text_libreria()` to:

```python
content_height = line_count * line_height
inner_top = outer_y + pad
inner_height = max(1, rh - (pad * 2))
cur_y = inner_top + max(0, (inner_height - content_height) // 2)
```

Use `content_x`/`content_width` consistently so horizontal alignment remains correct.

**Step 4: Run test to verify it passes**

Run: `python manage.py test apps.srv_textos.tests.HabilidadRenderAlignmentTests -v 2`
Expected: PASS

**Step 5: Commit**

```bash
git add apps/srv_textos/tests.py apps/srv_textos/views.py
git commit -m "feat: center habilidad text vertically"
```

### Task 3: Run Focused Regression Verification

**Files:**
- Modify: `apps/srv_textos/tests.py` (only if a gap appears during verification)
- Modify: `apps/srv_textos/views.py` (only if needed)

**Step 1: Run combined regression suite**

Run:

```bash
python manage.py test apps.srv_textos.tests.HabilidadDynamicHeightTests apps.srv_textos.tests.HabilidadRenderAlignmentTests apps.srv_textos.tests.GlobalCollisionResolverTests -v 2
```

Expected: PASS with no new regressions in the focused habilidad and collision flow.

**Step 2: Fix any failing regression minimally**

Only if needed, patch the smallest code path and re-run the same suite.

**Step 3: Commit**

```bash
git add apps/srv_textos/tests.py apps/srv_textos/views.py
git commit -m "test: verify habilidad box regressions"
```
