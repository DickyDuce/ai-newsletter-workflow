"""Create a Gmail draft of the newsletter, or send an approved draft.

Usage:
  py tools/gmail_send.py --issue <slug> --draft     create a draft to NEWSLETTER_TO
  py tools/gmail_send.py --send <draft_id>          send an approved draft
  py tools/gmail_send.py --auth                     run the one-time OAuth consent only

First run opens a browser for Google consent and saves token.json.
"""
import argparse
import base64
import sys
from email.message import EmailMessage

from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from common import ROOT, env, issue_dir, read_json, write_json

SCOPES = ["https://www.googleapis.com/auth/gmail.compose"]
CREDENTIALS = ROOT / "credentials.json"
TOKEN = ROOT / "token.json"


def gmail():
    creds = Credentials.from_authorized_user_file(str(TOKEN), SCOPES) if TOKEN.exists() else None
    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
        except RefreshError:
            print("Saved Google token expired or was revoked - re-authorising")
            creds = None
    if not creds or not creds.valid:
        if not CREDENTIALS.exists():
            sys.exit("credentials.json not found - download the OAuth Desktop client from Google Cloud Console")
        creds = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS), SCOPES).run_local_server(port=0)
    TOKEN.write_text(creds.to_json(), encoding="utf-8")
    return build("gmail", "v1", credentials=creds)


def plain_text(c):
    parts = [c["title"], "", c["intro"], ""]
    for s in c["sections"]:
        parts += [s["heading"].upper(), s["body_md"], ""]
    parts += ["KEY TAKEAWAYS"] + [f"- {t}" for t in c["key_takeaways"]] + [""]
    parts += ["SOURCES"] + [f"- {s['title']}: {s['url']}" for s in c["sources"]]
    return "\n".join(parts)


def build_message(slug):
    out_dir = issue_dir(slug)
    content = read_json(out_dir / "content.json")
    html_path = out_dir / "newsletter.html"
    if not html_path.exists():
        sys.exit("Missing newsletter.html - run build_html.py first")

    msg = EmailMessage()  # Gmail fills in From with the authorised account
    msg["To"] = env("NEWSLETTER_TO")
    msg["Subject"] = content["subject"]
    msg.set_content(plain_text(content))
    msg.add_alternative(html_path.read_text(encoding="utf-8"), subtype="html")

    hero = out_dir / "hero.png"
    if hero.exists():
        # Attach inline to the HTML part so <img src="cid:hero"> resolves.
        msg.get_payload()[1].add_related(hero.read_bytes(), "image", "png", cid="<hero>", filename="hero.png")
    return msg, out_dir


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--issue")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--draft", action="store_true")
    g.add_argument("--send", metavar="DRAFT_ID")
    g.add_argument("--auth", action="store_true")
    args = p.parse_args()

    try:
        service = gmail()
        if args.auth:
            print(f"Authorised. Token saved to {TOKEN}")
        elif args.draft:
            if not args.issue:
                sys.exit("--draft needs --issue <slug>")
            msg, out_dir = build_message(args.issue)
            raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
            draft = service.users().drafts().create(userId="me", body={"message": {"raw": raw}}).execute()
            write_json(out_dir / "draft.json", {"draft_id": draft["id"], "to": msg["To"], "subject": msg["Subject"]})
            print(f"Draft created: {draft['id']} -> {msg['To']}")
            print("Review it in Gmail > Drafts, then send with:")
            print(f"  py tools/gmail_send.py --send {draft['id']}")
        else:
            sent = service.users().drafts().send(userId="me", body={"id": args.send}).execute()
            print(f"Sent. Message id: {sent['id']}")
    except HttpError as e:
        sys.exit(f"Gmail API error {e.resp.status}: {e.reason}")


if __name__ == "__main__":
    main()
