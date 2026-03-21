import tempfile
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings


class MisCartasTemplateTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="pepe", password="secreto123"
        )

    def test_mis_cartas_no_longer_contains_pdf_action(self):
        self.client.login(username="pepe", password="secreto123")
        response = self.client.get("/mis-cartas/")
        self.assertNotContains(response, 'id="bulkPdfForm"')
        self.assertNotContains(response, 'id="generatePdfBtn"')
        self.assertNotContains(response, "Generar PDF")

    def test_pdf_generation_endpoint_is_not_available(self):
        self.client.login(username="pepe", password="secreto123")
        response = self.client.post(
            "/mis-cartas/generar-pdf/",
            data="{}",
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 404)

    def test_pdf_tab_is_not_linked_in_sidebar(self):
        self.client.login(username="pepe", password="secreto123")
        response = self.client.get("/mis-cartas/")
        self.assertNotContains(response, 'href="/pdf/"')


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class MisCartasModalCarouselTemplateTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="lucia", password="secreto123"
        )

    def _crear_png_usuario(self, filename: str):
        user_dir = Path(settings.MEDIA_ROOT) / "cartas" / self.user.username
        user_dir.mkdir(parents=True, exist_ok=True)
        user_dir.joinpath(filename).write_bytes(
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc```\x00\x00\x00\x04\x00\x01\x0b\xe7\x02\x9d\x00\x00\x00\x00IEND\xaeB`\x82"
        )

    def test_mis_cartas_renders_modal_carousel_markup_for_visible_cards(self):
        self._crear_png_usuario("alpha.png")
        self._crear_png_usuario("beta.png")
        self.client.login(username="lucia", password="secreto123")

        response = self.client.get("/mis-cartas/")

        self.assertContains(response, 'id="modalPrevBtn"')
        self.assertContains(response, 'id="modalNextBtn"')
        self.assertContains(response, 'data-card-url="')
        self.assertContains(response, 'data-card-filename="alpha.png"')
        self.assertContains(response, 'data-card-filename="beta.png"')

    def test_mis_cartas_template_contains_keyboard_and_index_navigation_logic(self):
        self._crear_png_usuario("alpha.png")
        self.client.login(username="lucia", password="secreto123")

        response = self.client.get("/mis-cartas/")

        self.assertContains(response, "visibleCards")
        self.assertContains(response, "showNextCard")
        self.assertContains(response, "showPrevCard")
        self.assertContains(response, "ArrowLeft")
        self.assertContains(response, "ArrowRight")

    def test_mis_cartas_template_handles_single_visible_card_state(self):
        self._crear_png_usuario("solo.png")
        self.client.login(username="lucia", password="secreto123")

        response = self.client.get("/mis-cartas/")

        self.assertContains(response, "updateCarouselControls")
        self.assertContains(response, "hidden")
