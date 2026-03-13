# Diseno: Semantica de anclaje para disciplinas en cripta

## Estado
Aprobado por usuario.

## Objetivo
Redefinir `disciplinas.box` en cartas de `cripta` para que deje de actuar como contenedor visual y pase a describir un ancla geometrica estable: posicion del icono inferior, tamano del icono y paso fijo entre disciplinas.

## Requisitos validados
- El cambio aplica a `cripta`.
- `disciplinas.box` no representa un contenedor.
- `box.x` marca el borde izquierdo del icono inferior.
- `box.y` marca el borde inferior del icono inferior.
- `box.width` marca el tamano del icono, sin deformarlo.
- `box.height` marca la distancia vertical fija entre disciplinas.
- Esa distancia no debe cambiar segun haya 2, 3 o 6 disciplinas.
- El checkbox `fixed_bottom` solo controla si la posicion vertical depende del bloque de `habilidad`.
- Cuando `fixed_bottom` este apagado, el icono inferior debe anclarse con una distancia fija respecto a `habilidad`.

## Enfoque aprobado
- Mantener `disciplinas.box` como interfaz de edicion en el editor.
- Cambiar su semantica en `cripta` para que represente `ancla + tamano + paso`.
- Introducir un offset explicito respecto a `habilidad` para el modo no fijo.

## Arquitectura funcional

### 1) Nueva semantica de `disciplinas.box` en `cripta`
- `box.x`: coordenada absoluta del borde izquierdo del icono inferior.
- `box.y`: coordenada absoluta del borde inferior del icono inferior.
- `box.width`: tamano cuadrado del icono.
- `box.height`: paso vertical constante entre iconos.

### 2) Render de disciplinas
- El numero de disciplinas solo determina cuantas se pintan.
- El tamano nunca se calcula desde el numero de iconos.
- La separacion vertical nunca se calcula desde el numero de iconos.
- Las disciplinas se apilan hacia arriba desde el icono inferior.

### 3) Modo `fixed_bottom`
- Si `anchor_mode == fixed_bottom`, se respeta `box.y` como coordenada absoluta.
- Si `anchor_mode != fixed_bottom`, el punto inferior del icono inferior se calcula usando un offset fijo respecto al borde superior de `habilidad`.
- Para ello se anade un campo explicito en reglas, propuesto como `rules.gap_from_habilidad`.
- Con `gap_from_habilidad = 0`, el borde inferior del icono inferior coincide con la parte superior de `habilidad`.

### 4) Editor de layouts
- El helper box de `disciplinas` deja de representar area ocupada.
- Pasa a representar:
  - izquierda = `x`
  - borde inferior = `y`
  - ancho = `size`
  - alto = `spacing`
- Redimensionar en horizontal cambia `box.width`.
- Redimensionar en vertical cambia `box.height`.
- Mover el helper cambia el ancla del icono inferior.

### 5) Compatibilidad
- Layouts legacy sin `box` se materializan desde `x`, `size`, `bottom` y `spacing`.
- Layouts antiguos con `box` se reinterpretan usando `size` y `spacing` ya persistidos, no la altura total del contenedor viejo.
- En modo no fijo, el gap por defecto sera `0` para preservar el comportamiento actual como base.

## Testing
- Tests de render en `apps.srv_textos.tests`
  - `box.height` no depende del numero de disciplinas
  - `box.width` controla tamano
  - `box.height` controla paso
  - `fixed_bottom` usa `box.y`
  - modo libre usa `gap_from_habilidad`
- Tests de editor/config en `apps.layouts.tests`
  - el helper de `disciplinas` guarda la nueva semantica
  - el offset a `habilidad` persiste correctamente

## Riesgos y mitigaciones
- Riesgo: romper layouts antiguos de `cripta`.
  - Mitigacion: materializar y reinterpretar datos legacy durante normalizacion.
- Riesgo: mezclar semantica vieja y nueva en editor y render.
  - Mitigacion: centralizar la conversion en servicios y metricas de render.
- Riesgo: que el checkbox actual cambie demasiado de significado.
  - Mitigacion: conservarlo como control exclusivo de dependencia respecto a `habilidad`.

## Criterio de exito
- En `cripta`, el tamano y la distancia entre disciplinas son invariantes respecto al numero de disciplinas.
- El modo libre se separa de `habilidad` con un gap fijo.
- El modo fijo respeta la coordenada absoluta del icono inferior.
