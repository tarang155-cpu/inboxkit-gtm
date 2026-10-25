import re
import unicodedata

COMPANY_SUFFIXES = {
    "llc", "ltd", "limited", "inc", "llp", "gmbh", "co", "corp", "plc", "smc",
    "private", "pvt", "group", "agency", "the",
}
NAME_PARTICLES = {"de", "da", "del", "della", "di", "van", "von", "der", "den", "la", "le", "du", "dos", "bin", "al"}
NAME_SUFFIXES = {"mba", "phd", "cpa", "jr", "sr", "ii", "iii", "msc", "pmp"}


def ascii_fold(s):
    return unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode()


def slug(s):
    return re.sub(r"[^a-z0-9]", "", ascii_fold(s).lower())


def company_key(name):
    """Normalise a company name so 'Robaitec (SMC Private) Limited' == 'Robaitec'."""
    s = ascii_fold(name or "").lower()
    s = re.split(r"\s[|\-:]\s|\s\|", s)[0]
    s = re.sub(r"\(.*?\)", " ", s)
    s = re.sub(r"\.(io|ai|co|com|net|in|eu)\b", " ", s)
    words = [w for w in re.findall(r"[a-z0-9]+", s) if w not in COMPANY_SUFFIXES]
    return "".join(words)


def split_name(full):
    """Return (first, last) with honorifics/credentials and initials handled."""
    s = (full or "").strip()
    s = re.sub(r",.*$", "", s)  # "Troy Aitken, MBA"
    parts = [p for p in re.split(r"\s+", s) if p]
    parts = [p for p in parts if slug(p) not in NAME_SUFFIXES]
    if not parts:
        return "", ""
    first = parts[0]
    if len(parts) == 1:
        return first, ""
    # keep particles with the surname: "Daniel de Vries", "Juan del Pino", "Jan van der Berg"
    i = len(parts) - 1
    while i > 1 and parts[i - 1].lower() in NAME_PARTICLES:
        i -= 1
    return first, " ".join(parts[i:])


def proper(s):
    if not s:
        return s
    if s.isupper() or s.islower():
        return s[:1].upper() + s[1:].lower()
    return s


def normalize_linkedin(url):
    u = (url or "").strip().lower()
    u = re.sub(r"^https?://", "", u)
    u = re.sub(r"^(www\.|[a-z]{2}\.)", "", u)
    u = u.split("?")[0].split("#")[0].rstrip("/")
    return u


def normalize_domain(d):
    d = (d or "").strip().lower()
    d = re.sub(r"^https?://", "", d)
    d = re.sub(r"^www\.", "", d)
    return d.split("/")[0]


DASHES = {"—": "em dash", "–": "en dash", "‒": "figure dash", "―": "horizontal bar"}


def find_dashes(text):
    return [(name, text.count(ch)) for ch, name in DASHES.items() if ch in text]
