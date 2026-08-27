# nightshift

**A procedural memory layer over the agent's native declarative memory.**

*[Léeme en español](README.es.md)*

> **Status: M3 — capture, retrieval and dream phase 1, as a Claude Code plugin.**
> It captures trajectories from real sessions, redacts them deterministically, injects
> prior ones, and consolidates them nightly with Claude Code itself ([ADR-003](doc/adr/ADR-003-modelo-de-dream.md)).
> **`verify` does not exist**, so nothing reaches `procedure` and nothing injected is
> verified — deliberately labelled as such. The go/no-go benchmark (M4) has its runner,
> its three fixture repos and its agent adapter, and **cannot run**: the pre-registration
> is still a draft. See [Milestones](#milestones).

Claude Code already ships **Auto Memory** (per-repo declarative notes) and **Auto
Dream** (background consolidation). nightshift does **not** replace them and does not
compete on "notes + sleep". It runs on top of them.

> Auto Memory remembers *what is true in this repo*. nightshift remembers *how it was
> found out*, and only promotes it to a procedure when reproducing it passes a gate.

## Why bother — the five capabilities

nightshift only invests where the native memory cannot reach **by design**, not by
immaturity. Anything the harness will plausibly ship next quarter is not a moat, so it
does not go on the roadmap.

| # | Capability | Native | nightshift |
|---|---|---|---|
| A | Procedural memory: causal trajectories (hypothesis → tools → decisive signal → fix) | No. Stores facts | Yes. CTE capture |
| B | Discarded alternatives with preconditions | No. Auto Dream deletes what was contradicted | Yes. `superseded_by` node + `valid_when` |
| C | Cross-repo / cross-harness | No. Sealed per repo | Yes. Trajectory abstraction + `deny_paths` |
| D | Verifiable consolidation: a trajectory becomes a procedure only if reproducing it passes a gate | No. Model judgement | Yes. Dream gated by the user's verifiers |
| E | Pre-`/compact` capture of intermediate reasoning | No | Yes. `PreCompact` hook |

The reasoning behind each row — specifically *why the native memory cannot do it by
design* — is [ADR-001](doc/adr/ADR-001-no-competir-con-auto-dream.md).

## Where this actually shows up

Two cases, both runnable. They are demonstrations, not evidence — and the numbers below
are printed exactly as they came out, including the ones that do not flatter the plugin.

### The same bug wearing another face

Ten bugs in the fixture repo share one cause — a function that decides what "the same
key" means and does not strip invisible characters — and no two share a symptom. One
raises `KeyError` on a key that is right there; another silently splits a customer's
totals in two.

A declarative fact — *"the bug was in `texto.py`"* — is useless for the second one: other
file, other symptom. A procedure — *"when two keys that look identical fail to match,
look for invisibles in the normaliser"* — works for all ten.

[`experimentos/01`](experimentos/01-mismo-bug-otra-cara.sh) runs three rows: no memory,
raw trajectory injected, and consolidated pattern injected. The middle row is the trap —
injecting the raw trace spends context on another problem's steps.

### What was discarded is not lost

Auto Dream **deletes** what gets contradicted. nightshift keeps it, linked to whatever
replaced it, with the precondition under which it applied.

Three weeks later someone proposes raising that timeout again. The declarative fact
—*"the timeout is 2000"*— is true and does not help. The trajectory says: it was tried,
who contradicted it, and what solved it instead.

[`experimentos/02`](experimentos/02-lo-descartado-no-se-pierde.sh) shows the discarded
trajectory surviving as `superseded`, linked, and reconstructable with `why`.

**What the experiments do not show:** that nightshift works. Six sessions are not
evidence — run-to-run variance on the *same* task with no memory available was 8, 13 and
10 tool calls, which is larger than any difference between rows. That is exactly why the
benchmark demands three runs per cell and thresholds frozen in advance. See
[`experimentos/`](experimentos/README.md).

## The project can kill itself

M4 is a pre-registered go/no-go benchmark whose baseline (`S0`) is **Claude Code with
Auto Memory and Auto Dream turned on**, not an agent without memory. If nightshift does
not beat that baseline by the thresholds written in
[`bench/PREREG.md`](bench/PREREG.md) **before any code exists**, the project is frozen
as a spec.

That is a result, not a failure: the spec plus a negative benchmark is publishable.

## What this is not

- Not a replacement, fork or patch of Auto Memory. It never writes under
  `~/.claude/projects/*/memory/`; it reads `MEMORY.md` only as a retrieval signal.
  Uninstalling nightshift must leave the native memory bit-identical.
- Not a cloud service. No remote API dependency, no new API keys. The model runs local.
- Not useful for one-shot tasks. Value shows up where the *process* matters —
  recurring debugging, transfer between repos — and it should not pretend otherwise.

## Install and run it

nightshift is a Claude Code plugin. It has **no dependencies** — Python 3.9+ standard
library only, no package to install, no API key.

```sh
git clone https://github.com/EvolvingAgentsLabs/nightshift
cd nightshift
./bin/nightshift init        # writes the config; capture refuses to run without deny_paths
claude --plugin-dir .        # load it for one session
```

`init` is not optional ceremony: with no resolved `deny_paths`, capture stays off and
`SessionStart` says so instead of capturing (spec §8.1).

At session start nightshift prints a one-line status (`nightshift: capturing · …`).
The injected memory itself is **not** printed: it goes to Claude's context via
`additionalContext`, which the terminal never renders. `/nightshift:status` lists what
was actually injected.

To iterate on the plugin itself: changes to `nightshift/*.py` take effect on the next
hook event, because every hook runs a fresh process. Run `/reload-plugins` when you
change `hooks/hooks.json`, a skill, or the manifest.

### Skills

| Skill | What it does |
|---|---|
| `/nightshift:status` | What has been captured, and what was injected into this session |
| `/nightshift:why <id>` | Reconstruct the source trajectory behind an injection — the M2 gate |
| `/nightshift:doctor` | Runtime invariant checks plus an end-to-end replay of all seven hooks |
| `/nightshift:dev` | Development state of the plugin, for sessions that modify it |
| `/nightshift:dream` | Phase 1 (`consolidate`) over closed trajectories, with Claude Code itself |
| `/nightshift:schedule` | The nightly run: which backend, what is installed, and how the last runs went |

`/nightshift:dream --verify` does not exist: phase 2 is M5, blocked until M4 returns a
verdict. **Nothing reaches `procedure`, so nothing injected is verified.**

### Hooks it registers

`SessionStart` · `UserPromptSubmit` · `PostToolUse` · `PostToolUseFailure` ·
`PreCompact` · `Stop` · `SessionEnd`

Three of those are corrections to the original plan, found by reading the current docs
and then by running the thing:

- `PostToolUse` does not fire on failures — they go to `PostToolUseFailure`. In a
  debugging trajectory the failure *is* the decisive signal.
- `PreCompact` does not carry the transcript, so the snapshot is assembled from
  nightshift's own store. It is a sealing signal, not a data source.
- `Stop` fires at the end of **every turn**, not the session. It seals the turn;
  `SessionEnd` closes the trajectory.
- A session that dies without `SessionEnd` leaves its trajectory `open` forever, and
  retrieval never sees it. `SessionStart` closes those orphans — other sessions only,
  and only when there has been no activity for `orphan_after_hours` (spec §5.8).
- `SessionStart` runs **before** you type, so the task type there is still `general`.
  Structural retrieval is redone on the first prompt that classifies the task, without
  repeating anything already injected (spec §5.7).

### What it stores, and where

`~/.nightshift/trajectories.sqlite3` — one location, whoever runs the process. `status`
reports how much it takes on disk, because a retention policy needs something to measure
first. Override
it with `NIGHTSHIFT_HOME` if you must. Never inside your repo,
and never under `~/.claude/projects/*/memory/` — a guard in `config.py` raises if any
code path tries, and a test asserts a full session leaves the native memory untouched.

Everything is redacted **before** it is persisted, by a deterministic redactor: regex
plus the repo's own identifiers, no model in the path. Anything under `deny_paths` is not
captured at all — not the path, not the content, not the fact that it happened.

## Repository layout

```
.claude-plugin/plugin.json     Plugin manifest
hooks/hooks.json               The seven hooks nightshift registers
bin/                           ns-hook (hook entrypoint) and nightshift (CLI), added to PATH
skills/                        /nightshift:status | why | doctor | dev | dream | schedule
nightshift/                    The implementation. Standard library only
  config.py                      Paths, deny_paths, the Auto Memory write guard
  redact.py                      Deterministic redactor — runs before persisting
  store.py                       SQLite; export_trajectory() emits trajectory.v1
  context.py                     Repo fingerprint, task classification, tool normalisation
  hook.py                        Hook dispatch. Never raises, always exits 0
  retrieve.py                    Structural ranking and injection
  dream.py                       Dream phase 1: Claude Code or a local model, by config
  schedule.py                    Pluggable scheduler: launchd | systemd | loop
  bench.py                       M4 runner: reads thresholds, never sets them
  simulate.py                    End-to-end rehearsal. Never touches the real store
  cli.py                         init | status | why | export | audit | dream | schedule | doctor | …
tests/                         Unit tests plus the capture→export→validate round trip
tools/                         The gate: lint-docs, lint-code, validate-schema
doc/00-spec.md                 Specification v0.3 (normative prose)
doc/PLAN-v0.3.md               Scope of record
doc/adr/ADR-001-…              Why we do not compete with Auto Dream
doc/adr/ADR-002-verify-gate.md What counts as reproduction
schema/trajectory.v1.json      Versioned Trajectory schema (normative data model)
schema/examples/               Valid and invalid fixtures
bench/PREREG.md                Pre-registered benchmark, thresholds frozen before M1
bench/fixtures/familia-a|c|d/  The M4 fixture repos (identifiers still to be frozen)
bench/fixtures/selftest/       Synthetic fixtures for the runner's gate. NOT the M4 fixtures
bench/agentes/                 The agent adapter: how each benchmark cell launches Claude Code
experimentos/                  Runnable demonstrations of what the plugin enables
doc/HANDOFF.md                 Control handoff: state, rules, and the ordered work queue
LATER.md                       Everything deliberately deferred, with the reason
```

## Milestones

| M | Deliverable | Gate |
|---|---|---|
| M0 🟡 | Docs: spec v0.3, ADR-001, ADR-002, versioned schema, PREREG, README | `make check` passes ✅ · Ismael's review of ADR-001 **still pending** |
| **M1** 🟡 | Capture: `PostToolUse`, `PostToolUseFailure`, `PreCompact`, `Stop`, `SessionEnd` → SQLite. Deterministic redactor | Code done, and the gate is now a command: `nightshift audit --min-sessions 5`. It still needs 5 real sessions in the store |
| **M2** 🟡 | Retrieve: structural injection at `SessionStart`, and again at the first classified prompt | Code done. `/nightshift:why` reconstructs the source trajectory of every injection |
| M3 🟡 | Dream `consolidate` ✅ + pluggable scheduler ✅ | Both shipped: `nightshift dream --selftest` passes and `nightshift schedule status` reports the last runs. The milestone gate — **3 consecutive unattended nights** — is Matías's to run |
| M4 🟡 | **Benchmark — go/no-go**. Runner ✅ | ≥ pre-registered threshold in ≥ 2 of A/C/D, zero regression vs S0. The runner is built and **refuses to run**: `bench/PREREG.md` is still a draft with 21 `TODO(Matias)` |
| M5 | Dream `verify` (ephemeral worktree + gate). **Only if M4 passes** | Precision of `procedure` > `candidate` on a benchmark re-run |
| M6+ | OpenCode adapter, plugin marketplace, Omarchy/Quattro | See [`LATER.md`](LATER.md) |

M5 comes after M4 on purpose: `verify` is the most expensive thing to build and is only
worth it if raw procedural memory already shows a gain.

## Running the gate

```sh
make check            # everything below
make lint-docs        # doc structure and internal links
make lint-code        # stdlib only, no network, Auto Memory coexistence, plugin well-formed
make validate-schema  # valid examples validate AND invalid ones are rejected
make test             # unit tests (stdlib unittest)
make selftest         # replays all seven hooks against a throwaway store
make dream-selftest   # the M3-a gate. Calls a model, so it is NOT part of check
make bench-selftest   # the M4 runner's gate (synthetic fixtures, no real benchmark)
make bench-fixtures   # every fixture task fails before and is fixed by its reference fix
make bench-check      # what the pre-registration still needs before M4 can run
make simulate         # the end-to-end rehearsal (closes no gate — see above)
```

`make check` is the gate. It needs no dependencies except
[`check-jsonschema`](https://github.com/python-jsonschema/check-jsonschema) for the schema
step, and falls back to `uvx` or `pipx` if it is not on `PATH`.

### Auditing what was actually stored

`nightshift audit` is the M1 gate as a script. It walks every string persisted in the
store and asserts that none matches a `deny_paths` pattern, none matches a secret rule
from the redactor, no absolute home path survived, nothing from the Auto Memory tree got
in, and no `abstraction.pattern` carries a path. It exits 1 on any finding, or with fewer
sessions than `--min-sessions`.

```sh
nightshift audit                    # leak checks only
nightshift audit --min-sessions 5   # the M1 gate: leaks AND five sessions that captured
nightshift audit --json             # same report, machine-readable
```

The report says **where** (trajectory, step, field) and **which rule** fired — never the
value. A report that quotes the leak spreads it to the terminal, the scrollback and
whoever's pipe it lands in.

### Dream phase 1 — `consolidate`

`nightshift dream` groups closed trajectories by task type, asks the **local** model for
the structural pattern behind each group, and leaves the result as a `candidate` with its
`abstraction` and `valid_when`. When a newer trajectory contradicts an older one, the old
one becomes `superseded` with a link to its successor — **it is never deleted**.

```sh
nightshift dream                  # consolidate the last 7 days
nightshift dream --max-groups 3   # cap how many groups one run consolidates
nightshift dream --dry-run        # show what it would do, write nothing
nightshift dream --selftest       # the M3-a gate, on a throwaway fixture store
```

Consolidation costs money now, so it is measured: every run records what it spent, and
`nightshift why` on a `candidate` tells you which model abstracted it and at what cost —
without that, `why` reconstructs the pattern but not where it came from.

The model runs through `subprocess`, and there are two backends (**ADR-003**): Claude
Code by default — the agent that is already installed and authenticated, invoked
non-interactively — or Qwen through ollama with `model_backend: "local"`. **If neither is
available, dream fails and says so** (exit 2): no heuristic pretending to be
consolidation. Exit 1 means the model produced something that could not be persisted.

The cost of the default is written down and not hidden: **redacted trajectories leave the
machine**. For a repository whose material cannot leave, the local backend is one line of
config. There is still no new API key, and no module of `nightshift/` speaks over the
network — `make lint-code` checks that.

Everything the model produces goes through the same gates as capture: the schema rejects
paths in `abstraction.pattern`, the redactor rejects repo identifiers, and the M1 auditor
rejects leaks. A rejected answer is retried, and a group that insists is dropped — if the
model produces something that does not validate, the bug is in the prompt, not the schema.

A `candidate` is **not** verified. It is injected with less weight and labelled as
unverified, because `verify` (M5) is blocked until M4 returns a verdict.

### Scheduling the nightly run

```sh
nightshift schedule status              # backend, next run, and how the last ones went
nightshift schedule install --dry-run   # show the unit, write nothing
nightshift schedule install             # write it and load it
nightshift schedule uninstall
```

Three backends behind one interface: `launchd` (macOS, the primary target), `systemd` (a
**user** timer, never a system unit) and `loop` (`nightshift schedule loop`, foreground,
for development). The backend is autodetected unless `scheduler_backend` says otherwise.
On macOS the job runs under `caffeinate -s`: a machine that sleeps halfway through
consolidation does not finish it.

Writing the unit and loading it are separate steps on purpose — `--dry-run` shows it
without writing, `--no-activate` writes it without loading it into the system manager.

Every dream run is recorded, and `schedule status` prints the last ones with their exit
codes. That is the point: a scheduler with no recorded runs is a promise, not a fact. The
M3 gate is three consecutive unattended nights, and a person runs it; this is what makes
it checkable.

### Rehearsing the whole thing

```sh
nightshift simulate              # synthetic sessions through the real hooks
nightshift simulate --no-model   # skip dream, for machines with no model available
```

It drives seven synthetic sessions through the seven hooks — including one that dies
without `SessionEnd`, one that touches a `deny_path`, and one carrying a secret — then
audits the store, checks the orphan got closed, checks retrieval ran in both passes,
consolidates with the configured model, installs the scheduler in a temporary `HOME` and runs
three simulated nights, and audits again. Everything happens in a throwaway store.

**It is not evidence for the M1 or M3 gates.** M1 asks for five *real* sessions; M3 asks
for three *unattended nights*. A synthetic session is not a real one, and three runs in a
loop are not three nights: there is no sleep, no battery, no launchd that forgot to fire —
which is exactly what those gates measure. That is also why the rehearsal never writes to
the real store: you cannot close a real-sessions gate by inventing sessions.

### The M4 benchmark runner

The runner is built. **It cannot run**, and that is the point:

```sh
nightshift bench check      # what the pre-registration still needs (exit 1 today)
nightshift bench plan --fixture <f>   # the experiment grid: planning is not running
nightshift bench run  --fixture <f> --agent "<cmd>"   # exits 3 while PREREG is open
nightshift bench selftest   # the runner's own gate, on synthetic fixtures
```

The three fixture repos are built — `bench/fixtures/familia-{a,c,d}/` — and
`nightshift bench fixtures` (`make bench-fixtures`) asserts task by task that **the gate
fails before and the reference fix resolves it**. A fixture where a task already passes,
or where no resolution exists, measures nothing and breaks nothing: it is the quietest way
to own a benchmark that does not measure. Family A is ten bugs with one shared cause;
family C is two repos with the same structural pattern and no shared vocabulary; family D
ships a hand-built ground truth and a deterministic classifier.

The agent adapter that launches each cell lives in `bench/agentes/` and **refuses to run
for the same reason the runner does**: without the model, the tool-call limit and the
reset protocol — all three `TODO(Matias)` — it does not pick values on its own.

`bench/PREREG.md` says **BORRADOR — no congelado** and holds 21 `TODO(Matias)`. Until a
person freezes it, `bench run` refuses and lists what is missing, by section and line. A
threshold that gets adjusted after seeing the result is not a threshold, and a runner
that runs with the pre-registration still open is the most comfortable way to adjust one
without noticing.

Two more rules the runner enforces on itself: **undecidable is not go** — a missing
threshold or a missing family yields no verdict rather than a favourable one — and there
is **no model judgement anywhere** in it: resolution is the fixture's gate (exit 0 now,
non-zero before), and family D's false/stale classification is the fixture's own
deterministic script.

`make doctor` is separate on purpose: it checks *your* installation (config present,
capture enabled), which CI has no business asserting.

## Working rules

Encoded in [`CLAUDE.md`](CLAUDE.md). In short: one milestone per branch; a gate is a
script, not a judgement call; every session ends in a measurable commit or the reason
goes to `LATER.md`; Claude Code reads benchmark thresholds, it never sets them.

## License

Apache-2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE).
