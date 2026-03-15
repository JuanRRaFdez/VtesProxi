# Libreria Habilidad Responsive All Layouts Design

## Goal

Hacer que el cuadro de `habilidad` en cartas de `libreria` sea realmente responsivo en todos los layouts de libreria, incluidos los ya guardados.

El comportamiento final debe ser:

- borde inferior fijo
- crecimiento solo hacia arriba
- alto real dependiente del texto y del `hab_font_size` efectivo
- texto centrado verticalmente dentro del recuadro final
- ningun layout de libreria sigue usando una altura visual fija para `habilidad`

## Current Problem

Hoy existen dos comportamientos en conflicto para `habilidad` de `libreria`:

1. layouts nuevos con semantica `bottom_anchor_margin`
2. layouts legacy o sin `box_semantics`, que siguen preservando la altura visual antigua

Eso deja el cuadro “fijo” en la practica para muchos layouts ya guardados. Aunque el motor ya conserva bien el borde inferior visual legacy, la altura antigua sigue actuando como suelo visual y evita que el recuadro se comporte de forma totalmente responsiva.

## Approved Direction

Se unifica `libreria` a una sola semantica responsiva para todos los layouts.

### Effective Semantics

Para cualquier layout de `libreria` con `habilidad.box`:

- `box.x`: borde izquierdo del recuadro
- `box.width`: ancho maximo disponible
- `box.y`: borde inferior efectivo del recuadro
- `box.height`: margen vertical interno simetrico entre texto y borde superior/inferior

El alto final ya no vendra de `box.height` como alto visual persistido. Se calculara siempre asi:

`outer_height = text_height + (vertical_margin * 2)`

Despues:

- `used_box.height = outer_height`
- `used_box.y = bottom_edge - outer_height`

Si el crecimiento empuja el recuadro por encima de `0`, se clampa a `y = 0` y el alto visible se ajusta al espacio restante.

## Legacy Layout Migration

Los layouts ya guardados de `libreria` deben entrar automaticamente en esta semantica responsiva.

Para no perder la referencia vertical que ya tienen:

- si el layout ya usa semantica nueva, `bottom_edge = box.y`
- si el layout es legacy o no declara `box_semantics`, `bottom_edge = box.y + box.height`

Con eso:

- se conserva el borde inferior visual que ya tenia el layout antiguo
- se abandona la altura visual fija antigua
- el cuadro pasa a crecer o encoger solo por el texto

El margen vertical interno para layouts legacy se derivara del alto antiguo disponible y del contenido real, pero no se seguira tratando como un alto fijo persistido.

## Scope

Aplica solo a `libreria`.

- `cripta` no cambia
- el renderer comun de habilidad se mantiene
- el editor de layouts de `libreria` debe alinearse con esta semantica para no mostrar una caja distinta a la del render real

## Editor Impact

En `/layouts/`, `habilidad` de `libreria` debe representarse con la misma semantica efectiva:

- mover el recuadro cambia el borde inferior y el borde izquierdo
- cambiar el ancho sigue actualizando `box.width`
- cambiar el alto debe seguir interpretandose como margen vertical interno, no como alto final congelado

Para layouts legacy, el editor debe presentar ya la semantica nueva normalizada, no el rectangulo fijo antiguo.

## Validation And Normalization

`apps/layouts/services.py` debe seguir aceptando layouts de libreria legacy, pero resolverlos operativamente al modelo responsivo.

En la practica:

- `legacy` deja de tener efecto visual distinto en `libreria`
- ausencia de `box_semantics` tambien entra en la semantica responsiva
- `bottom_anchor_margin` sigue siendo el nombre del modelo nuevo

No hace falta una migracion de base de datos para este cambio.

## Testing

Hace falta cubrir tres casos:

1. layout nuevo de libreria:
   - el cuadro crece y encoge con el texto
   - mantiene borde inferior fijo

2. layout legacy de libreria:
   - conserva el borde inferior visual heredado
   - deja de conservar la altura fija heredada
   - responde al tamaño del texto y al `hab_font_size`

3. reanclaje de disciplinas:
   - cuando `anchor_mode = free`, disciplinas sigue al `used_box` responsivo de habilidad
   - no vuelve a quedarse en `y=0` por culpa de una reinterpretacion incorrecta del cuadro

## Files Expected To Change

- `apps/srv_textos/views.py`
- `static/layouts/editor.js`
- `apps/srv_textos/tests.py`
- `apps/layouts/tests.py`
