# Diseno De Cripta Habilidad Bottom Anchor

**Fecha:** 2026-03-11

**Objetivo**

Limitar el ajuste dinamico del cuadro de habilidad al flujo de creacion y preview de cartas de cripta desde `apps/cripta`, usando solo el borde inferior persistido del `habilidad.box`. El borde superior se recalculara en render a partir del texto real.

**Problema Actual**

El motor comun de `apps/srv_textos/views.py` recalcula `used_box` para cualquier render que use `habilidad.box`. Eso extiende el comportamiento dinamico a contextos que no lo necesitan y vuelve ambiguo el contrato del layout.

**Decision**

- Se anade una senal explicita de contexto de render: `dynamic_habilidad_from_bottom`.
- Solo cuando esa senal venga activa desde el flujo de cripta y `card_type == 'cripta'`:
  - el borde inferior efectivo de habilidad sera `habilidad.box.y + habilidad.box.height`,
  - `habilidad.box.y` dejara de actuar como borde superior persistido,
  - el borde superior efectivo se recalculara con la altura real del texto.
- Fuera de ese contexto, el motor respetara el `habilidad.box` persistido normal.
- El texto seguira centrado verticalmente dentro del recuadro efectivo.

**Enfoque Tecnico**

1. Pasar `dynamic_habilidad_from_bottom` desde `apps/cripta/templates/cripta/importar_imagen.html` a los endpoints de render.
2. Propagar la bandera a `_render_carta()` y `_compute_layout_metrics()`.
3. En `_compute_layout_metrics()`, aplicar el recalc de `used_box` solo cuando la bandera este activa para cripta.
4. Mantener el resto del motor sin cambios de contrato.

**Compatibilidad**

- No cambia el schema persistido de layouts.
- No afecta a libreria.
- No afecta a otros usos de preview/render que no vengan de la app cripta con la bandera activa.

**Pruebas Previstas**

- El flujo con bandera activa en cripta ignora el borde superior persistido y usa solo el borde inferior.
- Sin bandera, el `habilidad.box` se respeta como caja fija normal.
- Los endpoints de render aceptan y propagan la nueva bandera.
