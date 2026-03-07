# Pestaña PDF Con Cantidad Por Carta Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Añadir una nueva pestaña `PDF` para buscar cartas guardadas del usuario, añadirlas sin duplicar y generar un PDF con cantidad por carta.

**Architecture:** Se añadirá una nueva vista HTML en `mis_cartas` para actuar como "carrito de PDF" y se reutilizará el endpoint `/mis-cartas/generar-pdf/` extendiendo su contrato para aceptar `items` con `{filename, quantity}`. La navegación principal incluirá la nueva pestaña `PDF`.

**Tech Stack:** Django 6, Django TestCase, plantilla Django + JavaScript vanilla, servicio ReportLab existente.

---

**Execution Skills:** `@test-driven-development` `@verification-before-completion`

### Task 1: Rutas y navegación para la pestaña PDF
- Añadir tests fallando para `/pdf/` y link en sidebar.
- Implementar ruta y vista protegida por login.
- Añadir enlace `PDF` al `base.html`.

### Task 2: UI de carrito PDF con cantidad por carta
- Añadir tests fallando para controles de la nueva plantilla.
- Implementar `pdf_builder.html` con búsqueda + listado + carrito sin duplicados + resumen de copias.
- Añadir JS para añadir carta, editar cantidades, quitar carta y enviar payload.

### Task 3: Extender endpoint de generación para `items`
- Añadir tests fallando para payload `items` y validación de cantidad.
- Extender `generar_pdf_cartas` para aceptar `items` (y mantener compatibilidad con `selected/copies`).
- Verificar suite de `mis_cartas` completa.
