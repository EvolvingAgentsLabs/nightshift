---
description: Show what nightshift has captured and what it injected into this session. Use when the user asks about nightshift status, captured trajectories, or what memory was injected.
disable-model-invocation: true
---

# /nightshift:status

Run the CLI and report its output:

```sh
nightshift status
```

If `nightshift` is not on `PATH`, use `"${CLAUDE_PLUGIN_ROOT}/bin/nightshift" status`.

Then summarise for the user in two or three lines:

- how many trajectories exist and in what state,
- what was injected into **this** session (the injections list), and
- the honest caveat: dream does not exist yet, so nothing has reached `candidate` or
  `procedure`. Everything injected is a raw trajectory and therefore weak evidence.

If the output says nightshift is not configured, tell the user to run `nightshift init`
and explain why: without a resolved `deny_paths`, capture refuses to run (spec §8.1).
