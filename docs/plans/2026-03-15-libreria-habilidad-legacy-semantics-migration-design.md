# Libreria Habilidad Legacy Semantics Migration Design

## Goal

Corregir la compatibilidad de `habilidad.box` en `libreria` para que los layouts existentes que hoy tienen `habilidad.rules.box_semantics = "legacy"` pasen a usar el comportamiento responsivo aprobado:

- borde inferior fijo
- crecimiento hacia arriba
- `box.width` como ancho maximo
- `box.height` como margen vertical interno simetrico

El objetivo practico es que la creacion de cartas de `libreria` reaccione al texto y al tamaño de fuente tambien en layouts viejos, sin obligar a regrabar el layout manualmente.

## Root Cause

El comportamiento responsivo ya existe en `apps/srv_textos/views.py`, pero solo se activa cuando:

`habilidad.rules.box_semantics == "bottom_anchor_margin"`

Sin embargo, `apps/layouts/services.py` sigue normalizando `libreria` con:

`rules.setdefault("box_semantics", "legacy")`

Y el layout real guardado en base de datos ya tiene `box_semantics: "legacy"`. Eso significa que la ruta nueva nunca se ejecuta en la creacion real de cartas.

## Approved Decision

Para `libreria`, `legacy` deja de tener efecto practico y pasa a resolverse igual que `bottom_anchor_margin`.

Eso aplica a:

- layouts nuevos de `libreria`
- layouts viejos sin `box_semantics`
- layouts existentes guardados con `box_semantics = "legacy"`

No aplica a:

- `cripta`
- otras capas del layout

## Behavior After Migration

En `libreria`, el motor debe considerar el modo nuevo activo cuando ocurra cualquiera de estas condiciones:

- `box_semantics == "bottom_anchor_margin"`
- `box_semantics == "legacy"`
- `box_semantics` no exista

Efecto:

- el borde inferior del recuadro sigue saliendo de `box.y`
- la altura real del recuadro se recalcula desde el texto real
- el cuadro crece hacia arriba
- el texto sigue centrado verticalmente dentro del `used_box`

## Compatibility Strategy

No vamos a mantener dos semanticas activas en `libreria`.

En vez de intentar migrar fila a fila o pedir al usuario que guarde otra vez el layout:

- la normalizacion de `libreria` dejara de introducir `legacy` como valor por defecto practico
- la validacion podra seguir aceptando `legacy` durante la transicion, pero el render y el editor lo trataran como alias de `bottom_anchor_margin`

Opcionalmente, cuando el editor vuelva a guardar el layout, puede persistir directamente `bottom_anchor_margin` para dejar el dato canonico saneado.

## Editor Impact

El editor de layouts de `libreria` ya proyecta el helper de `habilidad` con la semantica nueva.

La migracion debe garantizar que:

- si abre un layout viejo con `legacy`, el helper se vea ya con el comportamiento nuevo
- si el usuario lo edita y guarda, el layout quede persistido como `bottom_anchor_margin`

## Validation

`apps/layouts/services.py` debe seguir aceptando ambos valores mientras exista data vieja:

- `legacy`
- `bottom_anchor_margin`

Pero para `libreria`, ambos significaran lo mismo a efectos de render y editor.

## Testing

### Layout services

`apps/layouts/tests.py`

- normalizacion de `libreria` debe resolver por defecto a `bottom_anchor_margin` o equivalente practico
- validacion debe seguir aceptando `legacy`
- validacion debe seguir rechazando valores desconocidos

### Rendering

`apps/srv_textos/tests.py`

- un layout de `libreria` con `box_semantics = "legacy"` debe crecer hacia arriba igual que uno con `bottom_anchor_margin`
- un layout de `libreria` sin `rules.box_semantics` debe hacer lo mismo
- `cripta` no cambia

### Editor

`apps/layouts/tests.py`

- el script debe seguir conteniendo la ruta de `bottom_anchor_margin`
- el helper de `libreria` no debe depender de que el valor guardado sea exactamente `bottom_anchor_margin`

## Files Expected To Change

- `apps/layouts/services.py`
- `apps/srv_textos/views.py`
- `static/layouts/editor.js`
- `apps/layouts/tests.py`
- `apps/srv_textos/tests.py`
