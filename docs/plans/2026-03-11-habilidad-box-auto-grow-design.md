# Diseno De Habilidad Box Auto Grow

**Fecha:** 2026-03-11

**Objetivo**

Hacer que cualquier layout con `habilidad.box` use un cuadro de habilidad con borde inferior fijo, altura responsiva al contenido y crecimiento hacia arriba. Ademas, el bloque de texto debe quedar centrado verticalmente dentro del recuadro efectivo.

**Contexto Actual**

El motor de render de [`apps/srv_textos/views.py`](/home/juanrrafdez/VtesProxi/apps/srv_textos/views.py) ya calcula una altura dinamica para habilidad, pero cuando existe `habilidad.box` esa altura efectiva queda limitada por `box.height`. El resultado es un cuadro que no crece todo lo necesario y un texto que se dibuja con sesgo hacia la parte superior del fondo.

**Decision**

Para cualquier layout con `habilidad.box`:

- `box` seguira siendo la caja base persistida en el layout.
- El borde inferior efectivo se fijara en `box.y + box.height`.
- La altura real del render se calculara a partir del texto, el padding y el line spacing.
- `used_box` sera la caja efectiva renderizada: misma `x`, mismo `width`, borde inferior fijo y `y` recalculada hacia arriba.
- Si el crecimiento empuja la caja por encima de `y = 0`, se limitara a `0`.
- El texto se centrara verticalmente dentro del `used_box`.

Los layouts legacy sin `habilidad.box` mantendran la logica actual.

**Enfoque Tecnico**

1. Ajustar `_compute_layout_metrics()` para que `habilidad.box` no actue como limite de altura y para que `used_box` crezca hacia arriba manteniendo fijo el borde inferior.
2. Ajustar los helpers `_render_habilidad_text()` y `_render_habilidad_text_libreria()` para calcular la altura real del contenido y centrarlo verticalmente cuando reciben `box_height`.
3. Mantener el uso de `used_box` en colisiones y anclajes para que disciplinas, cripta y otras capas reaccionen a la caja efectiva.
4. Actualizar la cobertura de tests para reflejar el nuevo contrato.

**Compatibilidad**

- No se introduce nueva configuracion de layout.
- No cambia el schema persistido.
- El editor sigue guardando `habilidad.box` con la misma estructura.
- El cambio aplica a preview y render final porque se hace en el motor comun.

**Pruebas Previstas**

- Verificar que un texto largo con `habilidad.box` hace crecer `used_box.height`.
- Verificar que el borde inferior de `used_box` coincide con el borde inferior de `box`.
- Verificar que `used_box.y` se limita a `0` cuando el texto necesita mas altura que la disponible.
- Verificar que el render de habilidad centra verticalmente el contenido dentro del recuadro efectivo.
