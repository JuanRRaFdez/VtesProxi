# Diseno: Editor de layouts con preview limpia

## Estado
Aprobado por usuario.

## Objetivo
Hacer que el editor de layouts de `cripta` y `libreria` trabaje sobre una imagen base limpia, mostrando solo los recuadros editables, y alinear el modelo de geometria de `libreria` con el flujo mas consistente que ya se busca en `cripta`.

## Requisitos validados
- El cambio aplica al editor de `/layouts/`, no al render real de creacion de cartas.
- La preview del editor debe verse limpia para `cripta` y `libreria`.
- En el editor no deben renderizarse `clan`, `senda`, `disciplinas`, `simbolos`, `coste`, `habilidad`, `nombre`, `cripta` ni `ilustrador`.
- El usuario debe ver solo la imagen base fija y los recuadros editables.
- `libreria` debe editarse con la misma mentalidad que `cripta`: trabajar sobre cajas explicitas y no sobre reconstrucciones ambiguas desde campos legacy.
- Los layouts legacy deben seguir cargando.

## Enfoque aprobado
1. El editor usara una preview limpia por tipo de carta.
2. `libreria` materializara `box` explicitas para sus capas visuales stackeadas y editables.
3. El render real de cartas no cambiara de contrato ni de comportamiento funcional.

## Arquitectura funcional

### 1) Preview limpia del editor
- `apps/layouts/views.py` seguira exponiendo una preview fija por tipo (`Mimir` para `cripta`, `.44 Magnum` para `libreria`).
- El endpoint `api_preview` dejara de pedir una carta renderizada completa para el editor.
- En su lugar devolvera la imagen base fija preparada desde `static/layouts/images/...`, sin pintar contenido dinamico.
- El frontend del editor seguira mostrando esa imagen de fondo y dibujara encima los overlays editables que ya usa hoy.

### 2) Separacion de responsabilidades
- La preview del editor y el render final quedaran claramente separados.
- El editor se usara para maquetacion visual con recuadros.
- La creacion real de cartas en `apps/cripta` y `apps/libreria` seguira usando el motor de render con todos sus simbolos y textos.
- Esto evita mezclar requisitos de UX del editor con requisitos del render final.

### 3) Normalizacion de geometria en `libreria`
- `normalize_layout_config()` materializara `box` explicitas tambien para las capas stackeadas de `libreria`, especialmente `disciplinas` y `simbolos`.
- Si el layout ya trae `box`, se respetara.
- Si no la trae, se generara desde los campos legacy actuales (`x`, `y`, `bottom`, `size`, `spacing`) para mantener compatibilidad.
- El editor trabajara siempre con `box` como geometria fuente de verdad.

### 4) Compatibilidad con layouts existentes
- Los campos legacy seguiran presentes porque el render real todavia los usa como parte del contrato actual.
- Al editar un layout, la `box` se actualizara y los campos derivados (`size`, `spacing`, `bottom`, ratios, etc.) seguiran sincronizandose como compatibilidad.
- El objetivo no es eliminar el formato legacy ahora, sino dejar al editor sobre una geometria consistente.

## Flujo esperado
1. El usuario abre `/layouts/`.
2. Selecciona `cripta` o `libreria`.
3. Ve una imagen base limpia del tipo elegido.
4. Solo aparecen los recuadros de las capas configurables.
5. Al mover o redimensionar una capa, el editor guarda una `box` coherente y el overlay sigue alineado.

## Validacion y testing
- `apps/layouts/tests.py`
  - preview limpia para `cripta`
  - preview limpia para `libreria`
  - el preview del editor no fuerza contenido dinamico en modo limpio
- `apps/layouts/services.py`
  - tests de normalizacion para `disciplinas` y `simbolos` legacy en `libreria`
  - tests de validacion de `box` invalidas para esas capas
- `apps/srv_textos/tests.py`
  - regresiones para asegurar que el render real no cambia por este ajuste del editor

## Riesgos y mitigaciones
- Riesgo: mezclar preview limpia del editor con el flujo de render real.
  - Mitigacion: mantener un camino explicito para el editor y no tocar endpoints de creacion de cartas.
- Riesgo: romper layouts viejos de `libreria`.
  - Mitigacion: generar `box` al vuelo desde datos legacy y respetar `box` existentes.
- Riesgo: dejar validaciones a medias y permitir layouts incoherentes.
  - Mitigacion: ampliar `validate_layout_config()` para las capas que pasan a depender de `box`.

## Criterio de exito
- El editor de `cripta` y `libreria` muestra una imagen base limpia y solo recuadros.
- `libreria` deja de depender de reconstrucciones ambiguas para editar `disciplinas` y `simbolos`.
- El render real de cartas sigue funcionando como antes.
