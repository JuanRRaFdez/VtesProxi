# Autocompletado Cartas Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Añadir búsqueda incremental de cartas por nombre (sin mayúsculas ni acentos) y autocompletado de formulario en Cripta/Librería.

**Architecture:** Se incorporará un servicio de catálogo en backend que cargue e indexe `Cripta_2.json` y `Libreria_2.json` en memoria. El frontend consultará sugerencias con debounce y pedirá el detalle de una carta al seleccionarla para poblar campos y relanzar el render.

**Tech Stack:** Django 6, vistas JSON, JavaScript vanilla en plantilla Django, Django TestCase.

---

### Task 1: Cobertura de tests para búsqueda/autocompletado

**Files:**
- Create: `apps/srv_textos/tests.py`
- Modify: `apps/srv_textos/urls.py`
- Modify: `apps/srv_textos/views.py`

**Step 1: Write the failing test**
- Probar endpoint de sugerencias con búsqueda sin acentos/mayúsculas y límite de 10 resultados.
- Probar endpoint de detalle y mapeo de campos para Cripta/Librería.

**Step 2: Run test to verify it fails**
- Run: `python manage.py test apps.srv_textos -v 2`
- Expected: FAIL por endpoints inexistentes y/o lógica no implementada.

**Step 3: Write minimal implementation**
- Añadir endpoints JSON en `srv_textos`.
- Añadir helpers de normalización y mapeo de catálogo.

**Step 4: Run test to verify it passes**
- Run: `python manage.py test apps.srv_textos -v 2`
- Expected: PASS.

### Task 2: Integración UI de sugerencias y autocompletado

**Files:**
- Modify: `apps/cripta/templates/cripta/importar_imagen.html`

**Step 1: Write the failing test**
- Cobertura backend de contrato JSON ya creada en Task 1.
- Para frontend, validar manualmente comportamiento en entorno local.

**Step 2: Run test to verify it fails**
- No aplica test frontend automatizado actual.

**Step 3: Write minimal implementation**
- Añadir contenedor de sugerencias bajo `#nombre`.
- Añadir JS con debounce (`input`) + fetch de sugerencias.
- Añadir selección de sugerencia y aplicación de payload a selects/textarea/grids.
- Forzar un render único tras aplicar datos.

**Step 4: Run test to verify it passes**
- Run: `python manage.py test apps.srv_textos -v 2`
- Validación manual: escribir nombre parcial, seleccionar sugerencia y comprobar autocompletado + render.

### Task 3: Refactor y verificación final

**Files:**
- Modify: `apps/srv_textos/views.py`
- Create: `apps/srv_textos/card_catalog.py`

**Step 1: Write the failing test**
- Añadir prueba de caso límite (card_type inválido, carta no encontrada).

**Step 2: Run test to verify it fails**
- Run: `python manage.py test apps.srv_textos -v 2`
- Expected: FAIL por ramas no cubiertas/errores de validación.

**Step 3: Write minimal implementation**
- Endurecer validaciones, mensajes de error y normalización.

**Step 4: Run test to verify it passes**
- Run: `python manage.py test apps.srv_textos -v 2`
- Expected: PASS.
