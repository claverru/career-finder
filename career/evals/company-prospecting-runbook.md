# Company Prospecting Eval Cases

## Case 1: No vacancy required

- Input: a high-signal company discovered from a public leaderboard with no published role page.
- Expected: the company can still become a valid prospect if role plausibility and contact resolution are strong enough.

## Case 2: Contact priority avoids seniority bias

- Input: public evidence shows both a recruiter and a founder.
- Expected: the recruiter wins when both are relevant and public; the founder is not selected by default.

## Case 3: Public-channel fallback

- Input: no named person is available but a verified `careers@` or contact page exists.
- Expected: the prospect remains valid with lower `contact_confidence`.

## Case 4: Established company remains eligible

- Input: a large, established company with strong role and geography signals.
- Expected: it is not penalized for company size or maturity.

## Case 5: Generic marketing user

- Input: a marketing CV and a company with clear growth and marketing-function signals but no published marketing vacancy.
- Expected: the company can become a valid prospect for a marketing role family.

## Case 6: Dedupe in prospect state

- Input: the same company and target role family appear in multiple batches.
- Expected: `sync_prospect_state.py` keeps one canonical prospect keyed by `company + target_role_family`.
