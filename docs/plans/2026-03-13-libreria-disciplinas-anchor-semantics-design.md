# Libreria Disciplinas Anchor Semantics Design

## Summary

`disciplinas` en `libreria` debe adoptar exactamente la misma semántica que ya usa `cripta`. Deja de ser una caja contenedora y pasa a ser un helper geométrico con ancla inferior, tamaño de icono y separación vertical fija.

## Goals

- Unificar la semántica de `disciplinas` entre `cripta` y `libreria`.
- Hacer que el editor de layouts trate `disciplinas` de `libreria` igual que `cripta`.
- Mantener compatibilidad con layouts legacy de librería ya guardados.

## Semantics

Para `disciplinas` en `libreria`:

- `box.x`: borde izquierdo del icono inferior
- `box.y`: borde inferior del icono inferior
- `box.width`: tamaño del icono
- `box.height`: separación vertical fija entre iconos
- `rules.anchor_mode = "fixed_bottom"`: usa `box.y` tal cual
- `rules.anchor_mode = "free"`: el borde inferior del icono inferior se calcula como `habilidad.used_box.y - gap_from_habilidad`
- `rules.gap_from_habilidad`: distancia fija respecto a `habilidad`

## Architecture

### Normalization

`apps/layouts/services.py` dejará de materializar `disciplinas` de `libreria` con `_ensure_stack_box_section(..., bottom_anchored=True)` y reutilizará la misma normalización de ancla que `cripta`.

Compatibilidad:

- Si el layout legacy sólo tiene `x/size/bottom/spacing`, se convierte al nuevo modelo.
- Si ya tiene `rules.gap_from_habilidad`, se considera nuevo modelo.
- `size`, `spacing`, `bottom` y `y` siguen sincronizados como campos derivados para no romper otros consumidores.

### Render

`apps/srv_textos/views.py` dejará de tratar `disciplinas` de `libreria` como contenedor:

- no dividirá spacing por número de disciplinas
- no usará `height = spacing * icon_count`
- apilará siempre desde abajo hacia arriba con `box.width` y `box.height`

En la práctica, la rama de `libreria` para `disciplinas` se alinea con la de `cripta`.

### Editor

`static/layouts/editor.js` aplicará a `libreria` la misma lógica especial que hoy existe para `cripta`:

- el helper visual usa `top = box.y - box.height`
- el panel `Y` muestra el borde inferior real
- guardar el helper vuelve a persistir `box.y = frame.y + frame.height`
- en modo no fijo, guarda `rules.gap_from_habilidad`

## Error Handling

- `gap_from_habilidad` debe seguir siendo numérico y no negativo.
- `box.width` y `box.height` deben seguir validados como positivos.
- Los layouts viejos sin `box` explícita seguirán cargando tras la conversión.

## Testing

- tests de normalización para `libreria` con `disciplinas.box` tipo ancla
- tests de render para confirmar tamaño y spacing constantes en `libreria`
- tests del editor para asegurar que `libreria` usa la misma serialización que `cripta`
- regresión para `fixed_bottom` y `gap_from_habilidad` en `libreria`
