"""Merge copy with built rows to produce reviewable drafts (never sent).

Picks the sequence by country (India rows get the India sequence), alternates step-1 variants A and B,
and checks the merged text: no dashes, LinkedIn note within 300 characters (falls back to the short note).
"""
import re
from collections import OrderedDict

from .lint import META_PREFIXES, split_messages
from .textutil import find_dashes

LINKEDIN_NOTE_LIMIT = 300
SIGNAL_PLACEHOLDER = "[SIGNAL LINE from the Clay prompt]"


def parse_sequence(md):
    msgs = OrderedDict()
    for m in split_messages(md):
        subject = ""
        body = []
        for line in m["lines"]:
            low = line.strip().lower()
            if low.startswith("subject:"):
                subject = line.split(":", 1)[1].strip()
            elif not low.startswith(META_PREFIXES):
                body.append(line)
        msgs[m["title"]] = {"subject": subject, "body": "\n".join(body).strip()}
    return msgs


def merge(text, row, sender):
    tags = {
        "first_name": row["first_name"], "company_name": row["company_name"],
        "signal_line": row.get("signal_line") or SIGNAL_PLACEHOLDER,
        "signal_line_lc": row.get("signal_line_lc") or SIGNAL_PLACEHOLDER, "sender_name": sender,
        "unsubscribe_link": "[unsubscribe link]",
    }
    out = re.sub(r"\{\{\s*(\w+)\s*\}\}", lambda m: tags.get(m.group(1), m.group(0)), text)
    return re.sub(r"\n{3,}", "\n\n", out).strip()


def pick_sample(rows, n, india_share=0.6):
    """India-first, varied first-line basis, one person per company."""
    india = [r for r in rows if r.get("country") == "India"]
    rest = [r for r in rows if r.get("country") != "India"]
    want_india = min(len(india), int(round(n * india_share)))
    picked, seen_co = [], set()

    def take(pool, k):
        used_basis = set()
        for strict in (True, False):
            for r in pool:
                if len([p for p in picked if p in pool]) >= k:
                    return
                if r["company_name"] in seen_co or r in picked:
                    continue
                if strict and r["line_basis"] in used_basis:
                    continue
                picked.append(r)
                seen_co.add(r["company_name"])
                used_basis.add(r["line_basis"])

    take(india, want_india)
    take(rest, n - len(picked))
    return picked


def render(rows, seqs, sender):
    """Return (markdown, problems)."""
    md, problems = [], []
    for i, r in enumerate(rows):
        seq_name = "india" if r.get("country") == "India" else "global"
        seq = seqs[seq_name]
        variant = "Email 1, variant A (signal plus workflow)" if i % 2 == 0 else "Email 1, variant B (signal plus peer story)"
        email = seq[variant]
        subject = merge(email["subject"], r, sender)
        body = merge(email["body"], r, sender)
        note = merge(seq["LinkedIn connection note"]["body"], r, sender)
        note_kind = "full"
        if len(note) > LINKEDIN_NOTE_LIMIT:
            note = merge(seq["LinkedIn connection note, short"]["body"], r, sender)
            note_kind = "short (full note was over %d chars)" % LINKEDIN_NOTE_LIMIT
        if len(note) > LINKEDIN_NOTE_LIMIT:
            problems.append("%s: LinkedIn note still %d chars" % (r["email"], len(note)))
        for name, _ in find_dashes(subject + body + note):
            problems.append("%s: %s in merged copy" % (r["email"], name))
        if "{{" in body or "{{" in note:
            problems.append("%s: unmerged tag" % r["email"])
        md += [
            "## %d. %s, %s (%s)" % (i + 1, r["first_name"] + " " + r["last_name"], r["company_name"], r.get("country") or "unknown"),
            "",
            "- To: %s (%s)" % (r["email"], r["email_status"]),
            "- Sequence: %s, %s" % (seq_name, variant.split(" (")[0]),
            "- Fallback first line (workflow, `%s`): %s" % (r.get("line_basis", ""), r.get("first_line", "")),
            "- Qualifying signal: %s" % r["signal"],
            "",
            "**Subject:** %s" % subject,
            "",
            body,
            "",
            "**LinkedIn connection note** (%s, %d chars):" % (note_kind, len(note)),
            "",
            "> " + note,
            "",
        ]
    return "\n".join(md), problems
