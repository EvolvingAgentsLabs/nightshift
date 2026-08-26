---
description: Run nightshift's self-diagnosis and end-to-end self-test. Use when nightshift seems broken, after changing its code, or when the user asks whether nightshift is working.
disable-model-invocation: true
---

# /nightshift:doctor

Two checks. Run both, in this order.

```sh
nightshift doctor
nightshift selftest
```

`doctor` asserts runtime invariants: config present, `deny_paths` resolved, the store is
writable and outside the Auto Memory tree, the Auto Memory write guard actually refuses,
the redactor is deterministic and does not let a canary secret survive, and the declared
hooks are events nightshift knows.

`selftest` replays all seven hooks end to end against a throwaway store, then asserts the
captured trajectory closed correctly, contains a `tool_failure` and a `compact_snapshot`
step, has at least one decisive step, and leaked no secret.

Report which checks failed and what each one means. A failing `guard de Auto Memory` or
`redactor: el secreto no sobrevive` is a **stop-everything** bug, not a nit: those two are
the privacy invariants of the whole project (spec §8, ADR-001).

If both pass, say so plainly and give the store path so the user knows where the data is.
