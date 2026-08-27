# nightshift

**A procedural memory layer over the agent's native declarative memory.**
A proof of concept, not a product.

*[Léeme en español](README.es.md)*

> **Status: M3 — capture, retrieval and dream phase 1, as a Claude Code plugin.**
> Everything described below runs. Whether it *helps* is unmeasured: `verify` does not
> exist, so nothing reaches `procedure` and nothing injected is verified.

## What it does

nightshift looks over your shoulder while you work: every command, every error and every
correction is stored as a **trajectory** — redacted, on your machine, in a SQLite file.
At night a dream consolidates it into a **pattern**: what shape the problem had, which
signal gave it away, plus a diagram of the mechanism and a conjecture about which other
faces it will come back wearing. When you open the next session and describe what is
happening to you, it hands that back: not *"the timeout is 2000"* — which is what a
declarative memory knows — but *"this was already tried, someone raised the limit, it got
corrected because it papered over the symptom, and that discarded path was still the
right one when the limit was genuinely too low"*. In one sentence: **so the next session
does not walk from scratch the same road the last one already walked.**

```mermaid
flowchart LR
  S["your session"] -->|"7 hooks"| C["capture<br/>command · error · correction"]
  C --> R["deterministic redactor"]
  R --> D[("local store<br/>SQLite")]
  D -->|"at night"| DR["dream · consolidate<br/>draws the mechanism<br/>abstracts the pattern<br/>projects other faces<br/>contrasts what was discarded"]
  DR --> D
  D -->|"session start · your first prompt"| I["injected as context<br/>'this was already tried like this'"]
  I --> N["next session"]
  DR -. "M5 · does not exist" .-> V["verify<br/>reproduce against a gate"]
  V -. "nothing gets here" .-> P["procedure<br/>verified"]

  style V stroke-dasharray: 5 5
  style P stroke-dasharray: 5 5
```

## What it is not

Claude Code already ships **Auto Memory** (per-repo declarative notes) and **Auto Dream**
(background consolidation). nightshift does **not** replace them and does not compete on
"notes + sleep": it runs on top of them ([ADR-001](doc/adr/ADR-001-no-competir-con-auto-dream.md)).

> Auto Memory remembers *what is true in this repo*. nightshift remembers *how it was
> found out*.

## The five capabilities it claims

| | Capability | Built? |
|---|---|---|
| A | Procedural memory: the trajectory, not just the conclusion | yes |
| B | Discarded alternatives kept **with the precondition** that made them right | yes ([ADR-005](doc/adr/ADR-005-contraste-entre-implementaciones.md)) |
| C | Transfer across repositories | off by default |
| D | Every injection traceable to its source (`why`) | yes |
| E | Verification: nothing becomes a procedure until reproducing it passes a gate | **no — this is M5** |

E is the one that matters, and it is the one that does not exist.

## Install and run it

```sh
git clone https://github.com/EvolvingAgentsLabs/nightshift
cd nightshift
./bin/nightshift init          # creates the store and resolves deny_paths
claude --plugin-dir .          # load it in this session
```

Then, inside that session:

| Skill | What it answers |
|---|---|
| `/nightshift:status` | what is stored, what got injected here |
| `/nightshift:why <id>` | where an injection came from, step by step |
| `/nightshift:dream` | consolidate now instead of waiting for the night |
| `/nightshift:schedule` | install the nightly run |
| `/nightshift:doctor` | is capture actually working |
| `/nightshift:dev` | start a development session on the plugin itself |

## The honest part

The benchmark that would answer *"does remembering how something was figured out improve
an agent that already has declarative memory?"* has its runner, its three fixture repos
and its agent adapter — and **has never run**, because the pre-registration is still a
draft with open decisions. Everything injected today is a `candidate`: abstracted by a
model, reproduced by nobody.

A rehearsal is not evidence, and a demonstration is not a result.

- [`doc/00-spec.md`](doc/00-spec.md) — the spec
- [`doc/PLAN-v0.3.md`](doc/PLAN-v0.3.md) · [`doc/PLAN-M4.md`](doc/PLAN-M4.md) — the plan and the benchmark
- [`doc/adr/`](doc/adr/) — the decisions and what each one cost
- [`experimentos/`](experimentos/) — runnable experiments, including the ones whose results do not favour the plugin
- [`LATER.md`](LATER.md) — everything found and not fixed

## License

MIT.
