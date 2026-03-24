# Source Adapters

Supported source kinds:

- `leaderboard`: public ranking or leaderboard pages that list promising companies
- `funding_roundup`: public funding or growth roundup pages
- `company_directory`: public company directories or category pages
- `company_html`: official company pages such as home, about, careers, or contact
- `linkedin_company`: public LinkedIn company pages for discovery only
- `public_people`: public people or team pages used to improve contact resolution

Rules:

- validate the company before selecting a contact
- prefer official company pages over third-party directories when both are available
- never invent an email address or private contact detail
- recruiter or hiring contacts outrank founders when both are public and relevant
- a verified public channel is a valid fallback when no named person is available
