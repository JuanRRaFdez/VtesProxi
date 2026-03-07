COLUMNAS = 3
FILAS = 3


def calcular_paginas(num_imagenes: int) -> int:
    por_pagina = COLUMNAS * FILAS
    if num_imagenes <= 0:
        return 0
    return (num_imagenes + por_pagina - 1) // por_pagina


def expandir_por_copias(paths: list[str], copies: int) -> list[str]:
    expanded = []
    for path in paths:
        expanded.extend([path] * copies)
    return expanded


def validate_layout_params(width_mm: float, height_mm: float, copies: int) -> None:
    if width_mm <= 0:
        raise ValueError("width_mm debe ser > 0")
    if height_mm <= 0:
        raise ValueError("height_mm debe ser > 0")
    if copies <= 0:
        raise ValueError("copies debe ser > 0")
