"""Generate the hero infographic with Nano Banana via Kie.ai.

Usage: py tools/generate_infographic.py --issue <slug> [--aspect 16:9] [--prompt "override"]
Output: .tmp/<slug>/hero.png
"""
import argparse
import json
import sys
import time

import requests

from common import env, issue_dir, read_json

API = "https://api.kie.ai/api/v1/jobs"
POLL_SECONDS = 5
TIMEOUT_SECONDS = 600

ERRORS = {
    401: "Kie.ai rejected the API key - check KIE_API_KEY in .env",
    402: "Kie.ai account is out of credits - top up before rerunning",
    422: "Kie.ai rejected the request parameters",
    429: "Kie.ai rate limit hit - wait a minute and rerun",
}


def check(body):
    """Kie returns HTTP 200 on errors; the real status is in body['code']."""
    code = body.get("code")
    if code != 200:
        sys.exit(f"{ERRORS.get(code, f'Kie.ai error {code}')}: {body.get('msg')}")
    return body["data"]


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--issue", required=True)
    p.add_argument("--aspect", default="16:9")
    p.add_argument("--prompt", help="override the image_prompt from content.json")
    args = p.parse_args()

    out_dir = issue_dir(args.issue)
    prompt = args.prompt or read_json(out_dir / "content.json")["image_prompt"]
    headers = {"Authorization": f"Bearer {env('KIE_API_KEY')}", "Content-Type": "application/json"}

    payload = {
        "model": env("KIE_MODEL", "google/nano-banana", required=False),
        "input": {"prompt": prompt, "output_format": "png", "aspect_ratio": args.aspect},
    }
    resp = requests.post(f"{API}/createTask", headers=headers, json=payload, timeout=60)
    resp.raise_for_status()
    task_id = check(resp.json())["taskId"]
    print(f"Kie.ai task {task_id} created, waiting for image...")

    deadline = time.time() + TIMEOUT_SECONDS
    while time.time() < deadline:
        time.sleep(POLL_SECONDS)
        resp = requests.get(f"{API}/recordInfo", headers=headers, params={"taskId": task_id}, timeout=60)
        resp.raise_for_status()
        data = check(resp.json())
        state = data.get("state")
        if state == "success":
            urls = json.loads(data["resultJson"])["resultUrls"]
            break
        if state == "fail":
            sys.exit(f"Image generation failed ({data.get('failCode')}): {data.get('failMsg')}")
        print(f"  state: {state}")
    else:
        sys.exit(f"Timed out after {TIMEOUT_SECONDS}s waiting for task {task_id}")

    img = requests.get(urls[0], timeout=120)
    img.raise_for_status()
    (out_dir / "hero.png").write_bytes(img.content)
    print(f"Saved {out_dir / 'hero.png'} (credits used: {data.get('creditsConsumed')})")


if __name__ == "__main__":
    main()
