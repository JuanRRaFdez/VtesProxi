# Layout Editor Clean Preview Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make `/layouts/` use a clean fixed background for `cripta` and `libreria`, while normalizing `libreria` stack layers to explicit `box` geometry so the editor behaves consistently.

**Architecture:** The layout editor preview endpoint in `apps.layouts` will stop rendering a full card and will return the fixed base image prepared from `static/layouts/images`. The editor will continue to draw only overlay boxes on top of that image, and legacy `libreria` configs will be normalized to explicit `box` values before being sent to the editor or saved from the seed path.

**Tech Stack:** Django views/tests, Python layout normalization helpers, vanilla JS editor overlay logic, Pillow-backed image preparation helper already present in `apps.srv_textos.views`.

---

### Task 1: Convert the layout preview endpoint to a clean background

**Files:**
- Modify: `apps/layouts/tests.py`
- Modify: `apps/layouts/views.py`

**Step 1: Write the failing test**

Add tests in `apps/layouts/tests.py` near `LayoutPreviewApiTests` asserting that the editor preview:
- prepares the fixed image source for `cripta`
- prepares the fixed image source for `libreria`
- does not call `_render_carta_from_path`

```python
@patch('apps.layouts.views._render_carta_from_path')
@patch('apps.layouts.views._prepare_render_source_from_path')
def test_preview_for_cripta_returns_clean_fixed_source(self, mock_prepare, mock_render):
    mock_prepare.return_value = '/media/layout_preview_sources/mimir.png'
    response = self.client.post(
        reverse('layouts:api_preview'),
        data=json.dumps({
            'card_type': 'cripta',
            'layout_config': normalize_layout_config('cripta', load_classic_seed('cripta')),
        }),
        content_type='application/json',
    )
    self.assertEqual(response.status_code, 200)
    self.assertEqual(response.json()['imagen_url'], '/media/layout_preview_sources/mimir.png')
    mock_render.assert_not_called()
```

**Step 2: Run test to verify it fails**

Run: `/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.layouts.tests.LayoutPreviewApiTests -v 2`

Expected: FAIL because `apps.layouts.views` still imports/calls `_render_carta_from_path` and does not expose `_prepare_render_source_from_path`.

**Step 3: Write minimal implementation**

In `apps/layouts/views.py`:
- replace `get_card_autocomplete` and `_render_carta_from_path` usage in `api_preview()`
- import `_prepare_render_source_from_path` from `apps.srv_textos.views`
- validate the incoming `layout_config` exactly as today
- resolve `imagen_abspath` from `FIXED_LAYOUT_PREVIEWS`
- return the prepared clean source URL directly

```python
from apps.srv_textos.views import _prepare_render_source_from_path


@login_required
def api_preview(request):
    ...
    validated_layout = validate_layout_config(card_type, layout_config)
    preview = FIXED_LAYOUT_PREVIEWS[card_type]
    imagen_abspath = os.path.join(settings.BASE_DIR, preview['image_path'])
    image_url = _prepare_render_source_from_path(
        imagen_abspath,
        target_name=preview['card_name'],
    )
    if not image_url:
        return JsonResponse({'error': 'Imagen de preview no encontrada'}, status=404)
    return JsonResponse({'imagen_url': image_url})
```

**Step 4: Run test to verify it passes**

Run: `/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.layouts.tests.LayoutPreviewApiTests -v 2`

Expected: PASS for the updated clean-preview assertions.

**Step 5: Commit**

```bash
git add apps/layouts/tests.py apps/layouts/views.py
git commit -m "feat: use clean layout preview sources"
```

### Task 2: Normalize legacy `libreria` stack layers to explicit `box` values

**Files:**
- Modify: `apps/layouts/tests.py`
- Modify: `apps/layouts/services.py`

**Step 1: Write the failing test**

Add tests in `apps/layouts/tests.py` for legacy `libreria` configs:
- `normalize_layout_config('libreria', ...)` materializes `disciplinas.box`
- `normalize_layout_config('libreria', ...)` materializes `simbolos.box`
- `validate_layout_config('libreria', ...)` rejects invalid negative `box` values for `disciplinas` and `simbolos`
- `validate_layout_config('libreria', ...)` validates `habilidad.box` when present

```python
def test_normalize_libreria_materializes_stack_boxes(self):
    config = load_classic_seed('libreria')
    normalized = normalize_layout_config('libreria', config)
    self.assertIn('box', normalized['disciplinas'])
    self.assertIn('box', normalized['simbolos'])
    self.assertEqual(normalized['disciplinas']['box']['x'], normalized['disciplinas']['x'])

def test_validate_libreria_rejects_invalid_simbolos_box(self):
    config = normalize_layout_config('libreria', load_classic_seed('libreria'))
    config['simbolos']['box']['x'] = -1
    with self.assertRaises(LayoutValidationError):
        validate_layout_config('libreria', config)
```

**Step 2: Run test to verify it fails**

Run: `/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.layouts.tests.LayoutConfigValidationTests -v 2`

Expected: FAIL because `normalize_layout_config()` does not currently create `box` for `disciplinas` and `simbolos`, and validation does not call `_validate_box()` for those sections.

**Step 3: Write minimal implementation**

In `apps/layouts/services.py`:
- add a helper to materialize stack-layer boxes from legacy fields
- call it from `normalize_layout_config()` for `disciplinas` and `simbolos` when `card_type == 'libreria'`
- add `_validate_box()` checks for `disciplinas` and `simbolos`
- validate `habilidad.box` when it exists

```python
def _ensure_stack_box_section(normalized, section_name, *, default_y_from_bottom=False):
    section = normalized.get(section_name)
    if not isinstance(section, dict):
        return
    carta = normalized.get('carta') or {}
    card_height = int(carta.get('height', 1040) or 1040)
    size = max(1, int(section.get('size', 64) or 64))
    spacing = max(1, int(section.get('spacing', 80) or 80))
    if default_y_from_bottom:
        y = max(0, card_height - int(section.get('bottom', 0) or 0) - size)
    else:
        y = int(section.get('y', 0) or 0)
    section['box'] = {
        'x': int(section.get('x', 0) or 0),
        'y': y,
        'width': size,
        'height': max(60, spacing * 3),
    }
```

**Step 4: Run test to verify it passes**

Run: `/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.layouts.tests.LayoutConfigValidationTests -v 2`

Expected: PASS for the new normalization and validation coverage.

**Step 5: Commit**

```bash
git add apps/layouts/tests.py apps/layouts/services.py
git commit -m "feat: normalize libreria stack boxes"
```

### Task 3: Send normalized configs to the editor for new and existing layouts

**Files:**
- Modify: `apps/layouts/tests.py`
- Modify: `apps/layouts/views.py`

**Step 1: Write the failing test**

Add tests covering:
- `_serialize_layout()` returns normalized `config` for a legacy `libreria` layout
- `api_create()` stores a normalized config for a new `libreria` layout so the editor receives `box` immediately

```python
def test_api_create_for_libreria_returns_normalized_boxes(self):
    response = self.client.post(
        reverse('layouts:api_create'),
        data=json.dumps({'name': 'Nueva', 'card_type': 'libreria'}),
        content_type='application/json',
    )
    self.assertEqual(response.status_code, 201)
    layout = response.json()['layout']
    self.assertIn('box', layout['config']['disciplinas'])
    self.assertIn('box', layout['config']['simbolos'])
```

**Step 2: Run test to verify it fails**

Run: `/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.layouts.tests.LayoutApiTests -v 2`

Expected: FAIL because `api_create()` still persists the raw seed and `_serialize_layout()` still returns the stored config verbatim.

**Step 3: Write minimal implementation**

In `apps/layouts/views.py`:
- normalize configs when serializing layouts for the editor
- save a validated, normalized seed in `api_create()`

```python
def _serialize_layout(layout):
    return {
        'id': layout.id,
        'name': layout.name,
        'card_type': layout.card_type,
        'config': normalize_layout_config(layout.card_type, layout.config),
        'is_default': layout.is_default,
    }


layout = UserLayout.objects.create(
    user=request.user,
    name=name,
    card_type=card_type,
    config=validate_layout_config(card_type, load_classic_seed(card_type)),
    is_default=False,
)
```

**Step 4: Run test to verify it passes**

Run: `/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.layouts.tests.LayoutApiTests -v 2`

Expected: PASS for normalized editor payloads and newly created `libreria` layouts.

**Step 5: Commit**

```bash
git add apps/layouts/tests.py apps/layouts/views.py
git commit -m "feat: normalize editor layout payloads"
```

### Task 4: Full verification and regression check

**Files:**
- Modify: none
- Test: `apps/layouts/tests.py`
- Test: `apps/srv_textos/tests.py`

**Step 1: Run focused regression tests**

Run: `/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.layouts.tests apps.srv_textos.tests -v 1`

Expected: PASS with the existing layout-editor and render regressions still green.

**Step 2: Run project checks**

Run: `/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py check`

Expected: `System check identified no issues`.

**Step 3: Review git status**

Run: `git status --short`

Expected: only the intended implementation files and generated plan/design docs are tracked.

**Step 4: Commit final verification state**

```bash
git add apps/layouts/tests.py apps/layouts/views.py apps/layouts/services.py docs/plans/2026-03-13-layout-editor-clean-preview-design.md docs/plans/2026-03-13-layout-editor-clean-preview.md
git commit -m "feat: simplify layout editor previews"
```
