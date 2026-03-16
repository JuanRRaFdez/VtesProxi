# Libreria Habilidad Visual Height Design

## Goal

Corregir en `libreria` el centrado y la altura efectiva del bloque de `habilidad` para que el aire superior e inferior responda visualmente a `habilidad.box.height`.

## Problem

- El margen vertical configurado ya llega al render.
- Pero el centrado del texto usa la altura nominal de línea (`font_size + line_spacing`) en lugar de la altura visual real de los glifos.
- Eso deja aire extra arriba y abajo, así que el resultado visible no coincide con el margen del layout.

## Decision

En `libreria`, el alto del recuadro y el centrado vertical se calcularán a partir del alto visual real del bloque renderizado, no de la altura nominal de línea.

## Approach

- Mantener `habilidad.box.height` como única fuente del aire vertical configurado.
- Mantener `bg_padding` sólo como padding horizontal.
- Medir el alto visual real del texto ya envuelto.
- Calcular el cuadro como:
  - `alto_recuadro = alto_visual_real + (box.height * 2)`
- Centrar el texto usando ese alto visual real.
- No cambiar `cripta`.

## Testing

- Añadir un test rojo que demuestre que el hueco visible en librería se aproxima al margen configurado.
- Verificar que el borde inferior siga fijo y que el recuadro siga creciendo hacia arriba.
- Mantener en verde los tests existentes de cripta.
