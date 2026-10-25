"""Run with: python3 -m unittest discover -s tests -v

Uses fixtures only and DNS in offline mode, so it needs no network and no keys.
"""
import os
import shutil
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from gtm import emails, icp as icp_mod, lint, pipeline  # noqa: E402
from gtm.textutil import normalize_linkedin, split_name  # noqa: E402

FX = os.path.join(ROOT, "tests", "fixtures")


class PipelineFixtureTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        cache = os.path.join(cls.tmp, "dns.json")
        shutil.copy(os.path.join(FX, "dns.json"), cache)
        cls.icp = icp_mod.load_icp(os.path.join(ROOT, "config", "icp.json"))
        cls.res = pipeline.build(
            cls.icp, os.path.join(FX, "people.csv"), os.path.join(FX, "companies.csv"),
            os.path.join(FX, "suppression.csv"), os.path.join(cls.tmp, "out"), cache, offline=True)
        cls.reasons = {r["full_name"] + "|" + r["linkedin_url"]: (r["reject_stage"], r["reject_reason"])
                       for r in cls.res["rejects"]}
        cls.by_name = {}
        for r in cls.res["rejects"]:
            cls.by_name.setdefault(r["full_name"], []).append((r["reject_stage"], r["reject_reason"]))

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp)

    def stage(self, name):
        return [s for s, _ in self.by_name.get(name, [])]

    def test_every_row_accounted_for(self):
        self.assertEqual(len(self.res["accepted"]) + len(self.res["rejects"]), 19)

    def test_accepted(self):
        names = sorted(r["name"] for r in self.res["accepted"])
        self.assertEqual(names, ["Ada Founder", "Brad H.", "Pat Catchall"])

    # duplicates
    def test_duplicate_linkedin_url_any_casing(self):
        reasons = [r for _, r in self.by_name["Ada Founder"]]
        self.assertTrue(any(r.startswith("duplicate LinkedIn URL") for r in reasons))

    def test_same_name_same_domain(self):
        reasons = [r for _, r in self.by_name["Ada Founder"]]
        self.assertTrue(any(r.startswith("same name at same domain") for r in reasons))

    def test_cap_applies_after_email_checks(self):
        # Gia (bad email) and Hal (gmail) do not use up Acme's two slots; Cara is over the cap.
        self.assertEqual(self.by_name["Cara Ops"][0][1], "over cap of 2 contacts per company")

    # bad emails
    def test_bad_emails_rejected_with_reason(self):
        expect = {
            "Dan Typo": "invalid_syntax", "Eve Role": "role_account", "Finn NoMx": "no_mx",
            "Gia Bounce": "verifier_invalid", "Hal Gmail": "free_mail",
        }
        for name, status in expect.items():
            stage, reason = self.by_name[name][0]
            self.assertEqual(stage, "email", name)
            self.assertTrue(reason.startswith(status), (name, reason))

    def test_catch_all_kept_but_flagged(self):
        pat = [r for r in self.res["accepted"] if r["name"] == "Pat Catchall"][0]
        self.assertEqual(pat["verification_status"], "risky_catch_all")

    def test_pattern_guess_for_initial_only_last_name(self):
        brad = [r for r in self.res["accepted"] if r["name"] == "Brad H."][0]
        self.assertEqual(brad["email"], "brad@acme-outbound.com")
        self.assertEqual(brad["verification_status"], "pattern_mx_ok")

    # suppression
    def test_suppression_by_domain_company_linkedin_email(self):
        self.assertEqual(self.by_name["Lou Rival"][0], ("suppress", "competitor"))
        self.assertEqual(self.by_name["Mia Customer"][0], ("suppress", "existing customer"))
        self.assertEqual(self.by_name["Ned Optout"][0], ("suppress", "unsubscribed via LinkedIn reply"))
        self.assertEqual(self.by_name["Ola Unsub"][0], ("suppress", "unsubscribed via email"))

    # other filters
    def test_stale_role_title_icp_join(self):
        self.assertTrue(self.by_name["Ivy Moved"][0][1].startswith("stale role"))
        self.assertTrue(self.by_name["Jon Intern"][0][1].startswith("title out of ICP"))
        self.assertEqual(self.by_name["Kim Coffee"][0][0], "icp")
        self.assertEqual(self.by_name["Quin Orphan"][0][0], "join")

    def test_first_lines_have_no_dashes_and_cite_basis(self):
        for r in self.res["accepted"]:
            self.assertNotIn("—", r["first_line"])
            self.assertNotIn("–", r["first_line"])
            self.assertTrue(r["line_basis"])


    # Clay signal columns
    def test_clay_signal_used_first_and_varied_per_company(self):
        acc = {r["name"]: r for r in self.res["accepted"]}
        self.assertEqual(acc["Ada Founder"]["line_basis"], "signal_hiring")
        self.assertIn("two cold email campaign managers", acc["Ada Founder"]["first_line"])
        self.assertIn("acme-outbound.com/careers", acc["Ada Founder"]["qualifying_signal"])
        self.assertNotEqual(acc["Brad H."]["line_basis"], "signal_hiring")  # colleague gets a different opener

    def test_overlong_clay_evidence_falls_back(self):
        pat = [r for r in self.res["accepted"] if r["name"] == "Pat Catchall"][0]
        self.assertFalse(pat["line_basis"].startswith("signal_"))


class UnitTests(unittest.TestCase):
    def test_linkedin_normalisation(self):
        self.assertEqual(normalize_linkedin("HTTPS://www.LinkedIn.com/in/Foo/?trk=x"), "linkedin.com/in/foo")

    def test_name_split(self):
        self.assertEqual(split_name("Troy Aitken, MBA"), ("Troy", "Aitken"))
        self.assertEqual(split_name("Brad H."), ("Brad", "H."))
        self.assertEqual(split_name("Daniel de Vries"), ("Daniel", "de Vries"))

    def test_candidates_skip_last_name_patterns_for_initials(self):
        c = emails.candidates("Brad", "H.", "x.com", ["{first}@{domain}", "{first}.{last}@{domain}"])
        self.assertEqual(c, ["brad@x.com"])

    def test_copy_lint(self):
        claims = "| R1 | something | SAFE | url |"
        bad = ("## Email 1\nSubject: hi\nHi {{first_name}} — quick one? and another?\n"
               "We cost $2.50 a mailbox.\n")
        errs = lint.lint_text(bad, claims)
        joined = " ".join(errs)
        self.assertIn("em dash", joined)
        self.assertIn("questions", joined)
        self.assertIn("no opt-out", joined)
        self.assertIn("no Claims", joined)
        good = ("## Email 1\nSubject: hi\nHi {{first_name}}, mailboxes start at $2.50.\n"
                "Worth a look?\nReply \"no\" and I will not follow up.\nClaims: R1\n")
        self.assertEqual(lint.lint_text(good, claims), [])


if __name__ == "__main__":
    unittest.main()
