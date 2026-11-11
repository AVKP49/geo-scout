# GEO Scout — Complete Product & Build Specification

**Status:** Build authority. Written Nov 11, 2026. This document supersedes `DESIGN.md` (Nov 8, 2026) as the document the build agent works from. `DESIGN.md` remains the concept ancestor; where the two disagree, this document wins.
**Working title:** GEO Scout. Name undecided — see §16.
**Stack:** Flask (Python). See §7 for the pinned stack.
**Bar:** This spec is written to be **YC-acceptable**: any claim a YC partner would challenge is either sourced with a date, labeled as an estimate, or flagged **VERIFY AT BUILD**. No invented TAM, no fake metrics, no promised outcome the product cannot measure. "Valid" means: every feature in this spec is buildable with official APIs and public data, and every number the product shows is either measured by our own scans, measured from the customer's own connected accounts, or explicitly labeled as an estimate with its source.
**Build order (binding):** Phase 0 first (free-scan landing page). Phase 1 (tracker dashboard) starts only after Gate 1 passes (§13). Phase 2 (fix engine) starts only after Phase 1 has 5 paying customers retained 60 days. An agent that builds Phase 1 before Gate 1 passes is building against this spec.

---

## How to read this document

- **Part 1** is the company case: problem, market, model, unit economics, moat. Read it to understand *why* this is worth building.
- **Parts 3–5** are the phased product specs. Each phase has its own scope, flows, data, and acceptance criteria. Build one phase at a time.
- **Parts 6–9** are the engineering contract: data model, Flask architecture, engine integrations, honesty rules. These apply to all phases.
- **§13** is the validation plan. It is not optional and it is not marketing. It decides whether Phase 1 gets built at all.
- **§17** is the agent instruction sheet. Read it first if you are the build agent.

**Conventions used throughout:** **VERIFY AT BUILD** = a price, endpoint, or limit that changes over time; the agent must check the live vendor page at build time and record what it found. **ESTIMATED** = a number that is a modeled or third-party estimate, never presented as a measurement. **MEASURED** = a number produced by our own scans or the customer's own connected data.

---

# PART 1 — THE COMPANY CASE

## 1.1 Problem

When a customer asks Google or an AI engine "best HVAC company in Fremont," local businesses have no idea whether they show up. They Google themselves once, ask a friend to ask ChatGPT once, get one anecdotal answer, and learn nothing. There is no dashboard, no trend, no competitor comparison, and no fix list. Meanwhile the answers customers actually get are increasingly written by machines, not by search-result pages.

## 1.2 Solution

GEO Scout is a self-serve analytics tool for local businesses and content sites. Enter your business and city; it tracks the money queries that matter to you across Google AI Overviews, Perplexity, and Gemini, and shows a four-step funnel per query: **Demand → Surfaced → Clicked → Gap**. V1 measures and diagnoses. V2 fixes: it drafts the exact page, FAQ, or schema change that closes the gap, and (for care-plan customers) deploys it after the owner approves.

## 1.3 Why now

- **Consumer behavior has moved.** ChatGPT passed 1.2B weekly users (Oct 2026). Google AI Overviews passed 2.5B users. AI Mode passed 1B monthly users (May 2026). BrightLocal's 2026 survey (n=1,002) found 45% of consumers used AI for a local-business recommendation in the past year, up from 6% the year before (ChatGPT 31%, AI Mode 23%).
- **Zero-click is the norm.** 68% of US Google searches end without a click (SparkToro, Jan–Apr 2026); 83% when an AI Overview is present. Visibility inside the answer is the traffic now.
- **Small brands are nearly invisible in AI answers.** ChatGPT recommended 1.2% of locations in a 350,000-location SOCi study, vs. 35.9% in the Google 3-pack. Niche/small brands were named 11% of the time vs. 73% for global brands (Ranqo). The gap is the product.
- **The category is funded, but the enterprise tier is taken.** ~$619M disclosed venture capital across 10 GEO/AEO startups. Profound raised ~$334.5–335M at a $1.8B valuation (Series D, Sep 2026) and **removed its $99/$399 self-serve plans in Sep 2026** — trial + custom Enterprise only. Peec AI raised ~$29M and reported $10M ARR (May 2026). Scrunch was acquired by Sitecore (Jun 2026, ~$225M reported). Adobe bought Semrush (Apr 2026, ~$1.9B).
- **The price point is NOT the opening.** Otterly starts at $29, Peec at $95, Ahrefs sells GEO packs at $50. The opening is positioning: no rival is local-first (city/category prompts, Google Business Profile and local-pack context, distribution through a care-plan customer base). *This corrects an earlier draft of this spec that claimed a price gap. There is no price gap.*
- **The unproven thing, stated plainly:** SMB willingness to pay for a GEO *diagnostic specifically* is unproven. No public SMB customer counts exist for any GEO tool. 52% of smaller brands don't measure AI visibility at all, and only 2% tie it to revenue (NP Digital, n=812). That is why §13 exists: the product is validated with a free scan before the dashboard is built.

## 1.4 Who pays, and for what

| Persona | Who | What they pay for | Price |
|---|---|---|---|
| P1 — Local service owner | HVAC, plumber, contractor, dentist, salon; 1 business, 1 city, 5–15 money queries | Knowing whether they show up for "best X in [city]" and what to fix | $49–99/mo |
| P2 — Content-site owner | Food blog, local guide; 50–200 content queries | Which pages get cited in AI Overviews and which questions engines answer using competitors | $49–99/mo |
| P3 — Agency / multi-client (V2) | Manages 5–20 local clients | White-label reports, multi-client dashboard | $249/mo |

User zero is Aayushi's food blog, The Whisk Addict. Recipe sites are the most AI-Overview-exposed category on the internet. Dogfood there first; sell it second.

## 1.5 Business model and unit economics

- **Revenue:** subscriptions (Starter $49/mo weekly scans; Growth $99/mo daily scans; Agency $249/mo in V2) + one-time fix jobs in V2 ($495 one-time + $49/mo for a single-location fix package, per the second-pass demand research that ranked the fix-it offer #1 of 9 ideas). Free one-time scan is the lead magnet, not a revenue line.
- **Cost per customer (VERIFIED RANGES, re-check at build):** Perplexity ~$0.007/call. Gemini grounding $14/1,000 searches (5,000 free/mo; billed per search, not per prompt — the biggest cost variable). DataForSEO AI Overviews $1.20/1,000 standard queue. Keyword volume $0.06/1,000 (negligible). GSC/GA4 APIs free. Weekly probing ≈ **$1.45/customer/mo**; daily ≈ **$10/customer/mo** (no ChatGPT) or $15–20 with an OpenAI Responses web-search proxy (which is *not* what consumers see — never present it as ChatGPT coverage). Free scan ≈ **$0.03–0.07**. At 100 daily customers: ~$1,300/mo cost vs. $4,900 revenue at $49.
- **Unit economics at scale (ESTIMATED, from the research model):** 1,000 customers at $49/mo weekly = $49,000/mo revenue vs. ~$12,000–12,500/mo cost. At $99/mo daily = $99,000/mo revenue vs. ~$13,500–14,000/mo cost (Stripe ~$3,200 at the $99 tier). Launch weekly; daily is the $99 upsell.
- **LTV/CAC discipline:** SMB churn runs 3–7%/mo (30–60%/yr), so LTV at $49–99 is ≈ $700–$2,000. CAC must stay under $300–500. Paid ads fail for one-off/low-LTV consumer products and are not the channel here; the free scan, the care-plan base, and the founder's contractor network are the channels (§14). If CAC cannot be held under $300, the model does not work at $49 — that is a kill criterion, not a footnote.

## 1.6 Moat (honest version)

Engine coverage and probing are commoditized — any competent team can call the same three APIs. Defensibility lives in three places, in order: **(1)** the local prompt library (city × category × intent prompts, built from real local queries, not generic templates); **(2)** distribution (care-plan customers who already pay $99/mo and already open the monthly report; the founder's contractor network); **(3)** the diagnosis → fix → re-measure loop (the tool that shows the gap *and* closes it *and* proves it closed is stickier than the tool that only reports). The fix engine in Phase 2 is the moat-building phase. Phase 0 and Phase 1 deliberately do not claim a moat.

## 1.7 Competition

| Competitor | Position | Price (vendor pages read Nov 1, 2026 — VERIFY AT BUILD) | What it means for us |
|---|---|---|---|
| Profound | Enterprise GEO leader | Trial + custom Enterprise (self-serve removed Sep 2026) | Not our customer. Their exit from self-serve is the opening. |
| Peec AI | Self-serve GEO | ~$95/mo; ~$10M ARR May 2026 | Closest direct rival; generic, not local-first. |
| Otterly | Self-serve GEO | $29/mo | Cheapest; generic prompts, no local depth. |
| Ahrefs / Semrush / SE Ranking | SEO suites adding GEO | $50 packs / $99 toolkits | Bundling risk: GEO becomes a free tab inside a suite. |
| Scrunch (Sitecore) | Enterprise GEO | ~$250/mo | Enterprise; not our customer. |
| AthenaHQ / Goodie | GEO tools | ~$295/mo | Mid-market; not local-first. |
| BrightLocal | Local SEO (15,000 customers claimed) | $39/49/59 per location/mo | **Most dangerous event: BrightLocal adds a GEO tab.** Our defense is to be the GEO product their customers already use before they ship it. |
| Agencies | Done-for-you GEO | ~$995/mo confirmed (second-pass research) | They sell the fix at 10–20× our price. Our Phase 2 undercuts them with software. |

## 1.8 What GEO Scout is NOT

- Not a guarantee machine. No ranking promise anywhere in product, copy, or sales material. **Banned words (§9): "guarantee," "ensure," "rank #1," "top of Google."**
- Not an enterprise Profound clone. No narrative analysis, no 10-engine coverage in V1, no $500 price tag.
- Not a general SEO suite. No keyword research, no backlink database, no rank tracking for 10,000 keywords. One job: AI + Google visibility for the queries that make you money.
- Not a content farm. It never auto-publishes anything. Every suggested change is propose-and-approve: the tool drafts, the owner approves, then it deploys (Phase 2; in Phase 1 it hands the owner the exact text/schema to paste or approve).
- Not a buyer of links, a review manipulator, or any tactic that manufactures authority. The product reports reality; it does not fake it.

## 1.9 Land-and-expand (where this sits)

This product is step 2 of the sequence settled Oct 23, 2026: **(1)** website takeover + care $99/mo → **(2)** local visibility +$199–299/mo → **(3)** ads later. GEO Scout sells standalone *and* as the visibility add-on to care-plan customers. Same customer, same monthly report they'd actually open. The care-plan bundle price is set at launch (§16); do not hard-code a discount in Phase 0 or Phase 1 copy.

---

# PART 2 — PRODUCT DEFINITION

## 2.1 Core concepts

- **Business:** name, website URL, city/area, category, Google Business Profile URL (optional in Phase 1).
- **Tracked query:** a natural-language question a real customer would ask, e.g. "best HVAC company in Fremont." Stored verbatim, with a type (money/brand) and a location context.
- **Scan:** one run of all tracked queries against all engines. Starter: weekly. Growth: daily.
- **Citation:** one instance of the business (or a competitor) being named/linked in an engine's answer to a query. Fields: engine, query, cited (bool), position (first mention / mentioned / not cited), cited URL, snippet, sentiment (V1: neutral unless the snippet contains explicit negative language — keep this conservative).
- **Visibility Score (0–100):** the business's share of citations across all its tracked queries and engines, weighted by query importance. Money queries weight 2×; brand queries weight 1×. Formula: `Score = 100 × (Σ weight × cited scans) ÷ (Σ weight × total scans)`.
- **Share of voice:** per query, the business's citations as a share of all business citations in that answer.
- **Competitor:** any other business cited in the business's tracked queries. Ranked by citation count across the business's queries.
- **Diagnosis:** one or more causes from the §4.1 taxonomy, attached to a query with its evidence.
- **Recommendation (Phase 1, light):** a single concrete fix with the problem (plain words), the evidence (query + competitor page cited), the action (exact text/schema to add, or the page to create), the expected effect (which queries it helps), and a priority (P1/P2/P3).
- **Fix (Phase 2):** a recommendation carried through drafting → owner approval → deployment → re-measurement.

## 2.2 The funnel (the product)

For every tracked query, and rolled up per business:

**Demand → Surfaced → Clicked → Gap**

- **Demand (ESTIMATED):** estimated monthly searches for the query, from traditional search-volume data (Google Ads Keyword Planner / DataForSEO). This is the demand proxy. **Honesty rule: no AI engine publishes how many times a query was asked inside ChatGPT, Gemini, or Grok. The product never claims that number.** It shows estimated search demand (labeled "estimated") alongside observed citation frequency from our own scans.
- **Surfaced (MEASURED, sampled):** citation rate (share of scans where the business was cited), position ("first mention" = named/linked in the first 3 citations or the opening of the answer; "mentioned" = cited later; "not cited"), share of voice. For Google AI Overviews: link present in the overview's cited sources, and its position among those links. The UI uses "first mention / mentioned / not cited" — never "page 1" without that definition attached. All surfaced numbers are measured by our scans (weekly on Starter, daily on Growth) and labeled "observed in our scans."
- **Clicked (MEASURED, only when connected):** clicks to the business's own site from AI engines, measured only from the business's own data — Google Search Console (clicks from Google AI Overviews / AI Mode) and GA4 / referrer logs (sessions from Perplexity, ChatGPT, Gemini referrers). Requires the business to connect GSC and GA4. Without a connection, clicks show as "not connected — connect Search Console to unlock," **never as zero**. Click-through rate = AI-referred sessions ÷ citations observed, labeled as an estimate (citations are sampled scans, not every answer the engines served). **Competitor clicks are not measurable and are never shown.**
- **Gap (ESTIMATED):** uncaptured demand = `demand × (1 − citation rate)`; cited-but-not-clicked = `citations × (1 − CTR)`; total gap = the sum, shown per query and rolled up, with the competitor who captured the most of that query's citations named next to it. The gap is the product's headline number. The query table sorts by gap by default.

## 2.3 Data-source honesty table (binding)

Every number in the product carries a source label. No exceptions.

| Metric | Source | Measured or estimated | Phase |
|---|---|---|---|
| Query demand (monthly searches) | Google Ads Keyword Planner / DataForSEO | ESTIMATED (Google's numbers are rounded ranges) | 0–1 |
| How many times a query was asked inside ChatGPT/Gemini/Grok | — | **Not published by any engine. Never claimed.** Proxy = demand + our scan citation frequency | Never |
| Citations & position | Our scans (Perplexity API, Gemini API w/ grounding, Google AIO via SERP API) | MEASURED (sampled: weekly/daily) | 0–1 |
| Clicks to your site from AI | Your GSC + GA4 (connected) | MEASURED | 1 |
| Clicks on competitor links | — | **Not measurable. Never shown.** | Never |
| Click-through rate | Computed: AI sessions ÷ citations observed | ESTIMATED (sampled denominator) | 1 |
| Gap / uncaptured demand | Computed from demand × (1 − citation rate) + cited-but-not-clicked | ESTIMATED | 0–1 |
| Competitor share of voice | Our scans | MEASURED (sampled) | 1 |

Rules: ESTIMATED numbers always carry an "estimated" badge and a tooltip naming the source and the method. MEASURED numbers carry their source ("observed in our scans," "from your Search Console"). If a data source is unavailable, the UI says so ("not connected," "engine not covered in V1") — it never shows a zero or a guess. Demo/sample data (if any) is watermarked SAMPLE and never mixed with real scans. All formulas are documented in-app (a "how this is calculated" link on every score). No black-box numbers.

---

# PART 3 — PHASE 0: FREE-SCAN LANDING PAGE (build this first)

**Purpose:** Gate 1 (§13). A one-time free scan that proves, with real usage, whether small businesses want this at all — before a dollar is spent on the dashboard. The scan page is also the permanent distribution engine: it is the top of the funnel forever.
**Build estimate:** 1–2 weeks for one builder with AI coding help.
**What "done" means:** §3.7 acceptance criteria all pass, and the page is live at a public URL collecting scans.

## 3.1 What the page does (one paragraph)

A visitor enters a business name, website, and city (plus an optional category). The page suggests 5 tracked queries from the category × city prompt templates. The visitor confirms or edits them. The page runs one scan of those 5 queries against the 3 engines (Google AI Overviews, Perplexity, Gemini), computes demand, citation status, diagnosis, and the single top fix per query, and renders a shareable one-page visibility report. Email capture happens *after* the visitor sees the headline result (the shock first, the ask second). No account is created. No payment is taken.

## 3.2 Pages and routes

| Route | Purpose | Auth |
|---|---|---|
| `GET /` | Landing page: the problem in one line, the scan form, 3 example reports (SAMPLE-watermarked), the honesty note, FAQ | Public |
| `POST /scan` (or `POST /api/v1/free-scans`) | Accepts business + queries, creates a free-scan job, returns a scan ID and a status URL | Public, rate-limited (§7.6) |
| `GET /scan/:id` | Live progress page: real progress lines per engine ("Checking Perplexity… 2 of 5 queries"), never a spinner with lies | Public (unguessable ID) |
| `GET /r/:slug` | The finished shareable report (public link, no login) | Public |
| `POST /r/:slug/email` | Email capture: visitor enters email to get the report by email + the weekly tip series | Public |
| `GET /r/:slug/pdf` (Phase 0 stretch, not required) | Printable PDF of the report | Public |

## 3.3 The scan form (fields and validation)

- **Business name** (required, 2–100 chars). **Website URL** (required; must load with HTTP 200 within 10s; if it fails, show "we couldn't load that site — check the URL" and do not run a scan). **City / area** (required; free text, normalized to "City, ST" where possible). **Category** (required; dropdown of ~25 categories: HVAC, plumber, electrician, roofer, contractor/general, dentist, salon, restaurant, lawyer, real estate agent, food blog, local guide, other).
- **Queries:** the page auto-suggests 5 from the category × city templates (e.g. HVAC in Fremont: "best HVAC company in Fremont," "AC repair Fremont," "furnace replacement cost Fremont," "HVAC contractor near me," "[Business Name] reviews"). The visitor can edit, delete, and add (max 5, min 3). Each query is stored verbatim. A query is rejected if it is empty, over 200 chars, or an exact duplicate.
- **Anti-abuse:** one free scan per business website per 30 days (keyed on normalized domain). Rate limit: 5 scan starts per IP per hour, 20/day. A CAPTCHA (hCaptcha or Cloudflare Turnstile) on the form. Abuse is logged, not silently tolerated.
- **Free-scan limits (default, §16 decision 3):** 5 queries, 1 scan, 1 shareable report. The report shows demand, citation status, diagnosis, and the top fix per query. Full analytics history, trend lines, and the full fix list are paid (Phase 1).

## 3.4 The scan job (backend behavior)

1. Validate input; normalize the domain (strip scheme, www, trailing slash, lowercase).
2. Create a `free_scans` row (status `queued`). Enqueue a Celery task.
3. The worker runs, per query, per engine: Perplexity API call → parse citations; Gemini API with grounding → parse citations; Google AI Overview via the SERP provider → parse cited sources. **Timeout per engine call: 30s. Retries: 2 with exponential backoff. A failed engine call marks that engine's result `failed`, shows "couldn't check [engine] — retrying" on the progress page, and never presents stale or invented data as a result.**
4. Demand lookup: DataForSEO keyword volume for each query (or cached value if the same query was looked up in the last 30 days). If the volume API fails, demand shows as "not available," not a guess.
5. Diagnosis: run the §4.1 taxonomy per query (site fetch + schema check + entity snapshot vs. GBP where available). The free scan runs checks 1–3 and 6 of the taxonomy; checks 4–5 (authority, freshness) require the paid competitor/historical data and are marked "available in the full report."
6. Compute per-query gap and the roll-up: total estimated demand, citation rate, total gap, Visibility Score (same formula as §2.2).
7. Mark the scan `complete`, store the report, and render `/r/:slug`. Total target time: under 5 minutes; show real progress throughout. If any engine is down for the whole scan, the report still renders with that engine marked "not checked" and the score computed from the engines that did run — with a visible note saying so.

## 3.5 The report page (the product's first impression — design this like it matters)

Layout, top to bottom:
1. **Headline (the shock, plain language):** "Your business showed up in 1 of 15 AI answers for the searches that matter." One number, one sentence, no jargon. Under it, the Visibility Score (0–100) with its "how this is calculated" link.
2. **The funnel, one line:** "Your 5 queries represent ~8,400 estimated searches a month. You were cited in 7% of the answers we checked. That leaves ~7,800 searches a month going to someone else." Every number labeled ESTIMATED or MEASURED per §2.3.
3. **The query table (5 rows):** query | demand (ESTIMATED) | cited? (first mention / mentioned / not cited) | who beat you (top cited competitor + their page) | the gap | the top fix (one line). Sorted by gap, biggest first.
4. **The one fix (expanded):** the single highest-priority fix across all 5 queries, with the exact text or JSON-LD the owner can paste, and which queries it helps. This is the moment the product proves it is useful.
5. **Email capture (after the result, not before):** "Get this report by email, plus one fix a week." One field, one button. On submit: confirmation + the report link emailed. Email capture rate is a Gate 1 metric — do not hide the form, do not add friction, do not ask for a phone number.
6. **The honest footer:** what was measured, what was estimated, which engines were checked, the scan date, and "ChatGPT's consumer app isn't covered — no tool can measure it directly." The honesty footer is a feature, not a disclaimer.
7. **Share:** copy-link button + "share this report" (X/LinkedIn/Facebook). The shareable report is the viral loop: a business owner shares a bad score, other owners check theirs.

## 3.6 Email sequence (Phase 0, minimal)

- **Email 1 (immediate):** the report link + the one fix, plain text, from a real sender name.
- **Email 2 (day 3):** "Here's what changed if you made the fix" — a one-question reply prompt ("Did you make the change? Reply yes/no") to open a conversation, not a drip campaign.
- **Email 3 (day 7):** the paid offer — Starter $49/mo, weekly scans, full history, the fix list — with the founder's calendar link for a 15-minute call. Calls booked is a Gate 1 metric.
- Unsubscribe in one click. No purchased lists. No cold email.

## 3.7 Acceptance criteria (Phase 0 is not done until all pass)

1. A stranger can complete a scan in under 5 minutes with no help and no account.
2. The report's cited/not-cited results match a manual check (a human asks the same 3 engines the same queries) at ≥85% agreement on a 20-scan sample.
3. Per-scan cost is measured and logged; the free scan costs ≤ $0.10 all-in (target $0.03–0.07).
4. The page handles a failed engine gracefully (marked "not checked," score computed from the rest, note visible) — verified by forcing a failure in staging.
5. Rate limiting and the one-scan-per-domain-per-30-days rule are enforced and tested.
6. No banned words (§9) anywhere on the page, in emails, or in placeholder copy — verified by a full copy pass.
7. The page is live at a public URL, with analytics on: scans started, scans completed, email captures, calls booked.
8. Gate 1 (§13) runs for 2 weeks from launch. **Phase 1 does not start until Gate 1 passes.**

## 3.8 What Phase 0 deliberately does NOT include

No accounts, no login, no billing, no GSC/GA4 connect, no trend history, no competitor analytics page, no ChatGPT coverage, no auto-publishing, no dashboard. If a feature is not on the list in §3.2–3.6, it does not ship in Phase 0.

---

# PART 4 — PHASE 1: TRACKER DASHBOARD (the V1 SaaS)

**Purpose:** the paid product. Weekly/daily scans of a business's tracked queries, the full funnel, competitor view, diagnosis + one top fix per query, and the weekly digest that retains the customer.
**Build estimate:** 6–10 weeks for one builder with AI coding help (after Phase 0).
**Gate:** starts only after Gate 1 passes (§13).

## 4.1 The diagnosis taxonomy (the product's brain)

For every money query with zero citations, the tool assigns one or more causes, in this order of checking:

1. **No page answers the question.** The site has no page (or no section) that directly answers the query. Evidence: site crawl finds no matching page.
2. **Page exists, no structured data.** The page answers it in prose but carries no FAQ/HowTo/LocalBusiness/Recipe schema, so engines can't extract a clean answer. Evidence: schema check on the page.
3. **Entity mismatch.** The business name, address, or phone on the site disagrees with Google Business Profile / directories, or the site doesn't state the service area. Evidence: entity snapshot vs. GBP.
4. **Low authority vs. cited competitors.** Competitors' cited pages have materially more links/reviews/age. Evidence: competitor citation comparison (report facts — "cited competitors average 4.6★ / 200+ reviews; you show 4.2★ / 30" — not a computed authority score).
5. **Freshness.** The best matching page is stale (no update in 12+ months) while cited competitors updated recently.
6. **Not indexed / not retrievable.** The page is blocked, slow, or returns errors to crawlers. Evidence: fetch status.
7. **Engine has no live data for you.** (Mostly brand queries on new businesses.) The engine's retrieval finds nothing citable. Evidence: zero citations across all engines for brand queries.

The diagnosis is shown in plain words next to the query, with the evidence attached. Never a bare score without a reason.

## 4.2 Recommendations in Phase 1 — light (diagnosis + one top fix)

| Diagnosis | Recommendation | Priority |
|---|---|---|
| No page answers the question | Create a page/section that answers it in 150–300 words, with the question as a heading | P1 |
| No structured data | Add FAQPage (or HowTo / Recipe / LocalBusiness) schema to the matching page — tool provides the exact JSON-LD | P1 |
| Entity mismatch | Fix NAP (name/address/phone) to match GBP everywhere on the site; add service-area page | P1 |
| Low authority vs. competitors | Review-generation prompt (ask recent customers); get listed in the directories the cited competitors appear in | P2 |
| Freshness | Update the page (new date, one fresh paragraph, current pricing if applicable) | P2 |
| Not indexed | Fix the technical issue (robots/sitemap/speed) — flagged as "needs a human / your care plan" | P1 |
| No live data | Publish the basics first: GBP complete, 5+ reviews, one answering page per money query | P1 |

Rules: every recommendation links to its evidence (query, diagnosis, competitor page cited). Priority is by expected effect on money queries, not by ease. Phase 1 shows one top fix per query. The rest queue for Phase 2. The free report shows the diagnosis and the top fix; the full analytics history and the fix list are paid.

## 4.3 User flows

### 4.3.1 Onboarding (golden path — under 3 minutes)
1. Enter business name, website, city, category.
2. Tool fetches the site, confirms it loads, extracts business name/address/phone as shown (entity snapshot).
3. Tool suggests 10 tracked queries from category + city templates. User edits, deletes, adds (Starter 10, Growth 25).
4. First scan runs (async, ~2–5 min). User sees a loading state with a real progress line, not a spinner with lies.
5. Dashboard lands with the first Visibility Score, the cited/not-cited split, and the top 3 fixes.

### 4.3.2 Dashboard (the daily home)
- One number: Visibility Score + 7-day delta.
- "Where you showed up" — citations this week, by engine.
- "Where you didn't" — top 5 money queries with zero citations, each with its diagnosis (§4.1).
- "Who beat you" — top 3 competitors by citations, with their cited pages.
- "Do this next" — the single highest-priority recommendation, with its evidence.

### 4.3.3 Query detail
- The query, its type, its engines.
- Per engine: cited or not, position, the answer snippet (verbatim, short), the cited URL if any.
- The competitors cited for this query and their pages.
- The diagnosis (§4.1) and the linked recommendation (§4.2).

### 4.3.4 Weekly digest (email — the retention product)
- Plain English, one page: score, delta, new citations, lost citations, the one fix for this week, and the exact text/schema for that fix. The report is the retention product — the dashboard is the proof.

### 4.3.5 Settings & connections
- Business profile edit; query add/remove (within plan limits); scan cadence display (weekly/daily by plan); GSC + GA4 connect (OAuth, read-only scopes — §7.5); billing (Stripe portal); cancel (one click, no retention dark patterns; exit survey optional, one question).

## 4.4 Views (Phase 1)

- **Overview:** the funnel rolled up — total estimated demand, citation rate, AI-referred sessions, total gap — with 7/30-day trends.
- **Query table:** every tracked query with demand, citation rate, rank (first mention / mentioned / not cited), clicks, CTR, gap. Sortable by gap (default).
- **Engine comparison:** citation rate and share of voice per engine — "where you show up and where you're invisible."
- **Competitor share of voice:** top competitors by citations across your queries, with their cited pages.
- **Trends:** weekly lines for citation rate, Visibility Score, and AI-referred sessions.
- **Weekly digest (email):** the analytics summary in plain English.

## 4.5 Plans and limits (enforced in code, not in copy)

| | Free scan | Starter $49/mo | Growth $99/mo | Agency $249/mo (Phase 2) |
|---|---|---|---|---|
| Businesses | 1 (one-time) | 1 | 1 | 5 |
| Tracked queries | 5 | 10 | 25 | 25 per business |
| Scan cadence | Once | Weekly | Daily | Daily |
| Engines | 3 | 3 | 3 | 3 (+Phase 2 additions) |
| GSC + GA4 connect | No | Yes | Yes | Yes |
| Trend history | None | 3 months | 12 months | 12 months |
| Competitor analytics | Top 1 per query | Top 3 per query | Full | Full |
| CSV export | No | No | Yes | Yes |
| Weekly digest | No | Yes | Yes | Yes |
| White-label reports | No | No | No | Yes |

## 4.6 Acceptance criteria (Phase 1 is not done until all pass)

1. Onboarding completes in under 3 minutes for a stranger with no help.
2. Scan accuracy: ≥85% agreement with manual checks on a 50-query sample across the 3 engines.
3. Per-customer monthly probing cost is measured and ≤ $2 (weekly) / ≤ $12 (daily) at build-time API prices.
4. A failed scan shows "scan failed — retrying" and never presents stale data as fresh. Stale data is labeled with its date.
5. GSC/GA4 connect works end-to-end with read-only scopes; unconnected state shows "not connected," never zero.
6. Stripe subscription, upgrade/downgrade, and one-click cancel all work in test mode and are verified in live mode with a real $1 test before launch.
7. No banned words anywhere (§9). Full copy pass.
8. Gate 2 (§13) — 5 paying customers retained 60 days — is the launch criterion, not a post-launch metric.

---

# PART 5 — PHASE 2: FIX ENGINE (the moat)

**Purpose:** close the loop. The tool that shows the gap *and* fixes it *and* proves it fixed it is the one customers keep. Phase 2 is also where the "fix, don't report" offer ranked #1 in the second-pass demand research lives ($495 one-time + $49/mo for a single-location fix package; agencies confirmed at ~$995/mo for the same job done by hand).
**Gate:** starts only after Phase 1 has 5 paying customers retained 60 days.

## 5.1 Scope

- **Full prioritized fix list** per business (not one fix per query — every diagnosis mapped to every fix, ranked by expected gap closed).
- **Drafted fixes:** the tool drafts the exact FAQ text, the JSON-LD schema, and the page outline for each fix. Drafts are generated from the diagnosis + the cited competitor pages (what the engines actually cited), not from generic templates.
- **Propose-and-approve, forever:** the owner approves each fix before anything changes. No auto-publishing. Ever. For care-plan customers, approved fixes deploy to the site through the care-plan deploy path; for standalone customers, the tool hands over the exact text/schema to paste, with a checklist.
- **Re-measurement:** after a fix is marked deployed, the next scan cycle measures whether the citation rate for the affected queries moved. The fix shows a status: `drafted → approved → deployed → measured (improved / no change / worse)`. A fix that made things worse is flagged, not hidden.
- **Agency tier:** 5 businesses, white-label reports, multi-client dashboard, per-client Visibility Scores.
- **ChatGPT/Grok coverage:** only if a legitimate path emerges (official API or a licensed data feed). **Never** by scraping the consumer UI or automating a consumer account. If no legitimate path exists, the product lists them as "not covered" — it does not fake them.
- **Content-site mode refinements:** Recipe schema checks, per-page citation tracking for P2.

## 5.2 Acceptance criteria (Phase 2)

1. A drafted fix is approved by the owner before any deployment — verified by an audit log entry for every deployed fix.
2. Re-measurement works: a deployed fix shows a measured outcome within 2 scan cycles.
3. Agency tier: 5 businesses under one account, white-label report renders with the agency's name and no GEO Scout branding.
4. No fix is ever deployed without approval — tested by attempting a deploy with no approval in staging (must fail).
5. ChatGPT/Grok remain "not covered" unless a legitimate API path is documented and approved by AJ.

---

# PART 6 — DATA MODEL (PostgreSQL)

All tables use `id` (UUID, primary key), `created_at`, `updated_at`. Money is integer cents. Timestamps are UTC. OAuth tokens are encrypted at rest (§7.5). No table stores a password in plain text; passwords are bcrypt-hashed.

| Table | Key columns | Notes |
|---|---|---|
| `users` | `email` (unique, citext), `password_hash`, `name`, `stripe_customer_id`, `plan` (enum: free/starter/growth/agency), `status` (active/trialing/past_due/canceled) | One user owns many businesses. |
| `businesses` | `user_id` FK, `name`, `website_url`, `normalized_domain` (unique per user), `city`, `state`, `category`, `gbp_url`, `entity_snapshot` (JSONB: name/address/phone as found on site) | `normalized_domain`: lowercase, no scheme/www/trailing slash. |
| `queries` | `business_id` FK, `text` (verbatim), `query_type` (money/brand), `location_context`, `is_active`, `demand_monthly` (int, nullable), `demand_source`, `demand_updated_at` | Demand cached 30 days (§3.4 step 4). |
| `scans` | `business_id` FK (nullable for free scans), `free_scan_id` FK (nullable), `status` (queued/running/complete/failed), `started_at`, `completed_at`, `engines_run` (array), `cost_cents` (measured per-scan cost) | Every scan logs its measured cost. |
| `scan_results` | `scan_id` FK, `query_id` FK, `engine` (enum: google_aio/perplexity/gemini), `cited` (bool), `position` (first_mention/mentioned/not_cited/failed), `cited_url`, `snippet` (text, ≤500 chars), `raw_response_ref` (pointer to stored raw API response, not the full blob inline) | One row per query × engine per scan. |
| `competitors` | `business_id` FK, `name`, `domain`, `first_seen_at` | Derived from scan results; a competitor is any other business cited in this business's queries. |
| `competitor_citations` | `scan_result_id` FK, `competitor_id` FK, `cited_url`, `snippet` | The evidence behind "who beat you." |
| `diagnoses` | `business_id` FK, `query_id` FK, `scan_id` FK, `cause` (enum from §4.1 taxonomy), `evidence` (JSONB), `created_at` | One row per cause per query per scan. |
| `recommendations` | `business_id` FK, `query_id` FK, `diagnosis_id` FK, `action_text`, `schema_json` (JSONB, nullable), `priority` (P1/P2/P3), `status` (pending/done/dismissed) | Phase 1: one top fix per query. Phase 2: full list. |
| `fixes` (Phase 2) | `recommendation_id` FK, `draft_text`, `status` (drafted/approved/deployed/measured), `deployed_at`, `measured_outcome` (improved/no_change/worse), `approved_by_user_id` FK | Approval is a row, not a flag. |
| `connections` | `business_id` FK, `provider` (gsc/ga4), `access_token_encrypted`, `refresh_token_encrypted`, `token_expires_at`, `scope`, `connected_at`, `last_sync_at`, `status` | Tokens encrypted with Fernet; key from env only (§7.5). |
| `click_stats` | `business_id` FK, `query_id` FK (nullable), `period_start`, `period_end`, `source` (gsc/ga4), `sessions`, `clicks` | Only from the business's own connected data. |
| `free_scans` | `business_name`, `website_url`, `normalized_domain`, `city`, `category`, `email` (nullable until captured), `status`, `report_slug` (unique), `scan_id` FK, `ip_hash`, `created_at` | One free scan per domain per 30 days (§3.3). |
| `email_captures` | `free_scan_id` FK (nullable), `email`, `source` (free_scan/digest/landing), `captured_at`, `unsubscribed_at` | |
| `subscriptions` | `user_id` FK, `stripe_subscription_id` (unique), `plan`, `status`, `current_period_end`, `cancel_at_period_end` | Mirrors Stripe; Stripe is the source of truth. |
| `scan_costs` | `scan_id` FK, `engine`, `provider`, `cost_cents`, `calls`, `recorded_at` | Per-engine cost ledger; feeds the cost gate. |
| `audit_log` | `user_id` FK (nullable), `action`, `entity_type`, `entity_id`, `details` (JSONB), `created_at` | Every fix approval/deployment, every plan change, every data export. |

**Indexes (minimum):** `businesses(user_id)`, `queries(business_id, is_active)`, `scans(business_id, started_at)`, `scan_results(scan_id, query_id, engine)`, `diagnoses(business_id, query_id)`, `free_scans(normalized_domain, created_at)`, `free_scans(report_slug)`, `connections(business_id, provider)`.

---

# PART 7 — FLASK ARCHITECTURE (pinned stack)

## 7.1 Stack (decisions are made — the agent does not re-litigate them)

| Layer | Choice | Why |
|---|---|---|
| Language | Python 3.12+ | The founder specified Flask; the ecosystem for scan jobs and data work is Python. |
| Web framework | **Flask 3.x** | Specified by the founder. |
| ORM / migrations | Flask-SQLAlchemy 3.x + Flask-Migrate (Alembic) | |
| Database | PostgreSQL 16 | JSONB for snapshots/evidence; the data model needs it. |
| Background jobs | Celery 5.x + Redis (broker + result backend), Celery Beat for scheduling | Scan jobs are long (2–5 min) and must not block requests. |
| Auth | Flask-Login (session auth) + Flask-WTF CSRF; bcrypt via `passlib`/`bcrypt` | Dashboard is server-rendered; no JWT needed for V1. |
| Templates / frontend | Jinja2 + Tailwind CSS + HTMX (no SPA, no React) | Server-rendered, fast to build, matches the "when in doubt, remove" design bar. |
| Billing | Stripe Billing + Stripe webhooks (checkout + customer portal) | |
| Email | Postmark (default) or SendGrid — pick Postmark; transactional only | |
| Google APIs | `google-auth` + `google-api-python-client`; OAuth read-only scopes (§7.5) | |
| External APIs | `httpx` (sync client inside Celery tasks; timeouts enforced) | |
| Secrets | Environment variables only. Fernet key for token encryption from env. Never in code, never in git. | |
| Errors / monitoring | Sentry (errors) + structured JSON logging | |
| Tests | pytest + pytest-flask; Playwright for the 3 critical e2e flows (§12) | |
| CI | GitHub Actions: lint (ruff), type check (mypy, strict on new code), tests, build | |
| Deploy | Docker + Fly.io (default) — one web service, one worker service, one Beat service, managed Postgres, managed Redis (Upstash). Alternative if Fly.io is unavailable: Render. | |
| Analytics (product) | Plausible or PostHog (self-hosted option) for the landing page + in-app events | No Google Analytics on the free-scan page (it would be ironic and slow). |

## 7.2 Repository layout

```
geo-scout/
├── app/
│   ├── __init__.py            # create_app factory; config from env
│   ├── config.py              # Config classes (dev/staging/prod); no secrets in code
│   ├── models.py              # SQLAlchemy models (Part 6)
│   ├── auth/                  # login, signup, password reset, sessions
│   ├── billing/               # Stripe checkout, portal, webhooks
│   ├── scans/                 # scan job, engine clients, parsers
│   │   ├── engines/
│   │   │   ├── perplexity.py
│   │   │   ├── gemini.py
│   │   │   └── google_aio.py  # SERP provider client
│   │   ├── diagnosis.py       # §4.1 taxonomy
│   │   ├── scoring.py         # Visibility Score, CTR, gap (§2.2)
│   │   └── tasks.py           # Celery tasks
│   ├── queries/               # prompt templates (category × city), demand lookup
│   ├── reports/               # report rendering, PDF (Phase 0 stretch)
│   ├── digest/                # weekly email job
│   ├── connections/           # GSC/GA4 OAuth, token encryption
│   ├── web/                   # Jinja routes: landing, dashboard, settings
│   └── api/
│       └── v1/                # REST API (JSON) — §7.3
├── migrations/                # Alembic
├── tests/                     # unit + integration + e2e
├── templates/                 # Jinja templates
├── static/                    # Tailwind build output, JS (HTMX), images
├── celery_app.py
├── wsgi.py
├── Dockerfile
├── fly.toml
├── pyproject.toml
└── README.md                  # setup, env vars, how to run scans locally
```

## 7.3 API (REST, `/api/v1`, JSON)

Auth: session cookie for browser calls; API keys (per-user, `sk_live_…`, hashed in DB) for any programmatic access. All endpoints return `{data, error}` shapes; errors carry a stable `code` (e.g. `SCAN_LIMIT`, `ENGINE_FAILED`, `NOT_CONNECTED`).

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/v1/free-scans` | POST | Start a free scan (§3.4). Rate-limited. Returns scan ID + status URL. |
| `/api/v1/free-scans/:id` | GET | Scan status + progress lines. |
| `/api/v1/businesses` | GET/POST | List/create businesses (plan limits enforced). |
| `/api/v1/businesses/:id` | GET/PATCH/DELETE | Business profile. |
| `/api/v1/businesses/:id/queries` | GET/POST | Tracked queries (plan limits enforced). |
| `/api/v1/businesses/:id/queries/:qid` | PATCH/DELETE | Edit/deactivate a query. |
| `/api/v1/businesses/:id/scans` | POST | Trigger a manual scan (within cadence; Starter cannot scan more than weekly). |
| `/api/v1/businesses/:id/scans/:sid` | GET | Scan detail: results per query × engine. |
| `/api/v1/businesses/:id/overview` | GET | Funnel roll-up: demand, citation rate, sessions, gap, score, trends. |
| `/api/v1/businesses/:id/competitors` | GET | Competitor share of voice. |
| `/api/v1/businesses/:id/recommendations` | GET | Diagnosis + top fix per query. |
| `/api/v1/businesses/:id/connections` | GET/POST/DELETE | GSC/GA4 OAuth connect/disconnect. |
| `/api/v1/billing/checkout` | POST | Stripe Checkout session for a plan. |
| `/api/v1/billing/portal` | POST | Stripe customer portal session. |
| `/webhooks/stripe` | POST | Stripe events: subscription created/updated/deleted, payment failed. Signature-verified. |

## 7.4 Background jobs (Celery)

| Task | Schedule / trigger | Behavior |
|---|---|---|
| `run_scan(business_id)` / `run_free_scan(free_scan_id)` | On demand + Beat | Runs §3.4 / §4.3.1. Logs per-engine cost to `scan_costs`. Retries 2× with backoff. Never presents stale data as fresh. |
| `schedule_due_scans` | Beat, hourly | Enqueues weekly scans (Starter, due Mondays) and daily scans (Growth, due daily). Respects plan cadence — never scan more often than the plan allows. |
| `refresh_demand` | Beat, daily | Refreshes keyword volume for queries whose cache is older than 30 days. |
| `send_weekly_digest` | Beat, Mondays 08:00 local | Builds and sends the digest (§4.3.4). Tracks opens/clicks; a digest with zero opens for 4 straight weeks flags the account for a personal check-in. |
| `send_free_scan_emails` | Triggered | Email 1/2/3 from §3.6. |
| `sync_gsc_ga4` | Beat, daily per connected business | Pulls clicks/sessions into `click_stats`. A failed sync marks the connection `error`, never silently stale. |
| `cost_budget_check` | Beat, daily | Sums `scan_costs` per customer; alerts (email + Sentry) if a customer exceeds the per-customer budget (§4.6.3). |

## 7.5 Google connections (GSC + GA4) — OAuth, read-only

- Scopes (minimum, read-only): `https://www.googleapis.com/auth/webmasters.readonly` (Search Console), `https://www.googleapis.com/auth/analytics.readonly` (GA4).
- Tokens encrypted at rest with Fernet (key from env, rotated by re-encrypting on next refresh; never logged, never in error messages).
- The connect flow is standard OAuth 2.0 with `access_type=offline` + `prompt=consent` so a refresh token is issued.
- **Default decision (§16.4): GSC/GA4 connect is OPTIONAL at onboarding.** Clicks stay locked behind "not connected — connect Search Console to unlock" until the user connects. The product never blocks onboarding on a Google connection.
- A business's queries, scans, and reports belong to that business. Never shared, sold, or used to train anything.

## 7.6 Rate limits, caching, and failure behavior

- **Rate limits (Flask-Limiter, Redis-backed):** free-scan starts 5/IP/hour, 20/IP/day; login attempts 10/IP/15 min; API 300 requests/user/hour; scan triggers 1/business/hour (manual) on top of cadence.
- **Caching:** SERP/API results are cached within a single scan run (never re-call the same query × engine twice in one scan). Demand values cached 30 days. Dashboard aggregates cached 15 min (stale-while-revalidate is not used for scan results — scan results are always read from the DB).
- **Failure behavior (binding):** a failed engine call is marked `failed`, shown as "couldn't check [engine]," and excluded from the score with a visible note. A failed scan shows "scan failed — retrying" and never presents stale data as fresh. Stale data is labeled with its date. If a data source is unavailable, the UI says so — it never shows a zero or a guess.
- **No UI scraping of consumer ChatGPT/Gemini/Grok.** Official APIs only. If an engine has no API path, it is listed as "not covered in V1," not faked. If any requirement in this spec conflicts with an engine's terms of service, the terms win — flag it to AJ instead of working around it.

---

# PART 8 — ENGINE INTEGRATIONS (the honest method per engine)

**Rule for all engines:** measure what the API returns, parse citations from the response, store the raw response reference. Never synthesize a citation. Never present a proxy as the real thing.

## 8.1 Google AI Overviews (via SERP API)

- **Method:** SERP API call with the query + location (city, state) + device (desktop default; mobile as a Phase 1 stretch). Parse the AI Overview block: cited sources (URLs + positions), overview text. A business is "cited" if its domain appears in the overview's cited sources.
- **Provider (default, §16.2):** DataForSEO (AI Overview endpoint). **VERIFY AT BUILD:** confirm the endpoint, the per-1,000-call price (planning figure: $1.20/1,000 standard queue), and the location parameter format. Alternate: SerpApi — cost-check both at build and record the comparison in the repo (`docs/vendor-check.md`). Do not hard-code the provider choice in code; it lives in config.
- **Known constraint:** Google Custom Search API ends Jan 1, 2027 — it is not the path. Do not build on it.
- **Cost driver:** one SERP call per query per scan. 10 queries × 4 scans/month = 40 calls/mo on Starter — negligible at the planning price, but measure it.

## 8.2 Perplexity (official API)

- **Method:** official Perplexity API. Send the query as a user question; parse the returned citations (URLs) from the response. A business is "cited" if its domain appears in the citations.
- **VERIFY AT BUILD:** Perplexity retired Sonar Chat Completions on Sep 27, 2026. The agent must confirm the current official endpoint and request/response shape at build time and record it in `docs/vendor-check.md`. **Do not build against a retired endpoint.** Planning cost: ~$0.007/call.
- **Known constraint:** Perplexity's API answers are not identical to what a consumer sees in the Perplexity app. The product labels results "observed in our scans via the Perplexity API" and never claims they are the consumer experience.

## 8.3 Gemini (official API with grounding)

- **Method:** Gemini API with Google Search grounding enabled. Send the query; parse grounding sources (URLs) from the response. A business is "cited" if its domain appears in the grounding sources.
- **VERIFY AT BUILD:** confirm the grounding endpoint, the per-search billing (planning figure: $14/1,000 searches, 5,000 free/mo — billed per search, not per prompt), and the response shape. Grounding is the biggest cost variable in the product: a daily Growth customer with 25 queries runs 25 searches/day/engine-set — measure it in the first week of Phase 1 and report it to AJ before scaling.
- **Known constraint:** same as Perplexity — the API result is a proxy for the consumer experience, labeled as such.

## 8.4 ChatGPT and Grok — NOT in Phase 0 or Phase 1

- **ChatGPT:** there is no public API for consumer ChatGPT answers. The product does not cover it in Phase 0 or Phase 1 and never fakes it. The UI lists it as "not covered — no public API exists." An OpenAI Responses API call with web search is a *proxy*, not consumer ChatGPT — it may be used in a clearly-labeled experiment only with AJ's explicit approval, never as a shipped feature presented as ChatGPT coverage. Cost note for planning only: a proxy would add ~$5–10/customer/mo at daily cadence.
- **Grok:** API availability to be verified at build time; if a legitimate API path exists, it enters Phase 2 planning. Grok API pricing (planning figures, VERIFY AT BUILD): ~$2/$6 per 1M tokens, web search $5/1,000 searches.

## 8.5 Non-determinism (AI answers change run to run)

- AI answers are non-deterministic: repeat-naming of the same business across runs is ~56% (research figure). **Consequence for the product:** a single scan is a sample, never a verdict. The product shows trends (citation rate over scans), never a single-run judgment ("you rank #1" / "you're invisible") based on one scan. The Visibility Score is a rolling average across the last 4 scans, not the latest scan alone. The weekly digest reports movement, not a snapshot.
- **Spot-check procedure (§12):** a human manually asks the same 3 engines the same queries and compares cited/not-cited. Target ≥85% agreement. Disagreements are logged and investigated, not hidden.

## 8.6 Vendor verification checklist (complete at build, before launch)

The agent records the results in `docs/vendor-check.md` (a living file, re-checked quarterly):

1. DataForSEO AI Overview endpoint, price, location parameters — confirmed live.
2. SerpApi equivalent price — cost comparison recorded; provider choice justified.
3. Perplexity current official endpoint + request/response shape — confirmed live (not the retired Sonar Chat Completions).
4. Gemini grounding endpoint + per-search billing — confirmed live.
5. DataForSEO keyword-volume endpoint + price — confirmed live.
6. Stripe Billing + webhook signature verification — tested in test mode and live mode.
7. GSC + GA4 OAuth read-only scopes — consent screen configured, scopes verified.
8. Postmark (or SendGrid) sending domain + SPF/DKIM — verified.
9. Fly.io deploy + managed Postgres + Redis — running in staging.

---

# PART 9 — HONESTY, COPY & COMPLIANCE (binding)

## 9.1 Banned words

Never in product, marketing, sales, or placeholder copy: **"guarantee," "ensure," "rank #1," "top of Google," "we'll get you cited," "dominate," "crush."** Approved language: "visibility," "citations," "observed," "estimated," "tracked," "gap." A full copy pass for banned words is a launch gate (§13).

## 9.2 Labeling rules

- ESTIMATED numbers always carry an "estimated" badge + tooltip naming the source and method.
- MEASURED numbers carry their source label ("observed in our scans," "from your Search Console").
- Unavailable data shows "not connected" / "not covered in V1" / "not checked" — never zero, never a guess.
- Sample/demo data is watermarked SAMPLE and never mixed with real scans.
- Every score has a "how this is calculated" link. No black-box numbers.

## 9.3 Privacy, security, and terms

- A business's queries, scans, and reports belong to that business. Never shared, sold, or used to train anything.
- OAuth tokens encrypted at rest (Fernet, key from env). Passwords bcrypt-hashed. Secrets in env only, never in code or git.
- Stripe is the source of truth for subscriptions; the local `subscriptions` table mirrors it.
- Respect engine terms: official APIs only. No credential sharing, no automation of consumer UIs. If a requirement conflicts with an engine's ToS, the ToS wins — flag it to AJ.
- No medical/legal/financial claims. This is a measurement tool.
- Data retention: scan results retained for the life of the account + 90 days after cancellation (then deleted). A user can export their data (CSV, Growth+) and request deletion at any time; deletion completes within 30 days.
- Logs never contain API keys, OAuth tokens, or full raw engine responses with personal data.

---

# PART 10 — PRICING & BILLING

| Plan | Price | Cadence | Limits (§4.5) |
|---|---|---|---|
| Free scan | $0 | Once | 5 queries, 1 scan, shareable report |
| Starter | $49/mo | Weekly scans | 1 business, 10 queries, 3 engines, 3-mo history |
| Growth | $99/mo | Daily scans | 1 business, 25 queries, competitor analytics, 12-mo history, CSV |
| Agency (Phase 2) | $249/mo | Daily | 5 businesses, white-label |
| Fix package (Phase 2) | $495 one-time + $49/mo | Per location | Drafted fixes + deploy-with-approval + re-measurement |
| Care-plan bundle | TBD at launch (§16.5) | — | Starter included in the $99/mo care plan, or a bundle price set at launch. Do not hard-code a discount in Phase 0/1 copy. |

- **Billing implementation:** Stripe Billing, monthly subscriptions, Checkout for signup, Customer Portal for management. Webhooks (signature-verified) drive `subscriptions` status. Failed payments: Stripe Smart Retries + 3 dunning emails, then pause scans (account stays readable, scans stop). **Cancel is one click, no retention dark patterns;** exit survey is one optional question.
- **Pricing is config, not code.** Plan prices, query limits, and cadences live in the database/config, not hard-coded. Changing a price is a config change, not a deploy.
- **Free-trial policy:** no free trial of the paid plans — the free scan *is* the trial. A 14-day money-back guarantee on first payment is the risk reversal (decide at launch; default: yes).

---

# PART 11 — DESIGN & UX

## 11.1 Design bar (the founder's bar, binding)

Simple, elegant, coherent. **"When in doubt, remove."** Never a generic AI-built page; the design must excite. Reference standard: the founder's running tracker (clean, map-forward, one job done beautifully). Dense multi-row data goes in a real table, not in cards. One funnel, one table, one score — done well — beats a dashboard of twenty charts. Content is data, never hard-coded: queries, engines, prices, and recommendation rules live in config/database, not in code.

## 11.2 Pages (Phase 1)

| Page | Job | Design note |
|---|---|---|
| Landing / free scan (`/`) | Convert a stranger into a scan | One line of problem, the form, 3 SAMPLE reports, honesty note, FAQ. No nav clutter. |
| Report (`/r/:slug`) | Deliver the shock + the fix | §3.5 layout. The single most-designed page in the product. |
| Dashboard (`/app`) | The daily home | §4.3.2. One score, one table, one next fix. |
| Query detail (`/app/queries/:id`) | The evidence for one query | §4.3.3. Snippets verbatim and short. |
| Competitors (`/app/competitors`) | Who beat you | Share-of-voice bars, cited pages, nothing else. |
| Settings (`/app/settings`) | Profile, queries, connections, billing | Boring on purpose. |
| Billing (Stripe portal) | Pay / change / cancel | Stripe-hosted; do not rebuild it. |

## 11.3 Copy tone

Plain English, one page, one number, one next fix. The weekly digest reads like a text from a sharp friend, not a SaaS newsletter. Numbers first, adjectives last. Every claim in copy must survive §9. If a sentence promises an outcome, delete the sentence.

## 11.4 Accessibility & performance

- All pages usable at 360px wide (phone) and 1440px (desktop). No horizontal scroll on mobile.
- Dashboard first paint under 1.5s on a warm cache; scan progress page updates without full reloads (HTMX/SSE).
- WCAG 2.1 AA for contrast and focus states. Forms labeled. Errors in plain language next to the field.

---

# PART 12 — TESTING, QA & ACCEPTANCE

## 12.1 Test layers

| Layer | What | Target |
|---|---|---|
| Unit | Scoring formulas (§2.2), gap math, diagnosis rules, plan-limit enforcement, cost logging | Every formula has a test with hand-computed values. A formula change without a test update fails CI. |
| Integration | Engine clients against recorded fixtures (VCR-style cassettes, refreshed monthly); Stripe webhooks in test mode; GSC/GA4 OAuth in sandbox | No test calls a live paid API. |
| E2E (Playwright) | The 3 critical flows: (1) free scan start → report; (2) signup → onboarding → first scan → dashboard; (3) connect GSC → clicks appear | Run on every PR against staging. |
| Accuracy spot-check | Human asks the 3 engines the same queries, compares cited/not-cited | ≥85% agreement (§8.5). Run weekly in Phase 0, monthly in Phase 1. Log every disagreement. |
| Copy pass | Full read of every UI string, email, and placeholder for banned words (§9.1) and for any promised outcome | Before every phase launch. |
| Cost audit | Sum `scan_costs` per customer for the trailing 30 days; compare to §1.5 budgets | Weekly in Phase 1. Over budget → alert + investigation, never silent. |
| Security | Dependency audit (`pip-audit`), secret scan (gitleaks in CI), OAuth token encryption verified, rate limits tested | Every PR; full pass before launch. |

## 12.2 Definition of done (every phase)

1. All acceptance criteria for the phase (§3.7 / §4.6 / §5.2) pass with evidence (test output, screenshots, or a manual-check log — not a claim).
2. No banned words anywhere. No fake data anywhere. No hard-coded prices, limits, or engine endpoints.
3. `docs/vendor-check.md` is current for every external dependency the phase uses.
4. The phase is deployed to staging, then production, with a rollback plan (Fly.io release + DB migration that is reversible or forward-only-safe).
5. AJ has reviewed the phase on staging and said go. **Silence is not approval.**

---

# PART 13 — VALIDATION GATES & LAUNCH PLAN (binding)

These gates decide whether the next phase gets built. They are not marketing. A gate that fails stops the build.

## Gate 1 — Free-scan landing page (Phase 0 → Phase 1)

Run for 2 weeks from launch. **Pass = all three:** ≥100 scans completed, ≥20% email capture, ≥10 calls booked (15-minute calls from email 3, §3.6). **Fail = any one misses by more than half** (e.g. <50 scans) → stop, diagnose (traffic? offer? report quality?), fix once, re-run 2 weeks. **Fail twice → do not build Phase 1.** Fallback: sell one-off AI audits to care-plan clients (manual scan + report, $495 one-time) and revisit in 6 months.

## Gate 2 — Interviews & paying pilots (runs alongside Phase 1 build)

10–15 interviews with local businesses (contractor/HVAC first, from the founder's network) and dogfooding on Aayushi's blog + 3 local businesses for 4 weeks of scans before any paying customer. **Pass = ≥5 businesses pay for a 3-month pilot** (paid upfront or monthly with a 3-month commitment). **Fail → do not launch Phase 1 publicly.** Keep the pilots as a concierge service.

## Gate 3 — Concierge pilot & retention (Phase 1 → Phase 2)

4-week concierge pilot with the 5 paying customers: weekly scans run by hand if needed, fixes delivered manually, retention measured. **Pass = 5 paying customers retained 60 days** (same gate as the care plan). **Fail → Phase 2 does not start.** Fix retention first (report quality, fix quality, onboarding) or shut the SaaS down and keep the audit service.

## Launch sequence

1. Phase 0 live → Gate 1 (2 weeks) → decision.
2. Gate 2 interviews (parallel with Phase 1 build) → decision.
3. Phase 1 live to pilots → Gate 3 (60 days) → decision.
4. Phase 2 only after Gate 3 passes.

---

# PART 14 — GO-TO-MARKET & DISTRIBUTION

## 14.1 Beachhead (who first)

1. **Care-plan customers** (existing $99/mo site-care base): Starter included or bundled at launch; they already open the monthly report.
2. **The founder's contractor network** (HVAC, plumbers, roofers, GCs): the free scan is the conversation opener; a bad score is the pitch.
3. **Aayushi's food-blog audience** (P2): recipe sites are the most AI-Overview-exposed category; a food-blogger scan report is highly shareable.

## 14.2 Channels (ranked by fit)

1. **The free scan itself** (SEO + answer-engine + shareable reports): every report is a landing page; every shared bad score is distribution. Optimize the report page for "how do I show up in ChatGPT" and "[city] [category] AI search" queries.
2. **Founder network & direct outreach:** personal messages to contractors with their own scan result attached ("here's what AI says about your business — want the full picture?"). This is the highest-converting channel and the only one that works at zero CAC.
3. **Short-form video:** 60-second "I asked AI for the best plumber in Fremont — here's who it named and why" videos, one city × trade at a time. The scan result is the content.
4. **Local partnerships:** chambers of commerce, trade associations, and the Mills Realty / flipper network — a co-branded scan for their members.
5. **Paid ads:** only after CAC is measured under $300 on organic channels, and only for the trades product. Paid ads fail for one-off/low-LTV consumer products and are not a launch channel.

## 14.3 "Everybody on earth" — the honest version

Mass reach is won niche-by-niche, not at launch. The sequence is: one trade in one city (Fremont HVAC) → one trade nationally (HVAC everywhere) → all home services → all local services → content sites. Each beachhead must be won (≥100 scans, ≥20% capture, ≥10 calls) before the next starts. What would have to be true for genuinely viral reach: the shareable report becomes the thing business owners post when they get a bad score (social proof + curiosity), and a platform event (e.g. BrightLocal shipping a GEO tab) validates the category in the press. Neither is plannable; both are prepared for by making the report page excellent.

## 14.4 Metrics that matter (reviewed weekly)

Scans started → scans completed → email captures → calls booked → trials → paying → retained 60 days → expansion (Growth/Agency). One funnel, one table. Vanity metrics (page views, social likes) are not reviewed.

---

# PART 15 — RISKS & MITIGATIONS

| Risk | Likelihood / impact | Mitigation |
|---|---|---|
| BrightLocal adds a GEO tab | High / existential for the local wedge | Be the GEO product their customers use first; deepen the local prompt library and the fix loop (things a tab can't copy in a quarter). |
| Suites bundle GEO free (Ahrefs $50, SE Ranking $99) | High / medium | Compete on local depth + fix loop, not on coverage breadth. Never race a suite on price. |
| Perplexity / Gemini API changes or pricing | Medium / high | Abstraction layer: engine clients behind one interface (§7.2); vendor-check quarterly (§8.6); cost alerts (§7.4). |
| Google Custom Search API ends Jan 1, 2027 | Certain / low | Not the path. SERP provider only (§8.1). |
| AI answers non-deterministic (~56% repeat-naming) | Certain / medium | Trends, not snapshots; rolling 4-scan Visibility Score; spot-checks (§8.5). |
| SMB willingness to pay unproven | High / existential | Gates (§13). Free scan first; audits fallback. Never build the dashboard on faith. |
| ChatGPT coverage pressure (customers ask "where's ChatGPT?") | Certain / medium | Honest "not covered" labeling; the proxy question is a Phase 2 decision for AJ only. Never fake it. |
| CAC exceeds $300 at $49 | Medium / high | Kill criterion (§1.5). Organic + network channels only until CAC is proven. |
| Legal: roof/insurance-adjacent fix advice | Low / medium | The product measures and suggests content/schema fixes only. It never negotiates claims, never acts as a public adjuster, never gives legal advice. |

---

# PART 16 — OPEN DECISIONS (with defaults so the agent is never blocked)

| # | Decision | Default in this spec (agent builds to this unless AJ overrides) |
|---|---|---|
| 1 | **Name** | Working title GEO Scout. Ship Phase 0 under it; renaming is a config + copy change, not a rebuild. |
| 2 | **SERP provider** | DataForSEO. Cost-check vs. SerpApi at build; record in `docs/vendor-check.md`. Provider lives in config. |
| 3 | **Free-scan limits** | 5 queries / 1 scan / 1 report per domain per 30 days. |
| 4 | **GSC/GA4 connect** | Optional at onboarding. Clicks locked behind "not connected" until connected. |
| 5 | **Care-plan bundle price** | Set at launch. Do not hard-code a discount in Phase 0/1 copy. |
| 6 | **Free-trial / money-back** | No free trial of paid plans (the free scan is the trial). 14-day money-back on first payment. |
| 7 | **ChatGPT proxy** | Not shipped. Phase 2 decision for AJ only, clearly labeled if ever used. |

---

# PART 17 — AGENT INSTRUCTIONS (read first, follow literally)

1. **Read order:** this header → Part 1 → §2.2–2.3 → Part 3 → §7 → §9 → §13 → the rest.
2. **Phase discipline:** build Phase 0 completely and launch it. Do not start Phase 1 until Gate 1 passes. Do not start Phase 2 until Gate 3 passes. If AJ tells you to skip a gate, ask him to confirm in writing in this thread and record the override in `docs/decisions.md` with the date.
3. **Analytics first.** If a feature doesn't produce a measurable number, it doesn't ship in Phase 0 or Phase 1.
4. **Never invent a metric.** No AI-search-volume numbers. No competitor-click numbers. No ChatGPT coverage in Phase 0/1.
5. **Every number has a source label** (measured or estimated). The label is part of the feature, not a tooltip afterthought.
6. **No guarantee language anywhere** — product, emails, or placeholder copy. If you catch yourself writing "rank #1," delete the sentence.
7. **Content is data, never hard-coded:** queries, engines, prices, and recommendation rules live in config/database, not in code.
8. **When in doubt, remove.** One funnel, one table, one score — done well — beats a dashboard of twenty charts.
9. **Verify every external price, endpoint, and limit at build time** and record it in `docs/vendor-check.md`. Prices in this spec are planning figures, not facts. Perplexity's Sonar Chat Completions endpoint is retired — do not build against it.
10. **No invented data in demos.** Sample data is watermarked SAMPLE.
11. **If a requirement conflicts with an engine's terms of service, the terms win** — flag it to AJ instead of working around it.
12. **Definition of done is §12.2.** A phase is not done when the code runs; it is done when the acceptance criteria pass with evidence and AJ has said go on staging. Silence is not approval.
13. **Commit discipline:** small commits, one feature per commit, tests with every behavior change, no secrets in git (gitleaks runs in CI).
14. **Report progress in the language of §14.4:** scans, captures, calls, paying, retained — not lines of code or hours worked.

---

## Document history

- Nov 8, 2026 — `DESIGN.md` (concept spec, 260 lines, §0–§17). Working title GEO Scout; analytics-first redirect; honesty constraints; pricing $49/$99/$249; Next.js placeholder stack.
- Nov 8, 2026 — Market research (deep research): verdict BUILD WITH CONDITIONS; local-first wedge; corrected the price-gap claim; validation gates set.
- Nov 8, 2026 — Second-pass demand research: AI-Visibility Fix ranked #1 of 9 ideas ("fix, don't report"); agencies ~$995/mo; BrightLocal Sep 2026 citation data (websites 42%, GBP 28.63%).
- Nov 11, 2026 — **This document (`SPEC.md`)**: complete build spec. Flask stack pinned per the founder. Phases made explicit with binding gates. YC-grade company case (Part 1), full data model (Part 6), engine methods with verification checklist (Part 8), and agent instructions (Part 17). Supersedes `DESIGN.md` as the build authority.
