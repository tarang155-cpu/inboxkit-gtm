---
name: build-list
description: Turn an ICP description into a config, build the deduped, suppressed, email-checked, personalised lead list, and report the funnel. Use when the user gives a segment or ICP and wants a list, or asks to rerun the workflow on a new segment.
---

# Build a lead list from an ICP

## 1. Write the ICP config

Create `config/icp_<slug>.json` by copying `config/icp.json`. Fields:

| field | meaning |
|---|---|
| `name`, `description` | segment name, and the user's ICP in one or two sentences |
| `company.size_buckets` | Clay size buckets allowed, e.g. `["2-10", "11-50"]` |
| `company.industries_any` | LinkedIn industries allowed (blank industry passes) |
| `company.strong_keywords_any` | one hit in name+description qualifies the company |
| `company.include_keywords_any` | weaker terms; need `min_keyword_hits` of them if no strong hit |
| `company.exclude_keywords_any` | any hit rejects the company |
| `company.clay_description_any`, `clay_description_any_2`, `clay_signal_clause` | used by `run.py clay-query` to build the Clay DSL (two `contains` groups ANDed, plus a signal clause such as `employee_growth_6mo >= 1.1`) |
| `person.title_tiers` | list of lists, best first; a title must match one to pass, lower tier wins dedupe |
| `person.title_exclude_any` | any match rejects the person (intern, advisor, board...) |
| `person.require_current_company` | reject people whose current company is not the target company |
| `max_contacts_per_company` | cap, applied after email checks |
| `email_patterns` | tried in order when no email is supplied; `{first} {last} {f} {l} {domain}` |

Keep the keyword lists specific to the segment. Phrases match on word boundaries and tolerate a trailing "s".

## 2. Source the data

If `data/raw/<slug>/` does not exist yet, run the `source-from-clay` skill first.

## 3. Build

```bash
python3 run.py build --icp config/icp_<slug>.json \
  --people data/raw/<slug>/people.csv --companies data/raw/<slug>/companies.csv \
  --out out/<slug> --limit 100
python3 run.py check-out out/<slug>
```

## 4. Review and tune (do not hand-edit outputs)

Open `out/<slug>/report.md` and skim `rejects.csv` for the `icp` stage:
- good companies rejected for "not enough ICP keywords": add the phrases they actually use to `strong_keywords_any`
- noise passing: add an `exclude_keywords_any` term
- good people rejected for title: add the title word to a tier
Rerun after each change. Stop when the reject reasons read as correct decisions.

## 5. Report back

Tell the user: input rows, final rows, the reject table, the email status mix (and that `pattern_mx_ok` needs a
verifier pass before any real send), and five sample first lines with their `line_basis`.
