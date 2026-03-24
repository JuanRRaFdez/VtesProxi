from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase


class ImportarImagenTemplateTests(SimpleTestCase):
    def test_render_clan_does_not_skip_empty_selection(self):
        template = Path(
            settings.BASE_DIR,
            "apps",
            "cripta",
            "templates",
            "cripta",
            "importar_imagen.html",
        ).read_text(encoding="utf-8")

        self.assertIn("function renderClan()", template)
        self.assertNotIn("if (!clan) {\n                return;\n            }", template)

    def test_render_senda_does_not_skip_empty_selection(self):
        template = Path(
            settings.BASE_DIR,
            "apps",
            "cripta",
            "templates",
            "cripta",
            "importar_imagen.html",
        ).read_text(encoding="utf-8")

        self.assertIn("function renderSenda()", template)
        self.assertNotIn("if (!senda) {\n                return;\n            }", template)

    def test_habilidad_toolbar_buttons_and_wrapper_helper_exist(self):
        template = Path(
            settings.BASE_DIR,
            "apps",
            "cripta",
            "templates",
            "cripta",
            "importar_imagen.html",
        ).read_text(encoding="utf-8")

        self.assertIn('id="habilidad-bold-btn"', template)
        self.assertIn('id="habilidad-italic-btn"', template)
        self.assertIn("function wrapHabilidadSelection(before, after)", template)
        self.assertIn("wrapHabilidadSelection('**', '**')", template)
        self.assertIn("wrapHabilidadSelection('(', ')')", template)
