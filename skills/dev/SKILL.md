---
description: Working on nightshift itself — the plugin whose code is this repository. Use whenever editing nightshift's own hooks, redactor, store, retrieval, schema, spec or ADRs, or when asked what state nightshift development is in.
---

# Developing nightshift, which is also the plugin you are running

This repository **is** the plugin. If it was loaded with `--plugin-dir .`, the hooks
capturing this very session are the code in this working tree. Editing
`nightshift/hook.py` changes how the next tool call is captured.

Start by getting the state:

```sh
nightshift dev
```

## Ground rules (from CLAUDE.md, they are not suggestions)

- One milestone per branch. A gate is a script, not a judgement call.
- Every session ends in a measurable commit, or the reason goes to `LATER.md`.
- **Claude Code never sets benchmark thresholds.** It reads them from `bench/PREREG.md`.
  Filling in a `TODO(Matias)` is a violation, not a favour.
- Forbidden: writing under `~/.claude/projects/*/memory/`; remote API dependencies;
  any third-party import; starting M5 before M4's verdict; opening the OpenCode adapter.

## The loop when you change plugin code

1. Change the code.
2. `make check` — lint-docs, lint-code, schema examples, unit tests, and the end-to-end
   hook replay. All of it, not the part you think you touched.
3. `/reload-plugins` in the session so the hook changes actually take effect. Editing
   `hooks/hooks.json` or anything under `nightshift/` without reloading means you are
   testing the old code.
4. `nightshift selftest` again from inside the reloaded session.
5. Commit. If there is nothing to commit, write the reason in `LATER.md`.

## Dogfooding it on itself

`nightshift status` mid-session shows the trajectory being captured right now — this
session's own tool calls. `nightshift export <id>` emits it as `trajectory.v1` JSON,
which `make validate-schema` checks against the schema M0 froze. That round trip
(capture → export → validate against the M0 schema) is the cheapest proof that the
implementation and the spec have not drifted apart.

## What is real and what is not

- **Done:** capture (7 hooks), deterministic redactor, SQLite store, structural
  retrieval and injection, `why` reconstruction, doctor and selftest.
- **Not built:** dream (`consolidate` and `verify`), the scheduler, the benchmark.
  Nothing ever reaches `candidate` or `procedure` today, so **no injected memory is
  verified**. Do not describe it as if it were.
- **Not decided:** every `TODO(Matias)` in `bench/PREREG.md`, and the human gate of M0
  (Ismael's review of ADR-001), which is still pending.

Read `doc/00-spec.md` before changing behaviour, and update it in the same commit if the
behaviour no longer matches. The spec is normative; the code is not.
