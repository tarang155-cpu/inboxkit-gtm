# Clay signal prompts (structured alternative)

The main prompt, which writes `{{signal_line}}` directly, lives at the top of `copy/sequence_india.md` and
`copy/sequence_global.md`. Use the prompts below instead if you want Clay to return the raw signal fields and let
`gtm/personalize.py` turn them into the line from fixed templates.

These are written for Clay AI research columns (Claygent) on a table built from
`data/raw/clay_companies_export.csv` and `clay_people_export.csv`. They were **not run** for this submission
(no Clay subscription assumed, so no credits spent). The pipeline already reads their output: export the table
with the four columns below and `run.py build` uses the signal ahead of every other first-line rule.

Output columns (company table, and optionally the people table for prompt 5):

| column | content |
|---|---|
| `signal_type` | one of `hiring`, `tool_stack`, `case_study`, `new_client`, `expansion`, `award`, `linkedin_post`, `deliverability_post` |
| `signal_evidence` | the fact as a short noun phrase, max 9 words, copied or tightly paraphrased from the source |
| `signal_url` | the page the fact is on |
| `signal_date` | YYYY-MM-DD if the page shows one, else blank |

The phrase is dropped into a template (see `CLAY_SIGNAL_TEMPLATES` in `gtm/personalize.py`), for example
`hiring` + "two cold email campaign managers" becomes "Saw Acme is hiring for two cold email campaign managers,
so I guess client volume is up." So the evidence must read naturally after the template's lead-in.

Rules that apply to every prompt below (paste them at the end of each):

```
Rules:
- Only report something you can see on a page you visited. Include that page's URL.
- If you find nothing that matches, return all fields empty. Empty is a good answer; a guess is a bad one.
- Ignore anything older than the window given.
- signal_evidence: max 9 words, no em dashes or en dashes, no quotation marks, no company name.
- Return JSON only: {"signal_type": "...", "signal_evidence": "...", "signal_url": "...", "signal_date": "..."}
```

## 1. Hiring for outbound delivery roles (best signal for this ICP)

Why: an agency hiring people to run campaigns is adding clients, which means more domains, mailboxes and DNS
to set up. Indian agencies often post on Naukri and Instahyre rather than LinkedIn, so check those too.

```
You are researching the agency {{Company Name}} ({{Domain}}).
Find job openings they posted in the last 60 days for roles that deliver outbound for clients:
SDR, BDR, appointment setter, cold email specialist, campaign manager, email deliverability,
lead generation executive, outbound operations, GTM engineer.
Check, in order: {{Domain}}/careers or /jobs, their LinkedIn Jobs page ({{Company Linkedin Url}}/jobs),
Naukri.com, Instahyre, Wellfound, Indeed.
If you find roles, set signal_type to "hiring" and signal_evidence to the role(s) as a noun phrase,
plural if there are several, for example "two SDRs and a campaign manager" or "a cold email specialist".
```

## 2. Sending stack named on their own site

```
Visit {{Domain}}, including the homepage, services, about, case studies and any "our stack" or "tools" page.
Does the agency name the cold email or outbound tools it runs client campaigns on?
Count only sending or sequencing tools: Smartlead, Instantly, lemlist, Apollo, HeyReach, Saleshandy,
Reply.io, EmailBison, PlusVibe, Expandi, La Growth Machine.
If yes, set signal_type to "tool_stack" and signal_evidence to the tools, max three,
joined like "Smartlead and HeyReach" or "Instantly, Apollo and lemlist".
```

## 3. Recent case study or named client

```
Visit {{Domain}} and look for case studies, results, or client logos added in the last 6 months.
If there is a dated case study, set signal_type to "case_study" and signal_evidence to the client or project
name as they title it, for example "SMS-Magic" (the template reads "Read the SMS-Magic case study on the site").
If there is only a newly announced client with no case study, use signal_type "new_client" and the client name.
```

## 4. Expansion into a new market

Common for Indian agencies opening a US or UK entity to sell to clients there.

```
Search the web and {{Domain}} for news, press releases or LinkedIn company posts from the last 6 months
saying {{Company Name}} opened a new office, registered an entity, or launched in a new country or region.
If found, set signal_type to "expansion" and signal_evidence to the market, for example "the US market"
or "a new London office".
```

## 5. Founder or growth lead posting about cold email or deliverability (people table)

Run on the people table. Needs Clay's LinkedIn posts enrichment (or a posts scraper) as the input column.

```
Here are the recent LinkedIn posts by {{Full Name}}, {{Title}} at {{Company Name}}: {{Recent Posts}}
Find one post from the last 30 days about cold email, deliverability, inbox placement, domains, mailboxes,
warmup, Google or Microsoft sending limits, or running outbound for clients.
If it is about deliverability or infrastructure, set signal_type to "deliverability_post";
if it is about outbound more broadly, "linkedin_post".
signal_evidence is the topic as a noun phrase, for example "Microsoft blocking cold email domains" or
"why agencies should own their sending domains". signal_url is the post URL.
```

## Picking one signal per row

Add a Clay formula column (or let the pipeline do it) that takes the first non-empty result in this order:
1 hiring, 5 deliverability_post, 3 case_study, 4 expansion, 2 tool_stack, 5 linkedin_post. Write that one into
the four output columns. If none fire, leave them empty and the pipeline falls back to its free signals:
sending tools in the description, deliverability services, published stats, niche, languages, the agency's own
DMARC record, then headcount growth.

## Cost note

Each prompt is one AI research call per row. On 100 rows, 4 company prompts is 400 calls; the posts prompt adds a
posts lookup per person. Run prompt 1 on everyone, and prompts 2 to 4 only on rows where prompt 1 came back empty,
to cut that roughly in half.
