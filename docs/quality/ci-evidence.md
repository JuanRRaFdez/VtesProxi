# CI Evidence Contract (`quality-gate`)

## Objetivo

Definir una evidencia CI estable para que verify/archive se cierre con pruebas trazables del workflow `quality-gate`, evitando cierres basados solo en narrativa.

## Evidencia canonica

Cada run exitoso de `quality-gate` debe producir un `quality-evidence.json` con estos campos:

- `run_url`
- `run_id`
- `run_attempt`
- `workflow_name`
- `workflow_ref`
- `repository`
- `event_name`
- `commit_sha`
- `ref`
- `generated_at_utc`
- `jobs.static.name`
- `jobs.static.conclusion`
- `jobs.runtime.name`
- `jobs.runtime.conclusion`

Ejemplo de bloque portable para artifacts verify/archive:

```yaml
ci_evidence:
  run_url: https://github.com/<org>/<repo>/actions/runs/<run_id>
  run_id: "<run_id>"
  run_attempt: "<run_attempt>"
  workflow_name: quality-gate
  required_jobs:
    - static
    - runtime
  commit_sha: "<40-char-sha>"
  observed_at_utc: "<ISO-8601>"
  validation: valid | warning | invalid
```

## Ingestion primaria (gh CLI)

Comando principal:

```bash
gh run view <run_id> --json headSha,workflowName,jobs,conclusion,url
```

Checklist de validacion obligatoria:

1. `workflowName` es `quality-gate`.
2. `headSha` coincide con el commit que verify/archive evalua.
3. `conclusion` del run es `success`.
4. Existen jobs `static` y `runtime`.
5. Ambos jobs tienen conclusion `success`.
6. El bloque final guarda SIEMPRE `run_url` y `run_id`.

## Politica de frescura

- Verifica el run exitoso mas reciente del SHA/ref evaluado.
- Si el run no corresponde al commit objetivo o esta obsoleto, el estado no puede ser `valid`.

## Fallback cuando `gh` no esta disponible

Si la CLI/API de GitHub no esta disponible en el entorno de verify/archive:

- Se permite un bloque `ci_evidence` manual con `run_url`, `run_id`, `commit_sha`, `workflow_name` y estado observado de jobs.
- Ese fallback solo puede marcarse como `warning`.
- No se permite cierre warning-free (`valid`) hasta ejecutar validacion primaria con `gh run view`.

Matriz de decision:

| Contexto | Evidencia minima | Estado permitido |
| --- | --- | --- |
| `gh` disponible y validacion completa OK | `run_url`, `run_id`, SHA y jobs validados por API | `valid` |
| `gh` no disponible pero hay evidencia manual consistente | `run_url`, `run_id`, `commit_sha`, jobs declarados | `warning` |
| Evidencia incompleta o inconsistente | falta URL/ID/SHA o jobs requeridos | `invalid` |

## Retencion y trazabilidad

- El artifact de CI puede expirar por retention policy.
- Por eso verify/archive deben conservar referencias duraderas (`run_url`, `run_id`, `commit_sha`) dentro del artifact SDD.
