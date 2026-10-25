"""ICP config: company fit, person fit, and the Clay query that sources it."""
import json
import re

from .textutil import ascii_fold


def load_icp(path):
    with open(path) as f:
        icp = json.load(f)
    icp.setdefault("company", {})
    icp.setdefault("person", {})
    icp.setdefault("max_contacts_per_company", 2)
    icp.setdefault("email_patterns", ["{first}@{domain}"])
    return icp


def _hits(text, phrases):
    t = " " + re.sub(r"[^a-z0-9+]+", " ", ascii_fold(text).lower()) + " "
    found = []
    for p in phrases:
        needle = " " + re.sub(r"[^a-z0-9+]+", " ", p.lower()).strip()
        if needle + " " in t or needle + "s " in t:
            found.append(p)
    return found


def company_fit(company, icp):
    """Return (ok, reason, matched_keywords)."""
    c = icp["company"]
    if not company.get("domain"):
        return False, "company has no domain", []
    sizes = c.get("size_buckets")
    if sizes and company.get("size") and company["size"] not in sizes:
        return False, "size %s outside %s" % (company["size"], sizes), []
    industries = c.get("industries_any")
    if industries and company.get("industry") and company["industry"] not in industries:
        return False, "industry '%s' not in ICP" % company["industry"], []
    text = " ".join([company.get("company_name", ""), company.get("description", "")])
    bad = _hits(text, c.get("exclude_keywords_any", []))
    if bad:
        return False, "excluded keyword: %s" % ", ".join(bad), []
    strong = _hits(text, c.get("strong_keywords_any", []))
    weak = _hits(text, c.get("include_keywords_any", []))
    need = c.get("min_keyword_hits", 2)
    if not strong and len(weak) < need:
        return False, "not enough ICP keywords (strong=0, weak=%d)" % len(weak), weak
    return True, "", strong + [w for w in weak if w not in strong]


def title_rank(title, icp):
    """Lower is better. None means the title is out of ICP."""
    t = ascii_fold(title or "").lower()
    if not t:
        return None
    for bad in icp["person"].get("title_exclude_any", []):
        if bad.lower() in t:
            return None
    for rank, group in enumerate(icp["person"].get("title_tiers", [])):
        for kw in group:
            if kw.lower() in t:
                return rank
    return None


def clay_queries(icp):
    """Build the Clay Search DSL strings the source-from-clay skill runs."""
    c = icp["company"]
    clauses = []
    if c.get("industries_any"):
        clauses.append("industry in (%s)" % ", ".join('"%s"' % i for i in c["industries_any"]))
    kws = c.get("clay_description_any") or c.get("strong_keywords_any", [])
    if kws:
        clauses.append("description contains (%s)" % ", ".join('"%s"' % k for k in kws))
    if c.get("clay_description_any_2"):
        clauses.append("description contains (%s)" % ", ".join('"%s"' % k for k in c["clay_description_any_2"]))
    if c.get("size_buckets"):
        clauses.append("company_size in (%s)" % ", ".join('"%s"' % s for s in c["size_buckets"]))
    sig = c.get("clay_signal_clause")
    if sig:
        clauses.append(sig)
    companies = "select from companies where " + " and ".join(clauses)
    seniority = icp["person"].get("clay_seniority", ["Founder", "Owner", "C-suite", "Partner"])
    titles = icp["person"].get("clay_titles_similar", [])
    inner = 'seniority in (%s)' % ", ".join('"%s"' % s for s in seniority)
    if titles:
        inner = "(%s or job_title is_similar_to (%s))" % (inner, ", ".join('"%s"' % t for t in titles))
    people = "select from people where experiences.any(is_current = true and %s) limit %d by clay_company_id" % (
        inner, icp.get("max_contacts_per_company", 2))
    return companies, people
