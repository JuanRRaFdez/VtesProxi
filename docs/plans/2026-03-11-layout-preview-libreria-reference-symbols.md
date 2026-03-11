# Layout Preview Libreria Reference Symbols Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add fixed preview-only clan, path, and discipline references to the layout editor preview for libreria cards.

**Architecture:** The layout editor already uses `FIXED_LAYOUT_PREVIEWS` plus autocomplete payloads to render a deterministic preview card. This change extends the libreria fixed preview with reference-only overrides and makes `api_preview()` resolve those values the same way cripta already resolves its fixed path override.

**Tech Stack:** Django, Python, Django test runner

---

### Task 1: Add Failing Preview Regression Test

**Files:**
- Modify: `apps/layouts/tests.py`

**Step 1: Write the failing test**

Extend the libreria preview API test so it asserts the preview render receives:

```python
'gangrel.png'
'death.png'
[
    {'name': 'ofu', 'level': 'inf'},
    {'name': 'dom', 'level': 'inf'},
    {'name': 'tha', 'level': 'inf'},
]
```

**Step 2: Run test to verify it fails**

Run:

```bash
/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.layouts.tests.LayoutPreviewApiTests.test_preview_for_libreria_uses_fixed_44_magnum_payload -v 2
```

Expected: FAIL because the current preview only passes `.44 Magnum` payload values for `clan`, `senda`, and `disciplinas`.

**Step 3: Commit**

```bash
git add apps/layouts/tests.py
git commit -m "test: cover libreria preview reference symbols"
```

### Task 2: Implement Preview-Only Overrides

**Files:**
- Modify: `apps/layouts/views.py`

**Step 1: Write minimal implementation**

Update `FIXED_LAYOUT_PREVIEWS['libreria']` and `api_preview()` so libreria preview resolves `clan`, `senda`, and `disciplinas` from the fixed preview config before falling back to the autocomplete payload.

**Step 2: Run targeted test to verify it passes**

Run:

```bash
/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.layouts.tests.LayoutPreviewApiTests.test_preview_for_libreria_uses_fixed_44_magnum_payload -v 2
```

Expected: PASS.

**Step 3: Commit**

```bash
git add apps/layouts/views.py apps/layouts/tests.py
git commit -m "feat: add libreria preview reference symbols"
```

### Task 3: Run Regression Verification

**Files:**
- Modify: `apps/layouts/views.py` (only if needed)
- Modify: `apps/layouts/tests.py` (only if needed)

**Step 1: Run relevant suites**

Run:

```bash
/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.layouts.tests apps.srv_textos.tests -v 1
```

Expected: PASS with no regressions.

**Step 2: Fix any failing regression minimally**

If needed, patch only the preview resolution path and rerun the same suite.
