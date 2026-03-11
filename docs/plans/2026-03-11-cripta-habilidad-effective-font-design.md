# Diseno De Cripta Habilidad Effective Font

**Fecha:** 2026-03-11

**Objetivo**

Hacer que el recuadro de habilidad en la app cripta ajuste su altura al espacio real ocupado por el texto, usando el tamano de fuente efectivo del render (`hab_font_size`) en lugar del `font_size` fijo guardado en el layout.

**Problema Actual**

La altura dinamica de `habilidad` se calcula en `apps/srv_textos/views.py` con `lh['font_size']`, pero en la app cripta el texto real se renderiza con `hab_font_size` enviado desde el slider. Eso hace que el texto cambie de tamano dentro del fondo, mientras el recuadro reservado al texto no responde con la misma logica.

**Decision**

- Mantener `dynamic_habilidad_from_bottom` solo para el flujo de cripta.
- Recalcular la altura dinamica de `used_box` con el tamano de fuente efectivo del render cuando ese flujo este activo.
- Fuera de ese contexto, mantener el comportamiento actual del layout editor y del resto de renderizados.

**Enfoque Tecnico**

1. Pasar `hab_font_size` hasta `_compute_layout_metrics()`.
2. Elegir `effective_hab_font_size`:
   - `hab_font_size` si el render dinamico de cripta esta activo.
   - `lh['font_size']` en el resto de casos.
3. Usar ese tamano para `_compute_habilidad_dynamic_height()`.
4. Cubrir el cambio con tests especificos de altura dinamica en cripta.

**Compatibilidad**

- No cambia el schema del layout.
- No afecta al editor de layouts.
- No cambia libreria.
