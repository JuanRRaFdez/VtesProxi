# Layout Editor Semantic Layers Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Alinear el editor de layouts con el render final mediante reglas semanticas por capa, corrigiendo `habilidad`, `disciplinas`, `cripta`, `ilustrador`, `clan`, `senda`, `coste` y la preview fija de `Mimir`.

**Architecture:** El backend separará caja de layout y caja usada para el texto de `habilidad`, derivará `disciplinas` desde esa caja usada y normalizará capas cuadradas o de fuente fija antes de renderizar. El frontend dejará los overlays invisibles por defecto y aplicará perfiles por capa para hit areas, resize cuadrado, handles selectivos y selección por clic sobre zonas no visibles.

**Tech Stack:** Django, PIL, JSON layout config, tests con `django.test`, JavaScript vanilla, Interact.js, CSS.

---

### Task 1: Cubrir el nuevo contrato semantico del render

**Files:**
- Modify: `apps/srv_textos/tests.py`
- Modify: `apps/layouts/tests.py`

**Step 1: Write the failing test**

En `apps/srv_textos/tests.py`, añadir tests nuevos para `_compute_layout_metrics(...)`:

```python
def test_habilidad_box_does_not_grow_beyond_explicit_layout_box(self):
    config = normalize_layout_config('cripta', load_classic_seed('cripta'))
    config['habilidad']['box'] = {'x': 140, 'y': 760, 'width': 420, 'height': 120}
    config['habilidad']['font_size'] = 33
    metrics = _compute_layout_metrics(
        config,
        card_type='cripta',
        habilidad='Texto muy largo\\n' * 8,
        disciplinas=['ani', 'for', 'pot'],
    )
    self.assertEqual(metrics['habilidad']['box']['height'], 120)
    self.assertLessEqual(metrics['habilidad']['used_box']['height'], 120)
```

```python
def test_disciplinas_vertical_anchor_is_derived_from_habilidad_used_box(self):
    config = normalize_layout_config('cripta', load_classic_seed('cripta'))
    config['habilidad']['box'] = {'x': 140, 'y': 780, 'width': 420, 'height': 140}
    config['disciplinas']['box'] = {'x': 30, 'y': 10, 'width': 64, 'height': 180}
    metrics = _compute_layout_metrics(
        config,
        card_type='cripta',
        habilidad='Texto corto',
        disciplinas=['ani', 'for', 'pot'],
    )
    self.assertEqual(
        metrics['disciplinas']['box']['y'] + metrics['disciplinas']['box']['height'],
        metrics['habilidad']['used_box']['y'],
    )
```

Añadir tests para:
- `disciplinas.size` derivado de `box.width`
- `disciplinas.spacing` derivado de `box.height`
- `cripta` e `ilustrador` mantienen `font_size` fijo aunque cambie el frame

En `apps/layouts/tests.py`, añadir:

```python
def test_preview_for_cripta_forces_caine_path(self):
    self.client.force_login(self.user)
    with patch('apps.layouts.views.get_card_autocomplete', return_value={'nombre': 'Mimir', 'senda': ''}), \
         patch('apps.layouts.views._render_carta_from_path', return_value=('/media/render/mimir.png', None)) as mock_render:
        response = self.client.post(
            '/layouts/api/preview',
            data=json.dumps({'card_type': 'cripta', 'layout_config': load_classic_seed('cripta')}),
            content_type='application/json',
        )
    self.assertEqual(response.status_code, 200)
    self.assertEqual(mock_render.call_args.kwargs['senda'], 'caine.png')
```

**Step 2: Run test to verify it fails**

Run: `.venv/bin/python manage.py test apps.srv_textos.tests apps.layouts.tests -v 2`

Expected: FAIL porque las metricas actuales inflan `habilidad`, `disciplinas` no se deriva de `habilidad`, y la preview de `Mimir` no fuerza `caine.png`.

**Step 3: Write minimal implementation**

Todavia no implementar toda la UI. Solo preparar el contrato esperado en tests para el backend:
- importar `normalize_layout_config` y `_compute_layout_metrics` en `apps/srv_textos/tests.py`
- reutilizar fixtures o seeds existentes
- añadir helper local si hace falta para generar texto largo

**Step 4: Run test to verify it passes**

Run: `.venv/bin/python manage.py test apps.srv_textos.tests apps.layouts.tests -v 2`

Expected: sigue FAIL, pero ahora con fallos relevantes y estables que describen el contrato objetivo.

**Step 5: Commit**

```bash
git add apps/srv_textos/tests.py apps/layouts/tests.py
git commit -m "test: cover semantic layout layer rules"
```

### Task 2: Corregir metricas del render y la preview fija

**Files:**
- Modify: `apps/srv_textos/views.py`
- Modify: `apps/layouts/views.py`
- Test: `apps/srv_textos/tests.py`
- Test: `apps/layouts/tests.py`

**Step 1: Write the failing test**

Reutilizar los tests fallando de la tarea anterior como red bar para:
- `habilidad.used_box`
- anclaje vertical de `disciplinas`
- preview fija de `Mimir` con `caine.png`

**Step 2: Run test to verify it fails**

Run: `.venv/bin/python manage.py test apps.srv_textos.tests apps.layouts.tests -v 2`

Expected: FAIL en los casos nuevos.

**Step 3: Write minimal implementation**

En `apps/srv_textos/views.py`:
- cambiar `_compute_habilidad_dynamic_height(...)` para que devuelva altura usada estimada, no altura de caja persistida.
- en `_compute_layout_metrics(...)`:
  - conservar `habilidad.box` como `layout_box` limitado por el usuario.
  - añadir `habilidad.used_box`:

```python
used_hab_height = min(habilidad_box['height'], dynamic_hab_box_h)
used_hab_box = {
    'x': habilidad_box['x'],
    'y': habilidad_box['y'] + max(0, habilidad_box['height'] - used_hab_height),
    'width': habilidad_box['width'],
    'height': used_hab_height,
}
```

  - recalcular `disciplinas.box` con:

```python
disc_box = _clamp_box(...)
disc_box['y'] = max(0, used_hab_box['y'] - disc_box['height'])
disc_size = max(1, int(disc_box['width']))
disc_spacing = max(1, int(disc_box['height'] / max(1, len(disciplinas or []))))
```

  - usar `used_hab_box` como referencia de `cripta` y para colisiones asociadas
- en `_render_carta(...)`, usar `metrics['habilidad']['used_box']` para render de `habilidad`, `cripta` y dependencias relacionadas

En `apps/layouts/views.py`:
- extender `FIXED_LAYOUT_PREVIEWS['cripta']`:

```python
'path': 'caine.png',
```

- al montar el payload de preview:

```python
senda=preview.get('path', preview_payload.get('senda', '')),
```

**Step 4: Run test to verify it passes**

Run: `.venv/bin/python manage.py test apps.srv_textos.tests apps.layouts.tests -v 2`

Expected: PASS en los tests nuevos de backend.

**Step 5: Commit**

```bash
git add apps/srv_textos/views.py apps/layouts/views.py apps/srv_textos/tests.py apps/layouts/tests.py
git commit -m "feat: align render metrics with semantic layer rules"
```

### Task 3: Normalizar capas cuadradas y de fuente fija en editor y validacion

**Files:**
- Modify: `apps/layouts/services.py`
- Modify: `static/layouts/editor.js`
- Test: `apps/layouts/tests.py`

**Step 1: Write the failing test**

En `apps/layouts/tests.py`, añadir un test de API para `update-config`:

```python
def test_update_config_normalizes_square_symbol_layers(self):
    config = normalize_layout_config('cripta', load_classic_seed('cripta'))
    config['clan']['box'] = {'x': 20, 'y': 30, 'width': 80, 'height': 120}
    self.client.force_login(self.user)
    response = self.client.post(
        '/layouts/api/update-config',
        data=json.dumps({'layout_id': self.layout.id, 'config': config}),
        content_type='application/json',
    )
    self.assertEqual(response.status_code, 200)
    saved = response.json()['layout']['config']
    self.assertEqual(saved['clan']['box']['width'], saved['clan']['box']['height'])
```

Añadir otro para `senda` y `coste`.

**Step 2: Run test to verify it fails**

Run: `.venv/bin/python manage.py test apps.layouts.tests.LayoutConfigValidationTests -v 2`

Expected: FAIL porque la normalizacion actual no corrige cajas cuadradas.

**Step 3: Write minimal implementation**

En `apps/layouts/services.py`:
- añadir helper:

```python
def _normalize_square_box(section):
    box = section.get('box')
    if not isinstance(box, dict):
        return
    side = max(1, int(max(box.get('width', 1), box.get('height', 1))))
    box['width'] = side
    box['height'] = side
```

- aplicarlo a `clan`, `senda` y `coste` dentro de `normalize_layout_config(...)`

En `static/layouts/editor.js`:
- declarar un mapa por capa:

```javascript
const layerProfiles = {
  clan: { square: true, invisible: true },
  senda: { square: true, invisible: true },
  coste: { square: true, invisible: true },
  cripta: { fixedFont: true, resize: false, invisible: true },
  ilustrador: { fixedFont: true, resize: false, invisible: true },
  disciplinas: { invisible: true, derivedY: 'habilidad' },
};
```

- en `applyFrameToSection(...)`:
  - para capas cuadradas, forzar `frame.width === frame.height`
  - para `cripta` e `ilustrador`, no recalcular `font_size`

**Step 4: Run test to verify it passes**

Run: `.venv/bin/python manage.py test apps.layouts.tests.LayoutConfigValidationTests -v 2`

Expected: PASS

**Step 5: Commit**

```bash
git add apps/layouts/services.py static/layouts/editor.js apps/layouts/tests.py
git commit -m "feat: normalize square and fixed-font layout layers"
```

### Task 4: Hacer invisibles los overlays y dejar seleccion semantica por clic

**Files:**
- Modify: `static/layouts/editor.js`
- Modify: `static/layouts/editor.css`
- Modify: `apps/layouts/templates/layouts/editor.html`
- Test: `apps/layouts/tests.py`

**Step 1: Write the failing test**

En `apps/layouts/tests.py`, ampliar el test del editor:

```python
def test_editor_template_uses_overlay_mount_without_visible_labels(self):
    self.client.force_login(self.user)
    response = self.client.get('/layouts/')
    self.assertContains(response, 'id="layout-overlays"')
    self.assertNotContains(response, 'layout-layer-label')
```

Y añadir una comprobacion del JS entregado:

```python
def test_editor_script_contains_semantic_layer_profiles(self):
    response = self.client.get('/layouts/')
    self.assertContains(response, 'layerProfiles')
```

**Step 2: Run test to verify it fails**

Run: `.venv/bin/python manage.py test apps.layouts.tests -v 2`

Expected: FAIL porque el JS y el template actuales siguen creando labels visibles y no exponen perfiles semanticos.

**Step 3: Write minimal implementation**

En `static/layouts/editor.js`:
- dejar de crear:

```javascript
const label = document.createElement('span');
label.className = 'layout-layer-label';
label.textContent = layerName;
layer.appendChild(label);
```

- usar `layerProfiles` para:
  - ocultar borde/label
  - decidir si la capa es resizable
  - decidir si debe verse una silueta auxiliar solo cuando esta seleccionada
- permitir clic sobre hit area aunque la capa no tenga borde visible
- para `disciplinas`, recalcular su frame visual desde `habilidad` antes de pintar

En `static/layouts/editor.css`:
- hacer overlays transparentes por defecto
- mostrar solo handles y estado `active`
- mantener `pointer-events` en la hit area

Ejemplo:

```css
.layout-layer {
    position: absolute;
    background: transparent;
    border: 0;
}

.layout-layer.active {
    outline: 1px dashed rgba(255, 255, 255, 0.65);
}
```

**Step 4: Run test to verify it passes**

Run: `.venv/bin/python manage.py test apps.layouts.tests -v 2`

Expected: PASS

**Step 5: Commit**

```bash
git add static/layouts/editor.js static/layouts/editor.css apps/layouts/templates/layouts/editor.html apps/layouts/tests.py
git commit -m "feat: add invisible semantic overlays to layout editor"
```

### Task 5: Verificacion final y comprobacion manual del flujo real

**Files:**
- Modify: `docs/plans/2026-03-11-layout-editor-semantic-layers-design.md`
- Modify: `docs/plans/2026-03-11-layout-editor-semantic-layers.md`

**Step 1: Write the failing test**

No aplica test nuevo. Esta tarea es de verificacion integral y cierre.

**Step 2: Run test to verify current state**

Run: `.venv/bin/python manage.py test apps.layouts.tests -v 2`

Expected: PASS

Run: `.venv/bin/python manage.py test apps.srv_textos.tests -v 2`

Expected: PASS

**Step 3: Write minimal implementation**

No aplica codigo nuevo. Realizar comprobacion manual:
1. Abrir `/layouts/`.
2. Confirmar que `Mimir` muestra la senda `caine.png`.
3. Seleccionar `ilustrador`, `cripta`, `clan`, `senda`, `coste` y `disciplinas` haciendo clic sobre su zona invisible.
4. Redimensionar `clan`, `senda` y `coste` y comprobar que siguen cuadrados.
5. Mover o cambiar alto de `habilidad` y comprobar que `disciplinas` se recoloca justo encima.
6. Crear una carta nueva usando el layout editado y confirmar que el render final coincide.

**Step 4: Run test to verify it passes**

Registrar los comandos ejecutados y el resultado manual observado en la nota de trabajo o en el comentario de entrega.

**Step 5: Commit**

```bash
git add apps/layouts/tests.py apps/srv_textos/tests.py apps/layouts/views.py apps/layouts/services.py apps/srv_textos/views.py static/layouts/editor.js static/layouts/editor.css docs/plans/2026-03-11-layout-editor-semantic-layers-design.md docs/plans/2026-03-11-layout-editor-semantic-layers.md
git commit -m "feat: align layout editor with semantic layer behavior"
```
