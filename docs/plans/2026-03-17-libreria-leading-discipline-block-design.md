# Libreria Leading Discipline Block Design

## Goal

Hacer que, en cartas de librería, las líneas de `habilidad` que empiezan con un bloque de disciplinas como `[obl] or [tha]` o `[OBL] or [THA]` reserven toda esa anchura inicial en la columna izquierda y dejen el texto descriptivo alineado después de ese bloque.

## Constraints

- El comportamiento nuevo aplica sólo a `libreria`.
- `cripta` debe mantener el comportamiento actual.
- El conector reconocido es únicamente `or` en minúsculas.
- El bloque inicial puede contener:
  - uno o más símbolos de disciplina inline
  - espacios
  - `or`
- Si no aparece `or`, el bloque puede estar formado sólo por dos símbolos seguidos al inicio.
- El texto que sigue al bloque debe mantener la misma sangría al hacer wrap.

## Decision

Resolveremos esta maqueta en el motor de wrap/render de `habilidad`, no en el parser básico de símbolos.

La columna izquierda ya existe para el caso simple de una línea que empieza con una disciplina. Ahora ampliaremos esa idea para que, sólo en librería, el “prefijo de disciplinas” pueda ser un bloque compuesto por varios tokens iniciales.

## Approach

- Detectar, al construir o envolver líneas de `habilidad`, si una línea de librería empieza con un bloque de disciplinas.
- Ese bloque se considerará una unidad visual para la columna izquierda.
- El ancho reservado será la suma de:
  - símbolos de disciplina
  - espacios
  - el texto `or`
- El resto de la línea empezará después de esa anchura.
- Si la línea hace wrap, la continuación conservará la misma sangría colgante.

## Non-Goals

- No cambiaremos `cripta`.
- No convertiremos `OR` o `Or` en conectores válidos.
- No cambiaremos el parser general de cursivas/negritas.
- No introduciremos una gramática especial para cualquier palabra entre disciplinas; sólo `or`.

## Testing

Añadir cobertura para:

1. Librería con bloque inicial compuesto
- `[obl] or [tha] Texto...`
- `[OBL] or [THA] Texto...`

2. Librería con símbolos seguidos sin `or`
- prefijo inicial de dos símbolos inline

3. Wrap con sangría
- una línea larga con prefijo compuesto mantiene la continuación alineada con el texto, no con el bloque de disciplinas

4. Compatibilidad
- `OR` no activa esta regla
- `cripta` no cambia

## Important Note

El ajuste debe entrar en la lógica que calcula la sangría inicial de línea, no en un postproceso de dibujo, para que el layout del texto siga siendo coherente con el wrapping real.
