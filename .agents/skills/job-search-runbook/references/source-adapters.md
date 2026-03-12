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
- never use `linkedin_public` or an aggregator as the final apply link
- if a source later needs an MCP-backed integration, add it behind the same adapter boundary
