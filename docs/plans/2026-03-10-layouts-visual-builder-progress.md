# Visual Layouts Builder - Progress Log

## Snapshot
- Date: 2026-03-10
- Branch: `feat/layouts-app`
- Worktree: `/home/juanrrafdez/VtesProxi/.worktrees/layouts-app`
- HEAD: `1c3bb7d`
- Status at snapshot: clean (`git status` sin cambios pendientes antes de este documento)

## Completed Tasks
- Task 1 complete: app `apps.layouts` + modelo `UserLayout` + constraints + migracion inicial.
- Task 2 complete: ruta protegida `/layouts/` + template inicial + enlace en sidebar.
- Task 3 complete: API `list/create/detail` con ownership y semilla desde `layouts.json`.
- Task 4 complete: API `update-config` + validacion de esquema/rangos en backend.
- Task 5 complete: API `rename/delete/set-default` con update atomico de default por usuario/tipo.
- Task 6 complete: resolver de layout en `srv_textos` con prioridad `override -> layout_id -> default -> classic` y control de ownership.

## Commits Applied
- `590cf36` feat: add user layout model with constraints
- `a70051e` feat: add authenticated layouts editor route
- `a836e36` feat: add list/create/detail layout api endpoints
- `7597f1b` feat: validate and persist layout config updates
- `82c3f08` feat: add rename delete and set-default layout endpoints
- `1c3bb7d` feat: resolve render layout from user config with priority

## Verification Evidence
- `python manage.py test apps.layouts.tests.UserLayoutModelTests -v 2` -> PASS
- `python manage.py test apps.layouts.tests.LayoutEditorAccessTests -v 2` -> PASS
- `python manage.py test apps.layouts.tests.LayoutApiListCreateTests -v 2` -> PASS
- `python manage.py test apps.layouts.tests.LayoutConfigValidationTests -v 2` -> PASS
- `python manage.py test apps.layouts.tests.LayoutManagementApiTests -v 2` -> PASS
- `python manage.py test apps.srv_textos.tests.LayoutResolverPriorityTests -v 2` -> PASS

## Remaining Tasks (Plan)
- Task 7 pending: integrar selector de layouts en vistas Cripta/Libreria y enviar `layout_id` en render.
- Task 8 pending: editor visual drag/resize con Interact.js + assets `static/layouts`.
- Task 9 pending: test E2E del flujo completo.
- Task 10 pending: verificacion final completa + documentacion final.

## Resume Tomorrow
1. `cd /home/juanrrafdez/VtesProxi/.worktrees/layouts-app`
2. `git status --short --branch`
3. `/home/juanrrafdez/VtesProxi/.venv/bin/python manage.py test apps.srv_textos.tests.ImportViewsLayoutContextTests -v 2`
4. Ejecutar Task 7 en ciclo TDD (rojo -> verde -> commit).

## Notes
- En este entorno `python` no existe; usar `python3` o `/home/juanrrafdez/VtesProxi/.venv/bin/python`.
- Endpoints de `layouts` soportan payload `application/json` y form-encoded.
- `_resolve_layout_config` en `apps/srv_textos/views.py` es el punto unico para priorizar layout.
