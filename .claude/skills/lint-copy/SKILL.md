---
name: lint-copy
description: Check campaign copy against the brief's rules (no em or en dashes, one ask per message, opt-out in every email, claims backed by claims.md). Use whenever copy in copy/ is written or edited.
---

# Lint campaign copy

Format for files in `copy/`: one `## ` heading per message. Heading starts with `Email` for emails (opt-out
required) or `LinkedIn` for LinkedIn steps. Meta lines inside a message, not counted as body:
`Subject:`, `Claims: R1, A2`, `Notes:`, `Variant:`, `Send:`, `Channel:`.

```bash
python3 run.py lint-copy copy/*.md
```

Fix every FAIL, then rerun until it prints 0 problems:
- dash: rewrite the sentence with a comma, full stop or "and". Do not swap in a hyphen surrounded by spaces.
- more than one question: keep the single ask, turn other questions into statements.
- no opt-out: add a plain line such as `Not the right person or not interested? Reply "no" and I won't follow up.`
  plus `{{unsubscribe_link}}` if the sequencer supports it. (A question mark in the opt-out line counts toward
  the one-question limit, so phrase it as a statement if the message already asks something.)
- numbers without Claims: every price, count or percentage about InboxKit needs a `Claims:` line with ids
  from `claims.md`. Numbers about the prospect come from the lead row and are merge tags, not literals.
- unknown claim id: the claim is not in the register. Find it on inboxkit.com, add it with the URL, or drop it.
