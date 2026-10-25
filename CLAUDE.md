# InboxKit GTM workflow

This repo turns an ICP description into a deduped, suppressed, email-checked, personalised lead list that
imports straight into a sequencer (Smartlead, Instantly, or any of the others InboxKit exports to). It also
holds the campaign copy and the claims register the copy is allowed to use.

## Hard rules (never break these)

1. **Nothing gets sent.** Do not call any tool that sends email, sends LinkedIn messages, or starts a campaign
   (for example Smartlead `update_campaign_status` START or `send_*`, Gmail `send_message`). Output is CSV and
   drafts only. If a sequencer campaign is created it stays DRAFTED.
2. **No paid enrichment without asking.** Clay search is fine. Clay `add-contact-data-points` /
   `add-company-data-points`, and paid email verifiers, spend credits: ask the user first.
3. **Product claims come only from `claims.md`**, each with its inboxkit.com source URL. Do not use rows marked
   AVOID. If a claim is not in the register, fetch the inboxkit.com page, add it with its URL, then use it.
4. **Copy rules:** no em dashes or en dashes anywhere, one ask per message, a working opt-out in every email.
   Smartlead and Instantly are integrations: name them if useful, never attack anyone by name.
   Run `python3 run.py lint-copy copy/*.md` before calling copy done.
5. **Every input row is accounted for.** A row is either in `lead_list.csv` or in `rejects.csv` with a stage
   and reason. Never drop rows silently and never hand-edit an output file; change the config and rerun.
6. **First lines are generated, not written.** They come from `gtm/personalize.py` and carry a `line_basis`
   saying which fact they use. If a line is wrong, fix the rule or the input data, then rebuild.

## Commands

```bash
python3 -m unittest discover -s tests -v          # fixtures: bad emails, dupes, suppression (offline)
python3 run.py clay-query --icp config/icp.json   # Clay Search DSL for this ICP
python3 run.py build --icp config/icp.json \
  --people data/raw/clay_people_export.csv \
  --companies data/raw/clay_companies_export.csv \
  --out out/agencies --limit 100                  # add --offline to use only data/cache/dns.json
python3 run.py check-out out/agencies             # re-check output before import
python3 run.py lint-copy copy/*.md                # brief's copy rules
```

Python 3.9+, standard library only. No install step. DNS checks use DNS-over-HTTPS and are cached in
`data/cache/dns.json` (committed), so `--offline` reproduces a run with no network.

## Layout

- `config/icp.json` the ICP: company filter, title tiers, per-company cap, email patterns, Clay query hints
- `config/suppression.csv` competitors, partners, existing customers, opt-outs (type: domain, company, linkedin, email)
- `claims.md` the only allowed source of product claims
- `gtm/` pipeline code: `io` (header aliasing), `icp`, `emails`, `dns`, `personalize`, `pipeline`, `lint`
- `data/raw/` source exports (see `data/README.md` for formats); `data/cache/` DNS cache
- `out/<segment>/` `lead_list.csv` (the sheet), `sequencer_import.csv`, `rejects.csv`, `report.md`
- `copy/` email sequence and LinkedIn copy, linted
- `.claude/skills/` `source-from-clay`, `build-list`, `lint-copy`

## New segment (what the live rerun looks like)

1. Write `config/icp_<slug>.json` from the user's description (schema in `.claude/skills/build-list/SKILL.md`).
   Copy `config/icp.json` and change only what the segment needs.
2. Run the `source-from-clay` skill: `clay-query` prints the DSL, run it through the Clay MCP, page the
   companies, pull people 10 domains per call, save to `data/raw/<slug>/companies.csv` and `people.csv`.
3. `python3 run.py build --icp config/icp_<slug>.json --people ... --companies ... --out out/<slug> --limit 100`
4. Read `out/<slug>/report.md`. If the ICP stage rejects good companies (or passes bad ones), tune keywords in
   the ICP file and rerun. Report the funnel and the reject reasons to the user.
5. Add segment-specific suppressions (their existing customers, competitors) to `config/suppression.csv`.

## Email verification status meanings

`verified` (from a verifier), `risky_catch_all`, `pattern_mx_ok` (guessed `first@domain`, domain has MX, mailbox
not verified), `mx_unknown`. Rejected: `invalid_syntax`, `role_account`, `free_mail`, `disposable_domain`,
`no_mx`, `verifier_invalid`, `no_name`. Before any real send, `pattern_mx_ok` rows need a paid verifier pass;
say so when handing over a list.
