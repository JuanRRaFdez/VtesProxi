# Libreria Habilidad Responsive All Layouts Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Hacer que el cuadro de `habilidad` en todas las cartas de `libreria`, incluidos los layouts legacy, sea realmente responsivo al texto y al `hab_font_size`, manteniendo fijo el borde inferior y creciendo solo hacia arriba.

**Architecture:** El cambio vive principalmente en el calculo de metricas de `apps/srv_textos/views.py`. Los layouts nuevos seguiran usando `bottom_anchor_margin`; los layouts legacy de libreria se migraran en runtime conservando su borde inferior visual heredado (`box.y + box.height`) pero abandonando la altura fija antigua. El editor de layouts se alineara con esa semantica para que la preview y el render real sigan el mismo modelo.

**Tech Stack:** Django, Python, Pillow, JavaScript vanilla, unittest de Django.

---

### Task 1: Fijar por test el comportamiento responsivo de layouts legacy de libreria

**Files:**
- Modify: `apps/srv_textos/tests.py`
- Modify: `apps/srv_textos/views.py`

**Step 1: Write the failing tests**

Añadir o ajustar tests en `HabilidadDynamicHeightTests` para cubrir:

```python
def test_libreria_habilidad_legacy_semantics_preserves_bottom_edge_but_not_fixed_height(self):
    config = normalize_layout_config("libreria", load_classic_seed("libreria"))
    config["habilidad"]["rules"]["box_semantics"] = "legacy"
    config["habilidad"]["box"] = {"x": 54, "y": 678, "width": 639, "height": 290}

    short_metrics = srv_textos_views._compute_layout_metrics(
        config, "libreria", "Texto corto", hab_font_size=24
    )
    long_metrics = srv_textos_views._compute_layout_metrics(
        config, "libreria", "texto " * 80, hab_font_size=24
    )

    assert short_metrics["habilidad"]["used_box"]["y"] + short_metrics["habilidad"]["used_box"]["height"] == 968
    assert long_metrics["habilidad"]["used_box"]["y"] + long_metrics["habilidad"]["used_box"]["height"] == 968
    assert long_metrics["habilidad"]["used_box"]["height"] > short_metrics["habilidad"]["used_box"]["height"]
```

Y un segundo test para layouts sin `box_semantics`:

```python
def test_libreria_habilidad_missing_semantics_is_responsive_from_legacy_bottom_edge(self):
    ...
```

**Step 2: Run test to verify it fails**

Run:

```bash
/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.srv_textos.tests.HabilidadDynamicHeightTests -v 2
```

Expected: FAIL porque la ruta legacy todavia conserva la altura visual antigua como suelo fijo.

**Step 3: Write minimal implementation**

En `apps/srv_textos/views.py`:

- distinguir entre:
  - layouts nuevos de `libreria` -> `bottom_edge = box.y`, `vertical_margin = box.height`
  - layouts legacy o sin `box_semantics` -> `bottom_edge = box.y + box.height`
- recalcular siempre `used_box.height` desde el contenido real
- dejar de tratar la altura legacy como alto visual persistido del cuadro

La rama efectiva debe parecerse a:

```python
if is_libreria_legacy_visual_box:
    hab_box_bottom = habilidad_box["y"] + habilidad_box["height"]
    vertical_margin = ...
    outer_hab_box_h = max(1, dynamic_hab_content_h + (vertical_margin * 2))
    used_hab_box_y = max(0, hab_box_bottom - outer_hab_box_h)
```

**Step 4: Run test to verify it passes**

Run:

```bash
/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.srv_textos.tests.HabilidadDynamicHeightTests -v 2
```

Expected: PASS.

**Step 5: Commit**

```bash
git add apps/srv_textos/tests.py apps/srv_textos/views.py
git commit -m "feat: make libreria legacy habilidad responsive"
```

### Task 2: Alinear disciplinas con el cuadro responsivo migrado

**Files:**
- Modify: `apps/srv_textos/tests.py`
- Modify: `apps/srv_textos/views.py`

**Step 1: Write the failing test**

Añadir un test que asegure que, con `disciplinas.rules.anchor_mode = "free"` y un layout legacy de libreria, `disciplinas.box.y` sigue a `habilidad.used_box.y - gap_from_habilidad`.

```python
def test_libreria_disciplinas_follow_responsive_legacy_habilidad_box(self):
    ...
    assert metrics["disciplinas"]["box"]["y"] == metrics["habilidad"]["used_box"]["y"] - 31
```

**Step 2: Run test to verify it fails**

Run:

```bash
/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.srv_textos.tests.HabilidadDynamicHeightTests -v 2
```

Expected: FAIL si el cuadro de habilidad sigue calculandose con semantica fija.

**Step 3: Write minimal implementation**

En `apps/srv_textos/views.py`:

- comprobar que `disc_box['y']` para `libreria` en modo `free` siempre use `used_hab_box['y'] - gap_from_habilidad`
- no introducir ramas especiales adicionales para legacy fuera del calculo correcto de `used_hab_box`

**Step 4: Run test to verify it passes**

Run:

```bash
/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.srv_textos.tests.HabilidadDynamicHeightTests -v 2
```

Expected: PASS.

**Step 5: Commit**

```bash
git add apps/srv_textos/tests.py apps/srv_textos/views.py
git commit -m "feat: keep libreria disciplinas aligned with responsive habilidad"
```

### Task 3: Alinear el editor de layouts de libreria con la semantica responsiva

**Files:**
- Modify: `static/layouts/editor.js`
- Modify: `apps/layouts/tests.py`

**Step 1: Write the failing test**

Añadir cobertura en `apps/layouts/tests.py` para fijar que el helper del editor trata `legacy` y ausencia de `box_semantics` como flujo responsivo de `libreria`.

Ejemplo:

```python
def test_editor_script_treats_legacy_libreria_habilidad_as_bottom_anchor_margin(self):
    script = Path("static/layouts/editor.js").read_text(encoding="utf-8")
    assert "boxSemantics === 'legacy'" in script or "boxSemantics === \"legacy\"" in script
```

**Step 2: Run test to verify it fails**

Run:

```bash
/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.layouts.tests.LayoutEditorStaticAssetTests -v 2
```

Expected: FAIL si el script no refleja explicitamente la ruta legacy responsiva.

**Step 3: Write minimal implementation**

En `static/layouts/editor.js`:

- asegurar que `legacy` y ausencia de valor se resuelven visualmente como `bottom_anchor_margin`
- mantener `box.width` como ancho y `box.height` como margen vertical, no alto final fijo
- al guardar tras editar, persistir `section.rules.box_semantics = "bottom_anchor_margin"` para libreria

**Step 4: Run test to verify it passes**

Run:

```bash
/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.layouts.tests.LayoutEditorStaticAssetTests -v 2
```

Expected: PASS.

**Step 5: Commit**

```bash
git add static/layouts/editor.js apps/layouts/tests.py
git commit -m "feat: align libreria layout editor with responsive habilidad"
```

### Task 4: Verificacion final

**Files:**
- Modify: `apps/srv_textos/views.py`
- Modify: `apps/srv_textos/tests.py`
- Modify: `static/layouts/editor.js`
- Modify: `apps/layouts/tests.py`

**Step 1: Run focused suites**

Run:

```bash
/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.srv_textos.tests apps.layouts.tests -v 1
```

Expected: PASS.

**Step 2: Run checks**

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
git diff -- apps/srv_textos/views.py apps/srv_textos/tests.py static/layouts/editor.js apps/layouts/tests.py
```

Expected: solo cambios del cuadro responsivo de `habilidad` en libreria.

**Step 4: Commit**

```bash
git add apps/srv_textos/views.py apps/srv_textos/tests.py static/layouts/editor.js apps/layouts/tests.py
git commit -m "feat: make libreria habilidad responsive across all layouts"
```
