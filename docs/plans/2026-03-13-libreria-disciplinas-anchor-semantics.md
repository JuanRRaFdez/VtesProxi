# Libreria Disciplinas Anchor Semantics Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make `disciplinas` in `libreria` use the same anchor-box semantics already implemented for `cripta`.

**Architecture:** Reuse the existing `cripta` anchor model across normalization, editor serialization, and render metrics. `libreria` should stop treating `disciplinas` as a stacked container and instead persist lower-anchor position, icon size, and fixed spacing exactly like `cripta`.

**Tech Stack:** Django views/tests, layout normalization helpers, vanilla JS editor behavior.

---

### Task 1: Lock the new libreria disciplina semantics in tests

**Files:**
- Modify: `apps/srv_textos/tests.py`
- Modify: `apps/layouts/tests.py`

**Step 1: Write the failing test**

Add tests covering:

- `libreria` `disciplinas.box.width` drives icon size
- `libreria` `disciplinas.box.height` drives constant spacing independent from discipline count
- `fixed_bottom` keeps `box.y`
- free mode uses `gap_from_habilidad`
- normalization materializes `disciplinas.box` for `libreria` with `gap_from_habilidad`

**Step 2: Run test to verify it fails**

Run: `/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.srv_textos.tests apps.layouts.tests -v 2`

Expected: FAIL because `libreria` still uses container semantics.

**Step 3: Commit**

Do not commit yet.

### Task 2: Normalize libreria disciplinas with anchor semantics

**Files:**
- Modify: `apps/layouts/services.py`
- Test: `apps/layouts/tests.py`

**Step 1: Write minimal implementation**

- Reuse the anchor normalization helper already used for `cripta`
- Apply it to `libreria` as well
- Keep legacy conversion for old `bottom/spacing/size` configs

**Step 2: Run test to verify it passes**

Run: `/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.layouts.tests -v 2`

Expected: PASS for the new `libreria` normalization and validation cases.

**Step 3: Commit**

```bash
git add apps/layouts/services.py apps/layouts/tests.py
git commit -m "feat: normalize libreria disciplinas as anchor box"
```

### Task 3: Align the editor behavior with cripta for libreria disciplinas

**Files:**
- Modify: `static/layouts/editor.js`
- Test: `apps/layouts/tests.py`

**Step 1: Write minimal implementation**

- Extend the `disciplinas` special-case path so it applies to `libreria` too
- Keep `Y` in the property panel as lower-anchor Y
- Persist `gap_from_habilidad` in free mode

**Step 2: Run test to verify it passes**

Run: `/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.layouts.tests -v 2`

Expected: PASS for the editor behavior assertions.

**Step 3: Commit**

```bash
git add static/layouts/editor.js apps/layouts/tests.py
git commit -m "feat: use cripta disciplina editor semantics in libreria"
```

### Task 4: Make libreria render disciplinas like cripta

**Files:**
- Modify: `apps/srv_textos/views.py`
- Test: `apps/srv_textos/tests.py`

**Step 1: Write minimal implementation**

- Remove the `libreria` container-based disciplina branch
- Make `libreria` share the same anchor semantics as `cripta`
- Keep the stack bottom-up with constant size and spacing

**Step 2: Run test to verify it passes**

Run: `/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.srv_textos.tests -v 2`

Expected: PASS for the new `libreria` discipline render behavior.

**Step 3: Commit**

```bash
git add apps/srv_textos/views.py apps/srv_textos/tests.py
git commit -m "feat: render libreria disciplinas from anchor semantics"
```

### Task 5: Full verification

**Files:**
- Modify: none

**Step 1: Run the full relevant suites**

Run: `/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.cripta.tests apps.srv_textos.tests apps.layouts.tests -v 1`

Expected: PASS.

**Step 2: Run project checks**

Run: `/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py check`

Expected: `System check identified no issues`.

**Step 3: Review git status**

Run: `git status --short`

Expected: only intended implementation files and docs changed.

**Step 4: Commit final state if needed**

```bash
git add apps/layouts/services.py apps/layouts/tests.py static/layouts/editor.js apps/srv_textos/views.py apps/srv_textos/tests.py docs/plans/2026-03-13-libreria-disciplinas-anchor-semantics-design.md docs/plans/2026-03-13-libreria-disciplinas-anchor-semantics.md
git commit -m "feat: unify libreria disciplinas with cripta anchor semantics"
```
