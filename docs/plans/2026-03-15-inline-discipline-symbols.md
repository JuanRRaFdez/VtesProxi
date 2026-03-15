# Inline Discipline Symbols Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Hacer que el texto de habilidad en cartas de `cripta` y `libreria` renderice simbolos inline de disciplina usando `[dom]` para inferior y `[DOM]` para superior.

**Architecture:** Se ampliara el parser comun de tokens inline del texto de habilidad para resolver marcadores entre corchetes a rutas de `disc_inf` o `disc_sup`. El render de texto ya soporta tokens `symbol`, asi que la mayor parte del cambio vive en parsing y en tests.

**Tech Stack:** Django, Pillow, tests unitarios en `apps/srv_textos/tests.py`.

---

### Task 1: Fijar el contrato de parsing para disciplinas inline

**Files:**
- Modify: `apps/srv_textos/tests.py`
- Test: `apps/srv_textos/tests.py`

**Step 1: Write the failing test**

Añadir tests unitarios para el parsing/tokenizado del texto que comprueben:

- `[dom]` genera un token `symbol` que apunta a `disc_inf/dom`
- `[DOM]` genera un token `symbol` que apunta a `disc_sup/dom`
- aplica tanto al flujo de `cripta` como al de `libreria`

Usar helpers internos si ya existen para inspeccionar tokens en vez de testear pixeles.

**Step 2: Run test to verify it fails**

Run: `/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.srv_textos.tests -v 2`

Expected: FAIL porque el parser actual no resuelve esos marcadores.

**Step 3: Write minimal implementation**

Modificar `apps/srv_textos/views.py` para:

- añadir un helper que detecte tokens `[codigo]`
- resolver `disc_inf` o `disc_sup` según minusculas o mayusculas
- devolver `None` si no existe un icono valido

**Step 4: Run test to verify it passes**

Run: `/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.srv_textos.tests -v 2`

Expected: PASS en los tests nuevos.

**Step 5: Commit**

```bash
git add apps/srv_textos/tests.py apps/srv_textos/views.py
git commit -m "test: cover inline discipline symbols"
```

### Task 2: Mantener texto literal para marcadores desconocidos

**Files:**
- Modify: `apps/srv_textos/tests.py`
- Modify: `apps/srv_textos/views.py`

**Step 1: Write the failing test**

Añadir un test que compruebe que `[xyz]` o cualquier marcador sin icono no se convierte en token `symbol` y permanece como texto.

**Step 2: Run test to verify it fails**

Run: `/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.srv_textos.tests -v 2`

Expected: FAIL si el parser intenta tragarse el marcador o lo trata mal.

**Step 3: Write minimal implementation**

Ajustar el helper para que, si no hay fichero valido, devuelva el texto intacto al flujo normal.

**Step 4: Run test to verify it passes**

Run: `/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.srv_textos.tests -v 2`

Expected: PASS

**Step 5: Commit**

```bash
git add apps/srv_textos/tests.py apps/srv_textos/views.py
git commit -m "fix: preserve unknown inline discipline markers"
```

### Task 3: Integrar el helper en ambos renders de habilidad

**Files:**
- Modify: `apps/srv_textos/views.py`
- Test: `apps/srv_textos/tests.py`

**Step 1: Write the failing test**

Añadir o ampliar tests para que el tokenizado de ambos caminos use el helper comun:

- flujo de `cripta`
- flujo de `libreria`

El test debe proteger que ambos generan tokens `symbol` de disciplina inline y siguen dejando pasar el resto del texto.

**Step 2: Run test to verify it fails**

Run: `/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.srv_textos.tests -v 2`

Expected: FAIL si uno de los dos caminos sigue sin usar la resolucion nueva.

**Step 3: Write minimal implementation**

Aplicar el helper comun en:

- el parseo de palabras en `_render_habilidad_text()`
- el parseo de segmentos en `_segment_to_tokens_libreria()` o helper equivalente

Evitar duplicar logica.

**Step 4: Run test to verify it passes**

Run: `/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.srv_textos.tests -v 2`

Expected: PASS

**Step 5: Commit**

```bash
git add apps/srv_textos/tests.py apps/srv_textos/views.py
git commit -m "feat: render inline discipline symbols in card text"
```

### Task 4: Verificacion final

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

Confirmar que solo quedan los cambios esperados y preparar cierre con `superpowers:finishing-a-development-branch`.
