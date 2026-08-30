# nightshift

**A procedural and epistemic memory engine.**
A proof of concept, not a product.

*[Léeme en español](README.es.md)*

![Dream projects trajectories toward bugs; the same person meets them hours later on screen](doc/assets/night.png)

> **Status: M3 built** — capture, retrieval and dream phase 1, as a Claude Code plugin.
> The gate is `make dogfood`.
>
> **Everything on this page is a hypothesis about where this architecture fits, not a
> record of what it has done.** nightshift has only ever run on its own repository.
> Nobody has measured that it helps even there: `verify` does not exist,
> nothing reaches `procedure`, and every memory it injects is unverified. Read them as
> *"this is the shape of problem the machine was built for"*, never as case studies.

---

The core of nightshift is not about code. Its actual capability is to capture the **Chain
of Execution** (CTE), distil it into an **abstract mechanism — a physical scene** — and
**project future symptoms** before they occur, preserving discarded alternatives together
with the preconditions that made them right.

Take nightshift out of the IDE and out of Claude Code, and these are the domains its
architecture is shaped for.

## 1 · Cybersecurity: threat hunting and incident response

SOC analysts chase anomalies. An attacker reuses the same underlying mechanism while
changing the *face* of the attack — the symptom.

- **The trajectory:** the analyst's sequence — `alert → log query → false hypothesis →
  network query → exfiltration found`.
- **The dream:** draws the attacker's tactical mechanism (*"the attacker uses a legitimate
  pipe, but outside working hours"*).
- **The projection:** which other alerts this mechanism would raise — *"CPU spikes on the
  backup servers"*.
- **The hook:** when a junior analyst meets a projected symptom months later, the
  procedure comes back: *"someone already investigated this pattern; don't look at the
  malware, look at the scheduled crons — and blocking the IP was discarded because it was
  spoofed."*

## 2 · Differential diagnosis in internal medicine

Clinical diagnosis is by definition a chain of execution: symptom → physical exam → lab
result (negative) → hypothesis corrected → diagnosis.

- **Physical ideation, literally.** A pathological process *is* a physical mechanism — *"a
  blocked valve building pressure upstream"*. This is the one domain where the default
  medium is not a metaphor for the mechanism: it is the mechanism.
- **The problem it targets:** patients often present atypical symptoms of a common
  disease, and those are exactly the ones a mechanism can project. On *"shoulder pain +
  hiccups"*, the trajectory that once traced it back to diaphragmatic irritation from a
  hepatic problem would come back — before another shoulder X-ray gets ordered.

> This one carries a caveat the others do not. A memory engine that suggests which tests
> to skip is a clinical decision-support system, and those are regulated, validated and
> audited. nightshift is none of those things and does not reach `procedure`: it would be
> input to a clinician, never a recommendation, and it would need the verification stage
> that is still unbuilt before anyone put it near a patient.

## 3 · Helpdesk: closing the gap from tier 3 to tier 1

Tier-3 engineers fix infrastructure problems that surface at tier 1 in ridiculous shapes —
*"the print button is greyed out"* because the billing microservice exhausted the
connection pool.

- **The projection:** tier 3 fixes the bug; the mechanism is dreamt and projects which
  other tickets are about to arrive — *"the mobile app will time out"*, *"reports will
  come back blank"*.
- **The value:** when the end user calls tier 1 about the mobile app, the paraphrase hooks
  the procedural memory and the tier-1 agent gets the workaround instead of escalating.

## 4 · Industrial maintenance and robotics

The example in this repo's own store — *"sieve with no hole: sealed drums travel down a
belt…"* — is literally industrial maintenance.

- **The trajectory:** sensor readings plus operator actions — `stop motor → purge valve →
  error persists → change filter → resolved`.
- **The dream:** abstracts the mechanical failure and projects which other sensors will
  read anomalously if it recurs.
- **Preconditions (capability B):** *"dropping the pump pressure cleared the alert, but it
  was discarded because it slowed production. That path was right when the fluid was high
  viscosity."*

## 5 · Corporate memory and legal strategy

Companies lose fortunes repeating discarded strategies because nobody remembers *why* they
were discarded, or *under which conditions* they were right.

- **Capability B ([ADR-005](doc/adr/ADR-005-contraste-entre-implementaciones.md)) is the
  key here.** Trajectories of decisions: M&A, marketing bets, litigation.
- **The memory:** *"we tried to buy company X. We ran analysis Y. We found liability Z. We
  walked away."*
- **The hook:** years later the board proposes buying company W, structurally similar.
  What comes back: *"this structure was already investigated. Auditing their patents is a
  time sink; go straight at their labour liabilities. Licensing their technology was only
  valid below a 3% interest rate."*

## 6 · Game design and QA testing

Speedrunners and QA testers break games by chaining actions that should not interact.

- **The trajectory:** the input sequence — `jump → open inventory → take damage →
  invulnerability state`.
- **Ideation and projection:** draws the engine's mechanism (*"an animation interrupt
  desynchronises the collision flag"*) and projects which other item/action combinations
  exploit the same one.
- **Injection:** it points at patching **the abstract mechanism** rather than that one
  glitch — ahead of exploits players have not found yet.

## What these six have in common

nightshift is not "an assistant for programmers". It is an **empirical failure-anticipation
engine**. Any domain where the cost of repeating an investigation from scratch is high, and
where one systemic fault wears many different symptoms, is the shape it was built for.

Whether it actually delivers that is the open question, and it is open in the strict sense:
the benchmark that would answer it has a runner, three fixture repos and an agent adapter,
and **has never run**.

## What of that is actually built

Every domain above leans on one of these five capabilities. This is their real state, and
the last row is why none of the six is a case study:

| | Capability | Built? |
|---|---|---|
| A | Procedural memory: the trajectory, not just the conclusion | yes |
| B | Discarded alternatives kept **with the precondition** that made them right | yes ([ADR-005](doc/adr/ADR-005-contraste-entre-implementaciones.md)) |
| C | Transfer across repositories — or across cases, patients, tickets, machines | off by default |
| D | Every injection traceable to its source (`why`) | yes |
| E | Verification: nothing becomes a procedure until reproducing it passes a gate | **no — this is M5** |

**E is the one that matters, and it is the one that does not exist.** Until it does, every
memory is a `candidate`: abstracted by a model, reproduced by nobody. In a code repository
that means treat it as a hint. In a hospital, a SOC or a due-diligence room it means
something stronger: it is not usable as a recommendation.

## Run it

```sh
git clone https://github.com/EvolvingAgentsLabs/nightshift
cd nightshift
./bin/nightshift init          # creates the store, resolves deny_paths
claude --plugin-dir .          # load it in this session

make dogfood                   # the gate: check + doctor + audit + status, on the REAL store
make experiments               # which of the project's hypotheses are actually verified
```

| Skill | What it answers |
|---|---|
| `/nightshift:status` | what is stored, what got injected here |
| `/nightshift:why <id>` | where an injection came from, step by step |
| `/nightshift:resolve` | did a projected symptom happen? record it, with evidence |
| `/nightshift:dream` | consolidate now instead of waiting for the night |
| `/nightshift:sleep` | seal the current chapter and dream on it, mid-session |
| `/nightshift:schedule` | install the nightly run |
| `/nightshift:doctor` | is capture actually working |
| `/nightshift:dev` | start a development session on the plugin itself |

## Where to look next

- [`doc/HOW-IT-WORKS.md`](doc/HOW-IT-WORKS.md) — **how the machine actually works**: the four steps, the three ideas, what is built and what is not
- [`doc/00-spec.md`](doc/00-spec.md) — the spec
- [`doc/LOGBOOK.md`](doc/LOGBOOK.md) — what actually happened, at its real size
- [`doc/adr/`](doc/adr/) — the decisions and what each one cost
- [`experimentos/`](experimentos/) — runnable experiments, including the ones whose results do not favour the plugin
- [`LATER.md`](LATER.md) — everything found and not fixed

## License

Apache 2.0. See [`LICENSE`](LICENSE).
