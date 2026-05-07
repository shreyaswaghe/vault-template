"""Shared GitHub CLI helpers used by vault.py and index_rebuild.py.

All functions return None / empty list on failure (network, gh not installed,
auth missing) so callers can degrade gracefully.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess

# Default GitHub repo (owner/repo) used when no per-call --repo is given and a
# PR note's body doesn't embed a github.com/<owner>/<repo>/pull/<N> URL. Set
# via setup.sh, or override at runtime with --repo. When empty, gh is invoked
# without --repo, so it falls back to its own auto-detection from the cwd's
# git remote — which only works if you run the scripts from inside a checkout
# of your code repo.
DEFAULT_REPO = ""


def gh_available() -> bool:
    return shutil.which("gh") is not None


def gh_pr_view(num: int | str, repo: str | None = None) -> dict | None:
    """Fetch one PR. Returns parsed dict or None."""
    if not gh_available():
        return None
    cmd = [
        "gh", "pr", "view", str(num),
        "--json", "number,state,isDraft,mergedAt,closedAt,title,headRefName,url",
    ]
    if repo:
        cmd.extend(["--repo", repo])
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=30)
        return json.loads(result.stdout)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, json.JSONDecodeError):
        return None


def gh_pr_list(state: str = "all", author: str = "@me", repo: str | None = None, limit: int = 100) -> list[dict]:
    """List PRs. Returns list (possibly empty) of dicts."""
    if not gh_available():
        return []
    cmd = [
        "gh", "pr", "list",
        "--state", state,
        "--author", author,
        "--limit", str(limit),
        "--json", "number,title,state,mergedAt,headRefName,url,isDraft",
    ]
    if repo:
        cmd.extend(["--repo", repo])
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=30)
        return json.loads(result.stdout)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, json.JSONDecodeError):
        return []


def gh_state_to_status(gh_data: dict) -> str:
    """Map gh pr view JSON to our PR-note status enum (Proposed|Open|Merged|Closed)."""
    state = gh_data.get("state", "")
    if state == "MERGED":
        return "Merged"
    if state == "CLOSED":
        return "Closed"
    if state == "OPEN":
        return "Proposed" if gh_data.get("isDraft") else "Open"
    return ""


_REPO_URL_RE = re.compile(r"github\.com/([\w.-]+/[\w.-]+)/pull/\d+")


def extract_repo_from_text(text: str, default: str = DEFAULT_REPO) -> str:
    """Pull `owner/repo` out of a github.com pull URL in body text."""
    m = _REPO_URL_RE.search(text)
    if m:
        return m.group(1)
    return default


def title_to_kebab(title: str) -> str:
    """Convert a PR title to a kebab-case slug suitable for a filename component."""
    s = re.sub(r"[^\w\s-]", "", title).lower()
    s = re.sub(r"[\s_]+", "-", s).strip("-")
    return s or "untitled"
