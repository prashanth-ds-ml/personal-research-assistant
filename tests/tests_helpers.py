"""Shared fakes for the fetcher tests (no network, no models)."""

import json

import httpx

from research_assistant import fetcher as f

PUBLIC_IP = "93.184.216.34"


class Clock:
    """Fake clock: sleeping advances time, so throttling is testable without waiting."""

    def __init__(self):
        self.t = 1000.0
        self.slept: list[float] = []

    def now(self):
        return self.t

    def sleep(self, s):
        self.slept.append(s)
        self.t += s


def fake_resolve(host):
    return [host if host[0].isdigit() else PUBLIC_IP]


def make_fetcher(handler, clock=None):
    clock = clock or Clock()
    http = httpx.Client(transport=httpx.MockTransport(handler))
    return f.Fetcher(http=http, contact="me@example.com", sleep=clock.sleep, now=clock.now, resolve=fake_resolve), clock


def ok_llm(prompt, json_mode=False):
    if "keyword search query" in prompt:
        return json.dumps({"query": "hybrid retrieval"})
    if "How useful is this source" in prompt:
        return json.dumps({"score": 3})
    return "{}"


def fake_pdf_to_md(pdf_bytes, name):
    return f"# Converted {name}\n\n" + "Hybrid retrieval improves recall on real corpora. " * 40
