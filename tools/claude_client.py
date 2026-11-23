"""Thin wrapper around the Anthropic SDK shared by the research and writing tools."""
import sys

import anthropic

from common import env

FALLBACK_BETA = "server-side-fallback-2026-07-01"


def client():
    return anthropic.Anthropic(api_key=env("ANTHROPIC_API_KEY"))


def model():
    return env("ANTHROPIC_MODEL", "claude-opus-5-5", required=False)


def run(messages, system=None, tools=None, output_config=None, max_tokens=32000, max_continuations=5):
    """Stream a request to completion, resuming server-tool `pause_turn` stops.

    Uses server-side refusal fallbacks (`fallbacks: "default"`) so a safety
    decline is retried on Anthropic's recommended fallback model.
    """
    c = client()
    kwargs = {
        "model": model(),
        "max_tokens": max_tokens,
        "betas": [FALLBACK_BETA],
        "fallbacks": "default",
    }
    if system:
        kwargs["system"] = system
    if tools:
        kwargs["tools"] = tools
    if output_config:
        kwargs["output_config"] = output_config

    messages = list(messages)
    for _ in range(max_continuations + 1):
        try:
            with c.beta.messages.stream(messages=messages, **kwargs) as stream:
                response = stream.get_final_message()
        except anthropic.AuthenticationError:
            sys.exit("Anthropic API key rejected - check ANTHROPIC_API_KEY in .env")
        except anthropic.RateLimitError:
            sys.exit("Anthropic rate limit hit - wait a minute and rerun this step")
        except anthropic.APIStatusError as e:
            sys.exit(f"Anthropic API error {e.status_code}: {e.message}")
        except anthropic.APIConnectionError:
            sys.exit("Could not reach the Anthropic API - check your connection")

        if response.stop_reason == "refusal":
            sys.exit(f"Claude declined the request: {response.stop_details}")
        if response.stop_reason == "pause_turn":
            # Server-side tool loop paused; send the partial turn back to continue.
            messages = messages[:1] + [{"role": "assistant", "content": response.content}]
            continue
        if response.stop_reason == "max_tokens":
            sys.exit("Response hit max_tokens - raise max_tokens or narrow the topic")
        return response
    sys.exit("Too many pause_turn continuations - try a narrower topic")
