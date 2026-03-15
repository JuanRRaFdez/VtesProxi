# Unify Libreria Habilidad Render Design

## Goal

Hacer que el texto y el cuadro de `habilidad` en cartas de `libreria` se dibujen exactamente igual que en `cripta`.

## Current State

Hoy existen dos caminos distintos para renderizar `habilidad`:

- `cripta` usa `_parse_habilidad()` y `_render_habilidad_text()`
- `libreria` usa `_parse_libreria_habilidad()` y `_render_habilidad_text_libreria()`

Aunque ambos comparten parte de la infraestructura de cajas y métricas, el parser y el rasterizado del contenido no son iguales. Eso produce diferencias visibles en:

- reglas de formato del texto
- line breaking
- espaciado vertical
- composición de símbolos inline
- dibujo final dentro del cuadro

## Chosen Approach

Eliminar la bifurcación funcional de `habilidad` por tipo de carta y usar el mismo pipeline de `cripta` también para `libreria`.

Eso implica:

- `libreria` deja de usar un renderer propio para `habilidad`
- `libreria` pasa a usar `_parse_habilidad()` y `_render_habilidad_text()`
- el renderer específico de `libreria` se elimina o se deja como wrapper trivial sin comportamiento propio

Con este enfoque, la semántica del texto y su dibujo pasan a estar definidos por una sola fuente de verdad.

## Explicit Behavioral Change

El contrato de marcado del texto de `libreria` cambia:

- `**texto**` deja de tener significado especial
- el texto de `libreria` pasa a obedecer exactamente las reglas de `cripta`

Esto es una consecuencia deliberada del objetivo de igualdad total entre ambos tipos de carta.

## What Stays the Same

No cambia:

- `used_hab_box`
- el cálculo de altura dinámica del cuadro
- el origen y tamaño del cuadro de habilidad del layout
- color, opacidad, padding, radius y line spacing configurados por layout
- el resto de capas de la carta (`clan`, `senda`, `disciplinas`, `simbolos`, `coste`, `cripta`, `ilustrador`)

El cambio afecta sólo al contenido y dibujo del bloque de `habilidad`.

## Implementation Shape

La unificación se hará en tres niveles:

1. Render principal:
   - quitar la bifurcación `if card_type == 'libreria'` para `habilidad`
   - llamar siempre a `_render_habilidad_text()`

2. Parser/render específicos de librería:
   - retirar la dependencia funcional de `_parse_libreria_habilidad()` y `_render_habilidad_text_libreria()`
   - si se mantienen, que sea sólo por compatibilidad interna y sin comportamiento distinto

3. Tests:
   - actualizar las regresiones que asumían un renderer distinto para `libreria`
   - añadir cobertura para comprobar que, con mismos parámetros, `cripta` y `libreria` siguen el mismo render de habilidad

## Error Handling

- Si el texto es vacío, el comportamiento seguirá el del pipeline común actual.
- Si el cuadro tiene altura fija, el centrado vertical seguirá el del renderer común.
- Los símbolos inline ya soportados por el motor seguirán funcionando también en `libreria` porque el flujo común ya los entiende.

## Testing

Añadir o ajustar cobertura para:

- confirmar que `libreria` usa el mismo renderer de `habilidad` que `cripta`
- confirmar que el origen del cuadro y el centrado vertical siguen correctos
- proteger la desaparición de la semántica `**texto**` como comportamiento especial de librería

La verificación final debe correr al menos:

- `apps.srv_textos.tests`
- una regresión amplia con `apps.layouts.tests` y `apps.mis_cartas.tests`
