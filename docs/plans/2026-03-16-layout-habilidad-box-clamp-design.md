# Layout Habilidad Box Clamp Design

## Goal

Evitar que el editor de layouts genere un `habilidad.box.y` inválido al guardar desde el panel derecho.

## Problem

- El backend valida `habilidad.box.y` con rango `0..3000`.
- El editor ya clampa posiciones al arrastrar con el ratón.
- Pero al aplicar valores manuales desde el panel derecho, la ruta que traduce el frame al modelo puede dejar `habilidad.box.y` negativo.
- El resultado es un error al guardar: `habilidad.box.y fuera de rango`.

## Decision

Corregiremos el problema en el editor, en el punto donde un frame se convierte en sección de layout.

## Approach

- Mantener la validación backend intacta.
- En `static/layouts/editor.js`, clamplear `x` e `y` en la ruta común de `applyFrameToSection()` para las capas con geometría normal.
- No tocar las capas con semántica especial de borde inferior:
  - `disciplinas`
  - `habilidad` de `libreria`
- Con eso:
  - el drag y el panel derecho quedan alineados
  - el editor deja de poder fabricar `habilidad.box.y` negativo
  - el contrato del backend sigue siendo la fuente de verdad

## Testing

- Añadir un test de script en `apps/layouts/tests.py` que fije el clamp explícito de coordenadas en la ruta común del editor.
- Añadir un test de API en `apps/layouts/tests.py` que simule un payload de layout con `habilidad.box.y` negativo y confirme que el editor corregido ya no debería producirlo.
- Mantener en verde la suite de `layouts`.
