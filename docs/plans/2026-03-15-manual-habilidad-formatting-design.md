# Manual Habilidad Formatting Design

## Goal

Cambiar el formato de `habilidad` en `cripta` y `libreria` para que el estilo dependa solo de marcas explicitas escritas por el usuario, sin reglas automaticas del motor.

## Approved Formatting Rules

El comportamiento final sera:

- texto normal por defecto
- `**texto**` -> negrita
- `(texto)` -> cursiva
- los propios parentesis se muestran en cursiva junto con su contenido
- no existira ya formato automatico por `:`, `+` ni por ausencia de `:`

Esto aplica igual a `cripta` y `libreria`.

## Current Problem

Hoy el motor usa dos caminos distintos:

- `cripta` usa `_parse_habilidad()` con reglas automaticas:
  - hasta `:` en bold
  - parentesis en italic
  - cola final desde `+` en bold
- `libreria` usa `_parse_libreria_habilidad()`:
  - `** **` para bold
  - parentesis tratados aparte

Eso provoca dos problemas:

1. el texto de base de `cripta` aparece en negrita aunque el usuario no lo haya pedido
2. el comportamiento no es consistente entre `cripta` y `libreria`

## Parser Design

Se unifica el parseo de `habilidad` en un unico flujo comun.

### Reglas del parser

- cualquier texto fuera de marcas -> `normal`
- cualquier bloque entre `**` -> `bold`
- cualquier bloque entre parentesis -> `italic`

### Combinacion de estilos

Si un bloque bold contiene un parentesis, el contenido entre parentesis se renderiza en cursiva mientras el resto del bloque sigue en negrita.

En la practica:

- `**Titulo (nota)**`
  - `Titulo ` -> bold
  - `(nota)` -> italic

No se pretende soportar markdown complejo ni anidaciones arbitrarias fuera de este caso sencillo.

## Inline Symbols

Los simbolos inline ya soportados entre corchetes, por ejemplo `[dom]` o `[DOM]`, no cambian.

El parser de estilo debe seguir delegando en el flujo de tokens que ya resuelve:

- disciplinas inferiores y superiores
- simbolos especiales inline

Es importante que el cambio de formato no rompa esa funcionalidad.

## UI Changes

En la pantalla compartida de creacion (`apps/cripta/templates/cripta/importar_imagen.html`) se anadira una toolbar simple para el textarea de `habilidad`.

Botones:

- `B`: envuelve la seleccion con `**...**`
- `I`: envuelve la seleccion con `(...)`

Comportamiento:

- si hay texto seleccionado, se envuelve
- si no hay seleccion, se inserta el par vacio y el cursor queda dentro
- despues de insertar marcas, se relanza el render de habilidad para feedback inmediato

## Scope

Este cambio toca:

- parser/render de `habilidad` en `apps/srv_textos/views.py`
- tests de parser/render en `apps/srv_textos/tests.py`
- UI compartida de creacion en `apps/cripta/templates/cripta/importar_imagen.html`

No toca:

- layouts
- cajas o posiciones de habilidad
- simbolos inline de disciplina

## Compatibility

Consecuencia deliberada:

- textos antiguos que dependian de negritas automaticas por `:` o `+` dejaran de verse en negrita

Eso es correcto segun el objetivo aprobado: el motor ya no decide estilos por su cuenta.

Los parentesis seguiran renderizando en cursiva, lo que ademas coincide con la convencion original de las cartas.

## Testing

Se necesita cubrir:

### Parser / tokens

- texto plano -> todo `normal`
- `**texto**` -> `bold`
- `(texto)` -> `italic`
- `**texto (nota)**` -> bold con tramo italic dentro del parentesis
- `**texto** [dom]` -> mantiene simbolos inline

### Render

- `cripta` y `libreria` usan el mismo parser comun
- el renderer ya no aplica negritas automaticas por `:` ni `+`

### UI

- existen botones `B` e `I`
- el helper JS envuelve seleccion con `**...**` y `(...)`

## Files Expected To Change

- `apps/srv_textos/views.py`
- `apps/srv_textos/tests.py`
- `apps/cripta/templates/cripta/importar_imagen.html`
