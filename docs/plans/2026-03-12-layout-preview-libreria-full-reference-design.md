# Diseno De Layout Preview Libreria Full Reference

**Fecha:** 2026-03-12

**Objetivo**

Hacer que el preview fijo del editor de layouts para `libreria` muestre una carta de referencia completa con todas las capas visuales relevantes: nombre, clan, coste, disciplinas, texto, ilustrador y simbolos `action` y `equipment`.

**Problema Actual**

El preview fijo de `libreria` solo forzaba algunas referencias visuales parciales. Eso deja el editor sin una muestra estable de todas las capas que realmente se quieren ajustar al crear un layout de libreria.

**Decision**

- Mantener el cambio solo en `/layouts/api/preview`.
- Seguir usando la imagen base fija de libreria ya existente.
- Forzar un payload completo de referencia desde `FIXED_LAYOUT_PREVIEWS['libreria']`.
- No tocar la creacion real de cartas de libreria ni el autocomplete del catalogo.

**Enfoque Tecnico**

1. Extender `FIXED_LAYOUT_PREVIEWS['libreria']` con overrides para:
   - `nombre`
   - `clan`
   - `coste`
   - `disciplinas`
   - `habilidad`
   - `simbolos`
   - `illustrator`
2. En `api_preview()`, resolver esos campos desde `preview` antes que desde `preview_payload`.
3. Mantener la imagen fija `.44 Magnum` solo como base visual de fondo.
4. Cubrirlo con un test que demuestre que el preview del editor ya no depende del payload real del catalogo para esas capas.

**Compatibilidad**

- No cambia el render real de cartas de libreria.
- No cambia el schema de layouts.
- No afecta a la app `libreria/importar-imagen/`.
