# Workflow: Create a Newsletter Issue

## Objective
Turn a topic into a researched, well-written HTML newsletter with one hero infographic, delivered as a Gmail draft for approval, then sent.

**Default mode is zero-cost.** The agent (Claude Code) does the research and writing in-session, a Python script draws the infographic, and the Gmail API (free) creates the draft. The paid tools (Anthropic API and Kie.ai) are kept as an optional path at the bottom.

## Required inputs
- **Topic** (required): e.g. "The state of solid-state batteries"
- **Audience** (optional): defaults to "curious professionals who want a smart, fast briefing"
- **Tone** (optional): defaults to "confident, warm and plain-spoken; no hype or jargon"

## Prerequisites (one-time)
- `.env` has `NEWSLETTER_NAME` and `NEWSLETTER_TO`
- `credentials.json` (Google OAuth Desktop client with the Gmail API enabled) is in the project root
- First Gmail run: `py tools/gmail_send.py --auth` opens a browser for consent and saves `token.json`
- Dependencies: `py -m pip install -r requirements.txt` (use `py`; `python`/`pip` are not on PATH on this machine)

## Steps
Run commands from the project root. Each issue lives in `.tmp/<slug>/`, where the slug is `YYYY-MM-DD-topic-words`, e.g. `2026-10-12-solid-state-batteries`.

1. **Research (agent):** use WebSearch and WebFetch.
   - Aim for 5+ recent, authoritative sources: primary sources, reputable outlets, official data.
   - Collect concrete facts, exact numbers with dates, recent developments, and 3-5 headline stats suited to an infographic.
   - Only use facts you actually found; never invent statistics.
2. **Write (agent):** create `.tmp/<slug>/content.json` with the Write tool, using the schema below.
   - Length: 3-4 sections of 120-250 words each, about a 4-6 minute read.
   - Formatting: short paragraphs, **bold** key numbers, and bullets where useful.
   - Subject line under 60 characters. Preheader under 100.
   - `sources` must contain only URLs you actually used.
3. **Validate:** `py tools/validate_content.py --issue <slug>`. Fix anything it reports.
4. **Infographic:** `py tools/draw_infographic.py --issue <slug>`, which writes `hero.png` (1600x900).
   - Open `hero.png` with the Read tool and check it. Stat values should be short, at most 12 characters, e.g. "400 Wh/kg", "2x", "$1.2B".
   - Labels should be one short sentence.
5. **Build HTML:** `py tools/build_html.py --issue <slug>`, which writes `newsletter.html` (for email) and `preview.html` (for a browser).
6. **Draft:** `py tools/gmail_send.py --issue <slug> --draft`, which creates a Gmail draft to `NEWSLETTER_TO`.
7. **STOP and ask the user** to review the draft in Gmail > Drafts.
8. **Send (only after the user approves):** `py tools/gmail_send.py --send <draft_id>`. The draft ID is in `.tmp/<slug>/draft.json`.

## content.json schema
```json
{
  "topic": "...",
  "subject": "Under 60 chars",
  "preheader": "Inbox preview text, under 100 chars",
  "title": "Headline at the top of the email",
  "intro": "Opening paragraph (markdown)",
  "sections": [{"heading": "...", "body_md": "markdown, 120-250 words"}],
  "key_takeaways": ["One sentence each, 3-5 items"],
  "sources": [{"title": "...", "url": "https://..."}],
  "image_alt": "One-sentence description of the infographic",
  "infographic": {
    "title": "Short infographic headline",
    "subtitle": "Optional one-liner",
    "stats": [{"value": "400 Wh/kg", "label": "What the number means, one sentence"}],
    "source": "Main source name(s)"
  }
}
```
- `infographic.stats` takes 2-5 entries.
- With 4 or more stats, keep labels under about 60 characters so each fits in 3-4 lines.

## Edge cases and known behaviour
- **Sites that block WebFetch:**
  - Blocked so far: cnbc.com, forbes.com, aljazeera.com, and openai.com (403).
  - Use their facts from search-result summaries, or find the same facts on sites that load: TechCrunch, Slashdot (often quotes Bloomberg), and detailed explainer blogs that cite official help and pricing pages.
  - Attribute carefully and don't list a blocked page as a source unless its facts were confirmed elsewhere.
- **Vendor or competitor content:** skip benchmark comparisons that involve Anthropic/Claude models (the agent is Claude, so it's a conflict of interest), and skip rumours based on unnamed sources.
- **Not enough good stats for an infographic:**
  - Use 2-3 strong ones rather than padding with weak numbers.
  - If there are none, remove the `infographic` key and skip step 4. The email builds fine without `hero.png`.
- **Images:**
  - They're embedded inline (CID) rather than hot-linked, because Gmail strips data: URIs.
  - `build_html.py` skips the image automatically if `hero.png` is missing.
- **Gmail token expired or revoked:**
  - In Testing mode, tokens can expire after about 7 days.
  - The tool re-runs consent automatically. If that fails, delete `token.json` and run `--auth`.
- **Gmail "access blocked" during consent:** add the user's Google account as a test user on the OAuth consent screen.

## Optional paid path (not used by default)
These tools work but need paid API credit:
- `py tools/research_topic.py --topic "..."`: research with Claude API and web search. Writes `research.json` and prints the slug. Needs `ANTHROPIC_API_KEY`.
- `py tools/write_newsletter.py --issue <slug>`: writes `content.json` via the Claude API, including an `image_prompt` field.
- `py tools/generate_infographic.py --issue <slug>`: an AI image via Nano Banana on Kie.ai. Needs `KIE_API_KEY`.
  - Kie returns HTTP 200 even on errors. The real status is the `code` field: 401 bad key, 402 no credits, 422 bad parameters, 429 rate limited.
  - Image URLs expire after 14 days.

They're useful for running unattended. Use them only if the user adds credit.

## Changelog
- 2026-10-12: Initial version (paid tools).
- 2026-10-12: User has no budget for paid APIs. Default switched to agent-written content plus the Pillow-drawn infographic (`draw_infographic.py`), with `validate_content.py` added.
