# Classic Style Illustrator And Cripta Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Forzar que `ilustrador` y el numero de `cripta` usen siempre el estilo del layout `classic`, manteniendo editable solo su posicion en layouts personalizados.

**Architecture:** El renderer obtendra el estilo efectivo de `ilustrador` y `cripta` desde `apps/srv_textos/layouts.json`, separando estilo fijo de geometria editable. La medicion de `ilustrador` y el pintado final de ambas capas usaran esos tokens clasicos, mientras el `box` del layout activo seguira controlando posicion y ancho disponible.

**Tech Stack:** Django, PIL, JSON layouts, tests con `django.test`, renderer actual de `apps/srv_textos`.

---

### Task 1: Cubrir con tests el nuevo contrato de estilo classic

**Files:**
- Modify: `apps/srv_textos/tests.py`
- Modify: `apps/layouts/tests.py`

**Step 1: Write the failing test**

En `apps/srv_textos/tests.py`, anadir tests que describan el nuevo contrato:

```python
def test_ilustrador_metrics_use_classic_font_size_in_cripta(self):
    config = normalize_layout_config('cripta', load_classic_seed('cripta'))
    config['ilustrador']['font_size'] = 60
    metrics = srv_textos_views._compute_layout_metrics(
        config,
        card_type='cripta',
        habilidad='',
        ilustrador='Crafted with AI',
    )
    self.assertEqual(metrics['ilustrador']['fit']['font_size'], 24)
```

```python
def test_cripta_render_uses_classic_style_even_if_layout_overrides_it(self):
    override = normalize_layout_config('cripta', load_classic_seed('cripta'))
    override['cripta']['font_size'] = 80
    override['cripta']['color'] = 'red'
    # el test comprobara que el estilo efectivo sigue siendo el de classic
```

En `apps/layouts/tests.py`, anadir una comprobacion ligera de integracion de preview si hace falta, solo si el renderer mockeado no basta con `apps.srv_textos.tests`.

**Step 2: Run test to verify it fails**

Run: `.venv/bin/python manage.py test apps.srv_textos.tests -v 2`

Expected: FAIL porque hoy `ilustrador` y `cripta` aun usan `font_size` y color del layout activo.

**Step 3: Write minimal implementation**

Solo dejar los tests fallando de forma estable y especifica. No tocar aun el renderer.

**Step 4: Run test to verify it passes**

Run: `.venv/bin/python manage.py test apps.srv_textos.tests -v 2`

Expected: sigue FAIL, pero solo por las aserciones nuevas del contrato classic.

**Step 5: Commit**

```bash
git add apps/srv_textos/tests.py apps/layouts/tests.py
git commit -m "test: cover classic style for illustrator and cripta"
```

### Task 2: Resolver el estilo classic efectivo por tipo y capa

**Files:**
- Modify: `apps/srv_textos/views.py`
- Test: `apps/srv_textos/tests.py`

**Step 1: Write the failing test**

Reutilizar los tests en rojo de la tarea anterior para:
- `ilustrador` en `cripta`
- `ilustrador` en `libreria`
- `cripta` en cartas de `cripta`

**Step 2: Run test to verify it fails**

Run: `.venv/bin/python manage.py test apps.srv_textos.tests -v 2`

Expected: FAIL en las aserciones nuevas de estilo.

**Step 3: Write minimal implementation**

En `apps/srv_textos/views.py`, anadir un helper tipo:

```python
def _get_classic_style_tokens(card_type):
    classic = _load_layout('classic')
    if card_type == 'libreria':
        scope = classic.get('libreria', {})
        return {
            'ilustrador': scope.get('ilustrador', classic.get('ilustrador', {})),
            'cripta': classic.get('cripta', {}),
        }
    return {
        'ilustrador': classic.get('ilustrador', {}),
        'cripta': classic.get('cripta', {}),
    }
```

Usarlo en `_compute_layout_metrics(...)`:

```python
classic_tokens = _get_classic_style_tokens(normalized_card_type)
classic_il = classic_tokens['ilustrador']
il_fit = _fit_text_to_box(
    text=ilustrador,
    font_path='static/fonts/Gill Sans.otf',
    start_font_size=classic_il.get('font_size', 24),
    min_font_size=classic_il.get('font_size', 24),
    max_width=il_box['width'],
    ellipsis_enabled=True,
)
```

Guardar tambien en `metrics['ilustrador']` y `metrics['cripta']` los tokens de estilo efectivos:

```python
'style': {
    'font_size': classic_il.get('font_size', 24),
    'color': classic_il.get('color', 'white'),
}
```

Y para `cripta`:

```python
'style': {
    'font_size': classic_cripta.get('font_size', 35),
    'color': classic_cripta.get('color', 'white'),
}
```

**Step 4: Run test to verify it passes**

Run: `.venv/bin/python manage.py test apps.srv_textos.tests -v 2`

Expected: PASS en los tests nuevos de metricas/estilo.

**Step 5: Commit**

```bash
git add apps/srv_textos/views.py apps/srv_textos/tests.py
git commit -m "feat: resolve classic style tokens for illustrator and cripta"
```

### Task 3: Aplicar el estilo classic en el render final

**Files:**
- Modify: `apps/srv_textos/views.py`
- Test: `apps/srv_textos/tests.py`

**Step 1: Write the failing test**

Anadir tests de render acotados, por ejemplo con `ImageDraw.Draw.text` mockeado o inspeccionando las metricas previas, para comprobar que:
- `cripta` usa el color del `classic`
- `ilustrador` usa el color del `classic`
- el `font_size` efectivo del render coincide con el `classic`

Ejemplo:

```python
with patch('apps.srv_textos.views.ImageDraw.Draw') as mock_draw:
    srv_textos_views._render_carta(...)
    # comprobar fill y font usados
```

**Step 2: Run test to verify it fails**

Run: `.venv/bin/python manage.py test apps.srv_textos.tests -v 2`

Expected: FAIL porque `_render_carta(...)` aun usa `lil['color']`, `lcr['color']` y tamanos del layout activo.

**Step 3: Write minimal implementation**

En `_render_carta(...)`:
- para `cripta`, leer:

```python
cripta_style = (metrics.get('cripta') or {}).get('style', {})
effective_cripta_font_size = int(cripta_style.get('font_size', lcr['font_size']))
effective_cripta_color = cripta_style.get('color', lcr['color'])
```

- para `ilustrador`, leer:

```python
il_style = (metrics.get('ilustrador') or {}).get('style', {})
effective_il_color = il_style.get('color', lil['color'])
effective_il_font_size = int(il_style.get('font_size', il_font_size))
```

- usar esos valores al cargar la fuente y al pintar `draw.text(...)`

**Step 4: Run test to verify it passes**

Run: `.venv/bin/python manage.py test apps.srv_textos.tests -v 2`

Expected: PASS

**Step 5: Commit**

```bash
git add apps/srv_textos/views.py apps/srv_textos/tests.py
git commit -m "feat: render illustrator and cripta with classic style"
```

### Task 4: Verificacion completa y comprobacion de preview

**Files:**
- Modify: `docs/plans/2026-03-11-classic-style-ilustrador-cripta-design.md`
- Modify: `docs/plans/2026-03-11-classic-style-ilustrador-cripta.md`

**Step 1: Write the failing test**

No aplica test nuevo. Esta tarea es de verificacion integral.

**Step 2: Run test to verify current state**

Run: `.venv/bin/python manage.py test apps.srv_textos.tests -v 2`

Expected: PASS

Run: `.venv/bin/python manage.py test apps.layouts.tests -v 2`

Expected: PASS

**Step 3: Write minimal implementation**

No aplica codigo nuevo. Hacer comprobacion manual:
1. Abrir `/layouts/`.
2. Ver una preview de `Mimir`.
3. Confirmar que `ilustrador` se ve como en `classic`.
4. Confirmar que el numero de `cripta` se ve como en `classic`.
5. Abrir una preview de `libreria`.
6. Confirmar que `ilustrador` se ve como en `classic.libreria`.

**Step 4: Run test to verify it passes**

Registrar el resultado manual junto a la salida de los tests.

**Step 5: Commit**

```bash
git add apps/srv_textos/views.py apps/srv_textos/tests.py docs/plans/2026-03-11-classic-style-ilustrador-cripta-design.md docs/plans/2026-03-11-classic-style-ilustrador-cripta.md
git commit -m "feat: lock illustrator and cripta styling to classic"
```
