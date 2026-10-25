"""DNS lookups over HTTPS (no dependencies) with an on-disk cache.

The cache is committed so a clean checkout can run with --offline and get the
same answers as the original run.
"""
import json
import os
import time
import urllib.parse
import urllib.request

DOH_URL = "https://cloudflare-dns.com/dns-query"
TYPE_CODES = {"MX": 15, "TXT": 16}


class DnsCache:
    def __init__(self, path, offline=False, timeout=6.0):
        self.path = path
        self.offline = offline
        self.timeout = timeout
        self.data = {}
        if path and os.path.exists(path):
            with open(path) as f:
                self.data = json.load(f)
        self.network_calls = 0

    def save(self):
        if not self.path:
            return
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, "w") as f:
            json.dump(self.data, f, indent=1, sort_keys=True)

    def query(self, name, rtype):
        key = "%s %s" % (rtype, name.lower())
        if key in self.data:
            return self.data[key]
        if self.offline:
            return None  # unknown
        url = DOH_URL + "?" + urllib.parse.urlencode({"name": name, "type": rtype})
        req = urllib.request.Request(url, headers={"accept": "application/dns-json"})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                payload = json.load(resp)
        except Exception:
            return None
        self.network_calls += 1
        answers = [
            a.get("data", "").strip('"')
            for a in payload.get("Answer", [])
            if a.get("type") == TYPE_CODES[rtype]
        ]
        result = {"status": payload.get("Status"), "answers": answers, "ts": int(time.time())}
        self.data[key] = result
        return result

    def mx(self, domain):
        """Return list of MX hosts, [] if none, or None if unknown."""
        r = self.query(domain, "MX")
        if r is None:
            return None
        hosts = []
        for a in r["answers"]:
            parts = a.split()
            hosts.append(parts[-1].rstrip(".").lower() if parts else a)
        return hosts

    def dmarc(self, domain):
        """Return the DMARC policy (none/quarantine/reject), 'missing', or None if unknown."""
        r = self.query("_dmarc." + domain, "TXT")
        if r is None:
            return None
        for a in r["answers"]:
            txt = a.replace('" "', "").replace(" ", "").lower()
            if txt.startswith("v=dmarc1"):
                for tag in txt.split(";"):
                    if tag.startswith("p="):
                        return tag[2:]
                return "none"
        return "missing"


def mx_provider(hosts):
    if not hosts:
        return ""
    joined = " ".join(hosts)
    if "google" in joined:
        return "Google Workspace"
    if "outlook" in joined or "protection.outlook" in joined:
        return "Microsoft 365"
    if "zoho" in joined:
        return "Zoho"
    if "secureserver" in joined:
        return "GoDaddy"
    if "titan" in joined:
        return "Titan"
    return "Other"
