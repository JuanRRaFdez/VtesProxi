# Unify Libreria Habilidad Render Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Hacer que `libreria` dibuje el texto y el cuadro de `habilidad` exactamente igual que `cripta`, usando el mismo pipeline de render.

**Architecture:** El renderer principal dejará de bifurcar por tipo para `habilidad` y usará el pipeline común de `cripta`. Los tests se actualizarán para fijar el comportamiento común y proteger que el layout y el centrado vertical siguen correctos.

**Tech Stack:** Django, Pillow, tests unitarios en `apps/srv_textos/tests.py`.

---

### Task 1: Fijar el contrato común con tests

**Files:**
- Modify: `apps/srv_textos/tests.py`
- Test: `apps/srv_textos/tests.py`

**Step 1: Write the failing test**

Añadir tests que demuestren que `libreria` debe usar el mismo renderer de habilidad que `cripta`:

- mismo comportamiento de centrado vertical
- mismo tratamiento de símbolos inline
- misma semántica de texto cuando se invoca el render de habilidad con los mismos parámetros

Si hace falta, usar `patch` sobre el helper de render para comprobar que `_render_carta()` llama al mismo renderer en ambos tipos.

**Step 2: Run test to verify it fails**

Run: `/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.srv_textos.tests -v 2`

Expected: FAIL porque hoy `libreria` sigue usando `_render_habilidad_text_libreria()`.

**Step 3: Write minimal implementation**

Modificar `apps/srv_textos/views.py` para que la rama de `habilidad` en `_render_carta()` use el mismo helper en `cripta` y `libreria`.

**Step 4: Run test to verify it passes**

Run: `/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.srv_textos.tests -v 2`

Expected: PASS en los tests nuevos.

**Step 5: Commit**

```bash
git add apps/srv_textos/tests.py apps/srv_textos/views.py
git commit -m "test: cover shared habilidad renderer"
```

### Task 2: Retirar la semántica específica de librería

**Files:**
- Modify: `apps/srv_textos/views.py`
- Modify: `apps/srv_textos/tests.py`

**Step 1: Write the failing test**

Añadir un test que proteja explícitamente que `**texto**` ya no tenga tratamiento especial en `libreria`, y que el parser común sea la fuente de verdad.

**Step 2: Run test to verify it fails**

Run: `/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.srv_textos.tests -v 2`

Expected: FAIL mientras `libreria` siga teniendo parser/render propio.

**Step 3: Write minimal implementation**

En `apps/srv_textos/views.py`:

- dejar de usar `_parse_libreria_habilidad()` y `_render_habilidad_text_libreria()` como camino funcional
- si se mantienen temporalmente, que no definan comportamiento distinto al común

**Step 4: Run test to verify it passes**

Run: `/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.srv_textos.tests -v 2`

Expected: PASS

**Step 5: Commit**

```bash
git add apps/srv_textos/tests.py apps/srv_textos/views.py
git commit -m "feat: unify libreria habilidad rendering with cripta"
```

### Task 3: Verificación final

**Files:**
- Test: `apps/srv_textos/tests.py`
- Verify: `apps/srv_textos/views.py`

**Step 1: Run targeted suite**

Run: `/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.srv_textos.tests -v 1`

Expected: PASS

**Step 2: Run broader regression suite**

Run: `/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.srv_textos.tests apps.layouts.tests apps.mis_cartas.tests -v 1`

Expected: PASS

**Step 3: Run Django checks**

Run: `/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py check`

Expected: `System check identified no issues`

**Step 4: Review final state**

```bash
git status --short
```

Confirmar que sólo quedan los cambios esperados y preparar el cierre con `superpowers:finishing-a-development-branch`.
