# Diseno: Recuadros visibles en el editor de layouts

## Estado
Aprobado por usuario.

## Objetivo
Hacer que los recuadros del editor de `/layouts/` sean claramente visibles en todo momento y que cada capa muestre una etiqueta legible para identificarla al maquetar.

## Requisitos validados
- Todos los recuadros deben verse siempre, no solo el seleccionado.
- La capa activa debe resaltar mas que el resto.
- Cada recuadro debe mostrar una etiqueta con su nombre.
- La mejora aplica al editor de layouts.
- No se cambia el modelo de datos ni el comportamiento del render real de cartas.

## Enfoque aprobado
- Mantener el sistema actual de overlays en `static/layouts/editor.js`.
- Mejorar su apariencia visual en `static/layouts/editor.css`.
- Inyectar una etiqueta por capa desde el frontend al crear cada overlay.

## Arquitectura funcional

### 1) Visibilidad permanente de overlays
- Todas las capas del editor tendran siempre un borde visible.
- Tambien tendran un fondo translcido muy ligero para separar el recuadro de la ilustracion.
- Se anadira una sombra suave para mejorar el contraste sobre fondos claros y oscuros.

### 2) Estado activo reforzado
- La capa seleccionada tendra un borde mas grueso y un color mas intenso.
- Tambien tendra una sombra/glow adicional y un `z-index` superior.
- Esto permite localizar instantaneamente la capa activa sin perder de vista el resto.

### 3) Etiquetas de capa
- Cada recuadro mostrara una etiqueta con el nombre de la capa.
- La etiqueta sera una pill compacta situada en la esquina superior izquierda del recuadro, ligeramente por fuera del borde.
- La etiqueta no debe impedir la interaccion de drag/resize del recuadro.

### 4) Compatibilidad
- No se alteran `layout_config`, validaciones ni endpoints.
- La identificacion de la etiqueta se basa en `layerName`, ya disponible en el frontend.
- La mejora es puramente de presentacion e identificacion visual.

## Testing
- `apps/layouts/tests.py`
  - comprobar que el script del editor crea la etiqueta de capa
  - comprobar que la hoja de estilos contiene las clases de visibilidad/etiqueta necesarias
- Se mantiene la suite actual del editor para asegurar que no se rompe el flujo de preview y configuracion.

## Riesgos y mitigaciones
- Riesgo: demasiado ruido visual en pantallas pequenas.
  - Mitigacion: usar relleno muy suave y etiquetas compactas.
- Riesgo: la etiqueta interfiera con el drag.
  - Mitigacion: `pointer-events: none` en la etiqueta.
- Riesgo: el recuadro activo tape otros overlays.
  - Mitigacion: subir solo ligeramente el `z-index` del activo.

## Criterio de exito
- Al abrir `/layouts/`, todas las capas son localizables a simple vista.
- La capa activa se distingue claramente del resto.
- El usuario puede identificar cada recuadro por su etiqueta sin depender del panel lateral.
