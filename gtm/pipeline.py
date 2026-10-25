"""The build pipeline. Every input row ends up in exactly one place:
lead_list.csv (accepted) or rejects.csv (with the stage and reason it failed).

Stages, in order:
  1 join       person matched to a company row
  2 icp        company passes the ICP filter
  3 suppress   domain / company / LinkedIn on the suppression list
  4 person     title in ICP, still works at the company
  5 dedupe     same LinkedIn URL, or same name at same domain (best title wins)
  6 email      email resolved and passes checks (syntax, role, free mail, MX, verifier)
  7 suppress   email on the suppression list
  8 dedupe     same email twice, or over the per-company cap (applied after email
               checks so a bad address does not use up a company's slot)
  9 personalize first line generated and linted
 10 limit      over the --limit cap (kept in rejects so nothing silently disappears)
"""
import datetime
import os
from collections import Counter, OrderedDict

from . import emails, io
from .dns import DnsCache
from .icp import company_fit, title_rank
from .personalize import display_name, first_line
from .textutil import (NAME_PARTICLES, company_key, normalize_domain, normalize_linkedin, proper, slug,
                       split_name)


class Suppression:
    """Suppression list: rows of type,value,reason. Types: email, domain, linkedin, company."""

    def __init__(self, rows):
        self.by = {"email": {}, "domain": {}, "linkedin": {}, "company": {}}
        for r in rows:
            t = (r.get("type") or "").strip().lower()
            v = (r.get("value") or "").strip()
            if t not in self.by or not v:
                continue
            key = {"email": v.lower(), "domain": normalize_domain(v), "linkedin": normalize_linkedin(v),
                   "company": company_key(v)}[t]
            self.by[t][key] = r.get("reason") or t

    def match(self, kind, value):
        if not value:
            return None
        key = {"email": value.lower(), "domain": normalize_domain(value),
               "linkedin": normalize_linkedin(value), "company": company_key(value)}[kind]
        hit = self.by[kind].get(key)
        if hit is None and kind == "email" and "@" in value:
            hit = self.by["domain"].get(normalize_domain(value.split("@")[1]))
        return hit


def still_at_company(person, company):
    cur = company_key(person.get("current_company"))
    target = company_key(company.get("company_name"))
    if not cur or not target:
        return False
    return cur in target or target in cur


def build(icp, people_path, companies_path, suppression_path, out_dir, dns_cache_path,
          offline=False, limit=None, source_label="Clay search export"):
    people = io.read_people(people_path)
    companies = io.read_companies(companies_path) if companies_path else []
    suppression = Suppression(io.read_simple(suppression_path))
    dns = DnsCache(dns_cache_path, offline=offline)

    by_domain = {}
    for c in companies:
        c["domain"] = normalize_domain(c["domain"])
        if c["domain"]:
            by_domain.setdefault(c["domain"], c)


    rejects, survivors = [], []
    funnel = OrderedDict()

    def reject(p, stage, reason):
        p["reject_stage"], p["reject_reason"] = stage, reason
        rejects.append(p)

    fit_cache = {}
    for p in people:
        p["company_domain"] = normalize_domain(p["company_domain"])
        # 1 join
        if companies:
            c = by_domain.get(p["company_domain"])
            if not c:
                reject(p, "join", "company domain not in company export")
                continue
        else:
            c = {"company_name": p["current_company"], "domain": p["company_domain"], "description": ""}
        p["_company"] = c
        # 2 icp
        if c["domain"] not in fit_cache:
            fit_cache[c["domain"]] = company_fit(c, icp)
        ok, why, kws = fit_cache[c["domain"]]
        if not ok:
            reject(p, "icp", why)
            continue
        p["_keywords"] = kws
        # 3 suppression (pre-email)
        hit = (suppression.match("domain", c["domain"]) or suppression.match("company", c["company_name"])
               or suppression.match("linkedin", p["linkedin_url"]))
        if hit:
            reject(p, "suppress", hit)
            continue
        # 4 person
        rank = title_rank(p["title"], icp)
        if rank is None:
            reject(p, "person", "title out of ICP: '%s'" % (p["title"] or "blank"))
            continue
        if icp["person"].get("require_current_company", True) and not still_at_company(p, c):
            reject(p, "person", "stale role: now at '%s'" % p["current_company"])
            continue
        p["_rank"] = rank
        survivors.append(p)
    funnel["input rows"] = len(people)
    funnel["after join + ICP + suppression + person checks"] = len(survivors)

    # 5 dedupe: LinkedIn URL, then name+domain (best title wins)
    survivors.sort(key=lambda p: (p["_rank"], p["_source_line"]))
    seen_li, seen_nd, deduped = {}, {}, []
    for p in survivors:
        li = normalize_linkedin(p["linkedin_url"])
        nd = (slug(p["full_name"]), p["company_domain"])
        if li and li in seen_li:
            reject(p, "dedupe", "duplicate LinkedIn URL (kept line %s)" % seen_li[li])
            continue
        if nd in seen_nd:
            reject(p, "dedupe", "same name at same domain (kept line %s)" % seen_nd[nd])
            continue
        seen_li[li] = p["_source_line"]
        seen_nd[nd] = p["_source_line"]
        deduped.append(p)
    funnel["after dedupe"] = len(deduped)

    # 6-9 email, suppression, cap, personalisation
    accepted = []
    dmarc_cache = {}
    seen_email, per_co, used_bases = {}, Counter(), {}
    cap = icp.get("max_contacts_per_company", 2)
    for p in deduped:
        c = p["_company"]
        res = emails.resolve(p, c["domain"], icp["email_patterns"], dns)
        p.update(res)
        if res["verification_status"] in emails.REJECT:
            reject(p, "email", "%s (%s)" % (res["verification_status"], res["email"] or "no email"))
            continue
        hit = suppression.match("email", res["email"])
        if hit:
            reject(p, "suppress", hit)
            continue
        if res["email"] in seen_email:
            reject(p, "dedupe", "duplicate email (kept line %s)" % seen_email[res["email"]])
            continue
        if per_co[c["domain"]] >= cap:
            reject(p, "dedupe", "over cap of %d contacts per company" % cap)
            continue
        if c["domain"] not in dmarc_cache:
            dmarc_cache[c["domain"]] = dns.dmarc(c["domain"])
        used = used_bases.setdefault(c["domain"], [])
        line, basis = first_line(c, {"dmarc": dmarc_cache[c["domain"]]}, avoid=used, person=p)
        used.append(basis)
        if not line:
            reject(p, "personalize", "no fact available for a first line")
            continue
        p["first_line"], p["line_basis"] = line, basis
        seen_email[res["email"]] = p["_source_line"]
        per_co[c["domain"]] += 1
        accepted.append(p)
    funnel["after email checks + suppression"] = len(accepted)

    # 9 limit: best titles first, then strongest personalisation basis
    basis_rank = {"stack": 1, "infra": 2, "stat": 3, "niche": 4, "languages": 5, "dmarc": 6, "growth": 7}
    accepted.sort(key=lambda p: (p["_rank"], 0 if p["line_basis"].startswith("signal_")
                                 else basis_rank.get(p["line_basis"], 9), p["_source_line"]))
    if limit and len(accepted) > limit:
        for p in accepted[limit:]:
            reject(p, "limit", "over --limit %d" % limit)
        accepted = accepted[:limit]
    funnel["final list"] = len(accepted)
    dns.save()

    today = datetime.date.today().isoformat()
    lead_rows, seq_rows = [], []
    for p in accepted:
        c = p["_company"]
        first, last = split_name(p["full_name"])
        first = proper(p.get("first_name") or first)
        last = p.get("last_name") or " ".join(w if w.lower() in NAME_PARTICLES else proper(w) for w in last.split())
        signal = c.get("growth_signal") or ""
        for src in (p, c):
            if src.get("signal_type") and src.get("signal_evidence"):
                clay = "Clay %s: %s" % (src["signal_type"], src["signal_evidence"])
                if src.get("signal_url"):
                    clay += " (%s)" % src["signal_url"]
                signal = clay + ("; " + signal if signal else "")
                break
        if p["_keywords"]:
            signal = (signal + "; " if signal else "") + "positioning mentions: " + ", ".join(p["_keywords"][:4])
        lead_rows.append({
            "name": p["full_name"], "first_name": first, "last_name": last, "title": p["title"],
            "company": display_name(c["company_name"]), "domain": c["domain"], "linkedin_url": p["linkedin_url"],
            "email": p["email"], "verification_status": p["verification_status"], "mx_provider": p["mx_provider"],
            "qualifying_signal": signal, "first_line": p["first_line"], "line_basis": p["line_basis"],
            "country": c.get("country", ""), "source": "%s (%s line %s), %s" % (
                source_label, p["_source_file"], p["_source_line"], today),
        })
        clay_line = p["first_line"] if p["line_basis"].startswith("signal_") else ""
        seq_rows.append({
            "email": p["email"], "first_name": first, "last_name": last, "company_name": display_name(c["company_name"]),
            "website": c["domain"], "linkedin_profile": p["linkedin_url"], "title": p["title"],
            "first_line": p["first_line"], "first_line_lc": _lc_first(p["first_line"]),
            "signal_line": clay_line, "signal_line_lc": _lc_first(clay_line), "signal": signal,
            "email_status": p["verification_status"], "country": c.get("country", ""),
        })

    os.makedirs(out_dir, exist_ok=True)
    io.write_csv(os.path.join(out_dir, "lead_list.csv"), lead_rows, LEAD_FIELDS)
    io.write_csv(os.path.join(out_dir, "sequencer_import.csv"), seq_rows, SEQ_FIELDS)
    io.write_csv(os.path.join(out_dir, "rejects.csv"), rejects, REJECT_FIELDS)
    report = _report(icp, funnel, rejects, lead_rows, dns, offline)
    with open(os.path.join(out_dir, "report.md"), "w") as f:
        f.write(report)
    return {"funnel": funnel, "accepted": lead_rows, "rejects": rejects, "report": report}


LEAD_FIELDS = ["name", "title", "company", "domain", "linkedin_url", "email", "verification_status",
               "qualifying_signal", "source", "first_line", "line_basis", "first_name", "last_name",
               "mx_provider", "country"]
SEQ_FIELDS = ["email", "first_name", "last_name", "company_name", "website", "linkedin_profile", "title",
              "first_line", "first_line_lc", "signal_line", "signal_line_lc", "signal", "email_status", "country"]
REJECT_FIELDS = ["reject_stage", "reject_reason", "full_name", "title", "current_company", "company_domain",
                 "linkedin_url", "email", "_source_file", "_source_line"]


def _lc_first(line):
    """For use after "Hi Name, ": lower-case the opening word unless it is a number or an acronym."""
    if not line or not line[0].isupper() or (len(line) > 1 and line[1].isupper()):
        return line
    return line[0].lower() + line[1:]


def _report(icp, funnel, rejects, leads, dns, offline):
    lines = ["# Build report: %s" % icp.get("name", "icp"), ""]
    lines.append("DNS mode: %s, network lookups this run: %d" % ("offline (cache only)" if offline else "online",
                                                                   dns.network_calls))
    lines += ["", "## Funnel", ""]
    for k, v in funnel.items():
        lines.append("- %s: %d" % (k, v))
    lines += ["", "## Rejected rows by stage and reason", "", "| stage | reason | rows |", "|---|---|---|"]
    counts = Counter()
    for r in rejects:
        reason = r["reject_reason"]
        if reason.startswith("stale role"):
            reason = "stale role (works elsewhere now)"
        elif reason.startswith("title out of ICP"):
            reason = "title out of ICP"
        elif "kept line" in reason:
            reason = reason.split(" (kept")[0]
        elif r["reject_stage"] == "email":
            reason = reason.split(" (")[0]
        counts[(r["reject_stage"], reason)] += 1
    for (stage, reason), n in sorted(counts.items(), key=lambda x: (-x[1], x[0])):
        lines.append("| %s | %s | %d |" % (stage, reason, n))
    lines += ["", "## Email status of accepted rows", ""]
    for k, v in Counter(l["verification_status"] for l in leads).most_common():
        lines.append("- %s: %d" % (k, v))
    lines += ["", "## First-line basis", ""]
    for k, v in Counter(l["line_basis"] for l in leads).most_common():
        lines.append("- %s: %d" % (k, v))
    lines += ["", "## Sample first lines", ""]
    shown = set()
    for l in leads:
        if l["line_basis"] in shown:
            continue
        shown.add(l["line_basis"])
        lines.append("- **%s, %s** (%s): %s" % (l["name"], l["company"], l["line_basis"], l["first_line"]))
    lines.append("")
    return "\n".join(lines)
