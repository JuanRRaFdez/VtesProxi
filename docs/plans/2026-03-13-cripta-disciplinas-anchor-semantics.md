# Cripta Disciplinas Anchor Semantics Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Redefine `disciplinas.box` for `cripta` so it represents the lower icon anchor, icon size, and fixed vertical step, with optional fixed positioning independent from `habilidad`.

**Architecture:** The change should be centered in normalization, editor serialization, and render metrics. `apps.srv_textos.views` must stop deriving disciplina spacing from icon count in `cripta`, `apps.layouts.services` must reinterpret legacy config into the new anchor model, and `static/layouts/editor.js` must save the helper box with the new `x/y/width/height` meaning plus a fixed gap to `habilidad` when not using `fixed_bottom`.

**Tech Stack:** Django views/tests, Python layout normalization helpers, vanilla JS editor behavior, existing layout metrics renderer.

---

### Task 1: Lock the new `cripta` disciplina semantics in tests

**Files:**
- Modify: `apps/srv_textos/tests.py`
- Modify: `apps/layouts/tests.py`

**Step 1: Write the failing test**

Add tests covering:
- `box.height` is used as constant spacing in `cripta`, independent from discipline count
- `box.width` is used as icon size
- free mode uses a fixed gap to `habilidad`
- fixed mode uses `box.y`
- editor save/normalize path keeps the new semantics

```python
def test_cripta_disciplina_box_height_is_constant_spacing(self):
    config = normalize_layout_config('cripta', load_classic_seed('cripta'))
    config['disciplinas']['box'] = {'x': 40, 'y': 760, 'width': 64, 'height': 82}
    metrics_two = _compute_layout_metrics(config, card_type='cripta', disciplinas=[{'name': 'ani'}, {'name': 'aus'}])
    metrics_six = _compute_layout_metrics(config, card_type='cripta', disciplinas=[... six items ...])
    self.assertEqual(metrics_two['disciplinas']['spacing'], 82)
    self.assertEqual(metrics_six['disciplinas']['spacing'], 82)
```

**Step 2: Run test to verify it fails**

Run: `/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.srv_textos.tests apps.layouts.tests -v 2`

Expected: FAIL because current renderer divides spacing by icon count and the editor still serializes old semantics.

**Step 3: Write minimal implementation**

Do not implement yet. Continue to Tasks 2-4 after confirming the red state.

**Step 4: Commit**

Do not commit yet. Keep the failing tests uncommitted until the implementation turns them green.

### Task 2: Reinterpret legacy and edited `disciplinas.box` values for `cripta`

**Files:**
- Modify: `apps/layouts/services.py`
- Test: `apps/layouts/tests.py`

**Step 1: Write minimal implementation**

In `apps/layouts/services.py`:
- add a dedicated helper for `cripta` disciplina normalization
- map legacy fields to the new model:
  - `box.x` from `x`
  - `box.y` from legacy lower anchor
  - `box.width` from `size`
  - `box.height` from `spacing`
- add `rules.gap_from_habilidad` with default `0`
- preserve `anchor_mode`

```python
def _ensure_cripta_disciplina_anchor_section(normalized):
    section = normalized.get('disciplinas')
    if not isinstance(section, dict):
        return
    rules = section.setdefault('rules', {})
    rules.setdefault('anchor_mode', 'free')
    rules.setdefault('gap_from_habilidad', 0)
    section['box'] = {
        'x': int(section.get('x', 0) or 0),
        'y': int(section.get('box', {}).get('y', 0) or 0),
        'width': int(section.get('size', 64) or 64),
        'height': int(section.get('spacing', 80) or 80),
    }
```

**Step 2: Run test to verify it passes**

Run: `/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.layouts.tests -v 2`

Expected: PASS for normalization/validation cases added in Task 1.

**Step 3: Commit**

```bash
git add apps/layouts/services.py apps/layouts/tests.py
git commit -m "feat: normalize cripta disciplina anchor semantics"
```

### Task 3: Update editor save/load behavior for disciplina helper box

**Files:**
- Modify: `static/layouts/editor.js`
- Test: `apps/layouts/tests.py`

**Step 1: Write minimal implementation**

In `static/layouts/editor.js`:
- when loading `disciplinas`, treat the helper frame as:
  - `x = box.x`
  - `top = box.y - box.height`
  - `width = box.width`
  - `height = box.height`
- when saving `disciplinas`, write back:
  - `box.x = frame.x`
  - `box.y = frame.y + frame.height`
  - `box.width = frame.width`
  - `box.height = frame.height`
- keep `size = box.width` and `spacing = box.height`
- when not fixed, persist `rules.gap_from_habilidad` from the helper position relative to `habilidad`

```javascript
if (layerName === 'disciplinas') {
    section.box = {
        x: Math.round(normalizedFrame.x),
        y: Math.round(normalizedFrame.y + normalizedFrame.height),
        width: Math.max(30, Math.round(normalizedFrame.width)),
        height: Math.max(30, Math.round(normalizedFrame.height)),
    };
    section.size = section.box.width;
    section.spacing = section.box.height;
}
```

**Step 2: Run test to verify it passes**

Run: `/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.layouts.tests -v 2`

Expected: PASS for the editor serialization assertions added in Task 1.

**Step 3: Commit**

```bash
git add static/layouts/editor.js apps/layouts/tests.py
git commit -m "feat: save cripta disciplina helper as anchor box"
```

### Task 4: Make renderer use fixed size and fixed step in `cripta`

**Files:**
- Modify: `apps/srv_textos/views.py`
- Test: `apps/srv_textos/tests.py`

**Step 1: Write minimal implementation**

In `apps/srv_textos/views.py`:
- stop deriving `disciplinas.spacing` from `icon_count` when `card_type == 'cripta'` and `source == 'box'`
- compute the lower icon anchor from:
  - `box.y` if `fixed_bottom`
  - `used_hab_box['y'] - rules.gap_from_habilidad` if free
- build icon positions bottom-up using constant `box.height`

```python
if normalized_card_type == 'cripta' and has_disc_box:
    disc_size = max(1, int(disc_box['width']))
    disc_spacing = max(1, int(disc_box['height']))
    if disc_anchor_mode == 'fixed_bottom':
        lower_icon_bottom = int(disc_box['y'])
    else:
        gap = int(disc_rules.get('gap_from_habilidad', 0) or 0)
        lower_icon_bottom = max(0, used_hab_box['y'] - gap)
```

**Step 2: Run test to verify it passes**

Run: `/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.srv_textos.tests -v 2`

Expected: PASS for the new render metric and anchor tests.

**Step 3: Commit**

```bash
git add apps/srv_textos/views.py apps/srv_textos/tests.py
git commit -m "feat: render cripta disciplinas from anchor semantics"
```

### Task 5: Full verification

**Files:**
- Modify: none

**Step 1: Run focused suites**

Run: `/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.layouts.tests apps.srv_textos.tests -v 1`

Expected: PASS.

**Step 2: Run project checks**

Run: `/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py check`

Expected: `System check identified no issues`.

**Step 3: Review git status**

Run: `git status --short`

Expected: only intended implementation files and docs are tracked.

**Step 4: Commit final state if needed**

```bash
git add apps/layouts/services.py apps/layouts/tests.py static/layouts/editor.js apps/srv_textos/views.py apps/srv_textos/tests.py docs/plans/2026-03-13-cripta-disciplinas-anchor-semantics-design.md docs/plans/2026-03-13-cripta-disciplinas-anchor-semantics.md
git commit -m "feat: redefine cripta disciplina anchor semantics"
```
