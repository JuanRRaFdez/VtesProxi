# Diseno De Disciplinas Fixed Bottom

**Fecha:** 2026-03-12

**Objetivo**

Permitir que la capa `disciplinas` tenga un modo fijo en el editor de layouts para que la posicion vertical de los iconos deje de depender del recuadro de `habilidad`, usando el borde inferior del recuadro como referencia del borde inferior del icono mas bajo.

**Problema Actual**

El motor recalcula siempre la posicion vertical de `disciplinas` desde `used_hab_box`, asi que la columna de iconos responde al crecimiento del texto de `habilidad`. Eso impide fijar manualmente el arranque vertical de las disciplinas en layouts donde la referencia visual debe ser estable.

**Decision**

- Mantener el comportamiento actual como modo por defecto.
- Anadir un modo `fixed_bottom` solo para `disciplinas`.
- Exponerlo en el panel derecho como un checkbox "Fijar simbolos".
- Reutilizar `disciplinas.rules.anchor_mode` para persistir el estado, sin introducir otro campo paralelo.

**Semantica Del Recuadro**

- Borde izquierdo: coordenada `x` de la columna de iconos.
- Borde derecho: tamano del icono.
- Borde superior: separacion entre iconos.
- Borde inferior: referencia vertical.

En modo normal:
- El borde inferior sigue siendo responsivo al recuadro efectivo de `habilidad`.
- La columna se recoloca cuando `habilidad` crece o sube.

En modo `fixed_bottom`:
- El motor deja de reanclar `disciplinas` a `used_hab_box`.
- El borde inferior del recuadro pasa a representar el borde inferior del icono mas bajo.
- Los iconos se apilan desde abajo hacia arriba.
- `width` sigue definiendo el tamano del icono.
- `height` sigue definiendo la separacion vertical entre iconos.

**Enfoque Tecnico**

1. Validar `disciplinas.rules.anchor_mode = 'fixed_bottom'`.
2. En el editor:
   - anadir checkbox solo util para la capa `disciplinas`,
   - leer/escribir ese valor en `section.rules.anchor_mode`,
   - desactivar el selector `Anchor` general para esa capa para evitar conflicto de UI.
3. En `_compute_layout_metrics()`:
   - mantener el calculo actual del `disc_box`,
   - solo aplicar el reanclaje a `used_hab_box` cuando `anchor_mode != 'fixed_bottom'`.
4. Mantener el render de apilado de abajo hacia arriba ya existente.

**Compatibilidad**

- No cambia el schema de layout.
- Los layouts existentes siguen funcionando porque `anchor_mode` por defecto sigue siendo `free`.
- El cambio no afecta a `simbolos`, `coste`, `ilustrador` ni al render real fuera de la capa `disciplinas`.
