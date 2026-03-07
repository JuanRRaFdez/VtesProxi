import io

from PIL import Image
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

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


def _draw_cut_marks(pdf_canvas, x, y, w, h, mark_len=3 * mm):
    pdf_canvas.line(x, y, x + mark_len, y)
    pdf_canvas.line(x, y, x, y + mark_len)
    pdf_canvas.line(x + w, y, x + w - mark_len, y)
    pdf_canvas.line(x + w, y, x + w, y + mark_len)
    pdf_canvas.line(x, y + h, x + mark_len, y + h)
    pdf_canvas.line(x, y + h, x, y + h - mark_len)
    pdf_canvas.line(x + w, y + h, x + w - mark_len, y + h)
    pdf_canvas.line(x + w, y + h, x + w, y + h - mark_len)


def generate_pdf_bytes(
    image_paths: list[str],
    width_mm: float,
    height_mm: float,
    copies: int,
    cut_marks: bool,
) -> bytes:
    validate_layout_params(width_mm, height_mm, copies)
    all_paths = expandir_por_copias(image_paths, copies)

    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    _, page_h = A4

    card_w = width_mm * mm
    card_h = height_mm * mm
    margin = 5 * mm
    per_page = COLUMNAS * FILAS

    for idx, path in enumerate(all_paths):
        if idx > 0 and idx % per_page == 0:
            pdf.showPage()

        pos = idx % per_page
        col = pos % COLUMNAS
        row = pos // COLUMNAS

        x = margin + col * card_w
        y = page_h - margin - (row + 1) * card_h

        with Image.open(path) as image:
            if image.mode != "RGB":
                image = image.convert("RGB")
            pdf.drawImage(
                ImageReader(image),
                x,
                y,
                width=card_w,
                height=card_h,
                preserveAspectRatio=True,
                mask="auto",
            )

        if cut_marks:
            _draw_cut_marks(pdf, x, y, card_w, card_h)

    pdf.save()
    buffer.seek(0)
    return buffer.read()
