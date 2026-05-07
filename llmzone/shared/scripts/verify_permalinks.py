#!/usr/bin/env python3
"""
Coarse-grained staleness check for GitHub permalinks in vault notes.

Walks one or more markdown files (or directories), parses each
`https://github.com/<owner>/<repo>/blob/<sha>/<path>#L<a>[-L<b>]` link, and
reports failure modes against a local clone:

  - PATH-MOVED-OR-DELETED: the linked path no longer exists at master.
  - LINES-OUT-OF-RANGE: the path exists at master but the line range now
    falls outside the file's current length.
  - SYMBOL-MISSING: the closest backticked identifier near the link no
    longer appears anywhere in the file at master.
  - SYMBOL-DRIFTED: the identifier is in the file at master but outside
    the linked line range.

Symbol checks help detect renames and drifts that PATH/LINES wouldn't see;
they're best-effort, not authoritative.

Usage:
    verify_permalinks.py \\
        --repo <owner/repo> \\
        --repo-root <local/clone> \\
        [--ref master] \\
        [--no-symbol-check] \\
        <markdown-file-or-dir> [<markdown-file-or-dir>...]

Directories are walked recursively for `.md` files.
"""
import argparse
import os
import re
import subprocess
import sys
from collections import defaultdict


PERMALINK_RE = re.compile(
    r"\[([^\]]+)\]\(https://github\.com/([^/]+)/([^/]+)/blob/"
    r"([0-9a-f]{7,40})/([^#)\s]+)(#L\d+(?:-L\d+)?)?\)"
)

IDENT_IN_BACKTICKS_RE = re.compile(
    r"`([A-Za-z_][A-Za-z0-9_]{4,}(?:::[A-Za-z_][A-Za-z0-9_]+)*)(?:\([^`]*\))?`"
)

MIN_SYMBOL_LEN = 5


def parse_lines(anchor):
    if not anchor:
        return None, None
    m = re.match(r"#L(\d+)(?:-L(\d+))?", anchor)
    if not m:
        return None, None
    start = int(m.group(1))
    end = int(m.group(2)) if m.group(2) else start
    return start, end


def git_path_exists_at(repo_root, ref, path):
    try:
        subprocess.check_output(
            ["git", "-C", repo_root, "cat-file", "-e", f"{ref}:{path}"],
            stderr=subprocess.DEVNULL,
        )
        return True
    except subprocess.CalledProcessError:
        return False


_content_cache: dict = {}


def git_file_content(repo_root, ref, path):
    key = (repo_root, ref, path)
    if key in _content_cache:
        return _content_cache[key]
    try:
        out = subprocess.check_output(
            ["git", "-C", repo_root, "show", f"{ref}:{path}"],
            text=True, stderr=subprocess.DEVNULL,
        )
    except subprocess.CalledProcessError:
        out = None
    _content_cache[key] = out
    return out


def line_count_of(content):
    if content is None:
        return 0
    return content.count("\n") + (0 if content.endswith("\n") else 1)


def find_symbol_near(text, link_start, link_end):
    """Return the closest backticked identifier on the same line as the link.
    Allows function-call notation `Name(...)` and namespaced `Foo::Bar`."""
    line_start = text.rfind("\n", 0, link_start) + 1
    nl = text.find("\n", link_end)
    line_end = nl if nl != -1 else len(text)

    candidates = []
    for m in IDENT_IN_BACKTICKS_RE.finditer(text, line_start, line_end):
        if m.start() >= link_start and m.end() <= link_end:
            continue  # don't pick the visible-text span inside the link itself
        if m.end() <= link_start:
            distance = link_start - m.end()
        elif m.start() >= link_end:
            distance = m.start() - link_end
        else:
            continue  # overlaps the link — shouldn't happen
        candidates.append((distance, m.group(1)))

    if not candidates:
        return None
    candidates.sort(key=lambda x: x[0])
    return candidates[0][1]


def _word_boundary_search(content, symbol):
    if "::" in symbol:
        pattern = re.compile(
            r"(?<![A-Za-z0-9_:])" + re.escape(symbol) + r"(?![A-Za-z0-9_:])"
        )
    else:
        pattern = re.compile(r"\b" + re.escape(symbol) + r"\b")
    return [i + 1 for i, line in enumerate(content.splitlines())
            if pattern.search(line)]


def find_symbol_lines(content, symbol):
    """Return list of 1-indexed line numbers where `symbol` appears.
    For `Foo::Bar` symbols, fall back to just `Bar` if the qualified form
    isn't found — class-inline methods in C++ usually only appear with the
    qualified prefix at call sites, not at the definition."""
    if not content or not symbol:
        return []
    found = _word_boundary_search(content, symbol)
    if found:
        return found
    if "::" in symbol:
        last = symbol.rsplit("::", 1)[-1]
        if len(last) >= MIN_SYMBOL_LEN:
            return _word_boundary_search(content, last)
    return []


def collect_files(targets):
    out = []
    for t in targets:
        if os.path.isdir(t):
            for root, _, files in os.walk(t):
                for f in files:
                    if f.endswith(".md"):
                        out.append(os.path.join(root, f))
        else:
            out.append(t)
    return sorted(set(out))


def check_one(text, link_match, args, expected_owner, expected_name):
    """Return (status, detail) or None when there's no issue."""
    owner, name = link_match.group(2), link_match.group(3)
    ref_path = link_match.group(5)
    anchor = link_match.group(6)

    if (owner, name) != (expected_owner, expected_name):
        return "OTHER-REPO", None

    if not git_path_exists_at(args.repo_root, args.ref, ref_path):
        return "PATH-MOVED-OR-DELETED", None

    content = git_file_content(args.repo_root, args.ref, ref_path)
    length = line_count_of(content)
    start, end = parse_lines(anchor)

    if start is not None:
        hi = end if end is not None else start
        if hi > length:
            return ("LINES-OUT-OF-RANGE",
                    f"linked lines {start}-{hi}, file is {length} lines at {args.ref}")

    if args.no_symbol_check:
        return None

    symbol = find_symbol_near(text, link_match.start(), link_match.end())
    if not symbol or len(symbol) < MIN_SYMBOL_LEN:
        return None

    found_lines = find_symbol_lines(content, symbol)
    if not found_lines:
        return "SYMBOL-MISSING", f"`{symbol}` not found in file at {args.ref}"

    if start is not None:
        hi = end if end is not None else start
        in_range = any(start <= ln <= hi for ln in found_lines)
        if not in_range:
            sample = ", ".join(str(ln) for ln in found_lines[:5])
            more = "" if len(found_lines) <= 5 else f" (+{len(found_lines) - 5} more)"
            return ("SYMBOL-DRIFTED",
                    f"`{symbol}` now at line(s) {sample}{more}, linked range was {start}-{hi}")

    return None


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repo", required=True, help="Expected GitHub repo as owner/name")
    parser.add_argument("--repo-root", required=True, help="Local clone of the repo")
    parser.add_argument("--ref", default="master",
                        help="Git ref to verify against (default: master)")
    parser.add_argument("--no-symbol-check", action="store_true",
                        help="Skip the symbol-tracking check; only verify path and line range")
    parser.add_argument("targets", nargs="+",
                        help="Markdown files or directories to scan")
    args = parser.parse_args()

    expected_owner, expected_name = args.repo.split("/", 1)
    files = collect_files(args.targets)

    issues_by_file: dict = defaultdict(list)
    total_links = 0
    other_repo_links = 0

    for path in files:
        with open(path) as f:
            text = f.read()
        for m in PERMALINK_RE.finditer(text):
            result = check_one(text, m, args, expected_owner, expected_name)
            if result is None:
                total_links += 1
                continue
            status, detail = result
            if status == "OTHER-REPO":
                other_repo_links += 1
                continue
            total_links += 1
            line_no = text.count("\n", 0, m.start()) + 1
            issues_by_file[path].append(
                (line_no, status, m.group(1), m.group(5), m.group(4), detail)
            )

    if not issues_by_file:
        print(f"all {total_links} permalink(s) verified OK against {args.ref}")
        if other_repo_links:
            print(f"({other_repo_links} link(s) to other repos skipped)")
        return 0

    total_issues = 0
    for path in sorted(issues_by_file):
        items = issues_by_file[path]
        total_issues += len(items)
        print(f"\n{path}")
        for line_no, status, visible, ref_path, sha, detail in items:
            print(f"  L{line_no}  {status}  {visible}")
            print(f"           path: {ref_path}")
            print(f"           pinned sha: {sha[:10]}")
            if detail:
                print(f"           {detail}")

    print(f"\ntotal: {total_issues} issue(s) across {len(issues_by_file)} file(s) "
          f"of {total_links} permalink(s) checked")
    if other_repo_links:
        print(f"({other_repo_links} link(s) to other repos skipped)")
    return 1


if __name__ == "__main__":
    sys.exit(main())
