# Manual Habilidad Formatting Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Hacer que el texto de `habilidad` en `cripta` y `libreria` use solo formato manual: normal por defecto, `**...**` para negrita y `(...)` para cursiva, con botones de ayuda en la UI.

**Architecture:** El cambio se resuelve unificando el parseo de `habilidad` en un solo flujo comun en `apps/srv_textos/views.py`, eliminando las reglas automaticas antiguas y manteniendo la resolucion de simbolos inline. En la UI compartida se anade una toolbar simple que envuelve la seleccion del textarea con las marcas aprobadas y relanza el render.

**Tech Stack:** Django, Python, Pillow, JavaScript vanilla, unittest de Django.

---

### Task 1: Fijar por test el parser manual comun

**Files:**
- Modify: `apps/srv_textos/tests.py`
- Modify: `apps/srv_textos/views.py`

**Step 1: Write the failing tests**

Anadir tests que cubran:

```python
def test_parse_habilidad_plain_text_is_normal(self):
    segments = srv_textos_views._parse_habilidad("Texto normal")
    assert segments == [{"text": "Texto normal", "style": "normal"}]

def test_parse_habilidad_double_asterisks_are_bold(self):
    segments = srv_textos_views._parse_habilidad("**Negrita**")
    assert segments == [{"text": "Negrita", "style": "bold"}]

def test_parse_habilidad_parentheses_are_italic(self):
    segments = srv_textos_views._parse_habilidad("(Cursiva)")
    assert segments == [{"text": "(Cursiva)", "style": "italic"}]
```

Y ajustar cualquier test previo que hoy fije negrita automatica por `:` o `+`.

**Step 2: Run test to verify it fails**

Run:

```bash
/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.srv_textos.tests.TextInBoxHelpersTests -v 2
```

Expected: FAIL porque `_parse_habilidad()` todavia aplica reglas automaticas de `cripta`.

**Step 3: Write minimal implementation**

En `apps/srv_textos/views.py`:

- reescribir `_parse_habilidad()` para devolver texto normal por defecto
- reconocer `**...**` como `bold`
- no generar ya negrita automatica por `:` ni `+`

Mantener la salida como lista de segmentos `{"text": ..., "style": ...}`.

**Step 4: Run test to verify it passes**

Run:

```bash
/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.srv_textos.tests.TextInBoxHelpersTests -v 2
```

Expected: PASS.

**Step 5: Commit**

```bash
git add apps/srv_textos/tests.py apps/srv_textos/views.py
git commit -m "feat: switch habilidad parser to manual formatting"
```

### Task 2: Unificar el flujo de cursiva y simbolos inline

**Files:**
- Modify: `apps/srv_textos/tests.py`
- Modify: `apps/srv_textos/views.py`

**Step 1: Write the failing tests**

Anadir tests que cubran:

```python
def test_parse_habilidad_bold_block_with_parentheses_keeps_italic_inside(self):
    segments = srv_textos_views._parse_habilidad("**Titulo (nota)**")
    assert segments == [
        {"text": "Titulo ", "style": "bold"},
        {"text": "(nota)", "style": "italic"},
    ]

def test_render_habilidad_keeps_inline_discipline_symbols_with_manual_formatting(self):
    ...
```

Y un test que garantice que `libreria` ya no depende de `_parse_libreria_habilidad()`.

**Step 2: Run test to verify it fails**

Run:

```bash
/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.srv_textos.tests.HabilidadRenderAlignmentTests apps.srv_textos.tests.TextInBoxHelpersTests -v 2
```

Expected: FAIL porque el parseo y la tokenizacion todavia estan divididos entre `cripta` y `libreria`.

**Step 3: Write minimal implementation**

En `apps/srv_textos/views.py`:

- reutilizar un solo parser comun para `cripta` y `libreria`
- hacer que la logica de parentesis siga produciendo segmentos `italic`
- conservar `_append_text_tokens_with_inline_symbols()` y el flujo de simbolos inline
- eliminar o dejar sin uso la bifurcacion especifica de libreria si ya no aporta comportamiento distinto

**Step 4: Run test to verify it passes**

Run:

```bash
/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.srv_textos.tests -v 1
```

Expected: PASS.

**Step 5: Commit**

```bash
git add apps/srv_textos/tests.py apps/srv_textos/views.py
git commit -m "feat: unify habilidad text rendering across card types"
```

### Task 3: Anadir toolbar manual al textarea de habilidad

**Files:**
- Modify: `apps/cripta/templates/cripta/importar_imagen.html`
- Modify: `apps/srv_textos/tests.py`

**Step 1: Write the failing tests**

Anadir tests de template/script que cubran:

```python
def test_importar_imagen_template_exposes_habilidad_format_buttons(self):
    response = self.client.get("/cripta/importar-imagen/")
    self.assertContains(response, 'id="habilidad-bold-btn"')
    self.assertContains(response, 'id="habilidad-italic-btn"')
```

Y un test estatico o de contenido que fije helpers JS para envolver seleccion con `**...**` y `(...)`.

**Step 2: Run test to verify it fails**

Run:

```bash
/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.srv_textos.tests.ImportViewsLayoutContextTests -v 2
```

Expected: FAIL porque la toolbar todavia no existe.

**Step 3: Write minimal implementation**

En `apps/cripta/templates/cripta/importar_imagen.html`:

- anadir botones `B` e `I` junto al textarea `habilidad`
- anadir helper JS para:
  - envolver seleccion con `**...**`
  - envolver seleccion con `(...)`
  - insertar parejas vacias y dejar el cursor dentro cuando no haya seleccion
- llamar a `renderHabilidad()` tras la insercion

Usar ids claros como:

```html
id="habilidad-bold-btn"
id="habilidad-italic-btn"
```

**Step 4: Run test to verify it passes**

Run:

```bash
/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.srv_textos.tests.ImportViewsLayoutContextTests -v 2
```

Expected: PASS.

**Step 5: Commit**

```bash
git add apps/cripta/templates/cripta/importar_imagen.html apps/srv_textos/tests.py
git commit -m "feat: add manual habilidad formatting toolbar"
```

### Task 4: Verificacion final

**Files:**
- Modify: `apps/srv_textos/views.py`
- Modify: `apps/srv_textos/tests.py`
- Modify: `apps/cripta/templates/cripta/importar_imagen.html`

**Step 1: Run focused suites**

Run:

```bash
/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.srv_textos.tests -v 1
```

Expected: PASS.

**Step 2: Run broader regression**

Run:

```bash
/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.srv_textos.tests apps.layouts.tests apps.mis_cartas.tests -v 1
```

Expected: PASS.

**Step 3: Run checks**

Run:

```bash
/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py check
```

Expected: OK.

**Step 4: Review diff**

Run:

```bash
git status --short
git diff -- apps/srv_textos/views.py apps/srv_textos/tests.py apps/cripta/templates/cripta/importar_imagen.html
```

Expected: solo cambios del formato manual de `habilidad`.

**Step 5: Commit**

```bash
git add apps/srv_textos/views.py apps/srv_textos/tests.py apps/cripta/templates/cripta/importar_imagen.html
git commit -m "feat: make habilidad formatting fully manual"
```
