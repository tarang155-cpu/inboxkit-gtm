"""First lines generated from data the pipeline already holds.

Every line is built from a fact in the row (a Clay signal if the signal prompts
were run, else the company description, DNS record, or growth signal), and
`line_basis` records which fact was used so a reviewer can check it. No line is
written by hand.
"""
import re

from .textutil import ascii_fold, find_dashes

SENDING_TOOLS = ["Instantly", "Smartlead", "lemlist", "Apollo", "Saleshandy", "HeyReach", "Reply.io"]
INFRA_PHRASES = ["domain setup", "deliverability", "inbox warm", "inbox warm-up", "email infrastructure",
                 "outbound infrastructure", "sending pools", "domain audits", "domain infrastructure"]
NICHES = [
    (r"manufactur", "manufacturers"),
    (r"recruit(ment|ers)", "recruitment agencies"),
    (r"supply chain|logistics", "supply chain and logistics software"),
    (r"life science|biotech", "life sciences"),
    (r"\bk-12\b|\bsled\b", "public sector and K-12"),
    (r"healthcare", "healthcare"),
    (r"private equity|m&a|deal flow", "PE and M&A deal flow"),
    (r"\bgcc\b", "the GCC market"),
]
STAT_RE = re.compile(
    r"(?<![\d\-])([\d][\d,\.]*\s?[kKmM]?\+?)\s+(qualified meetings|meetings booked|campaigns launched|"
    r"qualified opportunities|projects|touchpoints|qualified leads)", re.I)
NUM_WORDS = {"two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7}
LANGS = ["English", "French", "German", "Spanish", "Italian", "Portuguese", "Dutch", "Polish"]
MAX_WORDS = 28


def display_name(name):
    s = re.split(r"\s[|\-–—:]\s|\s\|", name or "")[0]
    s = re.sub(r"\s*\(.*?\)", "", s).strip()
    s = re.sub(r"\s+(LLC|LLP|Ltd|Limited|Inc)\.?$", "", s, flags=re.I)
    return s


def _join(items):
    if len(items) <= 1:
        return "".join(items)
    return ", ".join(items[:-1]) + " and " + items[-1]


# Lines for signals found by the Clay prompts. {e} is the short evidence phrase Clay returns.
CLAY_SIGNAL_TEMPLATES = {
    "hiring": "Saw {co} is hiring for {e}, so I guess client volume is up.",
    "new_client": "Saw {co} recently started working with {e}.",
    "case_study": "Read the {e} case study on the {co} site.",
    "tool_stack": "Saw that {co} runs client campaigns on {e}.",
    "expansion": "Saw {co} is expanding into {e}.",
    "award": "Congrats on {e}.",
    "linkedin_post": "Your recent post on {e} was a good read.",
    "deliverability_post": "Your recent post on {e} hit close to home for anyone running client inboxes.",
}
MAX_EVIDENCE_WORDS = 9


def clay_signal_line(signal, co):
    t = (signal.get("signal_type") or "").strip().lower()
    e = (signal.get("signal_evidence") or "").strip().rstrip(".")
    if t not in CLAY_SIGNAL_TEMPLATES or not e or len(e.split()) > MAX_EVIDENCE_WORDS:
        return None
    return CLAY_SIGNAL_TEMPLATES[t].format(co=co, e=e)


def _candidates(company, dns_facts, person=None):
    co = display_name(company.get("company_name"))
    desc = company.get("description") or ""
    low = ascii_fold(desc).lower()

    for src in (person or {}, company):
        line = clay_signal_line(src, co)
        if line:
            yield "signal_" + src["signal_type"].strip().lower(), line

    tools = [t for t in SENDING_TOOLS if re.search(r"\b%s\b" % re.escape(t.lower()), low)]
    if tools:
        yield "stack", "Saw that %s runs client campaigns on %s." % (co, _join(tools[:3]))

    infra = [p for p in INFRA_PHRASES if p in low]
    if infra:
        yield "infra", "Noticed %s owns the deliverability side for clients too, not just the copy." % co

    m = STAT_RE.search(desc)
    if m and _is_big(m.group(1)):
        yield "stat", "%s %s is a lot of inboxes quietly doing the work behind %s." % (
            m.group(1).strip(), m.group(2).lower(), co)

    for pat, niche in NICHES:
        if re.search(pat, low):
            yield "niche", "Building %s around outbound for %s is a sharp focus." % (co, niche)
            break

    langs = [l for l in LANGS if l.lower() in low]
    nm = re.search(r"\b(two|three|four|five|six|seven|\d)\s+languages\b", low)
    n = len(langs) if len(langs) >= 3 else (NUM_WORDS.get(nm.group(1), nm.group(1)) if nm else 0)
    if n:
        yield "languages", "Running campaigns in %s languages is a lot of sending setup to keep clean." % n

    dmarc = (dns_facts or {}).get("dmarc")
    dom = company.get("domain")
    if dmarc == "none":
        yield "dmarc", "Noticed %s publishes DMARC at p=none right now." % dom
    elif dmarc == "missing":
        yield "dmarc", "Noticed %s has no DMARC record published yet." % dom

    g = company.get("growth_signal") or ""
    months = "12" if "12" in g else "6"
    if g:
        yield "growth", "Looks like the %s team has grown 10%%+ in the last %s months, congrats." % (co, months)


def _is_big(num):
    """Only quote stats that are clearly volume claims (100+, or with k/M or a plus sign)."""
    n = num.replace(",", "").replace(" ", "").lower()
    if n.endswith("+") or n[-2:-1] in ("k", "m") or n.endswith(("k", "m")):
        return True
    try:
        return float(n) >= 100
    except ValueError:
        return False


def lint_line(line):
    problems = []
    if find_dashes(line):
        problems.append("dash")
    if len(line.split()) > MAX_WORDS:
        problems.append("too long")
    if "!" in line:
        problems.append("exclamation")
    return problems


def first_line(company, dns_facts=None, avoid=(), person=None):
    """Return (line, basis). Falls through candidates until one passes lint.

    `avoid` lists bases already used for colleagues at the same company, so two
    people there do not get the same opener (falls back to a repeat if nothing else fits).
    """
    ok = [(b, l) for b, l in _candidates(company, dns_facts, person) if not lint_line(l)]
    for basis, line in ok:
        if basis not in avoid:
            return line, basis
    if ok:
        return ok[0][1], ok[0][0]
    return "", "none"
