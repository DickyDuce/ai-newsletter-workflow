"""Write the newsletter content (and the infographic prompt) from research.json.

Usage: py tools/write_newsletter.py --issue <slug> [--tone "..."]
Output: .tmp/<slug>/content.json
"""
import argparse
import json
import sys

from claude_client import run
from common import env, issue_dir, read_json, write_json

SCHEMA = {
    "type": "object",
    "properties": {
        "subject": {"type": "string", "description": "Email subject line, under 60 characters"},
        "preheader": {"type": "string", "description": "Inbox preview text, under 100 characters"},
        "title": {"type": "string"},
        "intro": {"type": "string", "description": "Opening paragraph, markdown allowed"},
        "sections": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "heading": {"type": "string"},
                    "body_md": {"type": "string", "description": "Markdown body, 120-250 words"},
                },
                "required": ["heading", "body_md"],
                "additionalProperties": False,
            },
        },
        "key_takeaways": {"type": "array", "items": {"type": "string"}},
        "sources": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"title": {"type": "string"}, "url": {"type": "string"}},
                "required": ["title", "url"],
                "additionalProperties": False,
            },
        },
        "image_prompt": {"type": "string"},
        "image_alt": {"type": "string"},
    },
    "required": ["subject", "preheader", "title", "intro", "sections", "key_takeaways",
                 "sources", "image_prompt", "image_alt"],
    "additionalProperties": False,
}

SYSTEM = """You are the editor of "{name}", an email newsletter. You write clear, engaging,
skimmable prose for {audience}. Tone: {tone}. Use only facts from the research briefing;
never invent statistics. Keep the whole issue a 4-6 minute read."""

PROMPT = """Write this week's issue from the research briefing below.

Requirements:
- 3-4 sections, each with a sharp heading and a markdown body (short paragraphs, bold the key numbers, bullets where useful).
- 3-5 key takeaways, one sentence each.
- sources: only URLs from the briefing's source list that support what you wrote.
- image_prompt: a detailed prompt for an AI image model to draw ONE hero infographic for this issue.
  Specify: a 16:9 landscape layout, the title text, 3-5 headline stats with their EXACT numbers and short labels
  (taken from the briefing), simple icons for each stat, a clean flat modern style, a cohesive 2-3 colour palette,
  generous whitespace, and large, legible, correctly spelled text. Keep all on-image text short.
- image_alt: one-sentence alt text describing the infographic.

<briefing>
{briefing}
</briefing>

<sources>
{sources}
</sources>"""


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--issue", required=True, help="issue slug (folder in .tmp/)")
    p.add_argument("--tone", default="confident, warm and plain-spoken; no hype or jargon")
    args = p.parse_args()

    out_dir = issue_dir(args.issue)
    research = read_json(out_dir / "research.json")

    system = SYSTEM.format(
        name=env("NEWSLETTER_NAME", "The Briefing", required=False),
        audience=research.get("audience", "curious professionals"),
        tone=args.tone,
    )
    prompt = PROMPT.format(
        briefing=research["briefing"],
        sources="\n".join(f"- {s['title']}: {s['url']}" for s in research["sources"]),
    )

    print("Writing newsletter...")
    for attempt in (1, 2):
        response = run(
            system=system,
            messages=[{"role": "user", "content": prompt}],
            output_config={"effort": "high", "format": {"type": "json_schema", "schema": SCHEMA}},
            max_tokens=24000,
        )
        text = next((b.text for b in response.content if b.type == "text"), "")
        try:
            content = json.loads(text)
            break
        except json.JSONDecodeError:
            if attempt == 2:
                sys.exit("Claude returned invalid JSON twice - rerun this step")
            print("Invalid JSON, retrying once...")

    content["topic"] = research["topic"]
    write_json(out_dir / "content.json", content)
    print(f"Saved {out_dir / 'content.json'}")
    print(f"Subject: {content['subject']}")


if __name__ == "__main__":
    main()
