# Libreria Habilidad Visual Height Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Hacer que en `libreria` el aire visible superior e inferior del cuadro de `habilidad` responda al margen configurado en el layout.

**Architecture:** Mantendremos el margen vertical configurado desde `box.height`, pero el renderer común dejará de centrar usando la altura nominal de línea. En su lugar, medirá la altura visual real del bloque ya envuelto y la usará para calcular el recuadro y el centrado vertical. `cripta` no cambia.

**Tech Stack:** Django, Pillow, unittest.

---

### Task 1: Escribir un test rojo para el alto visual real

**Files:**
- Modify: `apps/srv_textos/tests.py`

**Step 1: Write the failing test**

Añadir un test que renderice una habilidad de `libreria` y compruebe que el hueco visible superior e inferior se mantiene cercano al `vertical_padding` configurado.

**Step 2: Run test to verify it fails**

Run:

```bash
/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.srv_textos.tests.HabilidadRenderAlignmentTests -v 2
```

**Step 3: Write minimal implementation**

No aplica todavía.

**Step 4: Run test to verify it still fails for the right reason**

Repetir el test focalizado.

**Step 5: Commit**

No commit en este paso.

### Task 2: Usar alto visual real en el renderer común

**Files:**
- Modify: `apps/srv_textos/views.py`
- Modify: `apps/srv_textos/tests.py`

**Step 1: Write minimal implementation**

En `_render_habilidad_text(...)`:

- medir el alto visual real del bloque envuelto
- usar ese alto para calcular el recuadro cuando corresponda
- centrar verticalmente con ese alto visual

**Step 2: Run focused tests**

Run:

```bash
/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.srv_textos.tests.HabilidadRenderAlignmentTests apps.srv_textos.tests.HabilidadDynamicHeightTests -v 2
```

**Step 3: Refactor if needed**

Extraer helpers pequeños sólo si queda repetición evidente.

**Step 4: Verify broader relevant suite**

Run:

```bash
/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.srv_textos.tests -v 1
/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py check
```

**Step 5: Commit**

```bash
git add apps/srv_textos/views.py apps/srv_textos/tests.py docs/plans/2026-03-16-libreria-habilidad-visual-height-design.md docs/plans/2026-03-16-libreria-habilidad-visual-height.md
git commit -m "fix: use visual text height for libreria habilidad"
```
