# Source Adapters

Supported source kinds:

- `greenhouse`: public Greenhouse board API
- `lever`: public Lever postings API
- `ashby_public`: public Ashby board HTML
- `company_html`: official careers pages
- `linkedin_public`: public LinkedIn job URLs for discovery only

Rules:

- use the query plan to choose which sources to hit
- prefer direct ATS or official pages over generic web pages
- prefer public ATS APIs over board HTML when both are available
- never use `linkedin_public` or an aggregator as the final apply link
- if a source later needs an MCP-backed integration, add it behind the same adapter boundary

Adapter notes:

- `greenhouse`: prefer the public board API when available; use the board page HTML only as fallback.
- `lever`: prefer the public postings API at `https://api.lever.co/v0/postings/<site>?mode=json&limit=100`.
  Useful fields include `hostedUrl`, `applyUrl`, `categories.location`, `categories.allLocations`, `workplaceType`, `descriptionPlain`, and `additionalPlain`.
  Use it both for discovery and to verify whether a previously seen role is still active on the current official board.
