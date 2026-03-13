# Layout Editor Visible Boxes Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make all layout editor overlays clearly visible at all times and add a label to each box so users can identify layers directly on the canvas.

**Architecture:** The existing overlay DOM in `static/layouts/editor.js` will remain the source of truth. We will add lightweight label nodes when each layer is created and strengthen overlay contrast in `static/layouts/editor.css`, with tests covering the new label creation hook and stylesheet classes.

**Tech Stack:** Django template/tests, vanilla JS editor logic, CSS overlay styling.

---

### Task 1: Add regression tests for visible labeled overlays

**Files:**
- Modify: `apps/layouts/tests.py`

**Step 1: Write the failing test**

Add tests in `apps/layouts/tests.py` asserting:
- the editor script creates a `.layout-layer__label`
- the stylesheet includes classes for visible layers and labels

```python
def test_editor_script_creates_layer_labels(self):
    script = Path(settings.BASE_DIR / 'static' / 'layouts' / 'editor.js').read_text(encoding='utf-8')
    self.assertIn('layout-layer__label', script)

def test_editor_styles_define_visible_layer_labels(self):
    css = Path(settings.BASE_DIR / 'static' / 'layouts' / 'editor.css').read_text(encoding='utf-8')
    self.assertIn('.layout-layer__label', css)
    self.assertIn('.layout-layer.active', css)
```

**Step 2: Run test to verify it fails**

Run: `/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.layouts.tests.LayoutEditorTemplateTests -v 2`

Expected: FAIL because the label class does not exist yet in JS/CSS.

**Step 3: Write minimal implementation**

No production code in this task.

**Step 4: Commit**

Do not commit yet. Continue to Task 2 once the failure is confirmed.

### Task 2: Render labels for each overlay box

**Files:**
- Modify: `static/layouts/editor.js`
- Test: `apps/layouts/tests.py`

**Step 1: Write minimal implementation**

In `static/layouts/editor.js`, when creating each `.layout-layer`:
- create a child `span`
- assign class `layout-layer__label`
- set its text from `layerName`
- append it inside the layer node

```javascript
const label = document.createElement('span');
label.className = 'layout-layer__label';
label.textContent = layerName;
layer.appendChild(label);
```

**Step 2: Run test to verify it passes**

Run: `/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.layouts.tests.LayoutEditorTemplateTests.test_editor_script_creates_layer_labels -v 2`

Expected: PASS.

**Step 3: Commit**

```bash
git add static/layouts/editor.js apps/layouts/tests.py
git commit -m "feat: add labels to layout editor boxes"
```

### Task 3: Strengthen overlay visibility in CSS

**Files:**
- Modify: `static/layouts/editor.css`
- Test: `apps/layouts/tests.py`

**Step 1: Write minimal implementation**

Update `static/layouts/editor.css` so:
- `.layout-layer` gets a visible border, soft fill and shadow
- `.layout-layer.active` gets stronger border/glow and higher z-index
- `.layout-layer__label` is styled as a compact pill with `pointer-events: none`

```css
.layout-layer {
    border: 2px solid rgba(8, 126, 164, 0.95);
    background: rgba(8, 126, 164, 0.12);
    box-shadow: 0 0 0 1px rgba(255, 255, 255, 0.45), 0 6px 14px rgba(3, 28, 38, 0.18);
}

.layout-layer.active {
    border: 3px solid rgba(245, 159, 0, 0.98);
    box-shadow: 0 0 0 1px rgba(255, 244, 214, 0.8), 0 0 0 4px rgba(245, 159, 0, 0.18);
    z-index: 3;
}

.layout-layer__label {
    position: absolute;
    top: -1.1rem;
    left: 0;
    pointer-events: none;
}
```

**Step 2: Run test to verify it passes**

Run: `/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.layouts.tests.LayoutEditorTemplateTests.test_editor_styles_define_visible_layer_labels -v 2`

Expected: PASS.

**Step 3: Commit**

```bash
git add static/layouts/editor.css apps/layouts/tests.py
git commit -m "feat: make layout editor boxes more visible"
```

### Task 4: Full verification

**Files:**
- Modify: none

**Step 1: Run focused editor tests**

Run: `/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.layouts.tests -v 1`

Expected: PASS.

**Step 2: Run broader regression suite**

Run: `/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.layouts.tests apps.srv_textos.tests -v 1`

Expected: PASS.

**Step 3: Run project checks**

Run: `/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py check`

Expected: `System check identified no issues`.

**Step 4: Review git status**

Run: `git status --short`

Expected: only intended code and docs are tracked.

**Step 5: Commit final state if needed**

```bash
git add static/layouts/editor.css static/layouts/editor.js apps/layouts/tests.py docs/plans/2026-03-13-layout-editor-visible-boxes-design.md docs/plans/2026-03-13-layout-editor-visible-boxes.md
git commit -m "feat: improve layout editor box visibility"
```
