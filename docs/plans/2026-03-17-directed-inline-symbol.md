# Directed Inline Symbol Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Hacer que el token exacto `(D)` en el texto de `habilidad` se renderice como `directed.png` en cripta y librería.

**Architecture:** El cambio vive en el parser inline de `habilidad`, reutilizando el mismo pipeline que ya convierte `[dom]` y `[DOM]` en símbolos. No se toca la arquitectura del render; sólo se amplía la resolución de tokens especiales y se fijan regresiones en `apps/srv_textos/tests.py`.

**Tech Stack:** Django, PIL, unittest de Django.

---

### Task 1: Fijar por test la resolución de `(D)` como símbolo inline especial

**Files:**
- Modify: `apps/srv_textos/tests.py`
- Modify: `apps/srv_textos/views.py`

**Step 1: Write the failing test**

Añadir tests como:

```python
def test_inline_symbol_path_resolves_exact_directed_token(self):
    path = srv_textos_views._inline_symbol_path('(D)')
    self.assertIsNotNone(path)
    self.assertTrue(path.endswith('static/icons/directed.png') or path.endswith('static/icons/directed.svg'))

def test_inline_symbol_path_keeps_other_parentheses_as_text(self):
    path = srv_textos_views._inline_symbol_path('(rapida)')
    self.assertIsNone(path)
```

**Step 2: Run test to verify it fails**

Run:

```bash
/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.srv_textos.tests -v 1
```

Expected: FAIL porque hoy `(D)` no entra por `_inline_symbol_path()`.

**Step 3: Write minimal implementation**

En `apps/srv_textos/views.py`:

- ampliar `_inline_symbol_path()` para reconocer `(D)` exacto
- reutilizar `_special_symbol_path('Ⓓ')` o una ruta equivalente al icono `directed`

**Step 4: Run test to verify it passes**

Run:

```bash
/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.srv_textos.tests -v 1
```

Expected: PASS.

**Step 5: Commit**

```bash
git add apps/srv_textos/tests.py apps/srv_textos/views.py
git commit -m "feat: resolve directed token as inline symbol"
```

### Task 2: Fijar por test el render de `(D)` en cripta y librería

**Files:**
- Modify: `apps/srv_textos/tests.py`
- Modify: `apps/srv_textos/views.py`

**Step 1: Write the failing test**

Añadir regresiones de render como:

```python
def test_render_habilidad_cripta_loads_directed_symbol_for_exact_directed_token(self):
    ...

def test_render_habilidad_libreria_loads_directed_symbol_for_exact_directed_token(self):
    ...
```

Ambas deben comprobar que `_load_symbol()` recibe `static/icons/directed...`.

**Step 2: Run test to verify it fails**

Run:

```bash
/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.srv_textos.tests -v 1
```

Expected: FAIL antes del cambio o cobertura insuficiente.

**Step 3: Write minimal implementation**

Si hace falta, ajustar el troceado inline en `_append_text_tokens_for_single_line()` para asegurar que `(D)` se detecta también cuando vaya rodeado de espacios dentro de una línea.

**Step 4: Run test to verify it passes**

Run:

```bash
/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.srv_textos.tests -v 1
```

Expected: PASS.

**Step 5: Commit**

```bash
git add apps/srv_textos/tests.py apps/srv_textos/views.py
git commit -m "test: cover directed inline symbol rendering"
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
git commit -m "feat: render directed token as inline symbol"
```
