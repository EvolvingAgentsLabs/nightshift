# nightshift

**A procedural memory layer over the agent's native declarative memory.**

*[Léeme en español](README.es.md)*

> **Status: M0 — documentation only.** There is no code in this repository yet, and
> that is deliberate. The specification, the two ADRs, the versioned trajectory schema
> and the pre-registered benchmark all land before the first hook is written. See
> [Milestones](#milestones).

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

## Repository layout

```
doc/00-spec.md                 Specification v0.3 (normative prose)
doc/PLAN-v0.3.md               Scope of record
doc/adr/ADR-001-…              Why we do not compete with Auto Dream
doc/adr/ADR-002-verify-gate.md What counts as reproduction
schema/trajectory.v1.json      Versioned Trajectory schema (normative data model)
schema/examples/               Valid and invalid fixtures — the M0 gate
bench/PREREG.md                Pre-registered benchmark, thresholds frozen before M1
LATER.md                       Everything deliberately deferred, with the reason
```

## Milestones

| M | Deliverable | Gate |
|---|---|---|
| **M0** | Docs: spec v0.3, ADR-001, ADR-002, versioned schema, PREREG, README | `make check` passes **and** Ismael reviews ADR-001 |
| M1 | Capture: `PostToolUse`, `PostToolUseFailure`, `PreCompact`, `Stop` → SQLite. Deterministic redactor | 5 real sessions captured with no `deny_paths` leak (automated test over the dump) |
| M2 | Retrieve: structural injection at `SessionStart` | `/nightshift why` reconstructs the source trajectory of every injection |
| M3 | Dream `consolidate` + pluggable scheduler (`launchd`/`systemd`/`loop`) | 3 consecutive unattended nights |
| M4 | **Benchmark — go/no-go** | ≥ pre-registered threshold in ≥ 2 of A/C/D, zero regression vs S0 |
| M5 | Dream `verify` (ephemeral worktree + gate). **Only if M4 passes** | Precision of `procedure` > `candidate` on a benchmark re-run |
| M6+ | OpenCode adapter, plugin marketplace, Omarchy/Quattro | See [`LATER.md`](LATER.md) |

M5 comes after M4 on purpose: `verify` is the most expensive thing to build and is only
worth it if raw procedural memory already shows a gain.

## Running the M0 gate

```sh
make check          # lint-docs + validate-schema
make lint-docs      # structure, links, M0 boundaries
make validate-schema
```

`validate-schema` needs [`check-jsonschema`](https://github.com/python-jsonschema/check-jsonschema).
If it is not on `PATH`, the script falls back to `uvx` or `pipx`.

## Working rules

Encoded in [`CLAUDE.md`](CLAUDE.md). In short: one milestone per branch; a gate is a
script, not a judgement call; every session ends in a measurable commit or the reason
goes to `LATER.md`; Claude Code reads benchmark thresholds, it never sets them.

## License

Apache-2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE).
