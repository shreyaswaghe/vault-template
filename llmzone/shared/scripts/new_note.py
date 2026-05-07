#!/usr/bin/env python3
"""Create a new vault note from its template.

Usage:
  new_note.py algorithm <feature> <AlgorithmName>
  new_note.py algorithm-step <feature> <ParentAlgorithmName> <StepN_StepName>
  new_note.py decision <feature> <kebab-topic>
  new_note.py pr <feature> <pr-number> <kebab-topic> [--branch <name>]
  new_note.py runbook <feature> [<RunbookName>]            # default: Build_and_Test_<feature>

The feature dir must already exist under work/10_projects/. The script:
  - finds the matching template
  - substitutes placeholders (date, feature, paths, names)
  - writes to the canonical path
  - prints the new file path

Run `index_rebuild.py` afterwards to refresh indices.
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import date
from pathlib import Path

# Import sibling _gh helpers
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _gh import gh_pr_view, gh_state_to_status, title_to_kebab, gh_available  # noqa: E402

VAULT = Path(__file__).resolve().parents[2]
WORK = VAULT / "work"
PROJECTS = WORK / "10_projects"
TEMPLATES = VAULT / "shared" / "templates"

FEATURE_DIR_RE = re.compile(r"^([A-Za-z][A-Za-z0-9]*)_([A-Z][a-z]{2}\d{2})$")


def find_feature_dir(feature: str) -> Path:
    """Find <feature>_<MonYY>/ under PROJECTS, by exact feature-name prefix match."""
    candidates = []
    for d in PROJECTS.iterdir():
        if not d.is_dir():
            continue
        m = FEATURE_DIR_RE.match(d.name)
        if m and m.group(1) == feature:
            candidates.append(d)
    if not candidates:
        sys.exit(f"error: no feature dir found for '{feature}' under {PROJECTS}. Create '{feature}_<MonYY>/' first.")
    if len(candidates) > 1:
        sys.exit(f"error: multiple candidate dirs for '{feature}': {[c.name for c in candidates]}")
    return candidates[0]


def render_template(template_path: Path, substitutions: dict[str, str]) -> str:
    text = template_path.read_text()
    for k, v in substitutions.items():
        text = text.replace(f"<{k}>", v)
    return text


def write_note(target: Path, content: str, force: bool = False) -> None:
    if target.exists() and not force:
        sys.exit(f"error: {target.relative_to(VAULT.parent)} already exists (use --force to overwrite)")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content)
    print(f"created: {target.relative_to(VAULT.parent)}")
    print("next: run `python3 llmzone/shared/scripts/index_rebuild.py`")


def cmd_algorithm(args: argparse.Namespace) -> None:
    feat_dir = find_feature_dir(args.feature)
    target = feat_dir / "algorithms" / f"{args.name}.md"
    subs = {
        "feature-lowercase": args.feature.lower(),
        "feature": args.feature.lower(),
        "FeatureName": args.feature,
        "AlgorithmName": args.name,
        "subsystem": args.area or "",
        "MonYY": feat_dir.name.rsplit("_", 1)[1],
    }
    content = render_template(TEMPLATES / "Algorithm_Template.md", subs)
    content = re.sub(r"^date: .*$", f"date: {date.today().isoformat()}", content, count=1, flags=re.MULTILINE)
    content = re.sub(r"^# .+$", f"# {args.name}", content, count=1, flags=re.MULTILINE)
    write_note(target, content, args.force)


def cmd_algorithm_step(args: argparse.Namespace) -> None:
    feat_dir = find_feature_dir(args.feature)
    parent = args.parent
    parent_path = feat_dir / "algorithms" / f"{parent}.md"
    if not parent_path.exists():
        sys.exit(f"error: parent algorithm note not found: {parent_path.relative_to(VAULT.parent)}")
    step_dir = feat_dir / "algorithms" / parent
    step_dir.mkdir(exist_ok=True)
    target = step_dir / f"{args.name}.md"
    subs = {
        "feature-lowercase": args.feature.lower(),
        "feature": args.feature.lower(),
        "FeatureName": args.feature,
        "ParentAlgorithmName": parent,
        "subsystem": args.area or "",
        "MonYY": feat_dir.name.rsplit("_", 1)[1],
    }
    content = render_template(TEMPLATES / "AlgorithmStep_Template.md", subs)
    content = re.sub(r"^date: .*$", f"date: {date.today().isoformat()}", content, count=1, flags=re.MULTILINE)
    content = re.sub(r"^# .+$", f"# {args.name}", content, count=1, flags=re.MULTILINE)
    write_note(target, content, args.force)


def cmd_decision(args: argparse.Namespace) -> None:
    feat_dir = find_feature_dir(args.feature)
    today = date.today().isoformat()
    filename = f"{today}_{args.topic}.md"
    target = feat_dir / "decisions" / filename
    subs = {
        "feature-lowercase": args.feature.lower(),
        "feature": args.feature.lower(),
        "FeatureName": args.feature,
        "subsystem": args.area or "",
    }
    content = render_template(TEMPLATES / "Decision_Record_Template.md", subs)
    content = re.sub(r"^date: .*$", f"date: {today}", content, count=1, flags=re.MULTILINE)
    title = filename[:-3]
    content = re.sub(r"^# .+$", f"# {title}", content, count=1, flags=re.MULTILINE)
    write_note(target, content, args.force)


def cmd_pr(args: argparse.Namespace) -> None:
    feat_dir = find_feature_dir(args.feature)

    # Auto-fetch from gh unless --no-gh
    gh_data: dict | None = None
    if not args.no_gh and gh_available():
        gh_data = gh_pr_view(args.number, repo=args.repo)
        if gh_data is None:
            print(f"warn: gh fetch failed for PR #{args.number}; falling back to manual args", file=sys.stderr)

    # Resolve title, branch, status, url — gh wins when available; explicit args override
    gh_title = (gh_data or {}).get("title", "")
    gh_branch = (gh_data or {}).get("headRefName", "")
    gh_url = (gh_data or {}).get("url", f"https://github.com/<owner>/<repo>/pull/{args.number}")
    gh_status = gh_state_to_status(gh_data) if gh_data else "Open"

    topic = args.topic or (title_to_kebab(gh_title) if gh_title else None)
    if not topic:
        sys.exit("error: provide <topic> or run with gh available so the PR title can fill it")
    branch = args.branch or gh_branch or "<branch>"
    title_display = gh_title or args.topic.replace("-", " ")

    today = date.today().isoformat()
    filename = f"{today}_pr-{args.number}_{topic}.md"
    target = feat_dir / "prs" / filename
    subs = {
        "feature-lowercase": args.feature.lower(),
        "feature": args.feature.lower(),
        "FeatureName": args.feature,
        "subsystem": args.area or "",
        "number": str(args.number),
        "branch-name": branch,
    }
    content = render_template(TEMPLATES / "PR_Summary_Template.md", subs)
    content = re.sub(r"^date: .*$", f"date: {today}", content, count=1, flags=re.MULTILINE)
    content = re.sub(r"^status: .*$", f"status: {gh_status}", content, count=1, flags=re.MULTILINE)
    content = re.sub(r"^# .+$", f"# PR {args.number} — {title_display}", content, count=1, flags=re.MULTILINE)
    # Replace the templated [#<number>](<url>) line with the real URL
    content = re.sub(
        rf"PR: \[#{args.number}\]\(.*?\)",
        f"PR: [#{args.number}]({gh_url})",
        content,
        count=1,
    )
    write_note(target, content, args.force)
    if gh_data:
        print(f"  filled from gh: title='{gh_title}', status={gh_status}, branch={branch}")


def cmd_runbook(args: argparse.Namespace) -> None:
    feat_dir = find_feature_dir(args.feature)
    name = args.name or f"Build_and_Test_{args.feature}"
    target = feat_dir / "runbook" / f"{name}.md"
    subs = {
        "feature-lowercase": args.feature.lower(),
        "feature": args.feature.lower(),
        "FeatureName": args.feature,
        "subsystem": args.area or "",
    }
    content = render_template(TEMPLATES / "Runbook_Template.md", subs)
    content = re.sub(r"^date: .*$", f"date: {date.today().isoformat()}", content, count=1, flags=re.MULTILINE)
    content = re.sub(r"^# .+$", f"# {name}", content, count=1, flags=re.MULTILINE)
    write_note(target, content, args.force)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = p.add_subparsers(dest="cmd", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--area", help="Subsystem area (optional)")
    common.add_argument("--force", action="store_true", help="Overwrite existing file")

    a = sp.add_parser("algorithm", parents=[common])
    a.add_argument("feature"); a.add_argument("name")
    a.set_defaults(func=cmd_algorithm)

    s = sp.add_parser("algorithm-step", parents=[common])
    s.add_argument("feature"); s.add_argument("parent"); s.add_argument("name")
    s.set_defaults(func=cmd_algorithm_step)

    d = sp.add_parser("decision", parents=[common])
    d.add_argument("feature"); d.add_argument("topic")
    d.set_defaults(func=cmd_decision)

    pr = sp.add_parser("pr", parents=[common])
    pr.add_argument("feature"); pr.add_argument("number", type=int)
    pr.add_argument("topic", nargs="?", help="Kebab topic (auto-derived from PR title if gh available)")
    pr.add_argument("--branch", help="Git branch name (auto-derived from gh)")
    pr.add_argument("--repo", help="GitHub repo for gh lookup (default: gh's auto-detect)")
    pr.add_argument("--no-gh", action="store_true", help="Skip gh auto-fetch; require --branch and topic")
    pr.set_defaults(func=cmd_pr)

    rb = sp.add_parser("runbook", parents=[common])
    rb.add_argument("feature"); rb.add_argument("name", nargs="?")
    rb.set_defaults(func=cmd_runbook)

    args = p.parse_args()
    args.func(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
