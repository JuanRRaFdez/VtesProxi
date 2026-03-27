# AGENTS.md

## Repo Snapshot

- Main stack: Django 6.0 + DRF + SQLite.
- Primary code areas: `webvtes/`, `apps/`, `scripts/`, `desktop/`, `static/`.
- Quality gate is Python-first. There is a root `package.json`, but active repo automation is driven by `Makefile`, `pyproject.toml`, `.pre-commit-config.yaml`, and `.github/workflows/quality.yml`.
- No repo-level Cursor rules were found in `.cursor/rules/` or `.cursorrules`.
- No Copilot instructions were found in `.github/copilot-instructions.md`.

## Environment And Safety

- Use the repo virtualenv when available: `.venv/bin/python`, `.venv/bin/ruff`, `.venv/bin/mypy`, `.venv/bin/pre-commit`.
- Default Django settings module is `webvtes.settings` via `manage.py`.
- Local env defaults are documented in `README.md`: `DJANGO_ENV=local` and `DJANGO_ALLOW_LOCAL_SECRET_FALLBACK=1` allow local startup without an explicit secret.
- Outside local/desktop/dev, `DJANGO_SECRET_KEY` is mandatory. Do not change this fail-fast behavior casually.
- Do not build the Windows bundle unless the task is explicitly about packaging. Final Windows bundle creation is meant to happen on Windows.

## Source Of Truth For Commands

- `Makefile` defines the canonical quality commands.
- `pyproject.toml` defines Ruff and MyPy behavior.
- `.pre-commit-config.yaml` mirrors the same lint/format/typecheck contract.
- `.github/workflows/quality.yml` is the CI source of truth.
- `README.md` contains the verified local workflow and targeted test examples.

## Core Commands

- Install deps: `python -m pip install -r requirements.txt -r requirements-dev.txt`
- Lint: `make lint`
- Format: `make format`
- Typecheck: `make typecheck`
- Django system check: `make check`
- Full test suite: `make test`
- Full local gate: `make quality`
- Pre-commit on all files: `.venv/bin/pre-commit run --all-files`
- Ruff debt policy check: `make policy-check`

## What Each Command Really Runs

- `make lint` -> `ruff check webvtes scripts desktop`
- `make format` -> `ruff format webvtes scripts desktop`
- `make typecheck` -> `mypy --config-file pyproject.toml`
- `make check` -> `python manage.py check`
- `make test` -> `python manage.py test`
- `make quality` -> lint + typecheck + check + test

## Single-Test / Narrow-Scope Recipes

- One app test module: `.venv/bin/python manage.py test apps.layouts.tests -v 2`
- Another app module: `.venv/bin/python manage.py test apps.srv_textos.tests -v 2`
- One test class: `.venv/bin/python manage.py test apps.layouts.tests.LayoutUserBootstrapTests -v 2`
- One specific test method: `.venv/bin/python manage.py test apps.srv_textos.tests.HabilidadRenderAlignmentTests.test_render_habilidad_libreria_uses_same_common_renderer_path_as_cripta -v 2`
- Multiple focused modules/classes are commonly run together: `.venv/bin/python manage.py test apps.layouts.tests apps.srv_textos.tests -v 1`
- Settings-only tests also use dotted paths: `.venv/bin/python manage.py test webvtes.tests.test_settings_secret_key.SecretKeySettingsTests -v 2`
- Desktop settings check: `.venv/bin/python manage.py check --settings=webvtes.settings_desktop`

## CI Expectations

- CI workflow name: `quality-gate`.
- CI splits into `static` and `runtime` jobs.
- `static` runs `make lint` and `make typecheck`.
- `runtime` runs `make check` and `make test`.
- Successful CI emits `quality-evidence.json`; see `docs/quality/ci-evidence.md` if your task touches verify/archive flows.

## Style Rules From Automation

- Python version target is 3.12.
- Ruff line length is 100.
- Ruff lint rules enabled: `E`, `F`, `I`.
- Ruff ignores `I001` and `F405`; import sorting is not strictly enforced, so preserve surrounding style unless you are already cleaning imports.
- Ruff excludes `.git`, `.venv`, and `media`.
- MyPy currently gates `webvtes`, `scripts`, and `desktop` only.
- `apps/layouts` and `apps/srv_textos` are explicitly outside the hard MyPy gate for now; do not claim repo-wide type coverage.
- Pre-commit enforces Ruff, Ruff format, EOF fixer, trailing whitespace cleanup, merge-conflict checks, YAML validation, and MyPy.

## Python Conventions Observed In Code

- Use 4-space indentation and let Ruff format Python.
- Prefer `snake_case` for functions/variables and `PascalCase` for classes and Django test classes.
- Private module helpers are prefixed with `_` (for example `_resolve_layout_config`, `_expect_number`, `_safe_card_filename_base`).
- Keep validation logic explicit and close to the data it validates; this repo prefers small helper functions over clever abstractions.
- Raise domain-specific exceptions for validation/ownership flows (`LayoutValidationError`, `LayoutOwnershipError`) and convert them at HTTP boundaries.
- When re-raising after parsing/coercion failures, preserve cause with `raise ... from exc`.
- In typed modules (`scripts/ruff_policy_check.py`), prefer modern typing syntax like `dict[str, ...]` and `list[str]`.
- Do not introduce broad type-checking changes in `apps/` unless the task is specifically about expanding MyPy coverage.

## Imports

- Typical grouping in Python files is: stdlib -> Django/third-party -> local app imports.
- The codebase is not perfectly sorted because Ruff ignores `I001`; match the local file unless you are already touching the import block.
- Prefer absolute app imports such as `from apps.layouts.models import UserLayout`.

## Django / HTTP Conventions

- Function-based views are common; follow existing patterns before introducing class-based views.
- JSON endpoints usually guard the HTTP method first and return `JsonResponse({"error": ...}, status=...)` for failures.
- Error messages are user-facing and usually written in Spanish; keep wording consistent with nearby endpoints.
- For authenticated UI/API endpoints, `@login_required` is the default pattern.
- Use `get_object_or_404(...)` and constrained queryset filters for user-owned resources.
- Wrap multi-row default-switch operations in `transaction.atomic()`.
- Normalize request payloads early (`_get_payload`, card-type normalization, layout-id coercion) and validate before touching persistence.

## Models / Services / Data

- Business rules often live in service/helper modules rather than in fat models.
- `JSONField` configs are normalized before validation and before serialization back to the client.
- Preserve legacy compatibility when modifying layout schema behavior; `normalize_layout_config()` exists specifically for legacy-to-v2 handling.
- When adding constraints or defaults, mirror the existing explicitness in model constraints and validation helpers.

## Frontend / Templates / Static Files

- Templates live under app templates directories; shared shell is `apps/cripta/templates/base.html`.
- The UI uses Bootstrap CDN plus htmx in the base template.
- Layout editor assets are served from `static/layouts/`.
- Repo JS is plain browser JS, not TypeScript or bundler-managed code.
- Existing JS style uses IIFE wrappers, semicolons, single quotes, DOM lookups at the top, and helper functions for state updates.
- Existing CSS is plain CSS with component-like class names such as `.layout-editor-*` and responsive tweaks via simple media queries.
- There is no ESLint/Prettier/TS config in the repo; be extra conservative when editing JS/CSS and keep changes small and readable.

## Testing Conventions

- Test framework is Django's test runner with `TestCase` and `SimpleTestCase`.
- Name test classes `*Tests` and test methods `test_*`.
- Use `setUp()` for shared fixture creation when it improves readability.
- Use `self.client` / `self.client.force_login(...)` for request tests.
- Use `response.json()` for JSON assertions.
- Use `unittest.mock.patch` heavily for external/process boundaries and expensive rendering helpers.
- Keep tests specific and scenario-driven; many tests encode exact regression behavior in long descriptive names.
- Prefer targeted module/class/test runs while iterating, then run the broader related module(s).

## Repo-Specific Gotchas

- `make lint` and `make format` only cover `webvtes`, `scripts`, and `desktop`, not all `apps/`; inspect changed app files yourself and use targeted tests.
- The root `npm test` runs `jest`, but there is no repo-level JS test config or active JS test suite to rely on. Treat Node tooling as secondary unless your task clearly needs it.
- `media/` is excluded from Ruff and should not be reformatted or treated as source.
- Packaging scripts and desktop runtime behavior are covered by Python tests in `apps/layouts/tests.py`; use those before touching Windows packaging flows.

## Suggested Agent Workflow

- Read the relevant app/service/tests before editing.
- Prefer the narrowest Django test command that exercises your change.
- If you touched `webvtes`, `scripts`, or `desktop`, run the relevant make target(s) because those areas are in the active type/lint gate.
- Before finishing substantial work, run the smallest convincing set of checks and state exactly what you verified.
