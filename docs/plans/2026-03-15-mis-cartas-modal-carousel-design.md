# Mis Cartas Modal Carousel Design

## Goal

Permitir navegar entre las cartas visibles en la pagina actual de `Mis cartas` sin cerrar el modal, usando botones en pantalla y flechas izquierda/derecha del teclado.

## Current State

La vista `Mis cartas` en `apps/mis_cartas/templates/mis_cartas/mis_cartas.html` ya tiene un modal sencillo que abre una carta concreta. Ese modal solo conoce la `url` y el `filename` de la carta pulsada, asi que no puede moverse a la siguiente o a la anterior sin cerrar y volver a abrir otra miniatura.

## Chosen Approach

Se ampliara el modal existente para convertirlo en un visor navegable de las cartas visibles en la pagina actual. No se tocara la paginacion ni el backend de datos; la lista de cartas se derivara directamente del DOM renderizado en la pagina.

Este enfoque mantiene la UX actual, evita meter una galeria separada y hace que el carrusel respete automaticamente el filtro o la paginacion activa. Si el usuario esta viendo una busqueda con cuatro resultados en esa pagina, el modal solo navegara entre esas cuatro cartas. Si no hay busqueda, navegara entre las cartas visibles en la pagina abierta.

## Interaction Model

- Al hacer click en una miniatura, el modal abrira la carta seleccionada y guardara su indice dentro de la lista de cartas visibles.
- El modal tendra dos botones nuevos: `anterior` y `siguiente`.
- La navegacion sera circular:
  - desde la primera, `anterior` ira a la ultima visible
  - desde la ultima, `siguiente` volvera a la primera visible
- Las teclas `ArrowLeft` y `ArrowRight` haran la misma navegacion cuando el modal este abierto.
- `Escape` seguira cerrando el modal.
- Los enlaces de descargar y borrar se actualizaran cada vez que cambie la carta activa.
- Si solo hay una carta visible en la pagina, los botones de navegacion se ocultaran para no ensuciar el visor.

## Data Flow

La pagina ya renderiza todas las cartas visibles de la pagina actual. El frontend construira un array JS con la metadata necesaria de cada carta visible:

- `url`
- `filename`

Esa metadata saldra de atributos `data-*` en cada tarjeta o en cada wrapper clicable. El modal dejara de depender de argumentos inline sueltos y pasara a trabajar con un indice dentro de esa coleccion visible.

## Rendering and UX Notes

- Se conservara el overlay actual.
- Los botones de navegacion se colocaran a ambos lados de la imagen para que el gesto sea evidente.
- El modal seguira mostrando una sola carta cada vez; no se anadiran miniaturas ni una tira inferior.
- La logica de borrado no se ejecutara automaticamente al cambiar de carta. Solo cambiaremos la accion del formulario del modal a la carta activa.

## Error Handling

- Si por cualquier razon el indice activo queda fuera de rango, el modal no intentara renderizar una carta inexistente y cerrara o volvera a la primera valida.
- Si no hay cartas visibles, no habra carrusel ni controles.
- Las teclas de navegacion no haran nada si el modal esta cerrado.

## Testing

Se anadira cobertura en `apps/mis_cartas/tests.py` para fijar:

- que `Mis cartas` renderiza los atributos necesarios para el carrusel
- que el template incluye los controles de `anterior` y `siguiente`
- que el script contiene la logica de navegacion con teclado y la coleccion de cartas visibles

No hacen falta cambios en la vista Python ni en la paginacion, salvo que aparezca alguna necesidad menor durante la implementacion.
