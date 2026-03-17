# Directed Inline Symbol Design

## Goal

Hacer que el token exacto `(D)` dentro del texto de `habilidad` se renderice como el icono `directed.png` tanto en cartas de `cripta` como de `libreria`.

## Constraints

- Sólo debe activarse para `(D)` exacto, en mayúsculas.
- El resto de paréntesis debe seguir funcionando como hasta ahora:
  - texto normal
  - cursiva por convención original
- Debe integrarse con el sistema actual de símbolos inline:
  - disciplinas inferiores `[dom]`
  - disciplinas superiores `[DOM]`

## Decision

Resolveremos `(D)` como un símbolo inline especial en el mismo parser que ya usa el render de `habilidad`.

No añadiremos un segundo pipeline ni haremos sustituciones tardías en el render.

## Approach

- Ampliar `_inline_symbol_path()` para reconocer `(D)` como marcador especial.
- Reutilizar la resolución existente de iconos especiales, que ya contempla `directed.png`.
- Mantener intacto el tratamiento del resto de paréntesis.

Con esto:
- `cripta` y `libreria` heredarán el comportamiento automáticamente
- el wrapping y la alineación seguirán usando el mismo motor
- la columna especial de líneas que empiezan con disciplinas no se verá afectada

## Testing

Añadir cobertura para:

1. Parser inline
- `(D)` se resuelve a `directed`
- `(rapida)` no se convierte en símbolo

2. Render de `habilidad`
- `cripta` carga `directed.png` cuando aparece `(D)`
- `libreria` carga `directed.png` cuando aparece `(D)`

## Important Note

Este cambio debe entrar por el parser inline, no por una excepción ad hoc en el dibujado, para no romper el layout de línea ni el wrapping existente.
