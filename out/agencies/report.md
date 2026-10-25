# Build report: growing-outbound-agencies

DNS mode: offline (cache only), network lookups this run: 0

## Funnel

- input rows: 138
- after join + ICP + suppression + person checks: 104
- after dedupe: 100
- after email checks + suppression: 100
- final list: 100

## Rejected rows by stage and reason

| stage | reason | rows |
|---|---|---|
| person | stale role (works elsewhere now) | 15 |
| person | title out of ICP | 9 |
| icp | not enough ICP keywords (strong=0, weak=1) | 7 |
| dedupe | duplicate LinkedIn URL | 4 |
| suppress | competitor: email infrastructure vendor | 2 |
| suppress | DEMO entry: simulated prior unsubscribe to show the check works | 1 |

## Email status of accepted rows

- pattern_mx_ok: 100

## First-line basis

- growth: 41
- dmarc: 37
- niche: 8
- infra: 6
- stack: 3
- stat: 3
- languages: 2

## Sample first lines

- **Taha Anwar, Bleed AI** (stack): Saw that Bleed AI runs client campaigns on Instantly and Apollo.
- **Daniel de Vries, LeadHQ** (infra): Noticed LeadHQ owns the deliverability side for clients too, not just the copy.
- **Anuj Agrawal, Growleads.io** (stat): 500+ qualified meetings is a lot of inboxes quietly doing the work behind Growleads.io.
- **Karim Youssef, Pipeline Gurus** (niche): Building Pipeline Gurus around outbound for the GCC market is a sharp focus.
- **Matas Cibirka, Lynn Lead Gen** (languages): Running campaigns in 6 languages is a lot of sending setup to keep clean.
- **Sunil Arya, Pixelo Digital** (dmarc): Noticed pixelodigital.com publishes DMARC at p=none right now.
- **Gabriel Martínez, Reachflow** (growth): Looks like the Reachflow team has grown 10%+ in the last 6 months, congrats.
