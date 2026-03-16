# Inline Discipline Leading Column Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Reservar una columna invisible para simbolos de disciplina inline al inicio de linea en `habilidad`, de forma que el texto quede alineado a la izquierda despues del icono.

**Architecture:** El cambio vive en el renderer comun de `habilidad` en `apps/srv_textos/views.py`. Mantendremos el parser y el wrap actuales, pero anadiremos un layout especial para las lineas cuyo primer token visible sea un simbolo inline: icono en columna propia y texto en columna separada. La cobertura se fijara en `apps/srv_textos/tests.py`.

**Tech Stack:** Django, Python, Pillow, unittest de Django.

---

### Task 1: Fijar por test la columna reservada para lineas con disciplina inicial

**Files:**
- Modify: `apps/srv_textos/tests.py`
- Modify: `apps/srv_textos/views.py`

**Step 1: Write the failing tests**

Anadir tests que cubran:

```python
def test_render_habilidad_leaves_leading_icon_column_for_inline_discipline_lines(self):
    ...

def test_render_habilidad_keeps_regular_lines_in_current_centered_layout(self):
    ...
```

El primer test debe comprobar que, para una linea tipo `[aus] +1 intercept...`, el primer texto se dibuja claramente a la derecha del icono y no centrado junto a el.

**Step 2: Run test to verify it fails**

Run:

```bash
/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.srv_textos.tests.HabilidadRenderAlignmentTests -v 2
```

Expected: FAIL porque el renderer actual centra la linea completa.

**Step 3: Write minimal implementation**

En `apps/srv_textos/views.py`:

- detectar las lineas cuyo primer token sea `symbol`
- calcular un ancho reservado para columna de icono
- dibujar el icono en esa columna
- dibujar el texto restante desde una columna de texto fija, alineada a la izquierda

Mantener el comportamiento existente para lineas normales.

**Step 4: Run test to verify it passes**

Run:

```bash
/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.srv_textos.tests.HabilidadRenderAlignmentTests -v 2
```

Expected: PASS.

**Step 5: Commit**

```bash
git add apps/srv_textos/tests.py apps/srv_textos/views.py
git commit -m "feat: reserve leading icon column for discipline lines"
```

### Task 2: Soportar wrap con sangria colgante en la columna de texto

**Files:**
- Modify: `apps/srv_textos/tests.py`
- Modify: `apps/srv_textos/views.py`

**Step 1: Write the failing test**

Anadir un test que cubra un caso como:

```python
def test_render_habilidad_wraps_discipline_line_with_hanging_indent(self):
    ...
```

El test debe fijar que cuando la linea de disciplina se rompe:
- la primera linea mantiene el icono a la izquierda
- la continuacion arranca en la misma columna de texto
- la continuacion no cae debajo del icono

**Step 2: Run test to verify it fails**

Run:

```bash
/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.srv_textos.tests.HabilidadRenderAlignmentTests -v 2
```

Expected: FAIL porque el wrap actual no conoce esa sangria.

**Step 3: Write minimal implementation**

En `apps/srv_textos/views.py`:

- anadir una fase pequena de layout para lineas disciplinares largas
- reutilizar el ancho reservado de la columna de icono
- hacer que las sublineas renderizadas usen siempre la misma columna de texto

Evitar tocar el wrap normal de lineas no disciplinares.

**Step 4: Run test to verify it passes**

Run:

```bash
/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.srv_textos.tests.HabilidadRenderAlignmentTests -v 2
```

Expected: PASS.

**Step 5: Commit**

```bash
git add apps/srv_textos/tests.py apps/srv_textos/views.py
git commit -m "feat: add hanging indent for wrapped discipline lines"
```

### Task 3: Verificacion final

**Files:**
- Modify: `apps/srv_textos/views.py`
- Modify: `apps/srv_textos/tests.py`

**Step 1: Run focused suite**

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
git diff -- apps/srv_textos/views.py apps/srv_textos/tests.py docs/plans/2026-03-16-inline-discipline-leading-column-design.md docs/plans/2026-03-16-inline-discipline-leading-column.md
```

Expected: solo cambios del layout especial para lineas de disciplina inline y la documentacion asociada.

**Step 5: Commit**

```bash
git add apps/srv_textos/views.py apps/srv_textos/tests.py docs/plans/2026-03-16-inline-discipline-leading-column-design.md docs/plans/2026-03-16-inline-discipline-leading-column.md
git commit -m "docs: add plan for inline discipline leading column"
```
