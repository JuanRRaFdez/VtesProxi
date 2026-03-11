# VtesProxi

Aplicacion Django para generar proxies de cartas (Cripta y Libreria), con recorte, render de texto/simbolos y gestion de cartas guardadas.

## Editor de Layouts

La app `apps.layouts` permite crear y mantener layouts privados por usuario para `cripta` y `libreria`.

### Acceso
- URL: `/layouts/`
- Requiere login.
- Entrada de menu disponible en la barra lateral como `Layouts`.

### Flujo recomendado
1. Entrar en `Layouts`.
2. Elegir tipo de carta (`cripta` o `libreria`).
3. Crear o seleccionar un layout.
4. Mover/redimensionar capas en el editor visual.
5. Guardar configuracion.
6. (Opcional) Marcar layout como default.
7. Ir a `/cripta/importar-imagen/` o `/libreria/importar-imagen/` y usar el selector de layout.

### Prioridad de resolucion en render
Los endpoints de `srv_textos` resuelven el layout en este orden:
1. `layout_override`
2. `layout_id`
3. layout default del usuario para el tipo de carta
4. fallback `classic` desde `apps/srv_textos/layouts.json`

## Verificacion rapida

Usar el interprete del entorno virtual:

```bash
/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.layouts.tests -v 2
/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.srv_textos.tests -v 2
/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py check
```
