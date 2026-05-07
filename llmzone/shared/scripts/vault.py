#!/usr/bin/env python3
"""Unified vault CLI. Wraps new_note.py + index_rebuild.py and adds higher-level commands.

Subcommands:
  vault new feature <Name> [--month MonYY]
  vault new algorithm <feature> <Name>
  vault new algorithm-step <feature> <ParentName> <StepN_Name>
  vault new decision <feature> <kebab-topic>
  vault new pr <feature> <pr-number> <kebab-topic> [--branch X]
  vault new runbook <feature> [<Name>]
  vault archive <note-stem> [--status <terminal>]
  vault rebuild [--dry-run]
  vault check

Mutating subcommands auto-invoke `vault rebuild` at the end so indices stay fresh.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

# Import sibling _gh helpers
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _gh import gh_pr_list, gh_available  # noqa: E402

VAULT = Path(__file__).resolve().parents[2]   # llmzone/
WORK = VAULT / "work"
PROJECTS = WORK / "10_projects"
ARCHIVE = WORK / "50_archive"
SCRIPTS = VAULT / "shared" / "scripts"
TEMPLATES = VAULT / "shared" / "templates"

NEW_NOTE = SCRIPTS / "new_note.py"
INDEX_REBUILD = SCRIPTS / "index_rebuild.py"

FEATURE_DIR_RE = re.compile(r"^([A-Za-z][A-Za-z0-9]*)_([A-Z][a-z]{2}\d{2})$")
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

# Default terminal status to apply on `vault archive`, by note type
DEFAULT_ARCHIVE_STATUS = {
    "algorithm": "Superseded",
    "algorithm-step": "Superseded",
    "decision": "Deprecated",
    "runbook": "Deprecated",
    "pr-summary": None,    # keep whatever the PR's terminal status already is
    "log": "archived",
}


# ---------- helpers -----------------------------------------------------------

def run(cmd: list[str], **kwargs) -> int:
    return subprocess.call(cmd, **kwargs)


def rebuild(dry_run: bool = False, gh_sync: bool = False) -> int:
    args = [sys.executable, str(INDEX_REBUILD)]
    if dry_run:
        args.append("--dry-run")
    if gh_sync:
        args.append("--gh-sync")
    print(f"\n→ rebuilding indices{' (with gh-sync)' if gh_sync else ''}...")
    return run(args)


def find_feature_dir(feature: str) -> Path:
    candidates = []
    for d in PROJECTS.iterdir():
        if not d.is_dir():
            continue
        m = FEATURE_DIR_RE.match(d.name)
        if m and m.group(1) == feature:
            candidates.append(d)
    if not candidates:
        sys.exit(f"error: no feature dir found for '{feature}' under {PROJECTS}")
    if len(candidates) > 1:
        sys.exit(f"error: multiple candidate dirs for '{feature}': {[c.name for c in candidates]}")
    return candidates[0]


def find_note_by_stem(stem: str, archived: bool = False) -> Path | None:
    root = ARCHIVE if archived else PROJECTS
    for md in root.rglob(f"{stem}.md"):
        return md
    return None


def parse_frontmatter_text(text: str) -> tuple[dict[str, str], int, int]:
    """Returns (fm_dict, fm_text_start, fm_text_end). Indices are character positions
    of the lines between the two `---` delimiters (inclusive of the inner content)."""
    if not text.startswith("---\n"):
        return {}, -1, -1
    end = text.find("\n---", 4)
    if end == -1:
        return {}, -1, -1
    fm_text = text[4:end]
    fm = {}
    for line in fm_text.splitlines():
        if ":" in line and not line.lstrip().startswith("#"):
            k, _, v = line.partition(":")
            fm[k.strip()] = v.strip()
    return fm, 4, end


def set_frontmatter_field(text: str, key: str, value: str) -> str:
    fm, start, end = parse_frontmatter_text(text)
    if start == -1:
        return text
    fm_text = text[start:end]
    lines = fm_text.splitlines()
    new_line = f"{key}: {value}"
    found = False
    for i, line in enumerate(lines):
        if line.split(":", 1)[0].strip() == key:
            lines[i] = new_line
            found = True
            break
    if not found:
        lines.append(new_line)
    return text[:start] + "\n".join(lines) + text[end:]


# ---------- new feature -------------------------------------------------------

def cmd_new_feature(args: argparse.Namespace) -> None:
    name = args.name
    if not re.fullmatch(r"[A-Z][A-Za-z0-9]*", name):
        sys.exit(f"error: feature name must be PascalCase (got '{name}')")
    if args.month:
        if not re.fullmatch(r"[A-Z][a-z]{2}\d{2}", args.month):
            sys.exit(f"error: --month must look like 'Apr26' (got '{args.month}')")
        tag = args.month
    else:
        today = date.today()
        tag = MONTHS[today.month - 1] + str(today.year)[2:]
    feat_dir = PROJECTS / f"{name}_{tag}"
    if feat_dir.exists():
        sys.exit(f"error: {feat_dir.relative_to(VAULT.parent)} already exists")
    for sub in ("algorithms", "decisions", "prs", "runbook"):
        (feat_dir / sub).mkdir(parents=True)
    print(f"created: {feat_dir.relative_to(VAULT.parent)}")
    print(f"  with subdirs: algorithms/, decisions/, prs/, runbook/")
    print(f"\nnext steps:")
    print(f"  vault new algorithm {name} <AlgorithmName>")
    print(f"  vault new runbook {name}")
    rebuild()


# ---------- new note (delegates to new_note.py) ------------------------------

def cmd_new_note(args: argparse.Namespace, extra: list[str]) -> None:
    """Forward to new_note.py with the same subcommand."""
    cmd = [sys.executable, str(NEW_NOTE), args.note_type] + extra
    rc = run(cmd)
    if rc != 0:
        sys.exit(rc)
    rebuild()


# ---------- archive -----------------------------------------------------------

def cmd_archive(args: argparse.Namespace) -> None:
    note_path = find_note_by_stem(args.stem, archived=False)
    if not note_path:
        sys.exit(f"error: no active note with stem '{args.stem}' under {PROJECTS}")

    text = note_path.read_text()
    fm, _, _ = parse_frontmatter_text(text)
    note_type = fm.get("type", "")
    feature = fm.get("feature", "")
    if not feature:
        sys.exit(f"error: {note_path.relative_to(VAULT.parent)} has no `feature:` frontmatter")

    # Determine destination subdir from current path
    rel_parts = note_path.relative_to(PROJECTS).parts
    # rel_parts: (<feature_dir>, <subdir>, [<inner>, ...], <name>.md)
    if len(rel_parts) < 3:
        sys.exit(f"error: cannot infer subdir from {note_path}")
    subdir = rel_parts[1]
    inner = rel_parts[2:-1]  # any nested dirs (e.g., algorithms/<Algo>/)

    dest_dir = ARCHIVE / feature / subdir
    if inner:
        dest_dir = dest_dir / Path(*inner)
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = dest_dir / note_path.name
    if dest_path.exists():
        sys.exit(f"error: {dest_path.relative_to(VAULT.parent)} already exists")

    # Apply terminal status
    new_status = args.status or DEFAULT_ARCHIVE_STATUS.get(note_type)
    if new_status:
        text = set_frontmatter_field(text, "status", new_status)

    dest_path.write_text(text)
    note_path.unlink()
    print(f"archived: {note_path.relative_to(VAULT.parent)} → {dest_path.relative_to(VAULT.parent)}")
    if new_status:
        print(f"  status set to: {new_status}")

    # If parent dir is now empty, remove it (only for nested algorithm subdirs)
    if note_path.parent != PROJECTS / rel_parts[0] / subdir:
        try:
            note_path.parent.rmdir()
            print(f"  removed empty source dir: {note_path.parent.relative_to(VAULT.parent)}")
        except OSError:
            pass

    rebuild()


# ---------- prs (GitHub cross-reference) -------------------------------------

def _collect_known_pr_numbers() -> set[str]:
    """Walk all PR notes (active + archived), return the set of `pr:` values."""
    known: set[str] = set()
    for root in (PROJECTS, ARCHIVE):
        if not root.is_dir():
            continue
        for md in root.rglob("*.md"):
            if md.parent.name != "prs":
                continue
            try:
                text = md.read_text()
            except OSError:
                continue
            m = re.search(r"^pr:\s*(\d+)\s*$", text, re.MULTILINE)
            if m:
                known.add(m.group(1))
    return known


def cmd_prs(args: argparse.Namespace) -> None:
    if not gh_available():
        sys.exit("error: `gh` CLI not found on PATH")
    prs = gh_pr_list(state=args.state, author=args.author, repo=args.repo, limit=args.limit)
    if not prs:
        print(f"no PRs returned for author={args.author!r} state={args.state!r} repo={args.repo or 'default'}")
        return

    known = _collect_known_pr_numbers()
    missing = [pr for pr in prs if str(pr["number"]) not in known]

    print(f"found {len(prs)} PR(s) for author={args.author!r}; {len(known)} have notes; {len(missing)} missing\n")
    if not missing:
        print("all PRs have corresponding notes ✓")
        return
    print("PRs without a note:")
    for pr in sorted(missing, key=lambda p: -p["number"]):
        state = pr["state"]
        if pr.get("isDraft"):
            state = "DRAFT"
        print(f"  #{pr['number']} [{state:>6}]  {pr['title']}")
        print(f"           branch: {pr['headRefName']}")
        print(f"           url:    {pr['url']}")
    print(f"\ncreate one with: vault new pr <feature> <pr-number>  (auto-fills from gh)")


# ---------- check -------------------------------------------------------------

WIKILINK_RE = re.compile(r"\[\[([^\]\|#]+?)(?:#[^\]\|]+)?(?:\|[^\]]+)?\]\]")
H1_RE = re.compile(r"^#\s+(.+)$", re.MULTILINE)
NOTE_TYPES_REQUIRING_TLDR = {"algorithm", "decision", "pr-summary", "runbook"}
NOTE_TYPES_NEEDING_FEATURE = {"algorithm", "algorithm-step", "decision", "pr-summary", "runbook"}


def _walk_md_files(root: Path) -> list[Path]:
    if not root.is_dir():
        return []
    return [p for p in sorted(root.rglob("*.md"))]


def _parse_frontmatter_simple(text: str) -> dict[str, str]:
    """Lightweight frontmatter reader returning string-valued fields only.
    Strips inline `# comments`. Sufficient for check-time validation."""
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---", 4)
    if end == -1:
        return {}
    fm = {}
    for line in text[4:end].splitlines():
        if ":" in line and not line.lstrip().startswith("#"):
            k, _, v = line.partition(":")
            v = v.strip()
            if "#" in v:
                m = re.search(r"\s+#", v)
                if m:
                    v = v[: m.start()].strip()
            fm[k.strip()] = v
    return fm


def _has_tldr(text: str) -> bool:
    """A note has a TL;DR if the first non-blank, non-AUTOGEN, non-quote line
    after the H1 looks like a sentence (>= 4 words)."""
    h1_match = H1_RE.search(text)
    if not h1_match:
        return False
    after_h1 = text[h1_match.end():]
    in_autogen = False
    for raw in after_h1.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("<!-- AUTOGEN:") and "START" in line:
            in_autogen = True
            continue
        if line.startswith("<!-- AUTOGEN:") and "END" in line:
            in_autogen = False
            continue
        if in_autogen:
            continue
        if line.startswith("> "):
            continue   # template instructional quote
        if line.startswith("#"):
            return False  # next H2 with no TL;DR between
        # First content line — must look like prose (>= 4 words and end-ish)
        words = line.split()
        return len(words) >= 4
    return False


def _build_note_index() -> dict[str, list[Path]]:
    """Map filename-stem → list of paths (a stem may not be unique vault-wide).
    Used for resolving bare wikilinks like `[[Step3_ZoneSeeding]]`."""
    idx: dict[str, list[Path]] = {}
    for md in _walk_md_files(VAULT):
        idx.setdefault(md.stem, []).append(md)
    return idx


def _resolve_wikilink(target: str, source: Path, stem_idx: dict[str, list[Path]]) -> bool:
    """Return True if the link target resolves to a real file."""
    target = target.strip()
    if not target:
        return False
    # Full path (starts with llmzone/ or is absolute-style with /)
    if "/" in target:
        # Try as vault-relative path first
        candidate = (VAULT.parent / (target + ".md")).resolve()
        if candidate.exists():
            return True
        # Then try relative to the source file
        candidate = (source.parent / (target + ".md")).resolve()
        if candidate.exists():
            return True
        return False
    # Bare stem
    return target in stem_idx and len(stem_idx[target]) >= 1


def _strip_code(text: str) -> str:
    """Remove fenced code blocks and inline code spans so the wikilink scanner
    doesn't false-positive on example text inside backticks."""
    # Fenced code blocks (``` ... ```)
    text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    # Inline code spans (`...`)
    text = re.sub(r"`[^`\n]+`", "", text)
    return text


def _check_dangling_wikilinks(notes: list[Path]) -> list[str]:
    findings: list[str] = []
    stem_idx = _build_note_index()
    for md in notes:
        text = md.read_text()
        text_no_autogen = re.sub(
            r"<!-- AUTOGEN:[a-z0-9-]+ START -->.*?<!-- AUTOGEN:[a-z0-9-]+ END -->",
            "",
            text,
            flags=re.DOTALL,
        )
        text_scan = _strip_code(text_no_autogen)
        for match in WIKILINK_RE.finditer(text_scan):
            target = match.group(1)
            if not _resolve_wikilink(target, md, stem_idx):
                rel = md.relative_to(VAULT.parent)
                findings.append(f"  {rel}: dangling [[{target}]]")
    return findings


def _check_missing_tldr(notes: list[Path]) -> list[str]:
    findings: list[str] = []
    for md in notes:
        text = md.read_text()
        fm = _parse_frontmatter_simple(text)
        if fm.get("type") not in NOTE_TYPES_REQUIRING_TLDR:
            continue
        if not _has_tldr(text):
            findings.append(f"  {md.relative_to(VAULT.parent)}: no TL;DR sentence after H1")
    return findings


def _check_missing_feature(notes: list[Path]) -> list[str]:
    findings: list[str] = []
    for md in notes:
        text = md.read_text()
        fm = _parse_frontmatter_simple(text)
        if fm.get("type") not in NOTE_TYPES_NEEDING_FEATURE:
            continue
        if not fm.get("feature"):
            findings.append(f"  {md.relative_to(VAULT.parent)}: missing `feature:` frontmatter")
    return findings


def _check_stale_runbooks(notes: list[Path], days: int) -> list[str]:
    findings: list[str] = []
    threshold = date.today() - timedelta(days=days)
    for md in notes:
        text = md.read_text()
        fm = _parse_frontmatter_simple(text)
        if fm.get("type") != "runbook":
            continue
        date_str = fm.get("date", "")
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date_str):
            findings.append(f"  {md.relative_to(VAULT.parent)}: malformed `date:` ({date_str!r})")
            continue
        try:
            note_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            continue
        if note_date < threshold:
            age = (date.today() - note_date).days
            findings.append(f"  {md.relative_to(VAULT.parent)}: date {date_str} is {age} days old (threshold {days})")
    return findings


def cmd_check(args: argparse.Namespace) -> None:
    print(f"vault check — vault root: {VAULT.relative_to(VAULT.parent)}\n")

    # Walk active notes (10_projects + 40_logs); exclude archive and shared
    active_notes = []
    if PROJECTS.is_dir():
        active_notes.extend(_walk_md_files(PROJECTS))
    logs_dir = WORK / "40_logs"
    if logs_dir.is_dir():
        active_notes.extend(_walk_md_files(logs_dir))

    # All notes (incl. archive) for wikilink check
    all_notes = active_notes + _walk_md_files(ARCHIVE)

    sections = []

    # 1. Dangling wikilinks
    dangling = _check_dangling_wikilinks(all_notes)
    sections.append(("Dangling wikilinks", dangling))

    # 2. Missing TL;DR
    no_tldr = _check_missing_tldr(active_notes)
    sections.append(("Missing TL;DR sentence after H1", no_tldr))

    # 3. Missing feature
    no_feature = _check_missing_feature(active_notes)
    sections.append(("Missing `feature:` frontmatter", no_feature))

    # 4. Stale runbooks
    if not args.no_stale:
        stale = _check_stale_runbooks(active_notes, args.stale_days)
        sections.append((f"Runbooks older than {args.stale_days} days", stale))

    # Print findings
    total = 0
    for name, items in sections:
        if not items:
            print(f"✓ {name}: clean")
            continue
        total += len(items)
        print(f"✗ {name}: {len(items)} finding(s)")
        for f in items:
            print(f)
        print()

    # 5. gh-sync drift (delegates to index_rebuild --gh-sync --dry-run)
    if not args.no_gh:
        if gh_available():
            print("→ checking GitHub PR drift (--gh-sync --dry-run)...")
            rc = rebuild(dry_run=True, gh_sync=True)
            if rc != 0:
                total += 1
                print(f"✗ gh-sync exited non-zero ({rc})")
        else:
            print("- gh not available; skipping PR drift check")

    # 6. rebuild dry-run (catches index drift)
    print("\n→ checking index drift (rebuild --dry-run)...")
    rc = rebuild(dry_run=True)
    if rc != 0:
        total += 1

    print(f"\n{'all checks clean' if total == 0 else f'{total} finding(s) — review above'}")
    sys.exit(0 if total == 0 else 1)


# ---------- main --------------------------------------------------------------

def main() -> int:
    p = argparse.ArgumentParser(
        prog="vault",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sp = p.add_subparsers(dest="cmd", required=True)

    # new
    new = sp.add_parser("new", help="Create a new feature dir or note")
    new_sp = new.add_subparsers(dest="note_type", required=True)

    nf = new_sp.add_parser("feature", help="Create a new feature dir scaffolding")
    nf.add_argument("name", help="PascalCase feature name (e.g. VolumeMesherSizeFunction)")
    nf.add_argument("--month", help="Override month tag (e.g. Apr26). Defaults to current month.")
    nf.set_defaults(func=cmd_new_feature)

    # Other `vault new <type>` subcommands forward to new_note.py
    for note_type in ("algorithm", "algorithm-step", "decision", "pr", "runbook"):
        sub = new_sp.add_parser(note_type, help=f"Create a new {note_type} note (delegates to new_note.py)")
        sub.set_defaults(func=lambda a, e: cmd_new_note(a, e))
        # All remaining args are passed through; argparse won't validate them here

    # archive
    ar = sp.add_parser("archive", help="Move an active note to 50_archive/ with a terminal status")
    ar.add_argument("stem", help="Note stem (filename without .md), e.g. VolumeMesherSizeFunction")
    ar.add_argument("--status", help="Terminal status override (default: by-type)")
    ar.set_defaults(func=cmd_archive)

    # rebuild
    rb = sp.add_parser("rebuild", help="Refresh indices, status badges, and Related sections")
    rb.add_argument("--dry-run", action="store_true")
    rb.add_argument("--gh-sync", action="store_true", help="Sync PR statuses from GitHub before rebuild")
    rb.set_defaults(func=lambda a: sys.exit(rebuild(dry_run=a.dry_run, gh_sync=a.gh_sync)))

    # prs
    prs = sp.add_parser("prs", help="List GitHub PRs that don't yet have a vault note")
    prs.add_argument("--repo", help="GitHub repo (default: from gh's auto-detection or DEFAULT_REPO)")
    prs.add_argument("--author", default="@me", help="PR author filter (default: @me)")
    prs.add_argument("--state", default="all", choices=["open", "closed", "merged", "all"], help="PR state filter")
    prs.add_argument("--limit", type=int, default=100, help="Max PRs to fetch")
    prs.set_defaults(func=cmd_prs)

    # check
    ck = sp.add_parser("check", help="Run vault health checks (links, TL;DR, frontmatter, staleness, gh-sync drift)")
    ck.add_argument("--no-gh", action="store_true", help="Skip GitHub PR drift check")
    ck.add_argument("--no-stale", action="store_true", help="Skip stale-runbook check")
    ck.add_argument("--stale-days", type=int, default=60, help="Runbook age threshold in days (default: 60)")
    ck.set_defaults(func=cmd_check)

    args, extra = p.parse_known_args()

    # Forwarded `vault new <type>` calls need to forward `extra` to new_note.py
    if args.cmd == "new" and args.note_type != "feature":
        args.func(args, extra)
    else:
        if extra:
            print(f"warn: ignoring unrecognized args: {extra}", file=sys.stderr)
        args.func(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
