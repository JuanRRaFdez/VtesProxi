# Diseno: Estilo classic fijo para ilustrador y cripta

## Estado
Aprobado por usuario.

## Objetivo
Hacer que `ilustrador` y el numero de `cripta` usen siempre el estilo visual del layout `classic` del tipo de carta correspondiente, manteniendo editable solo su posicion dentro de los layouts personalizados.

## Requisitos validados
- El estilo de `ilustrador` debe ser siempre el del `classic`.
- El estilo del numero de `cripta` debe ser siempre el del `classic`.
- "Estilo" significa fuente, tamano y color.
- Esto debe aplicarse tanto al flujo normal de render como a la preview del editor.
- En `cripta`, `ilustrador` y el numero de `cripta` deben verse como en `classic`.
- En `libreria`, `ilustrador` debe verse como en `classic.libreria`.
- La posicion de ambas capas sigue saliendo del layout personalizado del usuario.
- El resize del editor no debe cambiar la tipografia de estas capas.

## Aclaracion funcional
- Las cartas de `libreria` no renderizan numero de `cripta`.
- Por tanto, en `libreria` solo aplica el estilo fijo de `ilustrador`.

## Enfoque aprobado
Opcion 1: tomar siempre los tokens de estilo del seed `classic`.

No se duplicaran valores en el renderer ni se anadiran flags nuevos al layout. El motor de render obtendra el estilo base desde `apps/srv_textos/layouts.json`, usando `classic` o `classic.libreria` segun el tipo de carta, y aplicara esos valores a `ilustrador` y `cripta` mientras mantiene la geometria del layout activo.

## Arquitectura funcional

### 1) Fuente de verdad del estilo
- El origen de estilo sera `apps/srv_textos/layouts.json`.
- Para `ilustrador`:
  - `cripta` usara `layouts.classic.ilustrador`
  - `libreria` usara `layouts.classic.libreria.ilustrador`
- Para `cripta`:
  - se usara `layouts.classic.cripta`

### 2) Separacion entre estilo y geometria
- `estilo fijo`
  - fuente
  - tamano
  - color
- `geometria editable`
  - `box`
  - `x`
  - `y`
  - `bottom`
  - anclaje vertical relativo a `habilidad`

El layout personalizado seguira moviendo estas capas, pero no podra cambiar su aspecto tipografico final.

### 3) Render de ilustrador
- El calculo de `fit` de `ilustrador` dejara de usar el `font_size` del layout activo.
- Se medira y renderizara con el `font_size` y color del `classic` correspondiente.
- La caja del usuario se mantiene para decidir posicion y ancho disponible.

### 4) Render de cripta
- El numero de `cripta` dejara de tomar `font_size` y color del layout activo.
- Se pintara siempre con el estilo de `classic.cripta`.
- La posicion seguira saliendo de la caja/anclaje del layout del usuario.

### 5) Editor de layouts
- No hace falta cambiar la interaccion general del editor.
- `ilustrador` y `cripta` seguiran comportandose como capas de posicion.
- El preview del editor reflejara automaticamente el nuevo estilo porque reutiliza el mismo motor de render.

## Testing
- `apps/srv_textos/tests.py`
  - test de que `ilustrador` usa el `font_size` del `classic` aunque el layout activo tenga otro distinto
  - test de que `ilustrador` usa el color del `classic`
  - test de que `cripta` usa el `font_size` del `classic` aunque el layout activo tenga otro distinto
  - test de que `cripta` usa el color del `classic`
  - test equivalente para `libreria.ilustrador`
- Verificacion completa:
  - `.venv/bin/python manage.py test apps.srv_textos.tests -v 2`
  - `.venv/bin/python manage.py test apps.layouts.tests -v 2`

## Riesgos y mitigaciones
- Riesgo: mezclar estilo del `classic` con caja del layout activo cree incoherencias al medir `ilustrador`.
  - Mitigacion: centralizar un helper que devuelva el estilo efectivo por tipo y capa antes del `fit`.
- Riesgo: algun test actual asuma que `font_size` de `ilustrador` o `cripta` sale del layout activo.
  - Mitigacion: ajustar esos tests al nuevo contrato y anadir regresiones directas.
- Riesgo: cambios de estilo en `classic` afecten layouts personalizados existentes.
  - Mitigacion: este es el comportamiento deseado; documentar que `classic` pasa a ser la fuente de verdad del estilo para estas capas.

## Criterio de exito
Un usuario mueve `ilustrador` o `cripta` en un layout personalizado y, al renderizar una carta o verla en la preview del editor, ambas capas conservan siempre el mismo aspecto visual del layout `classic` del tipo correspondiente, cambiando solo de posicion.
