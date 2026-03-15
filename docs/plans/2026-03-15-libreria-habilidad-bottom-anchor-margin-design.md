# Libreria Habilidad Bottom Anchor Margin Design

## Goal

Cambiar la semantica de `habilidad.box` en cartas de `libreria` para que deje de representar un rectangulo visual fijo y pase a representar:

- `box.x`: borde izquierdo absoluto del recuadro
- `box.y`: borde inferior absoluto del recuadro
- `box.width`: ancho maximo del recuadro
- `box.height`: margen vertical interno simetrico entre el bloque de texto y el borde superior/inferior del recuadro

El recuadro visible de habilidad en `libreria` sera responsivo, con borde inferior fijo y crecimiento hacia arriba en funcion del alto real del texto. El texto quedara siempre centrado verticalmente dentro del recuadro efectivo y nunca bajara por debajo del borde inferior definido por `box.y`.

## Scope

Este cambio aplica solo a `libreria`.

- `cripta` mantiene su semantica actual de `habilidad.box`
- el parser y renderer comun de habilidad no cambian de contrato
- el editor de layouts de `libreria` debe reflejar la nueva semantica visualmente

## Current Problem

Hoy `habilidad.box` se interpreta como un rectangulo clasico en `apps/srv_textos/views.py`:

- `box.y` es el borde superior
- `box.height` es el alto visual maximo del recuadro
- `used_box` puede recortar o crecer segun distintas ramas, pero no responde al modelo aprobado para `libreria`

En `static/layouts/editor.js` ocurre lo mismo:

- el helper visual de `habilidad` usa `y_ratio` y `box_bottom_ratio` para reconstruir un rectangulo completo
- al redimensionar se sigue persistiendo `box_bottom_ratio` y `font_size` a partir del alto visual del helper

Ese modelo no coincide con el comportamiento deseado para creacion de cartas de `libreria`.

## Approved Semantics For Libreria

### Rendering

Para `card_type == 'libreria'` y solo cuando el layout marque el nuevo modo:

- `box.x` fija el borde izquierdo del recuadro
- `box.y` fija el borde inferior del recuadro
- `box.width` fija el ancho maximo disponible para el texto
- `box.height` fija el margen vertical interno simetrico

El alto real del recuadro se calcula como:

`outer_height = text_height + (box.height * 2)`

Con eso:

- `used_box.x = box.x`
- `used_box.width = box.width`
- `used_box.height = outer_height`
- `used_box.y = box.y - outer_height`

Si el crecimiento hacia arriba supera el borde superior de la carta, `used_box.y` se clampa a `0` y `used_box.height` se ajusta al alto visible resultante. El borde inferior util del cuadro sigue siendo `box.y`.

El texto se sigue dibujando con el renderer comun y centrado verticalmente dentro del `used_box`. El interlineado no cambia.

### Editor

En `/layouts/`, para `libreria` y solo en el nuevo modo:

- el helper visible de `habilidad` representa el recuadro efectivo a partir del texto de referencia actual
- mover el helper desplaza el ancla inferior izquierda (`box.x`, `box.y`)
- cambiar el ancho actualiza `box.width`
- cambiar el alto del helper actualiza `box.height` como margen vertical interno, no como alto final del cuadro

La UI sigue mostrando un rectangulo, pero internamente `height` deja de significar alto visual persistido.

## Backward Compatibility

No se debe reinterpretar silenciosamente layouts viejos de `libreria`.

Se introduce un flag explicito en `habilidad.rules`, por ejemplo:

`box_semantics = "bottom_anchor_margin"`

Reglas:

- si el flag esta presente en `libreria`, se activa la nueva semantica
- si el flag no esta presente, `libreria` mantiene la semantica legacy actual
- `cripta` ignora este flag

Esto permite migrar layout a layout sin romper configuraciones existentes.

## Normalization And Validation

`apps/layouts/services.py` debe:

- asegurar que `habilidad.rules` existe
- aceptar `habilidad.rules.box_semantics` solo con valores soportados
- conservar el comportamiento actual cuando el flag no existe
- validar `habilidad.box.height` como margen vertical interno en el modo nuevo, manteniendo los mismos limites numericos razonables

No hace falta cambiar el schema externo del layout fuera de ese flag.

## Testing

Se necesita cobertura en dos niveles.

### Layout / editor

`apps/layouts/tests.py`

- normalizacion de `habilidad.rules.box_semantics` para `libreria`
- validacion de valores invalidos del flag
- presencia en el script del editor de la nueva ruta para `habilidad` de `libreria`

### Rendering / metrics

`apps/srv_textos/tests.py`

- `libreria` con flag nuevo calcula `used_box` desde borde inferior fijo y crecimiento hacia arriba
- el alto real usa `text_height + 2 * margin`
- el texto queda centrado dentro del recuadro efectivo
- el texto no queda por debajo del borde inferior
- si aumenta `hab_font_size`, el recuadro crece hacia arriba
- sin flag, `libreria` sigue usando la semantica legacy
- `cripta` no cambia

## Files Expected To Change

- `apps/srv_textos/views.py`
- `apps/layouts/services.py`
- `static/layouts/editor.js`
- `apps/srv_textos/tests.py`
- `apps/layouts/tests.py`
