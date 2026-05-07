#!/usr/bin/env python3
"""
Rewrite `file.cpp:NNN` style references in vault notes to GitHub permalinks
pinned at a given commit SHA.

The visible link text is identical to the original backtick string, so notes
remain readable when GitHub is unreachable.

Idempotent: skips any reference that's already wrapped in `[..](..)`.

Usage:
    permalink_rewrite.py \\
        --sha <commit-sha> \\
        --repo <owner/repo> \\
        --repo-root <local/clone> \\
        [--paths-json <override.json>] \\
        [--dry-run] \\
        <markdown-file> [<markdown-file>...]

Example:
    cd /path/to/your/repo && SHA=$(git rev-parse origin/main)
    permalink_rewrite.py \\
        --sha "$SHA" \\
        --repo <owner>/<repo> \\
        --repo-root /path/to/your/repo \\
        ~/obsidian/myvault/llmzone/work/10_projects/MyFeature_Apr26/algorithms/MyNote.md

The basename->repo-relative-path map is derived from `git ls-files` in
--repo-root, so it never goes stale as files are moved/renamed. Ambiguous
basenames (two files with the same name in different directories) are
skipped; in those cases, write the reference with a path prefix in the
note (e.g. `src/.../Utils.cpp:42`) and the script will resolve it directly.

--paths-json is optional: if provided, its entries override the auto-derived
map for the listed basenames. Useful for ambiguous-basename overrides or
when you want to point at a path that's outside `git ls-files` output.
"""
import argparse
import json
import os
import re
import subprocess
import sys


PATTERN = re.compile(
    r"`([A-Za-z0-9_/.]+\.(?:cpp|h|cu|cuh|py|ts|tsx|js|rs|go)):"
    r"(\d+(?:\s*[–-]\s*\d+)?(?:\s*,\s*\d+(?:\s*[–-]\s*\d+)?)*)`"
)

# File extensions to include when building the auto-derived basename map.
INDEXED_EXTENSIONS = ("*.cpp", "*.h", "*.cu", "*.cuh", "*.py", "*.ts",
                      "*.tsx", "*.js", "*.rs", "*.go")


def line_anchor(spec: str) -> str:
    """'489' -> '#L489'; '489–498' -> '#L489-L498'.
    For multi-range specs, link to the first range only."""
    first = spec.split(",")[0].strip()
    parts = re.split(r"[–-]", first)
    parts = [p.strip() for p in parts]
    if len(parts) == 1:
        return f"#L{parts[0]}"
    return f"#L{parts[0]}-L{parts[1]}"


def already_linked(text: str, span: tuple) -> bool:
    start, end = span
    return start > 0 and text[start - 1] == "[" and text[end : end + 2] == "]("


def build_basename_map_from_repo(repo_root: str) -> dict:
    """Run `git ls-files` and produce {basename: repo-relative-path}.
    Excludes basenames that map to multiple paths."""
    cmd = ["git", "-C", repo_root, "ls-files"] + list(INDEXED_EXTENSIONS)
    out = subprocess.check_output(cmd, text=True)
    paths = [p for p in out.splitlines() if p]
    by_base: dict = {}
    ambiguous = set()
    for p in paths:
        base = os.path.basename(p)
        if base in ambiguous:
            continue
        if base in by_base and by_base[base] != p:
            ambiguous.add(base)
            del by_base[base]
            continue
        by_base[base] = p
    return by_base


def make_rewriter(base_url: str, basename_map: dict):
    def rewrite(m: re.Match) -> str:
        full = m.group(0)
        path_or_basename = m.group(1)
        line_spec = m.group(2)
        if "/" in path_or_basename:
            rel_path = path_or_basename
        else:
            rel_path = basename_map.get(path_or_basename)
            if rel_path is None:
                return full
        url = f"{base_url}/{rel_path}{line_anchor(line_spec)}"
        return f"[{full}]({url})"
    return rewrite


def rewrite_text(text: str, base_url: str, basename_map: dict) -> str:
    rewriter = make_rewriter(base_url, basename_map)
    out = []
    i = 0
    for m in PATTERN.finditer(text):
        if already_linked(text, m.span()):
            continue
        out.append(text[i : m.start()])
        out.append(rewriter(m))
        i = m.end()
    out.append(text[i:])
    return "".join(out)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--sha", required=True, help="Commit SHA to pin links to")
    parser.add_argument("--repo", required=True, help="GitHub repo as owner/name")
    parser.add_argument("--repo-root", required=True,
                        help="Local clone of the repo, used to derive the basename map")
    parser.add_argument("--paths-json",
                        help="Optional JSON override map; entries take precedence over auto-derived")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print proposed changes; do not write")
    parser.add_argument("files", nargs="+", help="Markdown files to rewrite")
    args = parser.parse_args()

    base_url = f"https://github.com/{args.repo}/blob/{args.sha}"
    basename_map = build_basename_map_from_repo(args.repo_root)
    if args.paths_json:
        with open(args.paths_json) as f:
            override = json.load(f)
        basename_map.update(override)

    changed = 0
    for path in args.files:
        with open(path) as f:
            original = f.read()
        new = rewrite_text(original, base_url, basename_map)
        if new == original:
            print(f"unchanged {path}")
            continue
        changed += 1
        if args.dry_run:
            print(f"would update {path}")
        else:
            with open(path, "w") as f:
                f.write(new)
            print(f"updated {path}")
    suffix = " (dry run)" if args.dry_run else ""
    print(f"total: {changed} file(s){suffix}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
