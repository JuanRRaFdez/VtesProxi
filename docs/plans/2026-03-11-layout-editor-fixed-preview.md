# Fixed Layout Editor Preview Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Añadir una preview fija y real por tipo de carta en el editor de layouts, usando `Mimir` para `cripta` y `.44 Magnum` para `libreria`, con la carta completa visible en el panel y overlays editables encima.

**Architecture:** El backend de `apps.layouts` expondrá un endpoint de preview que resuelve una carta fija por tipo, obtiene sus datos del catálogo y llama al motor de render con el `layout_config` activo. El frontend sustituirá el fondo neutro por una preview real y usará un canvas escalado con conversiones entre coordenadas visibles y coordenadas del modelo para que la carta entera quepa en pantalla sin romper drag/resize.

**Tech Stack:** Django, PIL, JSON endpoints, catálogo de cartas existente, JavaScript vanilla, Interact.js, CSS.

---

### Task 1: Añadir contrato backend para preview fija del editor

**Files:**
- Modify: `apps/layouts/tests.py`
- Modify: `apps/layouts/views.py`
- Modify: `apps/layouts/urls.py`
- Modify: `apps/srv_textos/views.py`

**Step 1: Write the failing test**

Añadir una clase nueva en `apps/layouts/tests.py`:

```python
class LayoutPreviewApiTests(TestCase):
    def test_preview_for_cripta_uses_fixed_mimir_payload(self):
        user = get_user_model().objects.create_user(username='preview-user', password='secret')
        self.client.force_login(user)
        layout = UserLayout.objects.create(
            user=user,
            name='Preview',
            card_type='cripta',
            config=load_classic_seed('cripta'),
            is_default=False,
        )

        with patch('apps.layouts.views.get_card_autocomplete', return_value={'nombre': 'Mimir'}), \
             patch('apps.layouts.views._render_carta_from_path', return_value=('/media/render/mimir.png', None)) as mock_render:
            response = self.client.post(
                '/layouts/api/preview',
                data=json.dumps({'card_type': 'cripta', 'layout_config': layout.config}),
                content_type='application/json',
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['imagen_url'], '/media/render/mimir.png')
        self.assertEqual(mock_render.call_args.kwargs['nombre'], 'Mimir')
        self.assertEqual(mock_render.call_args.kwargs['ilustrador'], 'Crafted with AI')
```

Añadir otro test gemelo para `libreria` comprobando:
- nombre `.44 Magnum`
- `card_type='libreria'`
- ruta de imagen fija de librería

**Step 2: Run test to verify it fails**

Run: `.venv/bin/python manage.py test apps.layouts.tests.LayoutPreviewApiTests -v 2`

Expected: FAIL porque `/layouts/api/preview` no existe y `apps.layouts.views` aún no expone helpers de preview.

**Step 3: Write minimal implementation**

En `apps/layouts/views.py`:
- importar `get_card_autocomplete` desde `apps.srv_textos.card_catalog`
- importar `_render_carta_from_path` desde `apps.srv_textos.views`
- definir una tabla fija de preview:

```python
FIXED_LAYOUT_PREVIEWS = {
    'cripta': {
        'card_name': 'Mimir',
        'image_path': 'static/layouts/images/Mimir.png',
        'illustrator': 'Crafted with AI',
    },
    'libreria': {
        'card_name': '.44 Magnum',
        'image_path': 'static/layouts/images/44. magnum.png',
        'illustrator': 'Crafted with AI',
    },
}
```

- añadir helper que:
  - valide `card_type`
  - resuelva datos con `get_card_autocomplete(card_type, card_name)`
  - fuerce `ilustrador`
  - llame a `_render_carta_from_path(...)`

En `apps/layouts/urls.py`:

```python
path('api/preview', views.api_preview, name='api_preview'),
```

En `apps/srv_textos/views.py`:
- extraer el cuerpo de `_render_carta` a un helper reutilizable:

```python
def _render_carta_from_path(imagen_abspath, **kwargs):
    ...

def _render_carta(imagen_url, **kwargs):
    imagen_abspath = _resolve_imagen_path(imagen_url)
    return _render_carta_from_path(imagen_abspath, **kwargs)
```

**Step 4: Run test to verify it passes**

Run: `.venv/bin/python manage.py test apps.layouts.tests.LayoutPreviewApiTests -v 2`

Expected: PASS

**Step 5: Commit**

```bash
git add apps/layouts/tests.py apps/layouts/views.py apps/layouts/urls.py apps/srv_textos/views.py
git commit -m "feat: add fixed layout preview api"
```

### Task 2: Cubrir template y contrato visual mínimo del editor

**Files:**
- Modify: `apps/layouts/templates/layouts/editor.html`
- Modify: `apps/layouts/tests.py`
- Modify: `static/layouts/editor.css`

**Step 1: Write the failing test**

Extender `LayoutEditorTemplateTests` en `apps/layouts/tests.py`:

```python
def test_editor_template_contains_preview_mount_points(self):
    user = get_user_model().objects.create_user(username='editor-preview', password='secret')
    self.client.force_login(user)

    response = self.client.get('/layouts/')

    self.assertContains(response, 'id="layout-stage-viewport"')
    self.assertContains(response, 'id="layout-canvas"')
    self.assertContains(response, 'id="layout-preview-image"')
```

**Step 2: Run test to verify it fails**

Run: `.venv/bin/python manage.py test apps.layouts.tests.LayoutEditorTemplateTests -v 2`

Expected: FAIL porque esos nodos aún no existen.

**Step 3: Write minimal implementation**

Actualizar `apps/layouts/templates/layouts/editor.html` para que el panel izquierdo quede así:

```html
<div id="layout-stage-viewport" class="layout-stage-viewport">
  <div id="layout-canvas" class="layout-canvas">
    <img id="layout-preview-image" class="layout-preview-image" alt="Preview de carta">
    <div id="layout-stage" class="layout-stage">
      <div id="layout-overlays" class="layout-overlays"></div>
    </div>
  </div>
</div>
```

Actualizar `static/layouts/editor.css`:
- crear `layout-stage-viewport` con alto útil basado en viewport
- posicionar `layout-canvas` relativo
- hacer que `layout-preview-image` ocupe el canvas completo
- mantener overlays encima con `position:absolute`

Base sugerida:

```css
.layout-stage-viewport {
    min-height: 560px;
    max-height: calc(100vh - 240px);
    overflow: hidden;
    display: flex;
    align-items: center;
    justify-content: center;
}

.layout-canvas {
    position: relative;
    transform-origin: top left;
}

.layout-preview-image,
.layout-stage,
.layout-overlays {
    position: absolute;
    inset: 0;
}
```

**Step 4: Run test to verify it passes**

Run: `.venv/bin/python manage.py test apps.layouts.tests.LayoutEditorTemplateTests -v 2`

Expected: PASS

**Step 5: Commit**

```bash
git add apps/layouts/templates/layouts/editor.html apps/layouts/tests.py static/layouts/editor.css
git commit -m "feat: add layout preview canvas mounts"
```

### Task 3: Implementar preview real en frontend y escalado del canvas

**Files:**
- Modify: `static/layouts/editor.js`
- Modify: `static/layouts/editor.css`

**Step 1: Write the failing test**

No hay framework JS en el repo. En lugar de test unitario JS, escribir primero una comprobación de integración del endpoint/template y dejar verificación manual explícita en el plan de ejecución:
- el editor carga una imagen dentro de `#layout-preview-image`
- la carta completa se ve dentro del viewport
- al mover una caja, la preview se actualiza

Documentar esta limitación en comentarios del plan y no inventar una suite JS inexistente.

**Step 2: Run current backend/template tests to establish baseline**

Run: `.venv/bin/python manage.py test apps.layouts.tests.LayoutPreviewApiTests apps.layouts.tests.LayoutEditorTemplateTests -v 2`

Expected: PASS antes de tocar JS.

**Step 3: Write minimal implementation**

En `static/layouts/editor.js`:
- añadir referencias a:
  - `layout-stage-viewport`
  - `layout-canvas`
  - `layout-preview-image`
- mantener el layout en coordenadas nativas y calcular una escala visual:

```javascript
function computeStageScale(cardWidth, cardHeight) {
    const viewportRect = stageViewport.getBoundingClientRect();
    const scaleX = viewportRect.width / cardWidth;
    const scaleY = viewportRect.height / cardHeight;
    return Math.min(scaleX, scaleY, 1);
}
```

- crear helpers:

```javascript
function modelToDisplay(frame) {
    return {
        x: Math.round(frame.x * state.scale),
        y: Math.round(frame.y * state.scale),
        width: Math.round(frame.width * state.scale),
        height: Math.round(frame.height * state.scale),
    };
}

function displayToModel(frame) {
    return {
        x: frame.x / state.scale,
        y: frame.y / state.scale,
        width: frame.width / state.scale,
        height: frame.height / state.scale,
    };
}
```

- actualizar `renderLayers()` para:
  - fijar tamano nativo del canvas
  - calcular `state.scale`
  - dibujar overlays en coordenadas visibles
- actualizar `syncLayerFromElement()` y `applySelectedProperties()` para convertir de display a modelo
- implementar `requestPreview()`:

```javascript
async function requestPreview() {
    const response = await fetch('/layouts/api/preview', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken,
        },
        body: JSON.stringify({
            card_type: state.cardType,
            layout_config: state.config,
        }),
    });
    const payload = await response.json();
    if (!response.ok) {
        throw new Error(payload.error || 'No se pudo generar preview');
    }
    previewImage.src = payload.imagen_url;
}
```

- disparar preview al:
  - cargar editor
  - cambiar tipo
  - cambiar layout
  - aplicar propiedades
  - terminar drag
  - terminar resize

**Step 4: Run verification for regressions**

Run: `.venv/bin/python manage.py test apps.layouts.tests -v 2`

Expected: PASS

**Step 5: Commit**

```bash
git add static/layouts/editor.js static/layouts/editor.css
git commit -m "feat: render fixed card preview in layout editor"
```

### Task 4: Verificar renderer reutilizable y flujo completo de preview

**Files:**
- Modify: `apps/srv_textos/tests.py`
- Modify: `apps/layouts/tests.py`
- Modify: `apps/srv_textos/views.py` (solo si los tests piden ajuste)

**Step 1: Write the failing test**

Añadir en `apps/srv_textos/tests.py` una prueba puntual del helper extraido:

```python
class RenderFromPathTests(TestCase):
    def test_render_carta_from_absolute_path_returns_render_url(self):
        image_path = Path(settings.BASE_DIR) / 'static' / 'layouts' / 'images' / 'Mimir.png'
        render_url, error = srv_textos_views._render_carta_from_path(
            str(image_path),
            nombre='Mimir',
            clan='',
            senda='',
            disciplinas=[],
            simbolos=[],
            habilidad='',
            coste='',
            cripta='',
            ilustrador='Crafted with AI',
            card_type='cripta',
            layout_config=load_classic_seed('cripta'),
        )

        self.assertIsNone(error)
        self.assertTrue(render_url.startswith('/media/render/'))
```

Si el test resulta demasiado caro o dependiente del entorno, sustituirlo por una prueba con `patch('PIL.Image.open')` que confirme que el helper usa la ruta absoluta esperada. No inventar IO innecesario si hay fragilidad.

**Step 2: Run test to verify it fails**

Run: `.venv/bin/python manage.py test apps.srv_textos.tests.RenderFromPathTests -v 2`

Expected: FAIL porque `_render_carta_from_path` aún no existe o no está accesible con el contrato correcto.

**Step 3: Write minimal implementation**

Ajustar la extracción del helper en `apps/srv_textos/views.py` para que:
- valide la existencia de `imagen_abspath`
- mantenga el mismo contrato de salida `(render_url, error)`
- no cambie el comportamiento actual de `_render_carta`

**Step 4: Run focused tests and then full suites**

Run:
- `.venv/bin/python manage.py test apps.srv_textos.tests.RenderFromPathTests -v 2`
- `.venv/bin/python manage.py test apps.layouts.tests -v 2`
- `.venv/bin/python manage.py test apps.srv_textos.tests -v 2`

Expected: PASS en las tres ejecuciones.

**Step 5: Commit**

```bash
git add apps/srv_textos/tests.py apps/layouts/tests.py apps/srv_textos/views.py
git commit -m "test: cover fixed preview render path"
```

### Task 5: Verificacion manual del comportamiento visual

**Files:**
- No code changes required unless defects are found.

**Step 1: Run the application**

Run:

```bash
.venv/bin/python manage.py runserver
```

**Step 2: Verify `cripta` preview**

Comprobar en `/layouts/?card_type=cripta`:
- se ve `Mimir`
- la carta completa cabe en el panel
- el ilustrador visible es `Crafted with AI`
- mover `nombre`, `habilidad`, `disciplinas`, `cripta` e `ilustrador` actualiza la preview

**Step 3: Verify `libreria` preview**

Comprobar en `/layouts/?card_type=libreria`:
- se ve `.44 Magnum`
- la carta completa cabe en el panel
- el ilustrador visible es `Crafted with AI`
- mover cajas actualiza la preview sin descuadrarse

**Step 4: If manual verification reveals mismatch, fix minimally and rerun full tests**

Run:

```bash
.venv/bin/python manage.py test apps.layouts.tests -v 2
.venv/bin/python manage.py test apps.srv_textos.tests -v 2
```

**Step 5: Commit**

```bash
git add apps/layouts apps/srv_textos static/layouts
git commit -m "feat: add fixed real preview to layout editor"
```
