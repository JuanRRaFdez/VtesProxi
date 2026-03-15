# Libreria Habilidad Legacy Semantics Migration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Hacer que los layouts de `libreria` existentes con `habilidad.rules.box_semantics = "legacy"` usen automaticamente el comportamiento responsivo de `bottom_anchor_margin`.

**Architecture:** La migracion se resuelve por compatibilidad en tiempo de normalizacion, editor y render. `legacy` se mantiene como valor aceptado para no romper datos viejos, pero se interpreta como alias funcional de `bottom_anchor_margin` en `libreria`. `cripta` no cambia.

**Tech Stack:** Django, Python, Pillow, JavaScript vanilla, unittest de Django.

---

### Task 1: Fijar por test la compatibilidad de normalizacion y validacion

**Files:**
- Modify: `apps/layouts/tests.py`
- Modify: `apps/layouts/services.py`

**Step 1: Write the failing tests**

Añadir tests que cubran:

```python
def test_normalize_libreria_habilidad_defaults_to_bottom_anchor_margin(self):
    normalized = normalize_layout_config("libreria", load_classic_seed("libreria"))
    assert normalized["habilidad"]["rules"]["box_semantics"] == "bottom_anchor_margin"

def test_validate_accepts_libreria_habilidad_legacy_box_semantics(self):
    config = normalize_layout_config("libreria", load_classic_seed("libreria"))
    config["habilidad"]["rules"]["box_semantics"] = "legacy"
    validate_layout_config("libreria", config)
```

**Step 2: Run test to verify it fails**

Run: `/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.layouts.tests.LayoutConfigBoxSchemaTests apps.layouts.tests.LayoutConfigValidationV2Tests -v 2`

Expected: FAIL because normalization still defaults to `legacy`.

**Step 3: Write minimal implementation**

En `apps/layouts/services.py`:

- cambiar el default normalizado de `libreria` a `bottom_anchor_margin`
- mantener la validacion aceptando `legacy` y `bottom_anchor_margin`

Snippet orientativo:

```python
if card_type == "libreria":
    rules.setdefault("box_semantics", "bottom_anchor_margin")
```

**Step 4: Run test to verify it passes**

Run: `/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.layouts.tests.LayoutConfigBoxSchemaTests apps.layouts.tests.LayoutConfigValidationV2Tests -v 2`

Expected: PASS.

**Step 5: Commit**

```bash
git add apps/layouts/tests.py apps/layouts/services.py
git commit -m "feat: normalize libreria habilidad semantics to bottom anchor"
```

### Task 2: Fijar por test la compatibilidad del render con layouts legacy

**Files:**
- Modify: `apps/srv_textos/tests.py`
- Modify: `apps/srv_textos/views.py`

**Step 1: Write the failing tests**

Añadir tests que cubran:

```python
def test_libreria_habilidad_legacy_semantics_alias_grows_up_from_bottom(self):
    config = normalize_layout_config("libreria", load_classic_seed("libreria"))
    config["habilidad"]["rules"]["box_semantics"] = "legacy"
    ...

def test_libreria_habilidad_missing_semantics_defaults_to_bottom_anchor_margin(self):
    config = normalize_layout_config("libreria", load_classic_seed("libreria"))
    del config["habilidad"]["rules"]["box_semantics"]
    ...
```

Los asserts deben comprobar que:

- `used_box.y + used_box.height == box.y`
- el recuadro crece hacia arriba
- el alto cambia con `hab_font_size`

**Step 2: Run test to verify it fails**

Run: `/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.srv_textos.tests.HabilidadDynamicHeightTests -v 2`

Expected: FAIL because `legacy` still cae en la ruta antigua del renderer.

**Step 3: Write minimal implementation**

En `apps/srv_textos/views.py`:

- tratar `legacy` y ausencia de valor como equivalentes a `bottom_anchor_margin` cuando `card_type == "libreria"`

Snippet orientativo:

```python
box_semantics = hab_rules.get("box_semantics", "bottom_anchor_margin")
is_libreria_bottom_anchor_margin = (
    normalized_card_type == "libreria"
    and has_habilidad_box
    and box_semantics in {"legacy", "bottom_anchor_margin"}
)
```

**Step 4: Run test to verify it passes**

Run: `/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.srv_textos.tests.HabilidadDynamicHeightTests -v 2`

Expected: PASS.

**Step 5: Commit**

```bash
git add apps/srv_textos/tests.py apps/srv_textos/views.py
git commit -m "feat: migrate libreria legacy habilidad render semantics"
```

### Task 3: Alinear el editor con la migracion legacy

**Files:**
- Modify: `static/layouts/editor.js`
- Modify: `apps/layouts/tests.py`

**Step 1: Write the failing tests**

Extender la cobertura del script con una assertion que fije que `legacy` tambien entra en la ruta del helper de `habilidad` de `libreria`.

Ejemplo:

```python
def test_editor_script_handles_legacy_libreria_habilidad_semantics(self):
    script = Path(...).read_text(encoding="utf-8")
    assert "legacy" in script
    assert "bottom_anchor_margin" in script
```

**Step 2: Run test to verify it fails**

Run: `/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.layouts.tests.LayoutEditorStaticAssetTests -v 2`

Expected: FAIL because the script only keys off the explicit `bottom_anchor_margin` value.

**Step 3: Write minimal implementation**

En `static/layouts/editor.js`:

- hacer que el helper de `habilidad` en `libreria` trate `legacy` como alias de `bottom_anchor_margin`
- al guardar tras editar, persistir `section.rules.box_semantics = "bottom_anchor_margin"`

**Step 4: Run test to verify it passes**

Run: `/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.layouts.tests.LayoutEditorStaticAssetTests -v 2`

Expected: PASS.

**Step 5: Commit**

```bash
git add static/layouts/editor.js apps/layouts/tests.py
git commit -m "feat: migrate libreria legacy habilidad editor semantics"
```

### Task 4: Verificacion final

**Files:**
- Modify: `apps/layouts/services.py`
- Modify: `apps/srv_textos/views.py`
- Modify: `static/layouts/editor.js`
- Modify: `apps/layouts/tests.py`
- Modify: `apps/srv_textos/tests.py`

**Step 1: Run focused suites**

Run:

```bash
/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.layouts.tests apps.srv_textos.tests -v 1
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
git diff -- apps/layouts/services.py apps/srv_textos/views.py static/layouts/editor.js apps/layouts/tests.py apps/srv_textos/tests.py
```

Expected: solo cambios de la migracion.

**Step 4: Commit**

```bash
git add apps/layouts/services.py apps/srv_textos/views.py static/layouts/editor.js apps/layouts/tests.py apps/srv_textos/tests.py
git commit -m "feat: migrate libreria legacy habilidad semantics"
```
