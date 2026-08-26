# Ejemplos del esquema

Fixtures del gate de M0. `make validate-schema` comprueba que **todo** lo de `valid/`
valida contra `../trajectory.v1.json` y que **todo** lo de `invalid/` es rechazado.

Un ejemplo inválido que empieza a validar es un agujero en el esquema, y rompe el gate
igual que un ejemplo válido que deja de validar.

## `valid/`

| Archivo | Qué demuestra |
|---|---|
| `01-open-trajectory.json` | Trayectoria en curso. Incluye un paso `tool_failure` — la señal decisiva llega por `PostToolUseFailure`, no por `PostToolUse` (spec §5.2). |
| `02-candidate.json` | Consolidada por dream fase 1: tiene `abstraction` y `valid_when`, no tiene `verified`, y se inyecta con peso reducido (spec §6.3). |
| `03-verified-procedure.json` | Promovida por dream fase 2: `verified` completo con `run_id`, `base_commit` presente, peso pleno. Incluye un paso `compact_snapshot`. |
| `04-superseded.json` | Contradicha por una trayectoria posterior. Sobrevive enlazada por `superseded_by` en lugar de borrarse (capacidad B). |

## `invalid/`

Cada archivo viola **una** regla. La razón se documenta acá y no dentro del JSON,
porque el esquema prohíbe campos no declarados en la raíz.

| Archivo | Regla violada |
|---|---|
| `01-missing-required.json` | Faltan `repo_fingerprint` y `redaction`. Sin metadatos de redacción no se persiste (spec §8.2). |
| `02-procedure-without-verified.json` | `status: procedure` con `verified: null`. Sólo lo verificado es procedimiento (spec §4.1, ADR-002). |
| `03-verified-missing-run-id.json` | `verified` sin `run_id`. Sin `run_id` no hay auditoría (ADR-002 §5). |
| `04-abstraction-leaks-path.json` | `abstraction.pattern` contiene un path del repo. Última red contra fuga cross-repo (spec §4.4). |
| `05-bad-step-kind.json` | `kind` fuera del enum. |
| `06-superseded-without-link.json` | `status: superseded` sin `superseded_by`. |
| `07-repo-name-in-clear.json` | `repo_fingerprint` con el nombre del repo en claro en vez del SHA-256. |
| `08-unknown-field.json` | Campo desconocido en la raíz (`verifed`, typo de `verified`). Sin `additionalProperties: false` este typo dejaría la trayectoria sin verificar y con aspecto de verificada. |
