"""CSV in/out with header aliasing, so Clay, Apollo or hand-made exports all load."""
import csv
import os
import re

PEOPLE_ALIASES = {
    "person_id": ["person_id", "clay_profile_id", "profile_id", "id"],
    "full_name": ["full_name", "name", "full name", "person name"],
    "first_name": ["first_name", "first name", "firstname"],
    "last_name": ["last_name", "last name", "lastname"],
    "title": ["title", "job_title", "job title", "latest_title", "current title"],
    "current_company": ["current_company", "latest_company", "company", "company name", "company_name",
                        "latest_experience_company"],
    "linkedin_url": ["linkedin_url", "linkedin", "linkedin profile", "person linkedin url", "linkedin url", "url"],
    "location": ["location", "location_name", "person location"],
    "company_domain": ["company_domain", "search_company_domain", "domain", "company domain", "website"],
    "email": ["email", "work email", "work_email", "email address"],
    "email_status": ["email_status", "email status", "verification_status", "verification status"],
    "signal_type": ["signal_type", "person signal type"],
    "signal_evidence": ["signal_evidence", "person signal evidence"],
    "signal_url": ["signal_url", "person signal url"],
    "signal_date": ["signal_date", "person signal date"],
}

COMPANY_ALIASES = {
    "company_id": ["company_id", "clay_company_id"],
    "company_name": ["company_name", "name", "company name", "company"],
    "domain": ["domain", "website", "company domain", "company_domain"],
    "company_linkedin_url": ["company_linkedin_url", "linkedin_url", "company linkedin url", "url"],
    "country": ["country", "hq country"],
    "locality": ["locality", "city", "location"],
    "size": ["size", "company_size", "employee range", "headcount range"],
    "employee_count": ["employee_count", "employees", "headcount"],
    "industry": ["industry"],
    "growth_signal": ["growth_signal", "signal", "employee_growth", "headcount growth"],
    "description": ["description", "description_snippet", "about", "company description"],
    # Optional columns written by the Clay signal prompts (prompts/clay_signal_prompts.md)
    "signal_type": ["signal_type", "clay signal type"],
    "signal_evidence": ["signal_evidence", "clay signal evidence"],
    "signal_url": ["signal_url", "signal_source_url", "clay signal url"],
    "signal_date": ["signal_date", "clay signal date"],
}


def _key(h):
    return re.sub(r"\s+", " ", (h or "").strip().lower().replace("_", " "))


def _map_headers(headers, aliases):
    lookup = {}
    for canon, names in aliases.items():
        for n in names:
            lookup.setdefault(_key(n), canon)
    mapping = {}
    for h in headers:
        canon = lookup.get(_key(h))
        if canon and canon not in mapping.values():
            mapping[h] = canon
    return mapping


def read_rows(path, aliases):
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        mapping = _map_headers(reader.fieldnames or [], aliases)
        rows = []
        for i, raw in enumerate(reader, start=2):
            row = {canon: "" for canon in aliases}
            for h, v in raw.items():
                if h in mapping:
                    row[mapping[h]] = (v or "").strip()
            row["_source_file"] = os.path.basename(path)
            row["_source_line"] = i
            rows.append(row)
    return rows


def read_people(path):
    return read_rows(path, PEOPLE_ALIASES)


def read_companies(path):
    return read_rows(path, COMPANY_ALIASES)


def read_simple(path):
    if not path or not os.path.exists(path):
        return []
    with open(path, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def write_csv(path, rows, fields):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
