# Layout Cripta Y Gap Range Design

## Goal

Corregir el fallo de guardado de layouts de `cripta` cuando el editor genera un `y_gap` fuera del rango validado por backend.

## Problem

- El editor de layouts permite mover la capa `cripta` por el canvas con bastante libertad.
- Al sincronizar esa capa al modelo, `static/layouts/editor.js` recalcula `section.y_gap`.
- El backend valida `cripta.y_gap` con un rango `0..200` en `apps/layouts/services.py`.
- En cuanto el usuario coloca la capa suficientemente arriba, el editor genera un `y_gap` mayor que `200` y el guardado falla con `y_gap fuera de rango`.

## Decision

Haremos coherente el contrato entre editor y backend:

- el backend aceptara un rango de `y_gap` alineado con las coordenadas reales del canvas
- el editor clampetara la geometria de la capa `cripta` para no producir valores fuera del rango aceptado

## Approach

- En `apps/layouts/services.py`, ampliar el maximo permitido de `cripta.y_gap` desde `200` a un rango amplio coherente con el resto de coordenadas del layout.
- En `static/layouts/editor.js`, al renderizar y sincronizar la capa `cripta`, limitar su posicion vertical de forma que el `y_gap` derivado nunca salga del rango valido.
- No cambiar la semantica de `y_gap`: sigue siendo la distancia vertical entre el bloque de habilidad y el numero de cripta.
- No cambiar el render final de la carta.

## Testing

- Anadir un test de validacion en `apps/layouts/tests.py` que confirme que un `cripta.y_gap` alto, pero coherente con el canvas, ya no se rechaza.
- Anadir un test del script del editor para fijar que sigue recalculando `section.y_gap` y que la logica de la capa `cripta` ya no permite posiciones fuera del rango aceptado.
- Mantener en verde la suite actual de `layouts`.
