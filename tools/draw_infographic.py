"""Draw the hero infographic from the stats in content.json (free, no API).

Usage: py tools/draw_infographic.py --issue <slug>
Reads:  content.json -> "infographic": {"title", "subtitle", "stats": [{"value", "label"}], "source"}
Output: .tmp/<slug>/hero.png (1600x900)
"""
import argparse
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from common import env, issue_dir, read_json

W, H = 1600, 900
MARGIN = 80
BG = "#f8fafc"
INK = "#0f172a"
MUTED = "#64748b"
CARD = "#ffffff"
BORDER = "#e2e8f0"
ACCENTS = ["#2563eb", "#0d9488", "#7c3aed", "#ea580c", "#db2777"]

FONT_DIRS = [Path("C:/Windows/Fonts"), Path("/usr/share/fonts/truetype/dejavu"), Path("/Library/Fonts")]
REGULAR = ["segoeui.ttf", "arial.ttf", "DejaVuSans.ttf", "Arial.ttf"]
BOLD = ["segoeuib.ttf", "arialbd.ttf", "DejaVuSans-Bold.ttf", "Arial Bold.ttf"]


def font(size, bold=False):
    for d in FONT_DIRS:
        for name in BOLD if bold else REGULAR:
            if (d / name).exists():
                return ImageFont.truetype(str(d / name), size)
    return ImageFont.load_default(size)


def wrap(draw, text, fnt, max_width):
    lines, line = [], ""
    for word in text.split():
        test = f"{line} {word}".strip()
        if draw.textlength(test, font=fnt) <= max_width:
            line = test
        else:
            if line:
                lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines


def fit(draw, text, max_width, start, minimum, bold=True):
    """Largest font size (down to `minimum`) at which `text` fits on one line."""
    size = start
    while size > minimum and draw.textlength(text, font=font(size, bold)) > max_width:
        size -= 4
    return font(size, bold)


def draw_text_block(draw, xy, lines, fnt, fill, spacing=1.25):
    x, y = xy
    step = int(fnt.size * spacing)
    for line in lines:
        draw.text((x, y), line, font=fnt, fill=fill)
        y += step
    return y


def render(spec, brand):
    stats = spec.get("stats", [])[:5]
    if len(stats) < 2:
        sys.exit("infographic.stats needs at least 2 entries")

    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)

    # Brand strip + title
    d.rectangle([0, 0, W, 12], fill=ACCENTS[0])
    d.text((MARGIN, 52), brand.upper(), font=font(24, bold=True), fill=ACCENTS[0])
    title_font = font(60, bold=True)
    title_lines = wrap(d, spec["title"], title_font, W - 2 * MARGIN)[:2]
    y = draw_text_block(d, (MARGIN, 92), title_lines, title_font, INK, spacing=1.15)
    if spec.get("subtitle"):
        sub_font = font(30)
        y = draw_text_block(d, (MARGIN, y + 6), wrap(d, spec["subtitle"], sub_font, W - 2 * MARGIN)[:2], sub_font, MUTED)

    # Stat cards in one row, sized to their content and centred in the space left
    gap, pad = 28, 36
    n = len(stats)
    card_w = (W - 2 * MARGIN - gap * (n - 1)) // n
    inner = card_w - 2 * pad
    label_font = font(28 if n <= 3 else 24)
    label_step = int(label_font.size * 1.3)

    # One value size for every card: the largest at which all values fit.
    value_font = min((fit(d, str(s["value"]), inner, 120 if n <= 3 else 96, 36) for s in stats), key=lambda f: f.size)
    value_h = max(d.textbbox((0, 0), str(s["value"]), font=value_font)[3] for s in stats)
    labels = [wrap(d, s["label"], label_font, inner)[:4] for s in stats]
    rule_gap = 28
    card_h = 14 + pad + value_h + rule_gap * 2 + max(len(l) for l in labels) * label_step + pad

    area_top, area_bottom = max(y + 40, 280), H - 110
    top = area_top + max(0, (area_bottom - area_top - card_h) // 2)
    bottom = top + card_h

    for i, (stat, label_lines) in enumerate(zip(stats, labels)):
        x0 = MARGIN + i * (card_w + gap)
        accent = ACCENTS[i % len(ACCENTS)]
        d.rounded_rectangle([x0, top, x0 + card_w, bottom], radius=20, fill=CARD, outline=BORDER, width=2)
        d.rounded_rectangle([x0, top, x0 + card_w, top + 14], radius=7, fill=accent)
        value_y = top + 14 + pad
        d.text((x0 + pad, value_y), str(stat["value"]), font=value_font, fill=accent)
        rule_y = value_y + value_h + rule_gap
        d.line([x0 + pad, rule_y, x0 + pad + 60, rule_y], fill=accent, width=4)
        draw_text_block(d, (x0 + pad, rule_y + rule_gap - 8), label_lines, label_font, INK, spacing=1.3)

    # Footer
    if spec.get("source"):
        foot_font = font(22)
        line = wrap(d, f"Source: {spec['source']}", foot_font, W - 2 * MARGIN)[0]
        d.text((MARGIN, H - 70), line, font=foot_font, fill=MUTED)
    return img


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--issue", required=True)
    args = p.parse_args()

    out_dir = issue_dir(args.issue)
    content = read_json(out_dir / "content.json")
    if "infographic" not in content:
        sys.exit('content.json has no "infographic" section')
    img = render(content["infographic"], env("NEWSLETTER_NAME", "The Briefing", required=False))
    img.save(out_dir / "hero.png", optimize=True)
    print(f"Saved {out_dir / 'hero.png'}")


if __name__ == "__main__":
    main()
