# Diseño: Autocompletado de Cartas desde Catálogo JSON

## Objetivo
Permitir que al escribir el nombre de una carta en el editor (Cripta o Librería) aparezca una lista de coincidencias y, al seleccionar una, se rellenen automáticamente los campos del formulario usando `Cripta_2.json` o `Libreria_2.json`.

## Requisitos acordados
- Sugerencias mientras se escribe en el campo `Nombre`.
- Coincidencias sin distinguir mayúsculas/minúsculas ni acentos.
- Límite de resultados por búsqueda: 10.
- Inicio de búsqueda a partir de 2 caracteres.

## Arquitectura
1. Backend con índice en memoria de ambos JSON para búsquedas rápidas.
2. Endpoint de sugerencias por texto (`q`) y tipo de carta (`card_type`).
3. Endpoint de detalle por nombre exacto para devolver campos mapeados al formulario.
4. Frontend con dropdown de sugerencias + selección que aplica autocompletado y relanza render.

## Mapeo de campos
- `Name` -> `nombre`
- `Clan` -> selector de clan (`clan-select`) con normalización a archivo `.png`
- `Text` -> `habilidad`
- `Discipline` -> grilla de disciplinas (`disc-grid`)
- Cripta: `Capacity` -> `coste`, `Group` -> `cripta`
- Librería: `PoolCost`/`BloodCost` -> `coste` (`poolN/poolx` o `bloodN/bloodx`), `Type` -> `simbolos`

## Manejo de casos límite
- Nombre no encontrado: no se modifica el formulario.
- Clanes compuestos (`A/B`): se usa el primer clan compatible.
- Disciplinas no soportadas por iconografía actual: se ignoran.
- Datos incompletos en JSON: se aplican solo campos válidos.
