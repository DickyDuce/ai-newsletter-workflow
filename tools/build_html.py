"""Render content.json into an email-safe HTML newsletter.

Usage: py tools/build_html.py --issue <slug>
Output: .tmp/<slug>/newsletter.html (image as cid:hero, for Gmail)
        .tmp/<slug>/preview.html    (image as local file, open in a browser)
"""
import argparse
import re
from datetime import date
from pathlib import Path

import markdown
from jinja2 import Environment, FileSystemLoader, select_autoescape

from common import env, issue_dir, read_json

TEMPLATES = Path(__file__).parent / "templates"

# Inline styles for tags produced by markdown, since email clients ignore <style> blocks.
INLINE = {
    "p": "margin:0 0 16px;font-size:16px;line-height:1.6;color:#1f2933;",
    "ul": "margin:0 0 16px;padding-left:22px;",
    "ol": "margin:0 0 16px;padding-left:22px;",
    "li": "margin:0 0 8px;font-size:16px;line-height:1.6;color:#1f2933;",
    "a": "color:#2563eb;text-decoration:underline;",
    "strong": "color:#0f172a;",
    "blockquote": "margin:0 0 16px;padding:8px 16px;border-left:4px solid #2563eb;color:#475569;",
}


def md(text):
    html = markdown.markdown(text or "", extensions=["sane_lists"])
    for tag, style in INLINE.items():
        html = re.sub(rf"<{tag}(?=[\s>])", f'<{tag} style="{style}"', html)
    return html


def render(content, image_src, has_image):
    jinja = Environment(loader=FileSystemLoader(TEMPLATES), autoescape=select_autoescape(["html"]))
    jinja.filters["md"] = md
    return jinja.get_template("newsletter.html").render(
        c=content,
        name=env("NEWSLETTER_NAME", "The Briefing", required=False),
        issue_date=date.today().strftime("%B %d, %Y").replace(" 0", " "),
        image_src=image_src,
        has_image=has_image,
    )


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--issue", required=True)
    args = p.parse_args()

    out_dir = issue_dir(args.issue)
    content = read_json(out_dir / "content.json")
    has_image = (out_dir / "hero.png").exists()
    if not has_image:
        print("No hero.png found - building without the infographic")

    (out_dir / "newsletter.html").write_text(render(content, "cid:hero", has_image), encoding="utf-8")
    (out_dir / "preview.html").write_text(render(content, "hero.png", has_image), encoding="utf-8")
    print(f"Saved {out_dir / 'newsletter.html'}")
    print(f"Preview in browser: {out_dir / 'preview.html'}")


if __name__ == "__main__":
    main()
