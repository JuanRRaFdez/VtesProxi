# Diseno: Capas semanticas del editor de layouts

## Estado
Aprobado por usuario.

## Objetivo
Hacer que el editor de layouts y el render final compartan reglas semanticas por capa, para que `habilidad`, `disciplinas`, `cripta`, `ilustrador`, `clan`, `senda` y `coste` se comporten como el usuario espera al crear cartas nuevas desde un layout propio.

## Requisitos validados
- `habilidad` no debe crecer fuera de la caja marcada en el layout.
- El bloque de texto debe ser responsivo al contenido dentro de la caja disponible.
- `disciplinas` debe colocarse siempre justo por encima del recuadro real de `habilidad`.
- En `disciplinas`, el eje horizontal lo decide la posicion del recuadro del layout.
- En `disciplinas`, el tamano de icono responde al ancho del recuadro.
- En `disciplinas`, la separacion vertical responde a la altura del recuadro.
- `ilustrador` tendra tamano de fuente fijo.
- `cripta` tendra tamano de fuente fijo.
- `clan`, `senda` y `coste` deben comportarse siempre como cajas cuadradas; no se podran deformar.
- `nombre` no cambia por ahora.
- Los recuadros del editor y sus etiquetas deben quedar invisibles por defecto.
- La seleccion de capas invisibles se hara haciendo clic sobre su zona, aunque el recuadro no se pinte.
- `ilustrador` y `cripta` no necesitan recuadro visible; solo ubicacion.
- `habilidad` puede usar su propio bloque de texto/fondo como referencia visual.
- `disciplinas` puede usar la silueta real de los iconos como referencia visual.
- `clan`, `senda` y `coste` pueden usar la propia silueta cuadrada del simbolo.
- La preview fija de `Mimir` debe forzar tambien la senda de Cain, usando el asset `caine.png`.
- La preview fija de `Mimir` y `.44 Magnum` seguira usando `Crafted with AI` como ilustrador.

## Enfoque aprobado
Opcion 2: perfiles semanticos por capa.

El motor de render dejara de tratar todas las cajas como rectangulos genericos y pasara a calcular metricas segun el tipo de capa. El editor dejara de dibujar overlays visibles uniformes y usara hit areas invisibles, siluetas selectivas y reglas de interaccion por capa. Con esto, la preview fija y el editor quedaran alineados con el render final en vez de depender de heuristicas distintas.

## Arquitectura funcional

### 1) Modelo semantico por capa
- `nombre`
  - se mantiene con el comportamiento actual.
- `habilidad`
  - conserva la caja del layout como limite maximo disponible.
  - calcula una `used_box` real segun el contenido renderizado dentro de ese limite.
  - no podra inflarse por fuera de la caja dibujada por el usuario.
- `disciplinas`
  - conserva `x` y `width` desde el recuadro definido en el layout.
  - calcula su `y` siempre a partir de `habilidad.used_box`.
  - su altura efectiva sigue viniendo del recuadro del layout.
- `cripta`
  - se interpreta como ancla de posicion con fuente fija.
- `ilustrador`
  - se interpreta como ancla de posicion con fuente fija.
- `clan`, `senda`, `coste`
  - quedan normalizados como cuadrados en editor y render.

### 2) Reglas de render
- `habilidad`
  - la caja del layout pasa a ser `layout_box`.
  - el render calcula una `used_box` en funcion del texto, padding y reglas de autoshrink.
  - si el contenido ocupa menos alto, la caja usada se reduce.
  - si el contenido no cabe, se reducira la fuente hasta el minimo permitido antes de truncar; no se aumentara la altura por fuera del layout.
- `disciplinas`
  - `x` y `width` siguen el recuadro del usuario.
  - `height` sigue el alto configurado por el usuario.
  - `y` sera `habilidad.used_box.y - disciplinas.height`.
  - el tamano de icono saldra del ancho de la caja.
  - la separacion vertical saldra de la altura de la caja.
- `cripta`
  - se colocara relativa a `habilidad`, pero con `font_size` fijo.
- `ilustrador`
  - seguira una caja de posicion, pero con `font_size` fijo y sin autoshrink por resize.
- `clan`, `senda`, `coste`
  - cualquier frame no cuadrado se normalizara a lado unico.

### 3) Reglas del editor
- Los recuadros y nombres de capa desaparecen como overlay visible por defecto.
- Cada capa conserva una hit area invisible para permitir seleccion y drag.
- Cuando una capa se selecciona:
  - `habilidad` mostrara el propio bloque visual.
  - `disciplinas` mostrara la silueta real apilada.
  - `clan`, `senda`, `coste` mostraran la silueta cuadrada.
  - `ilustrador` y `cripta` solo mostraran handles de seleccion.
- `clan`, `senda` y `coste` usaran resize bloqueado a proporcion 1:1.
- `ilustrador` y `cripta` podran limitarse a mover posicion, o mantener un frame interno no visible solo para seleccion; en ambos casos su tamano de fuente no cambiara.
- El panel lateral seguira siendo la referencia textual de la capa seleccionada.

### 4) Persistencia y validacion
- La configuracion guardada seguira siendo JSON del layout.
- No hace falta un nuevo modelo en BD.
- Se anadiran metadatos y normalizaciones para que:
  - capas cuadradas se guarden cuadradas.
  - capas con tamano de fuente fijo no deriven `font_size` desde el resize.
  - `disciplinas` no use una posicion vertical libre si existe `habilidad`.
- La validacion del layout seguira rechazando valores fuera de rango.

### 5) Preview fija
- `cripta`
  - nombre: `Mimir`
  - imagen base: `static/layouts/images/Mimir.png`
  - senda forzada: `caine.png`
  - ilustrador forzado: `Crafted with AI`
- `libreria`
  - nombre: `.44 Magnum`
  - imagen base: `static/layouts/images/44. magnum.png`
  - ilustrador forzado: `Crafted with AI`

## Testing
- `apps/srv_textos/tests.py`
  - `habilidad` no crece fuera de la caja marcada.
  - `habilidad.used_box` se ajusta al contenido.
  - `disciplinas` se ancla encima de `habilidad`.
  - tamano y spacing de `disciplinas` responden a ancho y alto.
  - `cripta` e `ilustrador` conservan fuente fija.
- `apps/layouts/tests.py`
  - la preview fija de `Mimir` fuerza `senda='caine.png'`.
  - las actualizaciones de config normalizan cajas cuadradas.
  - el editor renderiza overlays invisibles sin etiquetas visibles.
- Verificacion completa:
  - `.venv/bin/python manage.py test apps.layouts.tests -v 2`
  - `.venv/bin/python manage.py test apps.srv_textos.tests -v 2`
- Verificacion manual:
  - abrir `/layouts/`
  - comprobar que `Mimir` muestra la senda de Cain
  - mover `habilidad` y verificar que `disciplinas` permanece pegada por encima
  - seleccionar capas invisibles haciendo clic en su zona
  - comprobar que `clan`, `senda` y `coste` no se deforman al redimensionar

## Riesgos y mitigaciones
- Riesgo: mezclar `layout_box` y `used_box` puede romper colisiones actuales.
  - Mitigacion: separar ambos conceptos en metricas y actualizar solo los consumidores necesarios.
- Riesgo: capas invisibles hagan dificil la seleccion.
  - Mitigacion: mantener hit areas internas y asas visibles al seleccionar.
- Riesgo: normalizar cuadrados al guardar provoque saltos visuales.
  - Mitigacion: aplicar la misma regla en drag/resize antes de persistir.
- Riesgo: `disciplinas` quede fuera de la carta con textos muy altos.
  - Mitigacion: clamp vertical en el calculo final y tests explicitos de limites.

## Criterio de exito
Un usuario crea o edita un layout y, al usarlo para generar una carta nueva, `habilidad`, `disciplinas`, `cripta`, `ilustrador`, `clan`, `senda` y `coste` aparecen donde el editor le hizo esperar. El bloque de texto respeta la caja marcada, `disciplinas` queda siempre pegada por encima, las capas invisibles siguen siendo editables por clic y la preview fija de `Mimir` muestra la senda de Cain.
