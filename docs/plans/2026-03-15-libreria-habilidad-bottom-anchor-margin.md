# Libreria Habilidad Bottom Anchor Margin Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Hacer que `habilidad.box` en `libreria` use semantica de ancla inferior + ancho + margen vertical simetrico, con recuadro responsivo que crece hacia arriba y texto centrado.

**Architecture:** El cambio se activa solo en `libreria` mediante un flag explicito en `habilidad.rules`. El backend recalcula `used_box` desde el borde inferior y el editor deja de persistir el alto visual del cuadro como si fuera el dato real, pasando a guardar el margen vertical interno. Se mantienen intactos `cripta` y los layouts legacy de `libreria` que no lleven el flag.

**Tech Stack:** Django, Python, Pillow, JavaScript vanilla, unittest de Django.

---

### Task 1: Añadir la cobertura de normalizacion y validacion del nuevo flag

**Files:**
- Modify: `apps/layouts/tests.py`
- Modify: `apps/layouts/services.py`

**Step 1: Write the failing tests**

Añadir tests que cubran:

```python
def test_normalize_libreria_habilidad_bottom_anchor_margin_flag(self):
    config = copy.deepcopy(BASE_LIBRERIA_LAYOUT)
    config["habilidad"]["rules"] = {"box_semantics": "bottom_anchor_margin"}
    normalized = normalize_layout_config("libreria", config)
    assert normalized["habilidad"]["rules"]["box_semantics"] == "bottom_anchor_margin"

def test_validate_rejects_invalid_libreria_habilidad_box_semantics(self):
    config = copy.deepcopy(BASE_LIBRERIA_LAYOUT)
    config["habilidad"]["rules"] = {"box_semantics": "nope"}
    with self.assertRaises(LayoutValidationError):
        validate_layout_config("libreria", config)
```

**Step 2: Run test to verify it fails**

Run: `/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.layouts.tests.LayoutConfigValidationTests -v 2`

Expected: FAIL because the new flag is not normalized or validated yet.

**Step 3: Write minimal implementation**

En `apps/layouts/services.py`:

- asegurar `habilidad.rules` como `dict`
- hacer `rules.setdefault("box_semantics", "legacy")` solo para `libreria`
- validar que el valor sea `legacy` o `bottom_anchor_margin`

Snippet orientativo:

```python
hab_rules = habilidad.get("rules")
if not isinstance(hab_rules, dict):
    hab_rules = {}
    habilidad["rules"] = hab_rules

if card_type == "libreria":
    hab_rules.setdefault("box_semantics", "legacy")
    if hab_rules["box_semantics"] not in {"legacy", "bottom_anchor_margin"}:
        raise LayoutValidationError("habilidad.rules.box_semantics invalido")
```

**Step 4: Run test to verify it passes**

Run: `/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.layouts.tests.LayoutConfigValidationTests -v 2`

Expected: PASS for the new normalization and validation tests.

**Step 5: Commit**

```bash
git add apps/layouts/tests.py apps/layouts/services.py
git commit -m "test: cover libreria habilidad box semantics flag"
```

### Task 2: Fijar por test la nueva metrica de habilidad en libreria

**Files:**
- Modify: `apps/srv_textos/tests.py`
- Modify: `apps/srv_textos/views.py`

**Step 1: Write the failing tests**

Añadir tests que cubran:

```python
def test_libreria_habilidad_bottom_anchor_margin_grows_up_from_bottom(self):
    config = build_libreria_layout()
    config["habilidad"]["rules"] = {"box_semantics": "bottom_anchor_margin"}
    config["habilidad"]["box"] = {"x": 160, "y": 820, "width": 420, "height": 24}

    metrics = _compute_layout_metrics(
        config,
        card_type="libreria",
        habilidad="Texto de prueba " * 20,
    )

    assert metrics["habilidad"]["used_box"]["y"] < 820
    assert metrics["habilidad"]["used_box"]["y"] + metrics["habilidad"]["used_box"]["height"] == 820

def test_libreria_habilidad_bottom_anchor_margin_uses_symmetric_vertical_margin(self):
    ...

def test_libreria_habilidad_without_flag_keeps_legacy_box_semantics(self):
    ...
```

**Step 2: Run test to verify it fails**

Run: `/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.srv_textos.tests.HabilidadDynamicHeightTests -v 2`

Expected: FAIL because `libreria` still uses top-left box semantics.

**Step 3: Write minimal implementation**

En `apps/srv_textos/views.py`:

- detectar `habilidad.rules.box_semantics == "bottom_anchor_margin"` cuando `card_type == "libreria"`
- calcular `dynamic_hab_box_h` con el renderer actual
- reinterpretar `habilidad_box["y"]` como borde inferior
- construir `used_hab_box` con crecimiento hacia arriba
- clamplear al borde superior si hace falta
- mantener la ruta legacy cuando el flag no exista

Snippet orientativo:

```python
is_libreria_bottom_anchor_margin = (
    normalized_card_type == "libreria"
    and isinstance(lh.get("rules"), dict)
    and lh["rules"].get("box_semantics") == "bottom_anchor_margin"
    and has_habilidad_box
)

if is_libreria_bottom_anchor_margin:
    vertical_margin = max(0, int(habilidad_box["height"]))
    outer_height = max(1, dynamic_text_height + (vertical_margin * 2))
    bottom = int(habilidad_box["y"])
    used_hab_box_y = max(0, bottom - outer_height)
    used_hab_box_h = max(1, bottom - used_hab_box_y)
```

**Step 4: Run test to verify it passes**

Run: `/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.srv_textos.tests.HabilidadDynamicHeightTests -v 2`

Expected: PASS for the new libreria metrics tests.

**Step 5: Commit**

```bash
git add apps/srv_textos/tests.py apps/srv_textos/views.py
git commit -m "feat: add libreria bottom-anchor habilidad metrics"
```

### Task 3: Fijar por test el render visual de libreria con el nuevo modo

**Files:**
- Modify: `apps/srv_textos/tests.py`
- Modify: `apps/srv_textos/views.py`

**Step 1: Write the failing tests**

Añadir tests que verifiquen:

```python
def test_render_habilidad_libreria_bottom_anchor_margin_keeps_bottom_edge(self):
    ...

def test_render_habilidad_libreria_bottom_anchor_margin_grows_with_font_size(self):
    ...

def test_render_habilidad_libreria_bottom_anchor_margin_centers_text_in_used_box(self):
    ...
```

Los tests deben inspeccionar el `draw.rounded_rectangle()` y el `draw.text()` o sus mocks para comprobar:

- borde inferior fijo
- crecimiento hacia arriba
- centrado vertical dentro del `used_box`

**Step 2: Run test to verify it fails**

Run: `/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.srv_textos.tests.HabilidadRenderAlignmentTests -v 2`

Expected: FAIL because the libreria render path still assumes top-left box semantics.

**Step 3: Write minimal implementation**

Reusar `_render_habilidad_text()` sin bifurcar el renderer:

- pasar `hab_y` y `hab_box_h` ya reinterpretados desde metrics
- mantener intacto el centrado vertical del helper comun
- no tocar `cripta`

**Step 4: Run test to verify it passes**

Run: `/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.srv_textos.tests.HabilidadRenderAlignmentTests -v 2`

Expected: PASS.

**Step 5: Commit**

```bash
git add apps/srv_textos/tests.py apps/srv_textos/views.py
git commit -m "feat: render libreria habilidad from bottom anchor"
```

### Task 4: Adaptar el editor de layouts de libreria a la nueva semantica

**Files:**
- Modify: `static/layouts/editor.js`
- Modify: `apps/layouts/tests.py`

**Step 1: Write the failing tests**

Añadir cobertura que fije:

```python
def test_editor_script_contains_libreria_habilidad_bottom_anchor_margin_flow(self):
    response = self.client.get(reverse("layouts:editor"))
    script = response.content.decode()
    assert "box_semantics" in script
    assert "bottom_anchor_margin" in script
```

Si ya existe un bloque de assertions sobre el script, extenderlo ahi.

**Step 2: Run test to verify it fails**

Run: `/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.layouts.tests.LayoutEditorViewTests -v 2`

Expected: FAIL because the editor still persists `habilidad` as a top-left visual rectangle.

**Step 3: Write minimal implementation**

En `static/layouts/editor.js`:

- en `frameFromSection()`, cuando sea `libreria` y `habilidad.rules.box_semantics == "bottom_anchor_margin"`, construir el helper usando:
  - `x = box.x`
  - `bottom = box.y`
  - `width = box.width`
  - `height = projected_text_height + margin * 2`
  - `y = bottom - height`
- en `applyFrameToSection()`, persistir:
  - `box.x = frame.x`
  - `box.y = frame.y + frame.height`
  - `box.width = frame.width`
  - `box.height = inferred_margin`
- no tocar el flujo actual de `cripta` ni el flujo legacy de `libreria`

Snippet orientativo:

```javascript
const isLibreriaBottomAnchorMargin =
    state.cardType === 'libreria' &&
    layerName === 'habilidad' &&
    section.rules &&
    section.rules.box_semantics === 'bottom_anchor_margin';
```

**Step 4: Run test to verify it passes**

Run: `/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.layouts.tests.LayoutEditorViewTests -v 2`

Expected: PASS.

**Step 5: Commit**

```bash
git add static/layouts/editor.js apps/layouts/tests.py
git commit -m "feat: teach layout editor libreria habilidad bottom-anchor margin"
```

### Task 5: Verificacion final y limpieza

**Files:**
- Modify: `apps/layouts/services.py`
- Modify: `apps/srv_textos/views.py`
- Modify: `static/layouts/editor.js`
- Modify: `apps/layouts/tests.py`
- Modify: `apps/srv_textos/tests.py`

**Step 1: Run focused test suites**

Run:

```bash
/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.layouts.tests apps.srv_textos.tests -v 1
```

Expected: PASS.

**Step 2: Run project checks**

Run:

```bash
/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py check
node --check static/layouts/editor.js
```

Expected: ambos OK.

**Step 3: Review diff**

Run:

```bash
git status --short
git diff -- apps/layouts/services.py apps/srv_textos/views.py static/layouts/editor.js apps/layouts/tests.py apps/srv_textos/tests.py
```

Expected: solo cambios del feature.

**Step 4: Commit**

```bash
git add apps/layouts/services.py apps/srv_textos/views.py static/layouts/editor.js apps/layouts/tests.py apps/srv_textos/tests.py
git commit -m "feat: add libreria habilidad bottom-anchor margin layout semantics"
```
