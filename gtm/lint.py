"""Copy linter for the rules in the brief.

Copy files are markdown. Each `## ` heading is one message. Inside a message:
  Subject: ...        (email only, not part of the body)
  Claims: R1, A2      (ids from claims.md backing any product claim in the body)
  Notes: ...          (ignored)
Everything else is the body.

Rules:
  - no em dash or en dash anywhere
  - at most one question mark per message (one ask)
  - every email message has a working opt-out line
  - any digit, %, or $ in a body needs a Claims: line, and every claim id must exist in claims.md
"""
import re

from .textutil import find_dashes

OPT_OUT_RE = re.compile(r"(\{\{\s*unsubscribe[^}]*\}\}|reply ['\"]?(stop|no|unsubscribe)['\"]?|opt out|unsubscribe)", re.I)
META_PREFIXES = ("subject:", "claims:", "notes:", "variant:", "send:", "channel:")


def claim_ids(claims_md):
    ids = set()
    for line in claims_md.splitlines():
        m = re.match(r"\|\s*([A-Z]\d+[a-z]?)\s*\|", line)
        if m:
            ids.add(m.group(1))
    return ids


def split_messages(md):
    msgs, cur = [], None
    for line in md.splitlines():
        if line.startswith("## "):
            cur = {"title": line[3:].strip(), "lines": []}
            msgs.append(cur)
        elif cur is not None:
            cur["lines"].append(line)
    return msgs


def lint_text(md, claims_md, path="copy"):
    errors = []
    known = claim_ids(claims_md)
    for name, n in find_dashes(md):
        errors.append("%s: %d %s(es) found" % (path, n, name))
    for msg in split_messages(md):
        t = msg["title"]
        if not t.lower().startswith(("email", "linkedin")):
            continue  # schedule tables, notes: only the dash rule applies
        body_lines = [l for l in msg["lines"] if not l.strip().lower().startswith(META_PREFIXES)]
        body = "\n".join(body_lines)
        claims_line = next((l for l in msg["lines"] if l.strip().lower().startswith("claims:")), "")
        cited = [c.strip() for c in claims_line.split(":", 1)[1].split(",")] if claims_line else []
        cited = [c for c in cited if c and c.lower() != "none"]
        visible = re.sub(r"\{\{.*?\}\}", "", body)
        if visible.count("?") > 1:
            errors.append("%s / %s: %d questions, the brief allows one ask" % (path, t, visible.count("?")))
        if t.lower().startswith("email") and not OPT_OUT_RE.search(body):
            errors.append("%s / %s: no opt-out line" % (path, t))
        if re.search(r"[\d%$]", visible) and not cited:
            errors.append("%s / %s: body has numbers but no Claims: line" % (path, t))
        for c in cited:
            if c not in known:
                errors.append("%s / %s: claim id %s not in claims.md" % (path, t, c))
    return errors
