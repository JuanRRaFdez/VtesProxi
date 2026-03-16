import importlib
import os
import tempfile
from copy import deepcopy
import json
from pathlib import Path
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import SimpleTestCase, TestCase

from apps.layouts.models import UserLayout
from apps.layouts.services import (
    LayoutValidationError,
    load_classic_seed,
    normalize_layout_config,
    validate_layout_config,
)


class UserLayoutModelTests(TestCase):
    def test_unique_name_per_user_and_card_type(self):
        user = get_user_model().objects.create_user(username='alice', password='secret')
        UserLayout.objects.create(
            user=user,
            name='Mi layout',
            card_type='cripta',
            config={},
            is_default=False,
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                UserLayout.objects.create(
                    user=user,
                    name='Mi layout',
                    card_type='cripta',
                    config={},
                    is_default=False,
                )

    def test_only_one_default_per_user_and_card_type(self):
        user = get_user_model().objects.create_user(username='bob', password='secret')

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                UserLayout.objects.create(
                    user=user,
                    name='Default 2',
                    card_type='libreria',
                    config={},
                    is_default=True,
                )


class LayoutUserBootstrapTests(TestCase):
    def test_new_user_gets_default_classic_layouts_for_both_card_types(self):
        user = get_user_model().objects.create_user(username='fresh', password='secret')

        defaults = list(
            UserLayout.objects.filter(user=user, is_default=True).order_by('card_type')
        )

        self.assertEqual(
            [(layout.card_type, layout.name) for layout in defaults],
            [('cripta', 'classic'), ('libreria', 'classic')],
        )

    def test_re_saving_user_does_not_duplicate_default_layouts(self):
        user = get_user_model().objects.create_user(username='stable', password='secret')

        user.first_name = 'Stable'
        user.save()

        self.assertEqual(UserLayout.objects.filter(user=user, card_type='cripta').count(), 1)
        self.assertEqual(UserLayout.objects.filter(user=user, card_type='libreria').count(), 1)


class LayoutDesktopSettingsTests(SimpleTestCase):
    def _load_desktop_settings(self, portable_dir):
        with patch.dict(os.environ, {'WEBVTES_PORTABLE_DIR': portable_dir}, clear=False):
            import webvtes.settings_desktop as desktop_settings
            return importlib.reload(desktop_settings)

    def test_desktop_settings_use_portable_database_and_media_paths(self):
        desktop_settings = self._load_desktop_settings('/tmp/webvtes-portable')

        self.assertEqual(
            Path(desktop_settings.DATABASES['default']['NAME']),
            Path('/tmp/webvtes-portable') / 'db.sqlite3',
        )
        self.assertEqual(
            Path(desktop_settings.MEDIA_ROOT),
            Path('/tmp/webvtes-portable') / 'media',
        )
        self.assertEqual(desktop_settings.ALLOWED_HOSTS, ['127.0.0.1', 'localhost'])


class LayoutDesktopRuntimeTests(SimpleTestCase):
    def test_seed_copy_only_copies_db_and_media_when_missing(self):
        from desktop.runtime import ensure_seeded_runtime

        with tempfile.TemporaryDirectory() as tmp_dir:
            base_dir = Path(tmp_dir)
            portable_dir = base_dir / 'portable'
            seed_dir = base_dir / 'seed'
            seed_media_dir = seed_dir / 'media'

            seed_media_dir.mkdir(parents=True)
            (seed_dir / 'db.sqlite3').write_bytes(b'seed-db')
            (seed_media_dir / 'example.txt').write_text('seed-media', encoding='utf-8')

            ensure_seeded_runtime(portable_dir, seed_dir)
            self.assertEqual((portable_dir / 'db.sqlite3').read_bytes(), b'seed-db')
            self.assertEqual(
                (portable_dir / 'media' / 'example.txt').read_text(encoding='utf-8'),
                'seed-media',
            )

            (portable_dir / 'db.sqlite3').write_bytes(b'user-db')
            (portable_dir / 'media' / 'example.txt').write_text('user-media', encoding='utf-8')

            ensure_seeded_runtime(portable_dir, seed_dir)
            self.assertEqual((portable_dir / 'db.sqlite3').read_bytes(), b'user-db')
            self.assertEqual(
                (portable_dir / 'media' / 'example.txt').read_text(encoding='utf-8'),
                'user-media',
            )

    def test_launcher_parses_supervisor_and_serve_modes(self):
        from desktop.windows_launcher import parse_args

        args = parse_args(['--serve', '--port', '8123'])

        self.assertTrue(args.serve)
        self.assertEqual(args.port, 8123)


class LayoutDesktopPackagingTests(SimpleTestCase):
    def test_windows_spec_references_required_seed_resources(self):
        spec = Path(settings.BASE_DIR, 'desktop', 'windows_launcher.spec').read_text(encoding='utf-8')

        self.assertIn('db.sqlite3', spec)
        self.assertIn('media', spec)
        self.assertIn('desktop/windows_launcher.py', spec)

    def test_windows_build_scripts_reference_pyinstaller_spec(self):
        build_bat = Path(
            settings.BASE_DIR,
            'scripts',
            'windows',
            'build_windows_bundle.bat',
        ).read_text(encoding='utf-8')
        build_ps1 = Path(
            settings.BASE_DIR,
            'scripts',
            'windows',
            'build_windows_bundle.ps1',
        ).read_text(encoding='utf-8')

        self.assertIn('windows_launcher.spec', build_bat)
        self.assertIn('windows_launcher.spec', build_ps1)


class LayoutLocalUserBootstrapScriptTests(TestCase):
    def test_bootstrap_local_user_creates_normal_user(self):
        from scripts.bootstrap_local_user import bootstrap_local_user

        result = bootstrap_local_user('compa', 'clave123')

        self.assertTrue(result['created'])
        user = get_user_model().objects.get(username='compa')
        self.assertFalse(user.is_superuser)
        self.assertFalse(user.is_staff)

    def test_bootstrap_local_user_is_idempotent(self):
        from scripts.bootstrap_local_user import bootstrap_local_user

        bootstrap_local_user('compa', 'clave123')
        result = bootstrap_local_user('compa', 'otra-clave')

        self.assertFalse(result['created'])
        self.assertEqual(get_user_model().objects.filter(username='compa').count(), 1)


class LayoutWindowsGitBootstrapScriptTests(SimpleTestCase):
    def test_clone_and_run_script_uses_localappdata_install_dir(self):
        script = Path(
            settings.BASE_DIR,
            'scripts',
            'windows',
            'clone_and_run.ps1',
        ).read_text(encoding='utf-8')

        self.assertIn('$env:LOCALAPPDATA', script)
        self.assertIn('WebVTES', script)

    def test_clone_and_run_script_clones_repo_and_bootstraps_user(self):
        script = Path(
            settings.BASE_DIR,
            'scripts',
            'windows',
            'clone_and_run.ps1',
        ).read_text(encoding='utf-8')

        self.assertIn('git clone', script)
        self.assertIn('bootstrap_local_user.py', script)
        self.assertNotIn('git pull', script)

    def test_batch_launcher_delegates_to_clone_and_run_powershell_script(self):
        launcher = Path(settings.BASE_DIR, 'run_windows_clone.bat').read_text(encoding='utf-8')

        self.assertIn('clone_and_run.ps1', launcher)
        self.assertIn('powershell', launcher.lower())


class LayoutEditorAccessTests(TestCase):
    def test_editor_requires_login(self):
        response = self.client.get('/layouts/')
        self.assertEqual(response.status_code, 302)


class LayoutApiListCreateTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(username='editor', password='secret')
        self.other_user = user_model.objects.create_user(username='other', password='secret')

    def test_list_returns_only_current_user_layouts(self):
        own_layout = UserLayout.objects.create(
            user=self.user,
            name='Propio',
            card_type='cripta',
            config={},
            is_default=False,
        )
        UserLayout.objects.create(
            user=self.other_user,
            name='Ajeno',
            card_type='cripta',
            config={},
            is_default=False,
        )

        self.client.force_login(self.user)
        response = self.client.get('/layouts/api/list', {'card_type': 'cripta'})

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual({layout['id'] for layout in payload['layouts']}, {
            own_layout.id,
            UserLayout.objects.get(user=self.user, card_type='cripta', is_default=True).id,
        })

    def test_create_builds_layout_from_classic_seed(self):
        self.client.force_login(self.user)
        response = self.client.post('/layouts/api/create', {
            'name': 'Mi classic',
            'card_type': 'cripta',
        })

        self.assertEqual(response.status_code, 201)
        created = UserLayout.objects.get(user=self.user, name='Mi classic', card_type='cripta')
        self.assertIn('carta', created.config)
        self.assertEqual(created.config['carta']['width'], 745)
        self.assertEqual(created.config['carta']['height'], 1040)

    def test_create_builds_libreria_layout_with_normalized_stack_boxes(self):
        self.client.force_login(self.user)
        response = self.client.post('/layouts/api/create', {
            'name': 'Mi libreria',
            'card_type': 'libreria',
        })

        self.assertEqual(response.status_code, 201)
        payload = response.json()['layout']['config']
        self.assertIn('box', payload['disciplinas'])
        self.assertIn('box', payload['simbolos'])

        created = UserLayout.objects.get(user=self.user, name='Mi libreria', card_type='libreria')
        self.assertIn('box', created.config['disciplinas'])
        self.assertIn('box', created.config['simbolos'])

    def test_list_normalizes_legacy_libreria_config_for_editor(self):
        own_layout = UserLayout.objects.create(
            user=self.user,
            name='Libreria legacy',
            card_type='libreria',
            config=load_classic_seed('libreria'),
            is_default=False,
        )

        self.client.force_login(self.user)
        response = self.client.get('/layouts/api/list', {'card_type': 'libreria'})

        self.assertEqual(response.status_code, 200)
        payload = response.json()['layouts']
        own_payload = next(layout for layout in payload if layout['id'] == own_layout.id)
        self.assertEqual(len(payload), 2)
        self.assertIn('box', own_payload['config']['disciplinas'])
        self.assertIn('box', own_payload['config']['simbolos'])

    def test_detail_rejects_other_user_layout(self):
        other_layout = UserLayout.objects.create(
            user=self.other_user,
            name='Privado',
            card_type='cripta',
            config={},
            is_default=False,
        )

        self.client.force_login(self.user)
        response = self.client.get(f'/layouts/api/detail/{other_layout.id}')

        self.assertEqual(response.status_code, 404)


class LayoutConfigValidationTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='config-user', password='secret')
        self.layout = UserLayout.objects.create(
            user=self.user,
            name='Editable',
            card_type='cripta',
            config=load_classic_seed('cripta'),
            is_default=False,
        )

    def test_update_config_rejects_invalid_payload(self):
        invalid_config = deepcopy(self.layout.config)
        invalid_config['carta']['width'] = -10

        self.client.force_login(self.user)
        response = self.client.post(
            '/layouts/api/update-config',
            data=json.dumps({
                'layout_id': self.layout.id,
                'config': invalid_config,
            }),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 400)
        self.layout.refresh_from_db()
        self.assertNotEqual(self.layout.config['carta']['width'], -10)

    def test_update_config_accepts_valid_payload(self):
        valid_config = deepcopy(self.layout.config)
        valid_config['carta']['width'] = 900

        self.client.force_login(self.user)
        response = self.client.post(
            '/layouts/api/update-config',
            data=json.dumps({
                'layout_id': self.layout.id,
                'config': valid_config,
            }),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        self.layout.refresh_from_db()
        self.assertEqual(self.layout.config['carta']['width'], 900)

    def test_update_config_accepts_v2_payload(self):
        valid_config = normalize_layout_config('cripta', deepcopy(self.layout.config))
        valid_config['nombre']['rules']['align'] = 'right'
        valid_config['nombre']['box']['width'] = 320

        self.client.force_login(self.user)
        response = self.client.post(
            '/layouts/api/update-config',
            data=json.dumps({
                'layout_id': self.layout.id,
                'config': valid_config,
            }),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        self.layout.refresh_from_db()
        self.assertEqual(self.layout.config['nombre']['rules']['align'], 'right')

    def test_update_config_normalizes_square_symbol_layers(self):
        valid_config = normalize_layout_config('cripta', deepcopy(self.layout.config))
        valid_config['clan']['box'] = {'x': 20, 'y': 30, 'width': 80, 'height': 120}
        valid_config['senda']['box'] = {'x': 55, 'y': 65, 'width': 90, 'height': 70}
        valid_config['coste']['box'] = {'x': 610, 'y': 820, 'width': 64, 'height': 96}

        self.client.force_login(self.user)
        response = self.client.post(
            '/layouts/api/update-config',
            data=json.dumps({
                'layout_id': self.layout.id,
                'config': valid_config,
            }),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        saved = response.json()['layout']['config']
        self.assertEqual(saved['clan']['box']['width'], saved['clan']['box']['height'])
        self.assertEqual(saved['clan']['size'], saved['clan']['box']['width'])
        self.assertEqual(saved['senda']['box']['width'], saved['senda']['box']['height'])
        self.assertEqual(saved['senda']['size'], saved['senda']['box']['width'])
        self.assertEqual(saved['coste']['box']['width'], saved['coste']['box']['height'])
        self.assertEqual(saved['coste']['size'], saved['coste']['box']['width'])


class LayoutConfigBoxSchemaTests(TestCase):
    def test_normalize_legacy_config_adds_box_for_nombre(self):
        legacy = load_classic_seed('cripta')

        normalized = normalize_layout_config('cripta', legacy)

        self.assertIn('box', normalized['nombre'])
        self.assertEqual(normalized['nombre']['box']['x'], legacy['nombre']['x'])

    def test_normalize_applies_text_defaults_for_nombre_and_ilustrador(self):
        normalized = normalize_layout_config('cripta', load_classic_seed('cripta'))

        self.assertEqual(normalized['nombre']['rules']['align'], 'center')
        self.assertEqual(normalized['ilustrador']['rules']['align'], 'left')

    def test_normalize_cripta_materializes_disciplina_anchor_box(self):
        normalized = normalize_layout_config('cripta', load_classic_seed('cripta'))

        self.assertEqual(normalized['disciplinas']['box']['x'], normalized['disciplinas']['x'])
        self.assertEqual(normalized['disciplinas']['box']['width'], normalized['disciplinas']['size'])
        self.assertEqual(normalized['disciplinas']['box']['height'], normalized['disciplinas']['spacing'])
        self.assertEqual(normalized['disciplinas']['rules']['gap_from_habilidad'], 0)

    def test_normalize_libreria_materializes_disciplina_anchor_box(self):
        normalized = normalize_layout_config('libreria', load_classic_seed('libreria'))

        self.assertEqual(normalized['disciplinas']['box']['x'], normalized['disciplinas']['x'])
        self.assertEqual(normalized['disciplinas']['box']['y'], normalized['disciplinas']['y'])
        self.assertEqual(normalized['disciplinas']['box']['width'], normalized['disciplinas']['size'])
        self.assertEqual(normalized['disciplinas']['box']['height'], normalized['disciplinas']['spacing'])
        self.assertEqual(normalized['disciplinas']['rules']['gap_from_habilidad'], 0)

    def test_normalize_libreria_materializes_box_for_simbolos(self):
        normalized = normalize_layout_config('libreria', load_classic_seed('libreria'))

        self.assertEqual(normalized['simbolos']['box']['x'], normalized['simbolos']['x'])
        self.assertEqual(normalized['simbolos']['box']['y'], normalized['simbolos']['y'])
        self.assertEqual(normalized['simbolos']['box']['width'], normalized['simbolos']['size'])
        self.assertEqual(normalized['simbolos']['box']['height'], normalized['simbolos']['spacing'] * 3)

    def test_normalize_libreria_habilidad_defaults_to_bottom_anchor_margin_box_semantics(self):
        normalized = normalize_layout_config('libreria', load_classic_seed('libreria'))

        self.assertEqual(normalized['habilidad']['rules']['box_semantics'], 'bottom_anchor_margin')

    def test_normalize_libreria_preserves_bottom_anchor_margin_box_semantics(self):
        config = load_classic_seed('libreria')
        config['habilidad']['rules'] = {'box_semantics': 'bottom_anchor_margin'}

        normalized = normalize_layout_config('libreria', config)

        self.assertEqual(normalized['habilidad']['rules']['box_semantics'], 'bottom_anchor_margin')


class LayoutConfigValidationV2Tests(TestCase):
    def test_validate_rejects_invalid_align(self):
        config = normalize_layout_config('cripta', load_classic_seed('cripta'))
        config['nombre']['rules']['align'] = 'diagonal'

        with self.assertRaises(LayoutValidationError):
            validate_layout_config('cripta', config)

    def test_validate_rejects_box_out_of_range(self):
        config = normalize_layout_config('cripta', load_classic_seed('cripta'))
        config['nombre']['box']['width'] = -1

        with self.assertRaises(LayoutValidationError):
            validate_layout_config('cripta', config)

    def test_validate_rejects_invalid_disciplinas_anchor_mode(self):
        config = normalize_layout_config('cripta', load_classic_seed('cripta'))
        config['disciplinas']['rules'] = {'anchor_mode': 'diagonal'}

        with self.assertRaises(LayoutValidationError):
            validate_layout_config('cripta', config)

    def test_validate_rejects_invalid_cripta_disciplinas_gap_from_habilidad(self):
        config = normalize_layout_config('cripta', load_classic_seed('cripta'))
        config['disciplinas']['rules']['gap_from_habilidad'] = -1

        with self.assertRaises(LayoutValidationError):
            validate_layout_config('cripta', config)

    def test_validate_rejects_invalid_libreria_disciplinas_gap_from_habilidad(self):
        config = normalize_layout_config('libreria', load_classic_seed('libreria'))
        config['disciplinas']['rules']['gap_from_habilidad'] = -1

        with self.assertRaises(LayoutValidationError):
            validate_layout_config('libreria', config)

    def test_validate_libreria_rejects_invalid_disciplinas_box(self):
        config = normalize_layout_config('libreria', load_classic_seed('libreria'))
        config['disciplinas']['box']['x'] = -1

        with self.assertRaises(LayoutValidationError):
            validate_layout_config('libreria', config)

    def test_validate_libreria_rejects_invalid_simbolos_box(self):
        config = normalize_layout_config('libreria', load_classic_seed('libreria'))
        config['simbolos']['box']['x'] = -1

        with self.assertRaises(LayoutValidationError):
            validate_layout_config('libreria', config)

    def test_validate_rejects_invalid_habilidad_box(self):
        config = normalize_layout_config('libreria', load_classic_seed('libreria'))
        config['habilidad']['box'] = {'x': 170, 'y': 600, 'width': -1, 'height': 180}

        with self.assertRaises(LayoutValidationError):
            validate_layout_config('libreria', config)

    def test_validate_rejects_invalid_libreria_habilidad_box_semantics(self):
        config = normalize_layout_config('libreria', load_classic_seed('libreria'))
        config['habilidad']['rules']['box_semantics'] = 'nope'

        with self.assertRaises(LayoutValidationError):
            validate_layout_config('libreria', config)

    def test_validate_accepts_libreria_habilidad_legacy_box_semantics(self):
        config = normalize_layout_config('libreria', load_classic_seed('libreria'))
        config['habilidad']['rules']['box_semantics'] = 'legacy'

        validate_layout_config('libreria', config)

    def test_validate_accepts_large_cripta_y_gap_within_canvas_range(self):
        config = normalize_layout_config('cripta', load_classic_seed('cripta'))
        config['cripta']['y_gap'] = 420

        validate_layout_config('cripta', config)


class LayoutManagementApiTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='manage-user', password='secret')
        self.layout = UserLayout.objects.create(
            user=self.user,
            name='Original',
            card_type='cripta',
            config=load_classic_seed('cripta'),
            is_default=False,
        )

    def test_rename_layout(self):
        self.client.force_login(self.user)
        response = self.client.post(
            '/layouts/api/rename',
            data=json.dumps({'layout_id': self.layout.id, 'name': 'Renombrado'}),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        self.layout.refresh_from_db()
        self.assertEqual(self.layout.name, 'Renombrado')

    def test_delete_layout(self):
        self.client.force_login(self.user)
        response = self.client.post(
            '/layouts/api/delete',
            data=json.dumps({'layout_id': self.layout.id}),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(UserLayout.objects.filter(id=self.layout.id).exists())

    def test_set_default_switches_previous_default_off(self):
        previous_default = UserLayout.objects.get(
            user=self.user,
            card_type='libreria',
            is_default=True,
        )
        next_default = UserLayout.objects.create(
            user=self.user,
            name='Default nuevo',
            card_type='libreria',
            config=load_classic_seed('libreria'),
            is_default=False,
        )

        self.client.force_login(self.user)
        response = self.client.post(
            '/layouts/api/set-default',
            data=json.dumps({'layout_id': next_default.id}),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        previous_default.refresh_from_db()
        next_default.refresh_from_db()
        self.assertFalse(previous_default.is_default)
        self.assertTrue(next_default.is_default)


class LayoutPreviewApiTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='preview-user', password='secret')
        self.client.force_login(self.user)

    def test_preview_for_cripta_returns_clean_fixed_source(self):
        layout = UserLayout.objects.create(
            user=self.user,
            name='Preview Cripta',
            card_type='cripta',
            config=load_classic_seed('cripta'),
            is_default=False,
        )

        with patch(
            'apps.layouts.views._prepare_render_source_from_path',
            create=True,
            return_value='/media/layout_preview_sources/mimir.png',
        ) as mock_prepare, patch(
            'apps.layouts.views._render_carta_from_path',
            create=True,
        ) as mock_render:
            response = self.client.post(
                '/layouts/api/preview',
                data=json.dumps({'card_type': 'cripta', 'layout_config': layout.config}),
                content_type='application/json',
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['imagen_url'], '/media/layout_preview_sources/mimir.png')
        self.assertTrue(mock_prepare.call_args.args[0].endswith('static/layouts/images/Mimir.png'))
        self.assertEqual(mock_prepare.call_args.kwargs['target_name'], 'Mimir')
        mock_render.assert_not_called()

    def test_preview_for_libreria_returns_clean_fixed_source(self):
        layout = UserLayout.objects.create(
            user=self.user,
            name='Preview Libreria',
            card_type='libreria',
            config=load_classic_seed('libreria'),
            is_default=False,
        )

        with patch(
            'apps.layouts.views._prepare_render_source_from_path',
            create=True,
            return_value='/media/layout_preview_sources/muestra-de-libreria.png',
        ) as mock_prepare, patch(
            'apps.layouts.views._render_carta_from_path',
            create=True,
        ) as mock_render:
            response = self.client.post(
                '/layouts/api/preview',
                data=json.dumps({'card_type': 'libreria', 'layout_config': layout.config}),
                content_type='application/json',
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['imagen_url'], '/media/layout_preview_sources/muestra-de-libreria.png')
        self.assertTrue(mock_prepare.call_args.args[0].endswith('static/layouts/images/44. magnum.png'))
        self.assertEqual(mock_prepare.call_args.kwargs['target_name'], '.44 Magnum')
        mock_render.assert_not_called()


class LayoutEditorTemplateTests(TestCase):
    def test_editor_template_contains_required_mount_points(self):
        user = get_user_model().objects.create_user(username='editor-ui', password='secret')
        self.client.force_login(user)
        response = self.client.get('/layouts/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="layout-stage"')
        self.assertContains(response, 'id="layout-properties"')

    def test_editor_template_contains_preview_mount_points(self):
        user = get_user_model().objects.create_user(username='editor-preview-ui', password='secret')
        self.client.force_login(user)
        response = self.client.get('/layouts/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="layout-stage-viewport"')
        self.assertContains(response, 'id="layout-canvas"')
        self.assertContains(response, 'id="layout-preview-image"')


class LayoutEditorAdvancedControlsTests(TestCase):
    def test_editor_contains_text_rule_controls(self):
        user = get_user_model().objects.create_user(username='rules-ui', password='secret')
        self.client.force_login(user)

        response = self.client.get('/layouts/')

        self.assertContains(response, 'id="prop-align"')
        self.assertContains(response, 'id="prop-min-font-size"')
        self.assertContains(response, 'id="prop-ellipsis-enabled"')

    def test_editor_contains_fixed_disciplinas_control(self):
        user = get_user_model().objects.create_user(username='disc-ui', password='secret')
        self.client.force_login(user)

        response = self.client.get('/layouts/')

        self.assertContains(response, 'id="prop-disciplinas-fixed"')


class LayoutEditorStaticAssetTests(SimpleTestCase):
    def test_editor_script_defines_semantic_layer_profiles(self):
        script = Path(settings.BASE_DIR, 'static', 'layouts', 'editor.js').read_text(encoding='utf-8')

        self.assertIn('const layerProfiles', script)
        self.assertIn('fixedFont: true', script)
        self.assertIn('square: true', script)

    def test_editor_script_creates_visible_layer_labels(self):
        script = Path(settings.BASE_DIR, 'static', 'layouts', 'editor.js').read_text(encoding='utf-8')

        self.assertIn('layout-layer__label', script)
        self.assertIn("label.textContent = layerName", script)

    def test_editor_css_defines_visible_labeled_overlays(self):
        stylesheet = Path(settings.BASE_DIR, 'static', 'layouts', 'editor.css').read_text(encoding='utf-8')

        self.assertIn('.layout-layer__label', stylesheet)
        self.assertIn('border: 2px solid', stylesheet)
        self.assertIn('background: rgba(', stylesheet)
        self.assertIn('pointer-events: none', stylesheet)

    def test_editor_script_defines_fixed_bottom_disciplinas_toggle(self):
        script = Path(settings.BASE_DIR, 'static', 'layouts', 'editor.js').read_text(encoding='utf-8')

        self.assertIn('prop-disciplinas-fixed', script)
        self.assertIn('fixed_bottom', script)

    def test_editor_script_defines_libreria_habilidad_bottom_anchor_margin_flow(self):
        script = Path(settings.BASE_DIR, 'static', 'layouts', 'editor.js').read_text(encoding='utf-8')

        self.assertIn('box_semantics', script)
        self.assertIn('bottom_anchor_margin', script)
        self.assertIn("boxSemantics === 'legacy'", script)
        self.assertIn("state.cardType === 'libreria'", script)
        self.assertIn("layerName === 'habilidad'", script)

    def test_editor_script_persists_disciplina_anchor_and_gap_for_all_card_types(self):
        script = Path(settings.BASE_DIR, 'static', 'layouts', 'editor.js').read_text(encoding='utf-8')

        self.assertIn('section.rules.gap_from_habilidad', script)
        self.assertIn('normalizedFrame.y + normalizedFrame.height', script)
        self.assertIn('propY.value = frame.y + frame.height', script)
        self.assertIn('getHabilidadTop', script)
        self.assertNotIn("layerName === 'disciplinas' && state.cardType === 'cripta'", script)

    def test_editor_script_clamps_cripta_y_gap_to_valid_range(self):
        script = Path(settings.BASE_DIR, 'static', 'layouts', 'editor.js').read_text(encoding='utf-8')

        self.assertIn('const MAX_CRIPTA_Y_GAP = 3000', script)
        self.assertIn('function clampCriptaYGap(yGap)', script)
        self.assertIn('clampCriptaYGap(Number(section.y_gap || 1))', script)
        self.assertIn('section.y_gap = clampCriptaYGap(', script)

    def test_editor_script_clamps_common_frame_coordinates_before_persisting_box(self):
        script = Path(settings.BASE_DIR, 'static', 'layouts', 'editor.js').read_text(encoding='utf-8')

        self.assertIn('const clampedFrame = {', script)
        self.assertIn('x: Math.max(0, Math.round(normalizedFrame.x))', script)
        self.assertIn('y: Math.max(0, Math.round(normalizedFrame.y))', script)
        self.assertIn('section.x = clampedFrame.x', script)
        self.assertIn('section.y = clampedFrame.y', script)
        self.assertIn("x: clampedFrame.x", script)
        self.assertIn("y: clampedFrame.y", script)

    def test_editor_script_prevents_negative_habilidad_box_y_from_properties_panel(self):
        script = Path(settings.BASE_DIR, 'static', 'layouts', 'editor.js').read_text(encoding='utf-8')

        self.assertIn("layerName === 'habilidad'", script)
        self.assertIn('section.box = {', script)
        self.assertIn('y: clampedFrame.y', script)


class EndToEndLayoutFlowTests(TestCase):
    def test_user_can_create_edit_set_default_and_render_with_layout(self):
        user = get_user_model().objects.create_user(username='e2e-user', password='secret')
        self.client.force_login(user)

        create_response = self.client.post(
            '/layouts/api/create',
            data=json.dumps({'name': 'Flujo E2E', 'card_type': 'cripta'}),
            content_type='application/json',
        )
        self.assertEqual(create_response.status_code, 201)
        layout_id = create_response.json()['layout']['id']

        detail_response = self.client.get(f'/layouts/api/detail/{layout_id}')
        self.assertEqual(detail_response.status_code, 200)
        config = detail_response.json()['layout']['config']
        config['carta']['width'] = 910

        update_response = self.client.post(
            '/layouts/api/update-config',
            data=json.dumps({'layout_id': layout_id, 'config': config}),
            content_type='application/json',
        )
        self.assertEqual(update_response.status_code, 200)

        default_response = self.client.post(
            '/layouts/api/set-default',
            data=json.dumps({'layout_id': layout_id}),
            content_type='application/json',
        )
        self.assertEqual(default_response.status_code, 200)

        with patch('apps.srv_textos.views._render_carta', return_value=('/media/render/e2e.png', None)) as mock_render:
            render_response = self.client.post(
                '/srv-textos/render-texto/',
                data=json.dumps({
                    'card_type': 'cripta',
                    'layout_id': layout_id,
                    'layout_name': '',
                    'imagen_url': '/media/recortes/e2e.png',
                    'nombre': 'Carta',
                    'clan': '',
                    'senda': '',
                    'disciplinas': [],
                    'simbolos': [],
                    'habilidad': '',
                    'coste': '',
                    'cripta': '',
                    'ilustrador': '',
                }),
                content_type='application/json',
            )

        self.assertEqual(render_response.status_code, 200)
        self.assertEqual(render_response.json()['imagen_url'], '/media/render/e2e.png')
        self.assertEqual(mock_render.call_count, 1)
        self.assertEqual(mock_render.call_args.kwargs['layout_config']['carta']['width'], 910)
