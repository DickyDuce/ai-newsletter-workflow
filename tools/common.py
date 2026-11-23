"""Shared helpers: env loading, issue directories, JSON I/O."""
import json
import os
import re
import sys
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
TMP = ROOT / ".tmp"

load_dotenv(ROOT / ".env")


def env(name, default=None, required=True):
    value = os.getenv(name, default)
    if required and not value:
        sys.exit(f"Missing {name} in .env")
    return value


def slugify(text):
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:50].strip("-")
    return f"{date.today():%Y-%m-%d}-{slug}"


def issue_dir(slug, create=False):
    path = TMP / slug
    if create:
        path.mkdir(parents=True, exist_ok=True)
    elif not path.is_dir():
        sys.exit(f"Issue folder not found: {path}")
    return path


def read_json(path):
    path = Path(path)
    if not path.exists():
        sys.exit(f"Missing {path.name} - run the previous step first")
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path, data):
    Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
