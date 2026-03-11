# Diseno: Layout Box Engine v2 para editor visual

## Estado
Aprobado por usuario.

## Objetivo
Evolucionar el sistema de layouts para que los elementos se definan por recuadros (`box`) editables en el editor visual, con reglas de render configurables por usuario. El foco principal es mejorar control y legibilidad de `nombre`, `ilustrador`, `habilidad`, `simbolos` y `disciplinas` sin romper compatibilidad con layouts legacy.

## Requisitos validados
- `nombre` e `ilustrador` deben renderizarse siempre dentro de su recuadro reservado.
- Alineacion horizontal configurable por usuario para ambos: `left | center | right`.
- Defaults de alineacion:
  - `nombre`: `center`
  - `ilustrador`: `left`
- Comportamiento de overflow de texto configurable por usuario.
- Default de overflow:
  - reducir fuente automaticamente hasta un minimo
  - si no cabe, truncar con `...`
- El motor anti-solape debe considerar todos los elementos cuando `habilidad` crece (no solo algunos).
- `simbolos` y `disciplinas` deben ajustar tamano para ocupar el maximo espacio util de su recuadro.
- En `disciplinas`, el recuadro horizontal controla tamano; el vertical controla separacion/stack.
- `habilidad` se define por limites horizontales y anclaje inferior; su altura es dinamica segun contenido.

## Enfoque aprobado
Opcion 2: **Motor de layout por cajas + reglas de flujo**.

Se define un schema `config` v2 con `box` por elemento y reglas de comportamiento. El render de `srv_textos` pasa a calcular metricas por etapa (layout base -> crecimiento de habilidad -> anti-solape -> render final). El editor visual expone propiedades por elemento para alinear, overflow, anclaje y ajustes de caja.

## Arquitectura funcional

### 1) Schema v2 por elemento
Cada elemento editable tendra:
- `box`: `{x, y, width, height}`
- `rules`: propiedades de comportamiento (alineacion, anclaje, overflow, etc).

Campos clave:
- `nombre.rules.align`, `ilustrador.rules.align`: `left|center|right`
- `nombre.rules.autoshrink_enabled`, `ilustrador.rules.autoshrink_enabled`: `bool`
- `nombre.rules.min_font_size`, `ilustrador.rules.min_font_size`: `int`
- `nombre.rules.ellipsis_enabled`, `ilustrador.rules.ellipsis_enabled`: `bool`
- `nombre.shadow.enabled` editable (reborde/sombra negro on/off)
- `rules.anchor_mode` en elementos movibles: `free|top_locked|bottom_locked`

### 2) Compatibilidad legacy
- Si un layout guardado no incluye `box`, se normaliza internamente desde campos legacy (`x`, `y`, `size`, `bottom`, ratios, etc).
- El usuario puede seguir cargando layouts anteriores sin romper render ni editor.

### 3) Render por etapas
- Etapa A: normalizar config a v2.
- Etapa B: calcular metricas base por elemento.
- Etapa C: calcular altura real de `habilidad` segun texto.
- Etapa D: resolver colisiones globales moviendo elementos hacia arriba segun prioridad.
- Etapa E: render final.

### 4) Politica anti-solape
- Solape detectado por interseccion de cajas 2D + `collision_gap`.
- Si `habilidad` crece, se empujan elementos hacia arriba en orden:
  1. `disciplinas`, `simbolos`
  2. `coste`
  3. `cripta`
  4. `ilustrador`
  5. `clan`, `senda`
  6. `nombre` (ultima opcion)
- Se respetan anclajes en lo posible; si no hay espacio fisico se hace clamp y se emite warning de preview.

### 5) Texto en caja (`nombre` / `ilustrador`)
- Se calcula ancho util de caja.
- Se aplica alineacion horizontal dentro del box.
- Si no cabe:
  1. reducir fuente hasta `min_font_size`
  2. si aun no cabe y `ellipsis_enabled`, truncar con `...`
- Resultado: texto siempre dentro de su caja.

### 6) Simbolos y disciplinas en caja
- Escalado automatico para ocupar el maximo posible sin salir del box.
- `disciplinas`: tamano ligado al ancho del box y separacion al alto disponible.
- `simbolos`: iconos adaptados al box y espaciado calculado.

## Cambios de UI (editor)
- El recuadro visual representa el `box` real de cada elemento.
- El panel de propiedades anade:
  - `align` (nombre/ilustrador)
  - `autoshrink`, `min_font_size`, `ellipsis`
  - `shadow.enabled` en `nombre`
  - `anchor_mode` en elementos con desplazamiento automatico
- Guardado sigue usando `POST /layouts/api/update-config`.

## Impacto en API y servicios
- `apps/layouts/services.py`:
  - normalizador legacy -> v2
  - validacion de `box` y enums
- `apps/srv_textos/views.py`:
  - helpers de texto en caja
  - helpers de iconos en caja
  - motor de colisiones

## Testing
- `apps/layouts/tests.py`:
  - validacion schema v2
  - normalizacion legacy
  - controles de template/editor
- `apps/srv_textos/tests.py`:
  - texto en caja + align + overflow
  - crecimiento de habilidad + anti-solape global
  - disciplinas/simbolos ajustados a box
  - regresion de prioridad de resolucion de layout

## Riesgos y mitigaciones
- Riesgo: complejidad de colisiones en todos los elementos.
  - Mitigacion: resolver desde config base en cada render (sin acumulacion), reglas simples y testeables.
- Riesgo: ruptura de layouts guardados antiguos.
  - Mitigacion: normalizador legacy obligatorio + tests de compatibilidad.
- Riesgo: UX del editor demasiado cargada.
  - Mitigacion: mostrar propiedades segun elemento seleccionado.

## Criterio de exito
Un usuario puede editar cajas y reglas de cada elemento, guardar layout, y renderizar cartas donde:
- nombre/ilustrador siempre quedan dentro de su box,
- simbolos/disciplinas aprovechan su box,
- habilidad crece dinamicamente sin solapar elementos finales.
