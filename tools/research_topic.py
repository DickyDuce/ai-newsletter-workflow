"""Research a newsletter topic with Claude + web search.

Usage: py tools/research_topic.py --topic "AI in healthcare" [--audience "..."] [--slug existing-slug]
Output: .tmp/<slug>/research.json
"""
import argparse
from datetime import date

from claude_client import run
from common import issue_dir, slugify, write_json

SYSTEM = """You are a meticulous research analyst preparing a briefing for a newsletter writer.
Search the web for the most recent, authoritative information on the topic. Prefer primary
sources, reputable outlets, official reports and data. Today's date is {today}."""

PROMPT = """Research this newsletter topic: {topic}
Target audience: {audience}

Produce a research briefing with:
1. A 3-4 sentence overview of where things stand right now.
2. 8-15 key findings: concrete facts, statistics (with exact numbers and dates), recent developments, and notable quotes.
3. 2-3 angles or tensions that would make the newsletter interesting.
4. 3-5 headline numbers that would work well in an infographic, each with a short label.

Cite your sources. Flag anything uncertain or disputed."""


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--topic", required=True)
    p.add_argument("--audience", default="curious professionals who want a smart, fast briefing")
    p.add_argument("--slug", help="reuse an existing issue folder")
    args = p.parse_args()

    slug = args.slug or slugify(args.topic)
    out_dir = issue_dir(slug, create=True)

    print(f"Researching '{args.topic}'...")
    response = run(
        system=SYSTEM.format(today=date.today().isoformat()),
        messages=[{"role": "user", "content": PROMPT.format(topic=args.topic, audience=args.audience)}],
        tools=[{"type": "web_search_20260209", "name": "web_search", "max_uses": 8}],
    )

    briefing, sources = [], {}
    for block in response.content:
        if block.type == "text":
            briefing.append(block.text)
            for c in getattr(block, "citations", None) or []:
                url = getattr(c, "url", None)
                if url and url not in sources:
                    sources[url] = {"url": url, "title": getattr(c, "title", "") or url}
        elif block.type == "web_search_tool_result" and isinstance(block.content, list):
            for r in block.content:
                if getattr(r, "url", None) and r.url not in sources:
                    sources[r.url] = {"url": r.url, "title": r.title, "cited": False}

    # Sources that were actually cited come first.
    ordered = sorted(sources.values(), key=lambda s: s.get("cited", True) is False)
    for s in ordered:
        s.pop("cited", None)

    write_json(out_dir / "research.json", {
        "topic": args.topic,
        "audience": args.audience,
        "date": date.today().isoformat(),
        "briefing": "".join(briefing).strip(),
        "sources": ordered,
    })
    print(f"Saved {out_dir / 'research.json'} ({len(ordered)} sources)")
    print(f"ISSUE_SLUG={slug}")


if __name__ == "__main__":
    main()
