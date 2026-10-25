"""Email resolution and checks.

Statuses (the `verification_status` column):
  verified            supplied by a verifier as valid
  risky_catch_all     verifier says the domain accepts everything
  pattern_mx_ok       guessed from the name pattern, domain has working MX (unverified mailbox)
  mx_unknown          could not check DNS (offline with no cache); kept, flagged
Rejected (row goes to rejects.csv):
  invalid_syntax, role_account, disposable_domain, free_mail, no_mx, verifier_invalid, no_name
"""
import re

from .dns import mx_provider
from .textutil import slug, split_name

EMAIL_RE = re.compile(r"^[a-z0-9._%+'-]+@[a-z0-9-]+(\.[a-z0-9-]+)*\.[a-z]{2,}$")
ROLE_LOCALPARTS = {
    "info", "sales", "contact", "hello", "support", "admin", "team", "office", "marketing",
    "hr", "jobs", "careers", "billing", "noreply", "no-reply", "help", "enquiries", "inquiries",
}
DISPOSABLE = {"mailinator.com", "guerrillamail.com", "10minutemail.com", "tempmail.com", "yopmail.com",
              "trashmail.com", "sharklasers.com"}
FREE_MAIL = {"gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "icloud.com", "aol.com", "proton.me"}
REJECT = {"invalid_syntax", "role_account", "disposable_domain", "free_mail", "no_mx", "verifier_invalid", "no_name"}


def candidates(first, last, domain, patterns):
    f = slug(first)
    l = slug(last)
    out = []
    for p in patterns:
        if ("{last}" in p or "{l}" in p) and len(l) < 2:
            continue  # "Brad H." -> only first-name patterns are safe
        e = p.format(first=f, last=l, f=f[:1], l=l[:1], domain=domain)
        if e not in out:
            out.append(e)
    return out


def check_syntax(email):
    e = (email or "").strip().lower()
    if not EMAIL_RE.match(e):
        return "invalid_syntax"
    local, domain = e.split("@", 1)
    if local in ROLE_LOCALPARTS:
        return "role_account"
    if domain in DISPOSABLE:
        return "disposable_domain"
    if domain in FREE_MAIL:
        return "free_mail"
    return ""


def resolve(person, domain, patterns, dns):
    """Return dict with email, verification_status, alt_emails, mx_provider."""
    out = {"email": "", "verification_status": "", "alt_emails": "", "mx_provider": ""}
    supplied = (person.get("email") or "").strip().lower()
    vstatus = (person.get("email_status") or "").strip().lower()

    if supplied:
        email = supplied
        domain = email.split("@")[-1] if "@" in email else domain
        alts = []
    else:
        first, last = split_name(person.get("full_name"))
        if person.get("first_name"):
            first, last = person["first_name"], person.get("last_name") or last
        if not slug(first):
            out["verification_status"] = "no_name"
            return out
        cands = candidates(first, last, domain, patterns)
        email, alts = cands[0], cands[1:]
    out["email"] = email
    out["alt_emails"] = " ".join(alts)

    bad = check_syntax(email)
    if bad:
        out["verification_status"] = bad
        return out
    if vstatus in ("invalid", "undeliverable", "bounced", "bad"):
        out["verification_status"] = "verifier_invalid"
        return out

    hosts = dns.mx(email.split("@")[1]) if dns else None
    out["mx_provider"] = mx_provider(hosts) if hosts else ""
    if hosts == []:
        out["verification_status"] = "no_mx"
        return out
    if vstatus in ("valid", "verified", "deliverable"):
        out["verification_status"] = "verified"
    elif vstatus in ("catch_all", "catch-all", "accept_all", "risky"):
        out["verification_status"] = "risky_catch_all"
    elif hosts is None:
        out["verification_status"] = "mx_unknown"
    else:
        out["verification_status"] = "pattern_mx_ok"
    return out
