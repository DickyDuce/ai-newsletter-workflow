"""Check a hand- or agent-written content.json before building the email.

Usage: py tools/validate_content.py --issue <slug>
Exits non-zero and lists every problem found.
"""
import argparse
import sys

from common import issue_dir, read_json

REQUIRED = {"subject": str, "preheader": str, "title": str, "intro": str,
            "sections": list, "key_takeaways": list, "sources": list, "image_alt": str}


def problems(c):
    out = []
    for key, typ in REQUIRED.items():
        if not isinstance(c.get(key), typ) or not c.get(key):
            out.append(f"'{key}' missing or empty")
    if len(c.get("subject", "")) > 70:
        out.append("subject longer than 70 characters")
    for i, s in enumerate(c.get("sections") or []):
        if not s.get("heading") or not s.get("body_md"):
            out.append(f"sections[{i}] needs heading and body_md")
    for i, s in enumerate(c.get("sources") or []):
        if not str(s.get("url", "")).startswith("http"):
            out.append(f"sources[{i}] has no valid url")
    info = c.get("infographic")
    if info is not None:
        if not info.get("title"):
            out.append("infographic.title missing")
        stats = info.get("stats") or []
        if not 2 <= len(stats) <= 5:
            out.append("infographic.stats needs 2-5 entries")
        for i, st in enumerate(stats):
            if not st.get("value") or not st.get("label"):
                out.append(f"infographic.stats[{i}] needs value and label")
            elif len(str(st["value"])) > 12:
                out.append(f"infographic.stats[{i}].value too long (keep it under 12 chars)")
    return out


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--issue", required=True)
    args = p.parse_args()

    found = problems(read_json(issue_dir(args.issue) / "content.json"))
    if found:
        sys.exit("content.json problems:\n- " + "\n- ".join(found))
    print("content.json OK")


if __name__ == "__main__":
    main()
