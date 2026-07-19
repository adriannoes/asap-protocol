#!/usr/bin/env python3
"""Collect public GitHub repository metrics and traffic (clones, referrers) via REST API.

**Stars** and **forks** are available without auth, but **traffic** endpoints require a
token with **push** access to the target repository (same as the Insights tab).

Weekly aggregation in CI should use ``TELEMETRY_GITHUB_TOKEN`` (fine-grained or classic PAT
with traffic scope). The legacy ``GITHUB_TOKEN`` env name is still accepted when
``scripts/telemetry/aggregate.py`` is run with ``--allow-github-skip`` only.

Uses ``GITHUB_TOKEN`` / ``TELEMETRY_GITHUB_TOKEN`` from the environment by default (never
print or log the token).

API: https://docs.github.com/en/rest
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

GITHUB_API_BASE = "https://api.github.com"
GITHUB_API_VERSION = "2022-11-28"
DEFAULT_OWNER = "asap-protocol"
DEFAULT_REPO = "asap-protocol"
DEFAULT_TOKEN_ENV = "GITHUB_TOKEN"
DEFAULT_ADAPTER_LABEL = "adapter-request"
REQUEST_TIMEOUT_SECONDS = 30.0

_FRAMEWORK_HEADING_RE = re.compile(
    r"(?mi)^###\s*Framework(?:\s+name)?\s*\n+\s*(.+)$",
)
_FRAMEWORK_LINE_RE = re.compile(r"(?mi)^\s*Framework\s*:\s*(.+)$")


def _github_headers(token: str) -> dict[str, str]:
    return {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": GITHUB_API_VERSION,
    }


def fetch_repo_summary(client: httpx.Client, owner: str, repo: str) -> dict[str, int]:
    """Return stargazers, forks, and related counts from ``GET /repos/{owner}/{repo}``."""
    response = client.get(f"/repos/{owner}/{repo}")
    response.raise_for_status()
    payload: object = response.json()
    if not isinstance(payload, dict):
        msg = "GitHub /repos response must be a JSON object"
        raise ValueError(msg)
    keys = (
        "stargazers_count",
        "forks_count",
        "open_issues_count",
        "watchers_count",
    )
    out: dict[str, int] = {}
    for key in keys:
        raw = payload.get(key)
        if not isinstance(raw, int):
            msg = f"GitHub /repos missing or invalid integer {key!r}"
            raise ValueError(msg)
        out[key] = raw
    return out


def fetch_traffic_clones(client: httpx.Client, owner: str, repo: str) -> dict[str, Any]:
    """Return clone totals and daily series from ``GET .../traffic/clones``."""
    response = client.get(f"/repos/{owner}/{repo}/traffic/clones")
    response.raise_for_status()
    payload: object = response.json()
    if not isinstance(payload, dict):
        msg = "GitHub /traffic/clones response must be a JSON object"
        raise ValueError(msg)
    count = payload.get("count")
    uniques = payload.get("uniques")
    clones = payload.get("clones")
    if not isinstance(count, int) or not isinstance(uniques, int):
        msg = "GitHub /traffic/clones missing count or uniques"
        raise ValueError(msg)
    if not isinstance(clones, list):
        msg = "GitHub /traffic/clones missing clones array"
        raise ValueError(msg)
    return {
        "count": count,
        "uniques": uniques,
        "clones": clones,
    }


def parse_framework_from_issue_body(body: str) -> str | None:
    """Extract a framework label from GitHub issue body text.

    Supports:

    - GitHub Issue Form export: ``### Framework name`` / ``### Framework`` blocks.
    - Free-form: a line ``Framework: My Framework``.

    Returns:
        The raw framework string, or ``None`` if not found.
    """
    if not body or not body.strip():
        return None
    match = _FRAMEWORK_HEADING_RE.search(body)
    if match:
        return match.group(1).strip()
    match = _FRAMEWORK_LINE_RE.search(body)
    if match:
        return match.group(1).strip()
    return None


def slug_framework_label(raw: str) -> str:
    """Normalize a framework name to a lowercase ``kebab-case`` key."""
    s = raw.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-") or "unknown"


def fetch_open_labeled_issues(
    client: httpx.Client,
    owner: str,
    repo: str,
    *,
    label: str,
) -> list[dict[str, Any]]:
    """List open issues with ``label`` (excludes pull requests)."""
    page = 1
    out: list[dict[str, Any]] = []
    while True:
        response = client.get(
            f"/repos/{owner}/{repo}/issues",
            params={
                "state": "open",
                "labels": label,
                "per_page": 100,
                "page": page,
            },
        )
        response.raise_for_status()
        payload: object = response.json()
        if not isinstance(payload, list):
            msg = "GitHub /issues response must be a JSON array"
            raise ValueError(msg)
        if not payload:
            break
        for item in payload:
            if not isinstance(item, dict):
                continue
            if "pull_request" in item:
                continue
            out.append(item)
        if len(payload) < 100:
            break
        page += 1
    return out


def summarize_adapter_requests(issues: list[dict[str, Any]]) -> dict[str, Any]:
    """Count open adapter-request issues by parsed framework name."""
    by_framework: dict[str, int] = defaultdict(int)
    unparsed = 0
    for issue in issues:
        body = issue.get("body")
        body_str = body if isinstance(body, str) else ""
        parsed = parse_framework_from_issue_body(body_str)
        if parsed is None:
            unparsed += 1
            continue
        key = slug_framework_label(parsed)
        by_framework[key] += 1
    result: dict[str, Any] = {
        "label": DEFAULT_ADAPTER_LABEL,
        "open_count": len(issues),
        "by_framework": dict(sorted(by_framework.items())),
    }
    if unparsed:
        result["unparsed_open_count"] = unparsed
    return result


def fetch_popular_referrers(client: httpx.Client, owner: str, repo: str) -> list[dict[str, Any]]:
    """Return top referrers from ``GET .../traffic/popular/referrers``."""
    response = client.get(f"/repos/{owner}/{repo}/traffic/popular/referrers")
    response.raise_for_status()
    payload: object = response.json()
    if not isinstance(payload, list):
        msg = "GitHub /traffic/popular/referrers must be a JSON array"
        raise ValueError(msg)
    out: list[dict[str, Any]] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        ref = item.get("referrer")
        views = item.get("views")
        uniq = item.get("uniques")
        if isinstance(ref, str) and isinstance(views, int) and isinstance(uniq, int):
            out.append({"referrer": ref, "views": views, "uniques": uniq})
    return out


def collect_github_signals(
    owner: str,
    repo: str,
    *,
    token: str,
    client: httpx.Client | None = None,
) -> dict[str, Any]:
    """Pull repo summary, traffic, popular referrers, and adapter-request breakdown."""
    collected_at = datetime.now(UTC).replace(microsecond=0).isoformat()
    slug = f"{owner}/{repo}"
    close_client = client is None
    http = client or httpx.Client(
        base_url=GITHUB_API_BASE,
        headers=_github_headers(token),
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    try:
        repo_summary = fetch_repo_summary(http, owner, repo)
        clone_stats = fetch_traffic_clones(http, owner, repo)
        referrers = fetch_popular_referrers(http, owner, repo)
        issues = fetch_open_labeled_issues(
            http,
            owner,
            repo,
            label=DEFAULT_ADAPTER_LABEL,
        )
        adapter_summary = summarize_adapter_requests(issues)
    finally:
        if close_client:
            http.close()
    return {
        "source": "github_rest_api",
        "repository": slug,
        "collected_at": collected_at,
        "repo": repo_summary,
        "traffic_clones": clone_stats,
        "traffic_referrers": referrers,
        "adapter_requests": adapter_summary,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Collect GitHub repo metrics and traffic (requires GITHUB_TOKEN with push)."
    )
    parser.add_argument(
        "--owner",
        default=DEFAULT_OWNER,
        help=f"Repository owner (default: {DEFAULT_OWNER})",
    )
    parser.add_argument(
        "--repo",
        default=DEFAULT_REPO,
        help=f"Repository name (default: {DEFAULT_REPO})",
    )
    parser.add_argument(
        "--token-env",
        default=DEFAULT_TOKEN_ENV,
        help=f"Environment variable holding a GitHub PAT (default: {DEFAULT_TOKEN_ENV})",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Write JSON to this path instead of stdout",
    )
    args = parser.parse_args(argv)
    token = os.environ.get(args.token_env, "").strip()
    if not token:
        print(
            f"Missing {args.token_env}: set a token with push access to "
            f"{args.owner}/{args.repo} (traffic endpoints require it).",
            file=sys.stderr,
        )
        return 1

    try:
        report = collect_github_signals(args.owner, args.repo, token=token)
    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code
        detail = ""
        try:
            body: object = exc.response.json()
            if isinstance(body, dict) and "message" in body:
                detail = str(body.get("message"))
        except (json.JSONDecodeError, ValueError):
            detail = exc.response.text[:500]
        print(
            f"GitHub API HTTP {status} for {exc.request.url!s}: {detail}",
            file=sys.stderr,
        )
        return 1
    except (httpx.HTTPError, ValueError) as exc:
        print(f"GitHub telemetry failed: {exc}", file=sys.stderr)
        return 1

    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
