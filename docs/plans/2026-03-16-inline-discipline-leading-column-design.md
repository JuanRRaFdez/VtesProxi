# Inline Discipline Leading Column Design

## Goal

Hacer que las lineas de `habilidad` que empiezan por un simbolo de disciplina inline, como `[aus] texto...`, se rendericen con una columna invisible reservada para el simbolo y una columna de texto alineada a la izquierda.

## Problem

- El renderer comun de `habilidad` centra cada linea completa como un solo bloque.
- Cuando una linea empieza por `[aus]`, `[cel]`, `[for]` o similar, el simbolo y el texto se centran juntos.
- Eso no reproduce el formato clasico de muchas cartas de libreria, donde el simbolo vive en su propia columna y el texto queda alineado despues de ese hueco.

## Decision

Solo las lineas cuyo primer token visible sea un simbolo de disciplina inline entraran en un modo de maquetacion de dos columnas:

- columna izquierda para el icono
- columna derecha para el texto

El resto del texto seguira usando el layout actual.

## Approach

- Mantener el parser y la tokenizacion actuales de simbolos inline.
- Detectar, despues del wrap, cuando una linea empieza por un token `symbol`.
- Para esas lineas:
  - reservar un ancho fijo de columna basado en el tamano del icono y su separacion
  - dibujar el icono pegado a la izquierda de la caja de contenido
  - dibujar el texto en una segunda columna, alineado a la izquierda
- Si el texto de esa linea necesita varias lineas visuales, las continuaciones deben arrancar en la misma columna de texto, no debajo del icono.
- El parrafo anterior o cualquier otra linea sin simbolo inicial seguira comportandose como ahora.

## Scope

- Se aplica al renderer comun de `habilidad`, asi que afecta igual a `cripta` y `libreria`.
- Solo se activa cuando el simbolo esta al principio de la linea renderizada.
- No se introduce sintaxis nueva.
- No cambia el comportamiento de simbolos inline en mitad de una frase.

## Testing

- Anadir un test rojo que demuestre que una linea `[aus] texto...` deja libre una columna para el icono y coloca el texto a la derecha.
- Anadir un test para garantizar que una linea normal sin simbolo inicial sigue centrada como antes.
- Anadir un test para un caso con wrap donde la continuacion de la linea disciplinar arranca alineada con la columna de texto.
