# InboxKit outbound workflow

ICP description in, sequencer-ready list out: enriched from the source export, verified as far as free checks
allow, deduped, suppressed, and personalised with a first line built from a fact about each company.
Built for the InboxKit GTM Engineer assignment. Nothing in this repo sends anything.

## Run it from a clean checkout

Needs Python 3.9+ and nothing else (standard library only).

```bash
python3 -m unittest discover -s tests -v
python3 run.py build --people data/raw/clay_people_export.csv \
  --companies data/raw/clay_companies_export.csv --out out/agencies --limit 100 --offline
```

`--offline` answers DNS from the committed cache (`data/cache/dns.json`), so the run is reproducible with no
network. Drop the flag to do live MX and DMARC lookups over DNS-over-HTTPS.

Outputs in `out/agencies/`:

| file | what it is |
|---|---|
| `lead_list.csv` | the 100-row sheet: name, title, company, domain, LinkedIn, email, verification status, qualifying signal, source, first line |
| `sequencer_import.csv` | same people in Smartlead/Instantly import shape, `first_line` and `signal` as custom fields |
| `rejects.csv` | every row that did not make it, with the stage and reason |
| `report.md` | funnel, reject reasons, email status mix, first-line basis, samples |

## What happens to each row

| stage | check | example reject reason |
|---|---|---|
| join | person's company domain exists in the company export | company domain not in company export |
| icp | size, industry, keyword fit, exclusions (`config/icp.json`) | not enough ICP keywords |
| suppress | domain, company name, LinkedIn URL (`config/suppression.csv`) | competitor; existing InboxKit customer |
| person | title in a tier, still works at the company | stale role: now at 'Rankz' |
| dedupe | LinkedIn URL normalised (case, www, trailing slash, query), then same name at same domain; best title kept | duplicate LinkedIn URL (kept line 4) |
| email | supplied email or pattern guess; syntax, role account, free mail, disposable, MX record, verifier status | no_mx (finn@deadmail-leads.com) |
| suppress | email address or email domain | unsubscribed via email |
| dedupe | same email twice; per-company cap applied after email checks so a bad address does not burn a slot | over cap of 2 contacts per company |
| personalize | first line generated from a row fact and linted (no dashes, under 28 words) | no fact available for a first line |
| limit | `--limit` | over --limit 100 |

`tests/fixtures/` holds a 19-row file built to hit every one of these: a duplicate URL in different casing, a
same-name duplicate, a malformed address, `info@`, a gmail address, a domain with no MX, a verifier "invalid",
a catch-all, a stale role, an intern, a competitor, an existing customer, a LinkedIn opt-out and an email
opt-out. The tests assert the exact outcome for each.

## Email verification, honestly

No paid enrichment was used. Where the source has no email, the pipeline guesses `first@domain` (alternates
`first.last@`, `flast@` are kept in `alt_emails`) and checks the domain has working MX. Those rows are marked
`pattern_mx_ok`: the domain receives mail, the mailbox itself is unverified. If the input carries a verifier
status (Clay, ZeroBounce, MillionVerifier exports), it is used: `invalid` is rejected, `catch_all` is kept and
flagged `risky_catch_all`, `valid` becomes `verified`. Run a verifier over `pattern_mx_ok` rows before any real
send.

## First lines

`gtm/personalize.py` picks the first rule that has a fact to work with, in this order: sending tools named
in the company description, deliverability services they sell, a volume stat they publish, a vertical niche,
languages they run campaigns in, their own domain's DMARC policy (live DNS), and finally the headcount growth
signal. `line_basis` in the output names the rule, so every line can be traced back to its source.

## Rerun on a new segment

See `CLAUDE.md` and the skills in `.claude/skills/` (`source-from-clay`, `build-list`, `lint-copy`). In short:
write `config/icp_<slug>.json`, `python3 run.py clay-query --icp ...` for the Clay DSL, pull search results via
the Clay MCP into `data/raw/<slug>/`, then `build`.
