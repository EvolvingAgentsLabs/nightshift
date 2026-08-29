# Logbook — what actually happened, at its real size

These sections used to live in [`README.md`](../README.md). They were moved here on
2026-08-29 so the README could stay short: this is the long form, kept whole, not a
summary of it. Nothing here is verified — `verify` is M5 and does not exist.

*[En español](BITACORA.md)*

## The night it dreamed about itself

On 2026-08-27 at 15:25 UTC the plugin consolidated its own development store and, from the
drawing of the mechanism, **projected four symptoms nobody had observed**
([ADR-004](adr/ADR-004-ideacion-y-proyeccion.md)). That same afternoon, measuring for
an unrelated reason, two turned out to be real:

| What dream projected | What was measured hours later |
|---|---|
| «Retrieval returns matches by structural shape, unrelated to the content of the work.» | Two prompts describing different symptoms returned the same ranking and the same scores |
| «A manual review of a recent record shows the full structure and every text field blank.» | Dream's own prompt showed six `(no summary)` steps out of a 400-step trajectory that had 177 with content |

Three things have to be said, or it is a fairy tale:

- **Neither was found *because* of the projection.** Both were written, injected and
  available, and the work rediscovered them by measuring. A conjecture nobody resolves is
  not memory — it is a note. That gap is what
  [`experimentos/preguntar.py`](../experimentos/preguntar.py) probes.
- **The scoreboard is no longer written by hand.** It used to live in prose, in two
  languages, and it drifted — this section once said *"six projections, two confirmed, two
  refuted, two open"* and two of those counts did not exist. Now the store computes it:
  ```sh
  nightshift resolve      # open conjectures, and the hit rate
  ```
  On 2026-08-28: **23 projected · 15 open · 5 confirmed · 3 refuted — 62% over 8
  resolved.** Do not copy that number anywhere; run the command.
- **The same work found three defects in the treatment arm itself.** All three were
  invisible because every hook exits 0 by design. Fixed; why they went unnoticed for weeks
  is the point.

## The second night, and the one thing that can be said about it

On 2026-08-28 the plugin consolidated its own development twice, and the two results were
not the same kind of thing. That difference is the most interesting observation this
project has produced, and it is also the easiest one to overclaim, so here it is at its
real size.

**The first candidate described a mechanism that does not exist.** It abstracted a
one-line bug — an `or` that dropped a marker — into *"a derived property travels as an
ephemeral flag that does not cross the sealing step"*, with a diagram, an analogy and five
coherent preconditions. It had not hallucinated: it lifted the reasoning already written
in the code's **own comments** — *"no flag in between"*, *"the command is redacted, and
that does not affect it"* — and presented it as its diagnosis of a bug those comments were
not about.

**The second one did not.** Its pattern — *"the work closes green because the automated
gate passes, but every real failure happens outside it, in improvised commands: a name
coined in intent travels as pure text and only breaks at the first stage that resolves it
against something real"* — is a fair description of what actually happened. Four of its
five signals are verifiable observations from that session: the gate green while ad-hoc
one-liners failed, a traceback from hand-built arguments, a shell parse error, a
trajectory left open with `unknown`. The fifth, a push rejected by refspec, **could not be
confirmed** — it may be a conflation. Four out of five, and the fifth named.

It also produced the store's first **contrast** ([ADR-005](adr/ADR-005-contraste-entre-implementaciones.md)):
the discarded approach kept with the precondition under which it was still right. Its
`cost` field names a real price of that day's change that nobody had written down —
*"correcting the definition retroactively rewrites what old trajectories meant, and no
record is kept that they meant something else."*

### What changed in between, and what that is worth

Between the two runs, two things shipped that target exactly the first failure: steps that
**read the repository** (`grep`, `cat`, `git log`) now reach the model labelled
`LECTURA-DEL-REPO` — context, never evidence — and the hypothesis must cite a step that
**observes** something, or stay `null`. Measured on the real store: **50% and 67%** of the
steps in those trajectories were the repository reading itself, arriving with the same
rank as a failure.

**And that is one run against one run, on different corpora, in different sessions.** It
is not evidence that the fix worked. It is the first observation consistent with it, and
the difference between those two sentences is the whole discipline of this repository.

Run it forward yourself:

```sh
nightshift why 07695a69     # the chain, the drawing, the contrast, what git says
nightshift resolve          # the conjectures it left open
```

## The defect that only showed up when someone measured the promise

The README above promises that when you *describe what is happening to you*, the memory
comes back. Nobody had measured that. Measured on the real store: **1 paraphrase out of 6
hooked.** The mechanism this project advertises most — memory latching onto a problem
before its symptom has been seen once — only fired when you used the model's own words.

The cause was one threshold for two kinds of text that are nothing alike: a sentence the
model distilled has no filler, so one content word is already signal; a raw error dump is
mostly harness scaffolding. Split in two, plus a rule that a match can never rest only on
words that say *that* something broke rather than *what*: **4 out of 6**, with the negative
control at zero both times.

The story since then, each step measured: the floor went up to 2 across every surface and
the classifier gate stopped blocking injection (amendment 0.3.10 — Matías's call), regular
plurals now fold to a canonical form (0.3.11), and the last two cases —
`resumen`/`memoria consolidada`, `métrica`/`contador de cobertura`, which share no word at
all — got a **semantic fallback** (ADR-003, amended 2026-08-29). It is a *command*, not a
service: `embedding_command` reads texts on stdin and writes vectors on stdout, the
network is spoken by the user's own script (`tools/embed-ollama.sh` wraps local ollama),
and `nightshift/` still imports no network module. Calibrated against real
`embeddinggemma` before writing the code: the two documented synonym pairs score 0.48 and
0.44 cosine against a 0.33 maximum for unrelated pairs. What it does **not** do, measured
and written down: bridge a symptom to an abstract mechanism (0.24–0.28, *below* the
unrelated pairs). It resolves same-register synonymy, not understanding. Off by default —
without the command, the ranking is byte-for-byte the lexical one.

Reproduce it: `python3 experimentos/05-enganche-por-parafrasis.py --alternativas`
