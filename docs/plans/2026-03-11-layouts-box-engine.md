# Layout Box Engine v2 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implementar un motor de layout basado en cajas (`box`) con reglas configurables por usuario para texto, simbolos y anti-solape global en render.

**Architecture:** Se extiende `config` a schema v2 con normalizacion legacy -> box y validacion estricta en `apps.layouts.services`. El render de `apps.srv_textos.views` pasa a un pipeline de metricas y colisiones, con helpers reutilizables para texto en caja, iconos y desplazamiento automatico. El editor visual expone propiedades nuevas y persiste v2 con APIs existentes.

**Tech Stack:** Django 6, Python 3, Django TestCase, JavaScript vanilla + Interact.js, templates Django.

---

**Execution rules:** aplicar @test-driven-development en cada tarea, validar resultados con @verification-before-completion antes de afirmar exito, y mantener commits pequenos.

### Task 1: Definir schema v2 y normalizador legacy -> box

**Files:**
- Modify: `apps/layouts/services.py`
- Modify: `apps/layouts/tests.py`

**Step 1: Write the failing test**

```python
class LayoutConfigBoxSchemaTests(TestCase):
    def test_normalize_legacy_config_adds_box_for_nombre(self):
        legacy = load_classic_seed('cripta')
        normalized = normalize_layout_config('cripta', legacy)
        self.assertIn('box', normalized['nombre'])
        self.assertEqual(normalized['nombre']['box']['x'], legacy['nombre']['x'])

    def test_normalize_applies_text_defaults_for_nombre_and_ilustrador(self):
        normalized = normalize_layout_config('cripta', load_classic_seed('cripta'))
        self.assertEqual(normalized['nombre']['rules']['align'], 'center')
        self.assertEqual(normalized['ilustrador']['rules']['align'], 'left')
```

**Step 2: Run test to verify it fails**

Run: `/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.layouts.tests.LayoutConfigBoxSchemaTests -v 2`
Expected: FAIL (`NameError`/`AttributeError` porque `normalize_layout_config` no existe).

**Step 3: Write minimal implementation**

```python
def normalize_layout_config(card_type, config):
    normalized = deepcopy(config)
    # for each section, build box from legacy fields when missing
    # inject text rules defaults:
    # nombre.align=center, ilustrador.align=left, autoshrink+ellipsis enabled
    return normalized
```

**Step 4: Run test to verify it passes**

Run: `/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.layouts.tests.LayoutConfigBoxSchemaTests -v 2`
Expected: PASS.

**Step 5: Commit**

```bash
git add apps/layouts/services.py apps/layouts/tests.py
git commit -m "feat: add layout v2 box normalizer with defaults"
```

### Task 2: Extender validacion de config v2 (box + enums + rangos)

**Files:**
- Modify: `apps/layouts/services.py`
- Modify: `apps/layouts/tests.py`

**Step 1: Write the failing test**

```python
class LayoutConfigValidationV2Tests(TestCase):
    def test_validate_rejects_invalid_align(self):
        config = normalize_layout_config('cripta', load_classic_seed('cripta'))
        config['nombre']['rules']['align'] = 'diagonal'
        with self.assertRaises(LayoutValidationError):
            validate_layout_config('cripta', config)

    def test_validate_rejects_box_out_of_range(self):
        config = normalize_layout_config('cripta', load_classic_seed('cripta'))
        config['nombre']['box']['width'] = -1
        with self.assertRaises(LayoutValidationError):
            validate_layout_config('cripta', config)
```

**Step 2: Run test to verify it fails**

Run: `/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.layouts.tests.LayoutConfigValidationV2Tests -v 2`
Expected: FAIL.

**Step 3: Write minimal implementation**

```python
def _validate_box(section_name, section):
    # require x,y,width,height numeric and in range

def _validate_text_rules(section_name, rules):
    # align in left|center|right
    # anchor_mode in free|top_locked|bottom_locked
    # min_font_size range
```

Integrar `normalize_layout_config` dentro de `validate_layout_config` para mantener compatibilidad legacy.

**Step 4: Run test to verify it passes**

Run: `/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.layouts.tests.LayoutConfigValidationV2Tests -v 2`
Expected: PASS.

**Step 5: Commit**

```bash
git add apps/layouts/services.py apps/layouts/tests.py
git commit -m "feat: validate v2 box schema and text rules"
```

### Task 3: Implementar helper de texto en caja (align + shrink + ellipsis)

**Files:**
- Modify: `apps/srv_textos/views.py`
- Modify: `apps/srv_textos/tests.py`

**Step 1: Write the failing test**

```python
class TextInBoxHelpersTests(SimpleTestCase):
    def test_fit_text_shrinks_then_ellipsis(self):
        fitted = srv_textos_views._fit_text_to_box(
            text='ABCDEFGHIJKLMNOPQRSTUVWXYZ',
            font_path='static/fonts/MatrixExtraBold.otf',
            start_font_size=50,
            min_font_size=18,
            max_width=80,
            ellipsis_enabled=True,
        )
        self.assertLessEqual(fitted['width'], 80)
        self.assertTrue(fitted['text'].endswith('...'))

    def test_horizontal_alignment_center(self):
        x = srv_textos_views._compute_aligned_x(100, 40, 'center')
        self.assertEqual(x, 130)
```

**Step 2: Run test to verify it fails**

Run: `/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.srv_textos.tests.TextInBoxHelpersTests -v 2`
Expected: FAIL (helpers no implementados).

**Step 3: Write minimal implementation**

```python
def _fit_text_to_box(...):
    # loop decreasing font size until min
    # if still overflow and ellipsis enabled, trim and append "..."
    return {'text': text, 'font_size': size, 'width': width}

def _compute_aligned_x(box_x, text_width, align):
    ...
```

**Step 4: Run test to verify it passes**

Run: `/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.srv_textos.tests.TextInBoxHelpersTests -v 2`
Expected: PASS.

**Step 5: Commit**

```bash
git add apps/srv_textos/views.py apps/srv_textos/tests.py
git commit -m "feat: add text-in-box helper with align shrink and ellipsis"
```

### Task 4: Renderizar nombre e ilustrador dentro de box configurable

**Files:**
- Modify: `apps/srv_textos/views.py`
- Modify: `apps/srv_textos/tests.py`

**Step 1: Write the failing test**

```python
class NameIllustratorBoxRenderTests(TestCase):
    def test_nombre_uses_box_alignment_and_shadow_toggle(self):
        config = normalize_layout_config('cripta', load_classic_seed('cripta'))
        config['nombre']['rules']['align'] = 'right'
        config['nombre']['shadow']['enabled'] = False
        metrics = srv_textos_views._compute_layout_metrics(config, card_type='cripta', habilidad='')
        self.assertEqual(metrics['nombre']['align'], 'right')
        self.assertFalse(metrics['nombre']['shadow_enabled'])

    def test_ilustrador_stays_within_box(self):
        config = normalize_layout_config('cripta', load_classic_seed('cripta'))
        metrics = srv_textos_views._compute_layout_metrics(config, card_type='cripta', habilidad='x')
        self.assertLessEqual(metrics['ilustrador']['text_width'], metrics['ilustrador']['box']['width'])
```

**Step 2: Run test to verify it fails**

Run: `/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.srv_textos.tests.NameIllustratorBoxRenderTests -v 2`
Expected: FAIL.

**Step 3: Write minimal implementation**

```python
# in _render_carta:
# use section['box'] + section['rules'] for nombre and ilustrador
# call _fit_text_to_box + _compute_aligned_x
# apply shadow only when enabled
```

**Step 4: Run test to verify it passes**

Run: `/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.srv_textos.tests.NameIllustratorBoxRenderTests -v 2`
Expected: PASS.

**Step 5: Commit**

```bash
git add apps/srv_textos/views.py apps/srv_textos/tests.py
git commit -m "feat: render name and illustrator inside configurable boxes"
```

### Task 5: Ajustar simbolos y disciplinas para ocupar su box

**Files:**
- Modify: `apps/srv_textos/views.py`
- Modify: `apps/srv_textos/tests.py`

**Step 1: Write the failing test**

```python
class SymbolsDiscBoxSizingTests(SimpleTestCase):
    def test_disciplines_size_scales_from_box_width(self):
        box = {'x': 10, 'y': 100, 'width': 120, 'height': 280}
        size, spacing = srv_textos_views._compute_disc_metrics_from_box(box, icon_count=3)
        self.assertLessEqual(size, 120)
        self.assertGreater(spacing, 0)

    def test_symbols_do_not_overflow_box(self):
        box = {'x': 10, 'y': 100, 'width': 100, 'height': 300}
        metrics = srv_textos_views._compute_symbol_metrics_from_box(box, icon_count=4)
        self.assertLessEqual(metrics['size'], 100)
```

**Step 2: Run test to verify it fails**

Run: `/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.srv_textos.tests.SymbolsDiscBoxSizingTests -v 2`
Expected: FAIL.

**Step 3: Write minimal implementation**

```python
def _compute_disc_metrics_from_box(box, icon_count):
    # size from width, spacing from height/icon_count
    return size, spacing

def _compute_symbol_metrics_from_box(box, icon_count):
    ...
```

Integrar en bloques de render de `disciplinas` y `simbolos`.

**Step 4: Run test to verify it passes**

Run: `/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.srv_textos.tests.SymbolsDiscBoxSizingTests -v 2`
Expected: PASS.

**Step 5: Commit**

```bash
git add apps/srv_textos/views.py apps/srv_textos/tests.py
git commit -m "feat: scale symbols and disciplines to fit user boxes"
```

### Task 6: Habilidad con altura dinamica y metricas unificadas

**Files:**
- Modify: `apps/srv_textos/views.py`
- Modify: `apps/srv_textos/tests.py`

**Step 1: Write the failing test**

```python
class HabilidadDynamicHeightTests(SimpleTestCase):
    def test_habilidad_height_grows_with_longer_text(self):
        config = normalize_layout_config('cripta', load_classic_seed('cripta'))
        short_metrics = srv_textos_views._compute_layout_metrics(config, 'cripta', 'corto')
        long_metrics = srv_textos_views._compute_layout_metrics(config, 'cripta', 'texto ' * 40)
        self.assertGreater(long_metrics['habilidad']['height'], short_metrics['habilidad']['height'])
```

**Step 2: Run test to verify it fails**

Run: `/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.srv_textos.tests.HabilidadDynamicHeightTests -v 2`
Expected: FAIL.

**Step 3: Write minimal implementation**

```python
def _compute_habilidad_dynamic_height(...):
    # based on wrapped lines, font size, padding and line spacing
    return dynamic_height
```

Conectar el resultado al pipeline de metricas.

**Step 4: Run test to verify it passes**

Run: `/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.srv_textos.tests.HabilidadDynamicHeightTests -v 2`
Expected: PASS.

**Step 5: Commit**

```bash
git add apps/srv_textos/views.py apps/srv_textos/tests.py
git commit -m "feat: compute dynamic habilidad box height from content"
```

### Task 7: Motor anti-solape global con prioridades y anclajes

**Files:**
- Modify: `apps/srv_textos/views.py`
- Modify: `apps/srv_textos/tests.py`

**Step 1: Write the failing test**

```python
class GlobalCollisionResolverTests(SimpleTestCase):
    def test_collision_resolver_moves_elements_up_when_habilidad_grows(self):
        metrics = {
            'habilidad': {'box': {'x': 150, 'y': 600, 'width': 400, 'height': 300}},
            'disciplinas': {'box': {'x': 40, 'y': 680, 'width': 90, 'height': 260}, 'anchor_mode': 'free'},
        }
        resolved = srv_textos_views._resolve_global_collisions(metrics, card_height=1040)
        self.assertLess(resolved['disciplinas']['box']['y'], 680)
```

**Step 2: Run test to verify it fails**

Run: `/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.srv_textos.tests.GlobalCollisionResolverTests -v 2`
Expected: FAIL.

**Step 3: Write minimal implementation**

```python
def _resolve_global_collisions(metrics, card_height):
    # iterate priorities and push-up while overlaps with habilidad box
    # respect anchor_mode where possible
    return metrics
```

Aplicar el resolver antes del render final de todos los elementos.

**Step 4: Run test to verify it passes**

Run: `/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.srv_textos.tests.GlobalCollisionResolverTests -v 2`
Expected: PASS.

**Step 5: Commit**

```bash
git add apps/srv_textos/views.py apps/srv_textos/tests.py
git commit -m "feat: add global collision resolver for layout boxes"
```

### Task 8: Editor visual - propiedades v2 por elemento

**Files:**
- Modify: `apps/layouts/templates/layouts/editor.html`
- Modify: `static/layouts/editor.js`
- Modify: `static/layouts/editor.css`
- Modify: `apps/layouts/tests.py`

**Step 1: Write the failing test**

```python
class LayoutEditorAdvancedControlsTests(TestCase):
    def test_editor_contains_text_rule_controls(self):
        user = get_user_model().objects.create_user(username='rules-ui', password='secret')
        self.client.force_login(user)
        response = self.client.get('/layouts/')
        self.assertContains(response, 'id="prop-align"')
        self.assertContains(response, 'id="prop-min-font-size"')
        self.assertContains(response, 'id="prop-ellipsis-enabled"')
```

**Step 2: Run test to verify it fails**

Run: `/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.layouts.tests.LayoutEditorAdvancedControlsTests -v 2`
Expected: FAIL.

**Step 3: Write minimal implementation**

```javascript
// editor.js
// map selected layer -> controls
// persist rule changes into state.config[layer].rules
// save via /layouts/api/update-config
```

Anadir controles en template para `align`, `autoshrink`, `min_font_size`, `ellipsis`, `shadow.enabled`, `anchor_mode`.

**Step 4: Run test to verify it passes**

Run: `/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.layouts.tests.LayoutEditorAdvancedControlsTests -v 2`
Expected: PASS.

**Step 5: Commit**

```bash
git add apps/layouts/templates/layouts/editor.html static/layouts/editor.js static/layouts/editor.css apps/layouts/tests.py
git commit -m "feat: add advanced box and text rule controls to layout editor"
```

### Task 9: Regresion de endpoints de render con config v2

**Files:**
- Modify: `apps/srv_textos/tests.py`
- Modify: `apps/layouts/tests.py`
- Modify: `apps/srv_textos/views.py` (solo ajustes detectados por tests)

**Step 1: Write the failing test**

```python
class BoxEngineRenderRegressionTests(TestCase):
    def test_render_texto_accepts_v2_layout_override(self):
        override = normalize_layout_config('cripta', load_classic_seed('cripta'))
        override['nombre']['rules']['align'] = 'right'
        response = self.client.post('/srv-textos/render-texto/', data=json.dumps({
            'card_type': 'cripta',
            'imagen_url': '/media/recortes/test.png',
            'layout_override': override,
            'nombre': 'Carta ejemplo',
        }), content_type='application/json')
        self.assertIn(response.status_code, (200, 404))
```

**Step 2: Run test to verify it fails**

Run: `/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.srv_textos.tests.BoxEngineRenderRegressionTests -v 2`
Expected: FAIL.

**Step 3: Write minimal implementation**

Aplicar ajustes minimos en normalizacion/render para que los endpoints acepten config v2 y fallback legacy sin errores.

**Step 4: Run test to verify it passes**

Run:
- `/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.layouts.tests -v 2`
- `/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.srv_textos.tests -v 2`

Expected: PASS en ambos.

**Step 5: Commit**

```bash
git add apps/layouts/tests.py apps/srv_textos/tests.py apps/srv_textos/views.py
git commit -m "test: add regression coverage for box engine render flow"
```

### Task 10: Verificacion final y documentacion de uso

**Files:**
- Modify: `README.md`
- Modify: `docs/plans/2026-03-11-layouts-box-engine-design.md` (si cambia alcance)

**Step 1: Write the failing test**

No aplica test nuevo; usar set de verificacion completo.

**Step 2: Run verification command set**

Run:
- `/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.layouts.tests -v 2`
- `/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.srv_textos.tests -v 2`
- `/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py check`

Expected: PASS completo, sin system check errors.

**Step 3: Write minimal implementation**

Actualizar README con reglas v2 (`box`, align, overflow, colisiones) y pasos de uso del editor.

**Step 4: Run verification again**

Run mismos comandos.
Expected: PASS estable.

**Step 5: Commit**

```bash
git add README.md docs/plans/2026-03-11-layouts-box-engine-design.md
git commit -m "docs: document layout box engine workflow and rules"
```
