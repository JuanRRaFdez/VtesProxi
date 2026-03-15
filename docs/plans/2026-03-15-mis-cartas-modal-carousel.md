# Mis Cartas Modal Carousel Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Permitir navegar en el modal de `Mis cartas` entre las cartas visibles en la pagina actual sin cerrarlo, con botones en pantalla y flechas izquierda/derecha.

**Architecture:** El backend no cambia. El template `mis_cartas.html` renderizara metadata `data-*` por carta y ampliara el modal actual con controles de navegacion. El script del mismo template mantendra una coleccion de cartas visibles, abrira por indice y actualizara imagen, descarga y borrado al navegar.

**Tech Stack:** Django templates, JavaScript inline, Django TestCase/SimpleTestCase.

---

### Task 1: Fijar el contrato del carrusel en tests de template

**Files:**
- Modify: `apps/mis_cartas/tests.py`
- Test: `apps/mis_cartas/tests.py`

**Step 1: Write the failing test**

Anadir un test en `MisCartasTemplateTests` que compruebe que `/mis-cartas/` incluye:

- botones de navegacion del modal, por ejemplo `id="modalPrevBtn"` y `id="modalNextBtn"`
- atributos `data-card-url` y `data-card-filename` en las cartas renderizadas

**Step 2: Run test to verify it fails**

Run: `/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.mis_cartas.tests.MisCartasTemplateTests -v 2`

Expected: FAIL porque el template actual no renderiza esos ids ni esos atributos.

**Step 3: Write minimal implementation**

Modificar `apps/mis_cartas/templates/mis_cartas/mis_cartas.html` para:

- renderizar `data-card-url="{{ carta.url }}"` y `data-card-filename="{{ carta.nombre }}"`
- anadir los botones del carrusel dentro del modal

**Step 4: Run test to verify it passes**

Run: `/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.mis_cartas.tests.MisCartasTemplateTests -v 2`

Expected: PASS

**Step 5: Commit**

```bash
git add apps/mis_cartas/tests.py apps/mis_cartas/templates/mis_cartas/mis_cartas.html
git commit -m "test: cover mis cartas modal carousel markup"
```

### Task 2: Fijar la logica JS del carrusel con tests de asset/template

**Files:**
- Modify: `apps/mis_cartas/tests.py`
- Test: `apps/mis_cartas/tests.py`

**Step 1: Write the failing test**

Anadir un test que lea el HTML de `/mis-cartas/` y compruebe que el script contiene la logica esperada:

- una coleccion de cartas visibles
- funciones o referencias de navegacion `showNextCard` y `showPrevCard` o equivalentes
- escucha de `ArrowLeft` y `ArrowRight`

El test debe ser tolerante al estilo concreto del JS, pero fijar claramente que existe navegacion de teclado y por indice.

**Step 2: Run test to verify it fails**

Run: `/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.mis_cartas.tests.MisCartasTemplateTests -v 2`

Expected: FAIL porque el script actual solo sabe abrir y cerrar una imagen suelta.

**Step 3: Write minimal implementation**

Actualizar el script inline de `apps/mis_cartas/templates/mis_cartas/mis_cartas.html` para:

- construir un array con las cartas visibles en la pagina actual
- abrir el modal por indice
- mover el indice al navegar
- actualizar imagen, descarga y borrado al cambiar de carta
- responder a `ArrowLeft`, `ArrowRight` y `Escape`

**Step 4: Run test to verify it passes**

Run: `/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.mis_cartas.tests.MisCartasTemplateTests -v 2`

Expected: PASS

**Step 5: Commit**

```bash
git add apps/mis_cartas/tests.py apps/mis_cartas/templates/mis_cartas/mis_cartas.html
git commit -m "feat: add mis cartas modal carousel navigation"
```

### Task 3: Pulir estados visuales del modal

**Files:**
- Modify: `apps/mis_cartas/templates/mis_cartas/mis_cartas.html`
- Test: `apps/mis_cartas/tests.py`

**Step 1: Write the failing test**

Anadir un test que compruebe que el template incluye un estado para ocultar o desactivar los botones de navegacion cuando solo haya una carta visible.

**Step 2: Run test to verify it fails**

Run: `/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.mis_cartas.tests.MisCartasTemplateTests -v 2`

Expected: FAIL si el template no distingue el estado de una sola carta.

**Step 3: Write minimal implementation**

En `apps/mis_cartas/templates/mis_cartas/mis_cartas.html`:

- anadir una clase o atributo para ocultar los botones cuando la coleccion visible tenga tamano 0 o 1
- mantener el modal funcional sin introducir cambios de backend

**Step 4: Run test to verify it passes**

Run: `/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.mis_cartas.tests.MisCartasTemplateTests -v 2`

Expected: PASS

**Step 5: Commit**

```bash
git add apps/mis_cartas/tests.py apps/mis_cartas/templates/mis_cartas/mis_cartas.html
git commit -m "refactor: hide carousel controls for single visible card"
```

### Task 4: Verificacion final

**Files:**
- Test: `apps/mis_cartas/tests.py`
- Verify: `apps/mis_cartas/templates/mis_cartas/mis_cartas.html`

**Step 1: Run targeted tests**

Run: `/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.mis_cartas.tests -v 1`

Expected: PASS

**Step 2: Run broader regression tests**

Run: `/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.mis_cartas.tests apps.layouts.tests apps.srv_textos.tests -v 1`

Expected: PASS

**Step 3: Run framework checks**

Run: `/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py check`

Expected: `System check identified no issues`

**Step 4: Commit verification-safe final state**

```bash
git status --short
```

Confirmar que solo quedan los cambios esperados del carrusel y, si todo esta correcto, preparar el cierre de rama con `superpowers:finishing-a-development-branch`.
