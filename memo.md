# InboxKit outbound plan: 15 qualified demos in 30 days

**Segment.** Founders and growth or ops leads at outbound, lead-gen and GTM agencies with 2 to 50 staff, India first, then US, UK and EU. They own the sending infrastructure and rebuild it for every client they sign. India leads because these agencies sell to US and UK clients, pay for seats in dollars, and do inbox setup late in IST to match client hours, which is exactly what flat $2.50 mailboxes ([pricing](https://www.inboxkit.com/pricing)) and setup in under 10 minutes per client ([agency page](https://www.inboxkit.com/agency-email-solution)) solve.

**Signal.** Headcount growth of 10%+ over 6 or 12 months (Clay search, free): a growing agency is signing clients, and every new client means new domains, mailboxes and DNS. On top of that, a Clay AI column writes one `{{signal_line}}` per person from hiring for SDR or campaign roles, a new market, a recent post about deliverability, a new case study, or named sending tools (prompt in `copy/`). Supporting evidence from our own DNS pass: 46 of the 68 agencies in the sample list (68%) publish DMARC at `p=none` or not at all on their main domain.

**Offer and single CTA.** A free audit of one client's sending domains (SPF, DKIM, DMARC, MX, blacklists), shown on a 15 minute call. Every message asks for that call and nothing else. A qualified demo is a founder or ops lead at an agency with 3+ clients on cold email who decides on infrastructure.

**Three weeks, two channels** (business days, per contact; a reply on either channel stops both):

| Day | 1 | 2 | 4 | 6 | 9 | 12 | 15 |
|---|---|---|---|---|---|---|---|
| Step | Email 1 (A/B 50:50) | LinkedIn connect, signal line | Email 2, cost | LinkedIn follow-up if accepted | Email 3, monitoring | LinkedIn follow-up 2 | Email 4, close |

New contacts are loaded in daily cohorts over days 1 to 8, so the last cohort finishes on day 23 and days 24 to 30 catch late replies and reschedules. India and global copy run in parallel. Kill rule: after the first 500 delivered, if positive replies are under 0.8%, pause the weaker step 1 variant and swap the signal source.

**Volume math, from 15 demos back** (every number is an assumption unless sourced):

| Step | Assumption | Result |
|---|---|---|
| Qualified demos | target | 15 |
| Booked demos | 80% of booked are held and qualified | 19 |
| Positive replies | 45% of positive replies book | 42 |
| LinkedIn positives | 600 connects (3 sender accounts, about 70 a week each), 30% accept, 5% of accepts reply positively, 30% overlap with email | 6 |
| Email positives needed | 42 minus 6 | 36 |
| Contacts emailed | 1.5% positive reply rate per contact over 4 emails | 2,400 |
| Contacts sourced | 25% of guessed `first@domain` emails fail verification | 3,200 |
| Raw Clay rows | 72% survive the pipeline (100 of 138 in the sample) | 4,450 |
| Agencies | 1.47 final contacts per agency in the sample | about 1,650 |

**Sending capacity.** 2,400 contacts across 4 emails is about 9,600 sends over 15 business days, peaking near 700 a day. At 10 to 15 cold emails per mailbox per day and 3 mailboxes per domain ([warmup page](https://www.inboxkit.com/email-warmup)) that is 48 mailboxes on 16 domains. A 14 day warmup would eat half the window, so start on pre-warmed mailboxes at $6 each a month and pre-warmed domains from $12.50 one time ([pricing](https://www.inboxkit.com/pricing)): about $290 for the month plus about $200 one time. Contact verification before send is the only other spend.

**Risks.** Agency founders get pitched constantly, so the signal line carries the open. Pattern-guessed emails must pass a verifier before day 1. If the agency pool runs short, widen to 51 to 200 staff and 12 month growth.
