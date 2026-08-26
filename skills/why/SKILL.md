---
description: Reconstruct the source trajectory behind something nightshift injected. Use when the user asks why a strategy was suggested, or passes a nightshift trajectory id.
disable-model-invocation: true
---

# /nightshift:why $ARGUMENTS

Auditability is a feature, not a debug tool: it is success condition 3 of the spec and
the gate of M2. Every injected item must be traceable to the trajectory it came from.

Run:

```sh
nightshift why $ARGUMENTS
```

`$ARGUMENTS` is a trajectory id; an 8-character prefix is enough.

Report back:

1. the task type, outcome and whether it is verified (right now nothing is — dream
   phase 2 lands in M5),
2. the causal chain: which steps are marked `DECISIVO` and which `CONTRADICHO`,
3. where it was injected and with what score and reason.

If the id is not found, run `nightshift status` and offer the recent ids instead of
guessing.
