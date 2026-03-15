# Inline Discipline Symbols Design

## Goal

Permitir que el texto de habilidad en cartas de `cripta` y `libreria` renderice simbolos de disciplina embebidos a partir de marcadores entre corchetes.

## Syntax

- `[dom]` renderiza el simbolo de disciplina inferior desde `static/disc_inf/dom.*`
- `[DOM]` renderiza el simbolo de disciplina superior desde `static/disc_sup/dom.*`

La sintaxis distingue el nivel por mayusculas completas del codigo.

## Current State

El motor de texto ya soporta iconos embebidos dentro del texto de habilidad. Hoy reconoce algunos simbolos especiales y los convierte en tokens `symbol` que participan correctamente en el word-wrap, el centrado y el render final.

El texto de cartas de libreria ya contiene casos reales como `[dom]`, pero ahora mismo esos patrones se dejan como texto plano porque el parser no los resuelve a iconos de disciplina.

## Chosen Approach

Extender el parser actual de tokens inline para reconocer patrones `[codigo]` y resolverlos como simbolos de disciplina, reutilizando exactamente el mismo flujo de tokens `symbol` que ya usa el render.

No se creara un segundo sistema de parseo ni un preprocesado separado. El cambio vivira en el motor común de render de habilidad para que funcione igual en `cripta` y `libreria`.

## Resolution Rules

- El contenido entre corchetes se inspecciona solo si cumple el formato esperado de codigo de disciplina.
- Si el contenido esta en minusculas, se busca en `static/disc_inf`.
- Si el contenido esta en mayusculas, se normaliza a minusculas para la ruta y se busca en `static/disc_sup`.
- Si el fichero existe, se emite un token `symbol`.
- Si no existe, el texto se deja intacto, incluidos los corchetes.

Ejemplos:

- `Gana [dom]` -> texto + icono de `disc_inf/dom`
- `Requiere [DOM]` -> texto + icono de `disc_sup/dom`
- `Texto [xyz] raro` -> se mantiene como texto literal si no hay icono

## Rendering Behavior

- Los simbolos inline usaran la escala actual de iconos embebidos del texto.
- Participaran en el calculo de anchura de linea y en el word-wrap.
- Seguiran el mismo centrado horizontal y vertical que ya aplica el motor de texto.
- No se modificara la logica de columnas de disciplinas de la carta; esto es solo para iconos dentro del texto.

## Scope

Aplica a:

- `_render_habilidad_text()` para `cripta`
- `_render_habilidad_text_libreria()` para `libreria`

No aplica a otros campos como `nombre`, `ilustrador` o `cripta`.

## Error Handling

- Un marcador invalido o desconocido no debe romper el render.
- Si no hay archivo para el codigo detectado, el marcador se conserva como texto literal.
- Si el token mezcla mayusculas y minusculas, no se interpretara como simbolo especial salvo que el helper decida normalizarlo explicitamente; por simplicidad, el contrato soportado sera minusculas completas para inferior y mayusculas completas para superior.

## Testing

Se añadira cobertura para:

- `cripta`: `[dom]` genera token de `disc_inf/dom`
- `cripta`: `[DOM]` genera token de `disc_sup/dom`
- `libreria`: mismo comportamiento
- un marcador desconocido como `[xyz]` permanece como texto

La cobertura ideal toca el nivel de tokens/parsing para evitar tests graficos fragiles y, si hace falta, una regresion ligera sobre el render para confirmar que no se rompe el flujo existente.
