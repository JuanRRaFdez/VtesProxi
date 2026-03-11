# Diseno De Layout Preview Libreria Reference Symbols

**Fecha:** 2026-03-11

**Objetivo**

Hacer que el preview fijo del editor de layouts para `libreria` muestre referencias visuales de clan, senda y disciplinas, igual que el preview fijo de `cripta`, sin afectar al render real de cartas de libreria.

**Problema Actual**

El preview de `libreria` en `apps/layouts/views.py` solo aporta la carta fija `.44 Magnum` y sus `simbolos`. Eso deja sin referencias visuales para cajas que dependan de clan, senda o disciplinas al ajustar el layout en el editor.

**Decision**

- Aplicar overrides solo en `/layouts/api/preview`.
- Mantener el render real de `libreria` sin defaults artificiales.
- Copiar el patron de `cripta`, donde el preview fijo puede forzar activos visuales solo para la previsualizacion del editor.

**Enfoque Tecnico**

1. Extender `FIXED_LAYOUT_PREVIEWS['libreria']` con:
   - `clan = 'gangrel.png'`
   - `path = 'death.png'`
   - `disciplinas = [{'name': 'ofu', 'level': 'inf'}, {'name': 'dom', 'level': 'inf'}, {'name': 'tha', 'level': 'inf'}]`
2. En `api_preview()`, resolver `clan`, `senda` y `disciplinas` desde `preview` antes que desde `preview_payload`.
3. Mantener `simbolos` desde el payload real de `.44 Magnum`.
4. Cubrirlo con una prueba que asegure que `_render_carta_from_path()` recibe esos overrides solo en el preview de `libreria`.

**Compatibilidad**

- No cambia el schema de layouts.
- No toca la app `libreria`.
- No altera el render final de cartas ni el autocomplete.
