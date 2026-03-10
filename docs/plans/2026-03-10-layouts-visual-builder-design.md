# Diseño: Constructor Visual de Layouts por Usuario

## Estado
Aprobado.

## Objetivo
Añadir una nueva pestaña/app `layouts` para que cada usuario autenticado pueda crear, editar y gestionar layouts visuales de cartas (Cripta y Librería) mediante arrastrar y redimensionar elementos directamente sobre la carta.

## Requisitos acordados
- Los layouts son privados por usuario.
- Persistencia en base de datos (no en archivo JSON como fuente principal de edición).
- Soporte para ambos tipos de carta: `cripta` y `libreria`.
- Edición visual tipo drag-and-drop sobre preview de carta.
- Redimensionado editable de elementos (posición y tamaño).
- Layout por defecto por usuario y por tipo de carta.

## Enfoque elegido
**Opción 2: Interact.js + Django (recomendada y aprobada).**

Se mantiene el backend Django actual para render y guardado de cartas, añadiendo una app específica de layouts con endpoints JSON autenticados y una UI visual en frontend. Interact.js se usa para interacción drag/resize sin introducir un pipeline de build JS complejo.

## Alcance de primera iteración
- CRUD completo de layouts por usuario.
- Selección de layout por defecto para `cripta` y `libreria`.
- Editor visual con preview en tiempo real.
- Integración del selector de layout en pantallas existentes (`/cripta/importar-imagen/` y `/libreria/importar-imagen/`).

## Fuera de alcance (iteración actual)
- Compartir layouts entre usuarios.
- Versionado/historial de cambios de un layout.
- Import/export de layouts entre cuentas.
- Editor basado en canvas avanzado (Fabric/Konva).

## Diseño técnico

### 1. Modelo de datos
Nueva app Django: `apps.layouts`.

Modelo principal: `UserLayout`.

Campos:
- `user` (FK a `auth.User`, obligatorio)
- `name` (`CharField`)
- `card_type` (`CharField`, choices: `cripta`, `libreria`)
- `config` (`JSONField`)
- `is_default` (`BooleanField`, default `False`)
- `created_at`, `updated_at`

Reglas:
- Unicidad de nombre por usuario + tipo (`UniqueConstraint(user, card_type, name)`).
- Un único layout por defecto por usuario + tipo (constraint condicional con `is_default=True`).
- Validaciones de estructura y rangos de `config` en backend.

### 2. Estructura de configuración (`config` JSON)
`config` conservará la misma semántica del layout actual para minimizar refactor del render:
- `carta` (width, height)
- `nombre` (x, y, font_size, color, shadow...)
- `clan` (x, y, size)
- `senda` (x, y, size)
- `disciplinas` (x, bottom, size, spacing)
- `simbolos` (librería: x, y, size, spacing)
- `habilidad` (x, y_ratio, max_width_ratio, font_size, bg_*)
- `coste` (left/right, bottom, size)
- `cripta` (font_size, y_gap)
- `ilustrador` (bottom, font_size, color)

Compatibilidad:
- `apps/srv_textos/layouts.json` se conserva como semilla/fallback (`classic`) para bootstrap y resiliencia.

### 3. API de layouts
Nuevas rutas en `apps/layouts/urls.py` (todas con login):
- `GET /layouts/` -> vista principal del editor visual.
- `GET /layouts/api/list?card_type=...` -> layouts del usuario por tipo.
- `POST /layouts/api/create` -> crear layout nuevo desde plantilla base.
- `GET /layouts/api/detail/<id>` -> detalle de layout.
- `POST /layouts/api/update-config` -> persistir `config`.
- `POST /layouts/api/rename` -> renombrar.
- `POST /layouts/api/delete` -> borrar.
- `POST /layouts/api/set-default` -> activar por defecto (por tipo).

Políticas:
- Prohibido acceder a layouts de otro usuario.
- Respuestas JSON con errores explícitos (`400/403/404/405`).

### 4. Integración con render existente (`srv_textos`)
Se unifica resolución de layout en un resolver interno con prioridad:
1. `layout_override` (editor visual en preview temporal).
2. `layout_id` explícito del usuario.
3. layout `is_default=True` del usuario para `card_type`.
4. fallback `classic` desde `layouts.json`.

Objetivo: no romper endpoints actuales (`render-nombre`, `render-clan`, `render-texto`, `guardar-carta`).

### 5. UI del editor visual
Nueva template en `apps/layouts/templates/layouts/editor.html`.

Composición:
- Columna izquierda: preview de carta + overlays editables.
- Columna derecha: propiedades numéricas del elemento seleccionado.
- Toolbar superior: selector `card_type`, selector layout, crear/duplicar/renombrar/borrar, guardar, marcar por defecto.

Interacción:
- Cada elemento de layout se representa como capa draggable/resizable.
- Interact.js gestiona drag/resize y límites del contenedor.
- Al mover/redimensionar:
  - se actualiza estado local de `config`,
  - se lanza render con debounce usando endpoint existente y `layout_override`.

### 6. Integración con Cripta y Librería actuales
En `apps/cripta/views.py` y `apps/libreria/views.py`:
- El combo de layout dejará de leer del JSON global.
- Leerá layouts del usuario para ese tipo y preseleccionará su default.

En el JS de `importar_imagen.html`:
- Se enviará `layout_id` en payload de render.
- Se conserva `layout_name` solo como compatibilidad temporal/fallback.

### 7. Manejo de errores
- `400`: payload inválido o configuración fuera de rango.
- `403`: layout no pertenece al usuario autenticado.
- `404`: layout inexistente.
- `500`: error inesperado (log interno, mensaje genérico en cliente).

UI:
- Mensajes de feedback en barra superior del editor (guardado OK/error).
- Recuperación segura ante render fallido (mantener último preview válido).

### 8. Seguridad
- Todos los endpoints de layouts bajo `@login_required`.
- Validación estricta de IDs y ownership por consulta.
- No aceptar rutas de archivos ni payloads arbitrarios fuera de esquema.

### 9. Testing
Automatizado:
- `apps/layouts/tests.py`
  - CRUD por usuario.
  - Aislamiento entre usuarios.
  - `set-default` garantiza único default por tipo.
  - validación de `config` y errores esperados.
- `apps/srv_textos/tests.py`
  - render con `layout_override`.
  - render con `layout_id` propio.
  - rechazo de `layout_id` ajeno.

Manual:
- Drag y resize en desktop y móvil.
- Cambio de default por tipo y efecto inmediato en Cripta/Librería.
- Flujo completo crear -> editar -> guardar -> usar en generación real.

## Riesgos y mitigaciones
- Riesgo: complejidad del mapping UI->config para elementos heterogéneos.
  - Mitigación: normalizar adaptadores por elemento y usar esquema de validación común.
- Riesgo: muchas peticiones de render durante drag.
  - Mitigación: debounce + “guardar al soltar” para persistencia; preview limitado a frecuencia controlada.
- Riesgo: regresión en render legacy por cambio de resolución de layout.
  - Mitigación: fallback explícito a `classic` y tests en endpoints existentes.

## Criterio de éxito
Un usuario autenticado puede:
1. abrir la pestaña `Layouts`,
2. crear un layout de Cripta o Librería,
3. mover/redimensionar elementos visualmente con preview,
4. guardar el layout,
5. marcarlo como default,
6. usarlo después en `/cripta/importar-imagen/` o `/libreria/importar-imagen/` sin tocar JSON manualmente.
