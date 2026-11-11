# Vendor verification

Checked 2026-11-11 against public vendor documentation. No paid calls were made.
Documented API shapes are not the same as an authenticated integration test.

| Dependency | Finding | Live account status |
|---|---|---|
| Perplexity | Agent API POST `https://api.perplexity.ai/v1/agent`; fast effort with web_search. Completed `output` messages have output_text; citations can be url_citation annotations or numbered references to search_results IDs. `usage.cost.total_cost` reports request cost when present. | Account/key absent; paid fixture validation and actual costs pending. |
| Sonar migration | Official migration page confirms support ended September 27, 2026; some synchronous legacy requests are reformulated as Agent API requests. This build uses Agent API directly. | No legacy endpoint used. |
| Google AI Overviews | DataForSEO POST `/v3/serp/google/organic/live/advanced`; task array, explicit location/language/device. `ai_overview` references parsed; `load_async_ai_overview=true` may add $0.002 when used. Parse provider-reported task cost. | Account absent. Live path chosen for interactive latency; queue pricing from the spec is not the live rate. Exact baseline price, location codes and billing require verification. |
| Search demand | DataForSEO POST `/v3/keywords_data/google_ads/search_volume/live`; accepts up to 1,000 keywords in one array and charges per request, not simply per keyword. Cache by query and configured geography for 30 days. | No account; price and live keyword coverage pending. |
| SerpApi comparison | Public page lists Free 250 searches/month; Starter $25 for 1,000; Developer $75 for 5,000; Production $150 for 15,000. Per-included-search equivalents: $0.025/$0.015/$0.01, assuming full utilization. AIO retrieval may require additional requests. | Alternative not implemented. DataForSEO choice remains provisional until actual costs are compared. |
| Gemini | Current docs recommend Interactions API POST `/v1beta/interactions`; legacy generateContent remains supported. Gemini 3+ search billing: $14/1,000 search queries after 5,000 shared free/month; default paid grounding cap 1,500/day. **Terms prohibit the intended tracking/analysis/storage of grounded results. Integration disabled.** | Do not create/request a Gemini key for this build. A written permission or a suitable licensed feed is required to reconsider coverage. |
| Turnstile | Server verification POST `/turnstile/v0/siteverify`; verify success, hostname and free_scan action. | Site/secret keys and production hostname registration pending. |
| Postmark | POST `https://api.postmarkapp.com/email`; server token header, response ErrorCode check. | Account/sender/SPF/DKIM absent. Configure appropriate streams for consented follow-ups before enabling the sequence; the default outbound stream must not be assumed suitable for promotional mail. |
| Fly.io | Docker deployment config supplied for web, worker and one Beat process; PostgreSQL and Redis URLs required. | No hosting account; no staging/live environment or deployment verification yet. |
| Stripe, GSC, GA4 | Outside Phase 0. | Not implemented; no credentials requested. |

## Primary sources read

- https://docs.perplexity.ai/docs/agent-api/quickstart.md
- https://docs.perplexity.ai/api-reference/agent-post.md
- https://docs.perplexity.ai/docs/agent-api/migrate-from-sonar/overview
- https://docs.perplexity.ai/docs/getting-started/pricing.md
- https://docs.dataforseo.com/v3/serp/google/organic/live/advanced/
- https://docs.dataforseo.com/v3/keywords_data/google_ads/search_volume/live/
- https://serpapi.com/pricing
- https://aistudio.google.com/docs/google-search.md
- https://aistudio.google.com/api-reference/interactions-api/create-interaction.md
- https://aistudio.google.com/docs/pricing.md
- https://aistudio.google.com/docs/terms#grounding-with-google-search
- https://developers.cloudflare.com/turnstile/get-started/server-side-validation/
- https://postmarkapp.com/developer/api/email-api

## Specific Gemini restriction

The Grounding with Google Search use-restrictions section says: "You will not ... cache,
frame, syndicate, resell, analyze, train on, or otherwise learn from Grounded Results or
Search Suggestions." It also prohibits copying, storing or implementing monitoring of
grounded results except narrow display/history/legal exceptions. This app's database of
citations and visibility metrics does not fit those documented exceptions.

## Still required before launch

Authenticated recorded fixtures; cost reconciliation including failed attempts; provider
terms and commercial redistribution review for the remaining integrations; ≥85% human
spot-check agreement; sender-domain verification; staging failure exercise; verified
hosting costs; Ajay's staging approval. Re-check vendor docs quarterly and on API changes.
