# Data

- `raw/clay_companies_export.csv`: Clay company search results (search only, no enrichment), pulled
  2026-10-23 and 2026-10-25. Includes noise companies on purpose; the ICP stage filters them.
- `raw/clay_people_export.csv`: Clay people search at those company domains, founders and growth/ops
  leaders, max 2 or 3 per company per query. Includes duplicates and people who have changed jobs, as Clay
  returned them.
- `cache/dns.json`: MX and DMARC answers from DNS-over-HTTPS, committed so `--offline` runs match.

Any CSV with recognisable headers loads (see `gtm/io.py` for the aliases): name, title, current company,
company domain, LinkedIn URL, and optionally email and email status.
