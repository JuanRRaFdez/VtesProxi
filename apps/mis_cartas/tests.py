from django.test import SimpleTestCase
from apps.mis_cartas import pdf_service


class PdfServiceHelpersTests(SimpleTestCase):
    def test_calcular_paginas_uses_grid_3x3(self):
        self.assertEqual(pdf_service.calcular_paginas(0), 0)
        self.assertEqual(pdf_service.calcular_paginas(1), 1)
        self.assertEqual(pdf_service.calcular_paginas(9), 1)
        self.assertEqual(pdf_service.calcular_paginas(10), 2)

    def test_expandir_por_copias_duplicates_paths(self):
        paths = ["/tmp/a.png", "/tmp/b.png"]
        self.assertEqual(
            pdf_service.expandir_por_copias(paths, 2),
            ["/tmp/a.png", "/tmp/a.png", "/tmp/b.png", "/tmp/b.png"],
        )

    def test_validate_layout_params_rejects_bad_values(self):
        with self.assertRaises(ValueError):
            pdf_service.validate_layout_params(width_mm=0, height_mm=88, copies=1)
        with self.assertRaises(ValueError):
            pdf_service.validate_layout_params(width_mm=63, height_mm=-1, copies=1)
        with self.assertRaises(ValueError):
            pdf_service.validate_layout_params(width_mm=63, height_mm=88, copies=0)
