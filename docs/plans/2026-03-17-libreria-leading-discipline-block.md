# Libreria Leading Discipline Block Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Hacer que las líneas de habilidad de librería que empiezan con un bloque de disciplinas como `[obl] or [tha]` reserven toda esa anchura en la columna izquierda y mantengan esa sangría al hacer wrap.

**Architecture:** El cambio vive en el motor de composición de líneas de `habilidad` en `apps/srv_textos/views.py`. Ampliaremos la lógica actual de “leading symbol + hanging indent” para soportar, sólo en librería, un prefijo compuesto por símbolos inline de disciplina y el conector `or`. La cobertura se fijará en `apps/srv_textos/tests.py`.

**Tech Stack:** Django, PIL, unittest de Django.

---

### Task 1: Fijar por test el bloque inicial compuesto de disciplinas en librería

**Files:**
- Modify: `apps/srv_textos/tests.py`
- Modify: `apps/srv_textos/views.py`

**Step 1: Write the failing test**

Añadir tests como:

```python
def test_render_habilidad_libreria_reserves_leading_column_for_compound_discipline_block(self):
    ...

def test_render_habilidad_libreria_reserves_leading_column_for_uppercase_compound_discipline_block(self):
    ...
```

Ambos deben comprobar que el primer texto descriptivo empieza después del bloque `[obl] or [tha]` o `[OBL] or [THA]`, no después del primer símbolo únicamente.

**Step 2: Run test to verify it fails**

Run:

```bash
/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.srv_textos.tests -v 1
```

Expected: FAIL porque hoy la columna izquierda sólo reserva el primer símbolo.

**Step 3: Write minimal implementation**

En `apps/srv_textos/views.py`:

- detectar un prefijo inicial de línea para librería
- incluir en ese prefijo símbolos inline de disciplina, espacios y `or`
- usar el ancho total del bloque como sangría inicial

**Step 4: Run test to verify it passes**

Run:

```bash
/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.srv_textos.tests -v 1
```

Expected: PASS.

**Step 5: Commit**

```bash
git add apps/srv_textos/tests.py apps/srv_textos/views.py
git commit -m "feat: reserve libreria leading column for compound discipline blocks"
```

### Task 2: Fijar por test el wrap y los casos límite

**Files:**
- Modify: `apps/srv_textos/tests.py`
- Modify: `apps/srv_textos/views.py`

**Step 1: Write the failing test**

Añadir tests para:

```python
def test_render_habilidad_libreria_wraps_compound_discipline_line_with_hanging_indent(self):
    ...

def test_render_habilidad_libreria_does_not_treat_uppercase_or_as_connector(self):
    ...

def test_render_habilidad_cripta_keeps_existing_single_symbol_behavior(self):
    ...
```

**Step 2: Run test to verify it fails**

Run:

```bash
/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.srv_textos.tests -v 1
```

Expected: FAIL o cobertura insuficiente antes del ajuste fino.

**Step 3: Write minimal implementation**

Ajustar la detección del bloque inicial para que:

- `or` sólo cuente en minúsculas
- `cripta` no entre en la nueva rama
- la continuación de línea reciba la misma sangría colgante que el bloque compuesto

**Step 4: Run test to verify it passes**

Run:

```bash
/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.srv_textos.tests -v 1
```

Expected: PASS.

**Step 5: Commit**

```bash
git add apps/srv_textos/tests.py apps/srv_textos/views.py
git commit -m "test: cover libreria compound discipline block wrapping"
```

### Task 3: Verificación final

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

Expected: `System check identified no issues`.

**Step 4: Final commit**

```bash
git add apps/srv_textos/views.py apps/srv_textos/tests.py
git commit -m "feat: support compound leading discipline blocks in libreria"
```
