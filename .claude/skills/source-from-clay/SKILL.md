---
name: source-from-clay
description: Pull companies and people for an ICP from Clay search (no enrichment credits) and save them as raw CSVs the pipeline reads. Use before build-list when a segment has no data in data/raw yet.
---

# Source a segment from Clay (search only)

Clay search is free. Enrichment (`add-contact-data-points`, `add-company-data-points`) spends credits: do not
call it unless the user says so.

1. `python3 run.py clay-query --icp config/icp_<slug>.json` prints two DSL strings.
2. Companies: call the Clay `search-companies` tool with the first DSL. Call `load-more-search-results` with
   the returned `taskId` until you have about 1.5x the companies you need (people pull about 1.5 contacts per
   company, and the pipeline rejects 20 to 30%). Do not render widgets; this is an intermediate step.
   - `contains` with a list is OR across tokens; a second `contains` clause ANDs. Semantic
     `products_and_services is_similar_to` is noisy for agencies, prefer keyword clauses plus industry.
   - If the first page is mostly noise, tighten the keyword groups in the ICP file and rerun the query.
3. Write `data/raw/<slug>/companies.csv` with columns:
   `clay_company_id,company_name,domain,company_linkedin_url,country,locality,company_size,employee_count,industry,growth_signal,description_snippet`
   Keep the description text as Clay returned it (trim to the sentences that describe what they do); the
   ICP filter and first lines read it. `growth_signal` is the signal clause in words, e.g.
   `headcount growth >=10% over 6 months`. Include every company returned, noise too: the ICP stage filters it.
4. People: call `search-contacts` with the second DSL, 10 company domains per call in `companyIdentifiers`.
5. Append to `data/raw/<slug>/people.csv` with columns:
   `clay_profile_id,full_name,latest_title,latest_company,latest_start,linkedin_url,location,profile_domain,search_company_domain`
   `search_company_domain` is the domain you searched (the join key). `latest_company` is what Clay says the
   person's current company is; keep it even when it differs, the pipeline rejects stale roles with a reason.
   Write rows after every batch so nothing is lost.
6. Hand off to the `build-list` skill.

Other sources work too: any CSV with name, title, company, domain and LinkedIn columns loads, because
`gtm/io.py` maps common header names (Clay table exports, Apollo, Sales Navigator scrapes). If the export already
has emails and a verifier status column, the pipeline uses them instead of guessing.
