# Diseno: Preview fija de carta en el editor de layouts

## Estado
Aprobado por usuario.

## Objetivo
Mostrar una carta real completa dentro del editor de layouts, usando una preview fija por tipo de carta, para que el usuario coloque y redimensione las cajas directamente sobre el render final en vez de trabajar sobre un fondo gris.

## Requisitos validados
- El editor de `cripta` usara siempre la carta `Mimir`.
- El editor de `libreria` usara siempre la carta `.44 Magnum`.
- La imagen base de `cripta` sera `static/layouts/images/Mimir.png`.
- La imagen base de `libreria` sera `static/layouts/images/44. magnum.png`.
- Los datos del resto de campos se rellenaran automaticamente desde el catalogo por nombre de carta.
- El ilustrador se forzara siempre a `Crafted with AI`.
- No se añadiran controles para cambiar la carta de preview.
- La preview debe verse completa dentro de la pantalla del editor; no debe requerir que el usuario “busque” zonas fuera del viewport.
- Las cajas del editor deben seguir editandose directamente encima de la carta real.

## Enfoque aprobado
Opcion 2: preview real fija por tipo usando el motor actual de render.

Se anade un endpoint propio del editor de layouts que construye una carta de preview fija por tipo, resuelve los datos desde el catalogo y renderiza la carta con el `layout_config` activo. El frontend sustituye el fondo neutro por esa preview y escala el canvas del editor para que la carta completa quepa dentro del panel sin romper la correspondencia entre cajas y render final.

## Arquitectura funcional

### 1) Preview fija por tipo
- `cripta`
  - nombre de carta: `Mimir`
  - imagen base: `static/layouts/images/Mimir.png`
  - ilustrador: `Crafted with AI`
- `libreria`
  - nombre de carta: `.44 Magnum`
  - imagen base: `static/layouts/images/44. magnum.png`
  - ilustrador: `Crafted with AI`

### 2) Resolucion automatica de datos
- El editor no almacenara datos de preview en BD.
- El backend resolvera los datos de la carta en tiempo real a partir del nombre fijo usando el catalogo existente.
- Se reutilizara el mapeo actual para rellenar:
  - `clan`
  - `coste`
  - `cripta`
  - `disciplinas`
  - `simbolos`
  - `habilidad`
- Solo `ilustrador` quedara sobreescrito con el valor fijo aprobado.

### 3) Endpoint propio del editor
- Se anadira un endpoint en `apps.layouts` para pedir la preview del layout activo.
- El endpoint recibira:
  - `card_type`
  - `layout_config`
- Respondera con:
  - `imagen_url` renderizada
  - metadatos basicos de la preview, si hacen falta para depuracion
- El editor no dependera del flujo de formularios de `cripta` o `libreria`.

### 4) Reutilizacion del renderer
- El motor de render actual ya sabe pintar todos los elementos y aplicar `layout_config`.
- Para poder usar imagenes base que viven en `static/layouts/images`, se extraera o ampliara la logica de render para aceptar una ruta absoluta de imagen base ademas del flujo actual via `MEDIA_URL`.
- El flujo existente de importacion y render normal no debe romperse.

### 5) Canvas escalable del editor
- La carta seguira teniendo un sistema de coordenadas nativo basado en el tamano real del layout.
- Visualmente, el editor la mostrara escalada para que quepa completa en el panel.
- Las capas del editor se dibujaran por encima de la preview usando la misma escala.
- La interaccion drag/resize convertira entre:
  - coordenadas de modelo
  - coordenadas visibles escaladas
- Resultado esperado: mover una caja en el editor sigue significando mover esa misma caja en el render final, aunque la carta se vea mas pequena.

## Cambios de UI
- El `stage` del editor mostrara una imagen real de carta en vez del fondo gris plano.
- Se anadira un viewport/canvas dedicado para:
  - preview renderizada
  - overlays editables
- El panel lateral de propiedades se mantiene.
- No se anaden inputs ni selectores nuevos para escoger carta de preview.

## Flujo de usuario esperado
1. El usuario entra en `/layouts/`.
2. El editor muestra inmediatamente la carta fija del tipo actual.
3. El usuario cambia de layout o mueve/redimensiona cajas.
4. La preview se vuelve a renderizar con debounce.
5. La carta completa sigue visible y las cajas permanecen alineadas sobre ella.

## Testing
- `apps/layouts/tests.py`
  - endpoint de preview devuelve un render para `Mimir`
  - endpoint de preview devuelve un render para `.44 Magnum`
  - el endpoint fuerza `Crafted with AI`
  - el template incluye el nodo de preview y el canvas del editor
- `apps/srv_textos/tests.py`
  - cobertura puntual si hace falta para el nuevo helper de render desde ruta absoluta
- Verificacion completa:
  - `.venv/bin/python manage.py test apps.layouts.tests -v 2`
  - `.venv/bin/python manage.py test apps.srv_textos.tests -v 2`

## Riesgos y mitigaciones
- Riesgo: la imagen base en `static/` no entra por el flujo actual del renderer.
  - Mitigacion: extraer helper de render que acepte ruta absoluta sin cambiar el contrato publico existente.
- Riesgo: al escalar el canvas, drag/resize deje de coincidir con las coordenadas guardadas.
  - Mitigacion: centralizar conversion `modelo <-> display` en helpers de frontend y cubrir el flujo manualmente.
- Riesgo: demasiadas peticiones de preview mientras el usuario arrastra.
  - Mitigacion: debounce y actualizacion solo al terminar el drag/resize o al aplicar propiedades.

## Criterio de exito
Un usuario abre el editor de layouts y ve la carta completa del tipo actual (`Mimir` o `.44 Magnum`) dentro del panel. Al mover o redimensionar cajas, la preview se actualiza y refleja exactamente el layout que luego se usara al crear cartas reales.
