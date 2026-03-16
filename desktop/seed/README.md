# Desktop Seed Assets

Este directorio se usa para preparar el bundle portable de Windows.

El build copia aquí, justo antes de ejecutar PyInstaller:

- `db.sqlite3`
- `media/`

Así el paquete final arranca con el mismo usuario, layouts y cartas que existan en el entorno local desde el que se construye el bundle.

No hace falta versionar esos archivos generados; sólo se versiona esta documentación.
