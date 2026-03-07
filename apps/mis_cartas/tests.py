import json
import tempfile
from pathlib import Path
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase, override_settings
from PIL import Image
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


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class MisCartasPdfEndpointTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="ana", password="secreto123"
        )

    def _crear_png_usuario(self, filename: str):
        user_dir = Path(settings.MEDIA_ROOT) / "cartas" / self.user.username
        user_dir.mkdir(parents=True, exist_ok=True)
        user_dir.joinpath(filename).write_bytes(
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc```\x00\x00\x00\x04\x00\x01\x0b\xe7\x02\x9d\x00\x00\x00\x00IEND\xaeB`\x82"
        )

    def test_requires_login(self):
        response = self.client.post(
            "/mis-cartas/generar-pdf/",
            data=json.dumps({"selected": ["uno.png"]}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 302)

    def test_rejects_empty_selection(self):
        self.client.login(username="ana", password="secreto123")
        response = self.client.post(
            "/mis-cartas/generar-pdf/",
            data=json.dumps({"selected": []}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_rejects_missing_card(self):
        self.client.login(username="ana", password="secreto123")
        response = self.client.post(
            "/mis-cartas/generar-pdf/",
            data=json.dumps({"selected": ["no-existe.png"]}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 404)

    def test_returns_pdf_file_for_valid_selection(self):
        self._crear_png_usuario("uno.png")
        self.client.login(username="ana", password="secreto123")
        response = self.client.post(
            "/mis-cartas/generar-pdf/",
            data=json.dumps(
                {"selected": ["uno.png"], "width_mm": 63, "height_mm": 88, "copies": 1}
            ),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")


class PdfServiceRenderTests(SimpleTestCase):
    def test_generate_pdf_bytes_returns_real_pdf(self):
        with tempfile.TemporaryDirectory() as tmp:
            img_path = Path(tmp) / "uno.png"
            Image.new("RGB", (300, 420), color=(20, 20, 20)).save(img_path, "PNG")

            pdf = pdf_service.generate_pdf_bytes(
                [str(img_path)],
                width_mm=63,
                height_mm=88,
                copies=1,
                cut_marks=True,
            )

        self.assertTrue(pdf.startswith(b"%PDF"))
        self.assertIn(b"/Type /Page", pdf)
