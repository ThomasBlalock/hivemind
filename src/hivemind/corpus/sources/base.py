"""Shared types + a tiny GitHub Contents API client used by adapters.

We use plain ``urllib`` rather than the ``gh`` CLI for two reasons:

1. ``gh`` isn't guaranteed to be on every dev machine.
2. Tests need to mock the network without touching subprocess.

Unauthenticated rate limits are 60/hr per IP, which is fine for our scale
(50–100 fetches per ``corpus pull``).
"""

from __future__ import annotations

import base64
import json
import logging
from dataclasses import dataclass, field
from typing import Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

log = logging.getLogger(__name__)

GITHUB_API = "https://api.github.com"
USER_AGENT = "hivemind-corpus-puller/0.1"


@dataclass
class NormalizedSkill:
    """A skill ready to be written to disk as a markdown file with frontmatter.

    ``id`` is the per-source slug; the writer prefixes it with the source name
    so the same skill name from two sources doesn't clobber.
    """

    id: str
    title: str
    description: str
    triggers: list[str]
    body: str
    source: str  # "<owner>/<repo>@<sha>"
    extra: dict[str, str] = field(default_factory=dict)


class SourceAdapter(Protocol):
    name: str  # registered key, e.g. "anthropic_skills"

    def pull(self, limit: int | None = None) -> list[NormalizedSkill]:
        """Fetch and normalize. ``limit`` caps the number of skills (for tests
        + bandwidth control)."""
        ...


# --- HTTP helper ----------------------------------------------------------


def fetch_json(url: str, *, timeout: float = 15.0) -> object:
    """GET ``url`` and return parsed JSON. Raises on HTTP error."""
    req = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/vnd.github+json"})
    try:
        with urlopen(req, timeout=timeout) as resp:  # noqa: S310 — trusted GitHub host only
            return json.loads(resp.read().decode("utf-8"))
    except HTTPError as e:
        raise RuntimeError(f"GitHub API error {e.code} fetching {url}: {e.reason}") from e
    except URLError as e:
        raise RuntimeError(f"Network error fetching {url}: {e.reason}") from e


def gh_contents(owner: str, repo: str, path: str, ref: str | None = None) -> list[dict] | dict:
    """Wrap ``GET /repos/{owner}/{repo}/contents/{path}`` with optional ref."""
    url = f"{GITHUB_API}/repos/{owner}/{repo}/contents/{path}"
    if ref:
        url += f"?ref={ref}"
    out = fetch_json(url)
    return out  # may be dict (single file) or list (directory)


def gh_file_text(owner: str, repo: str, path: str, ref: str | None = None) -> str:
    """Fetch a file and decode its base64-encoded content."""
    item = gh_contents(owner, repo, path, ref=ref)
    if not isinstance(item, dict) or "content" not in item:
        raise RuntimeError(f"expected file at {owner}/{repo}/{path}, got: {type(item).__name__}")
    encoded = item["content"].replace("\n", "")
    return base64.b64decode(encoded).decode("utf-8")


# --- frontmatter helpers --------------------------------------------------


def parse_frontmatter(text: str) -> tuple[dict, str]:
    """Parse YAML frontmatter. Returns ``(metadata, body)``.

    If the file has no ``---`` block, ``metadata`` is empty and the whole text
    is treated as the body. We import yaml lazily so the base module stays
    cheap to import.
    """
    if not text.startswith("---"):
        return {}, text.strip()
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text.strip()
    import yaml

    try:
        meta = yaml.safe_load(parts[1]) or {}
    except yaml.YAMLError:
        meta = {}
    body = parts[2].strip()
    return (meta if isinstance(meta, dict) else {}), body


def slugify(name: str) -> str:
    """Make a filesystem-safe slug from a human title."""
    out: list[str] = []
    for ch in name.lower():
        if ch.isalnum():
            out.append(ch)
        elif ch in " _-/":
            out.append("-")
    s = "".join(out).strip("-")
    while "--" in s:
        s = s.replace("--", "-")
    return s or "skill"
