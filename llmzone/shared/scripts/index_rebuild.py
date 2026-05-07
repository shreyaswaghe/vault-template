#!/usr/bin/env python3
"""Rebuild llmzone indices and per-note autogen blocks.

For each note: writes a derived `Status` badge and a `Related` section between
AUTOGEN markers. For the work scope: writes Active_Work, Map_of_Contents
Projects/Archive sections, and per-feature Archived.md.

Idempotent. Hand-written content above/below AUTOGEN markers is preserved.

Run after creating, moving, or archiving any note. Surfaces L1 warnings on
stderr when in-note `status:` disagrees with the derived state.
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

# Import sibling _gh module without polluting sys.path globally
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _gh import gh_pr_view, gh_state_to_status, extract_repo_from_text, gh_available  # noqa: E402

VAULT = Path(__file__).resolve().parents[2]   # llmzone/
WORK = VAULT / "work"
PROJECTS = WORK / "10_projects"
ARCHIVE = WORK / "50_archive"
INDEX = WORK / "00_index"

FEATURE_DIR_RE = re.compile(r"^(?P<name>[A-Za-z][A-Za-z0-9]*)_(?P<tag>[A-Z][a-z]{2}\d{2})$")
H1_RE = re.compile(r"^# .+$", re.MULTILINE)
MONTH_FULL = {
    "Jan": "January", "Feb": "February", "Mar": "March", "Apr": "April",
    "May": "May", "Jun": "June", "Jul": "July", "Aug": "August",
    "Sep": "September", "Oct": "October", "Nov": "November", "Dec": "December",
}
SUBDIR_LABEL = {
    "algorithms": "Algorithms",
    "decisions": "Decisions",
    "prs": "PRs",
    "runbook": "Runbook",
}
SUBDIR_ORDER = ["algorithms", "decisions", "prs", "runbook"]

# Terminal statuses: human-set, derivation does not override these
TERMINAL_STATUSES = {"Superseded", "Reverted", "Deprecated", "Closed"}


@dataclass
class Note:
    path: Path
    frontmatter: dict[str, object]
    type_: str = ""
    feature: str = ""
    status: str = ""
    date: str = ""
    is_archived: bool = False    # path-based: True if note lives under 50_archive/
    # Derived at runtime
    derived_status: str = ""
    derived_reason: str = ""

    @property
    def stem(self) -> str:
        return self.path.stem

    @property
    def vault_link(self) -> str:
        rel = self.path.relative_to(VAULT.parent)
        return str(rel.with_suffix(""))

    def get_list(self, key: str) -> list[str]:
        v = self.frontmatter.get(key)
        if isinstance(v, list):
            return [s for s in v if s]
        if isinstance(v, str) and v:
            return [v]
        return []

    def get_str(self, key: str) -> str:
        v = self.frontmatter.get(key, "")
        return v if isinstance(v, str) else ""


@dataclass
class Feature:
    name: str
    tag: str
    dir_name: str
    notes: list[Note] = field(default_factory=list)

    @property
    def display(self) -> str:
        if not self.tag:
            return self.name
        mon, yy = self.tag[:3], self.tag[3:]
        return f"{self.name} ({MONTH_FULL.get(mon, mon)} 20{yy})"

    @property
    def sort_key(self) -> tuple:
        if not self.tag:
            return (0, 0, self.name)
        mon, yy = self.tag[:3], self.tag[3:]
        month_idx = list(MONTH_FULL.keys()).index(mon) if mon in MONTH_FULL else 0
        return (-int(yy), -month_idx, self.name)

    def active_notes_by_type(self, type_: str) -> list[Note]:
        return [n for n in self.notes if n.type_ == type_ and not n.is_archived]

    def archived_notes(self) -> list[Note]:
        return [n for n in self.notes if n.is_archived]


# ---------- Frontmatter parsing ----------------------------------------------

def _parse_value(val: str) -> object:
    # Strip inline `# comment` (templates use these for in-line docs).
    # Only strip when '#' is preceded by whitespace, to avoid eating `#L42` etc.
    if "#" in val:
        m = re.search(r"\s+#", val)
        if m:
            val = val[: m.start()]
    val = val.strip()
    if val.startswith("[") and val.endswith("]"):
        inner = val[1:-1].strip()
        if not inner:
            return []
        return [s.strip().strip('"').strip("'") for s in inner.split(",") if s.strip()]
    return val


def parse_frontmatter(path: Path) -> dict[str, object] | None:
    text = path.read_text()
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---", 4)
    if end == -1:
        return None
    fm: dict[str, object] = {}
    for line in text[4:end].splitlines():
        if ":" in line and not line.lstrip().startswith("#"):
            k, _, v = line.partition(":")
            fm[k.strip()] = _parse_value(v)
    return fm


def load_note(path: Path) -> Note | None:
    fm = parse_frontmatter(path)
    if fm is None:
        return None
    return Note(
        path=path,
        frontmatter=fm,
        type_=str(fm.get("type", "")),
        feature=str(fm.get("feature", "")),
        status=str(fm.get("status", "")),
        date=str(fm.get("date", "")),
    )


# ---------- Discovery ---------------------------------------------------------

def discover() -> tuple[dict[str, Feature], list[Note]]:
    """Return (features_by_name, all_notes)."""
    features: dict[str, Feature] = {}
    all_notes: list[Note] = []

    if PROJECTS.is_dir():
        for d in sorted(PROJECTS.iterdir()):
            if not d.is_dir():
                continue
            m = FEATURE_DIR_RE.match(d.name)
            if not m:
                continue
            feat = Feature(name=m["name"], tag=m["tag"], dir_name=d.name)
            features[feat.name] = feat
            for md in sorted(d.rglob("*.md")):
                if md.name == "Archived.md" and md.parent == d:
                    continue
                note = load_note(md)
                if note:
                    note.is_archived = False
                    feat.notes.append(note)
                    all_notes.append(note)

    if ARCHIVE.is_dir():
        for md in sorted(ARCHIVE.rglob("*.md")):
            if md.name == "README.md":
                continue
            note = load_note(md)
            if not note:
                continue
            fname = note.feature
            if not fname:
                print(f"warn: {md.relative_to(VAULT)} has no `feature:` frontmatter — skipping", file=sys.stderr)
                continue
            if fname not in features:
                tag = ""
                if note.date and re.match(r"\d{4}-\d{2}", note.date):
                    yyyy, mm = note.date[:4], note.date[5:7]
                    months = list(MONTH_FULL.keys())
                    try:
                        tag = months[int(mm) - 1] + yyyy[2:]
                    except (ValueError, IndexError):
                        pass
                features[fname] = Feature(name=fname, tag=tag, dir_name="")
            note.is_archived = True
            features[fname].notes.append(note)
            all_notes.append(note)

    return features, all_notes


# ---------- Cross-ref index ---------------------------------------------------

@dataclass
class Index:
    by_stem: dict[str, Note] = field(default_factory=dict)
    by_pr_number: dict[str, Note] = field(default_factory=dict)
    # PR notes whose `reverts:` field includes a given PR number
    pr_reverters: dict[str, list[Note]] = field(default_factory=lambda: defaultdict(list))
    # Algorithm notes whose `supersedes:` equals a given algorithm stem
    algo_supersedors: dict[str, list[Note]] = field(default_factory=lambda: defaultdict(list))


def build_index(all_notes: list[Note]) -> Index:
    idx = Index()
    for n in all_notes:
        idx.by_stem[n.stem] = n
        if n.type_ == "pr-summary":
            pr_num = n.get_str("pr")
            if pr_num:
                idx.by_pr_number[pr_num] = n
            for r in n.get_list("reverts"):
                idx.pr_reverters[str(r)].append(n)
        if n.type_ == "algorithm":
            sup = n.get_str("supersedes")
            if sup:
                idx.algo_supersedors[sup].append(n)
    return idx


# ---------- Status derivation -------------------------------------------------

def derive_status(note: Note, idx: Index) -> tuple[str, str]:
    """Return (derived_status, reason). Empty derived_status means no derivation;
    reason is a short markdown-safe explanation for the badge."""
    # Don't override human-set terminal states
    if note.status in TERMINAL_STATUSES:
        return ("", "")
    if note.type_ == "algorithm":
        # Superseded?
        sups = idx.algo_supersedors.get(note.stem, [])
        for s in sups:
            s_status = s.derived_status or s.status
            if s_status in {"Implemented", "Merged"}:
                return ("Superseded", f"by [[{s.vault_link}|{s.stem}]]")
        # Reverted? — most recent referenced PR is Reverted
        prs = note.get_list("prs")
        pr_notes = [idx.by_pr_number.get(str(p)) for p in prs]
        pr_notes = [p for p in pr_notes if p]
        if pr_notes:
            pr_notes.sort(key=lambda p: (p.date, p.stem))
            most_recent = pr_notes[-1]
            if most_recent.status == "Reverted":
                return ("Reverted", f"by [[{most_recent.vault_link}|PR {most_recent.get_str('pr')}]]")
            # Implemented? — any referenced PR is Merged
            for p in pr_notes:
                if p.status == "Merged":
                    return ("Implemented", f"via [[{p.vault_link}|PR {p.get_str('pr')}]]")
        return ("", "")

    if note.type_ == "decision":
        sb = note.get_str("superseded_by")
        if sb:
            target = idx.by_stem.get(sb)
            link = f"[[{target.vault_link}|{sb}]]" if target else f"`{sb}`"
            return ("Superseded", f"by {link}")
        return ("", "")

    if note.type_ == "pr-summary":
        # Reverted? — another PR's reverts includes this PR
        my_num = note.get_str("pr")
        reverters = idx.pr_reverters.get(my_num, [])
        if reverters:
            reverters.sort(key=lambda p: (p.date, p.stem))
            r = reverters[-1]
            return ("Reverted", f"by [[{r.vault_link}|PR {r.get_str('pr')}]]")
        return ("", "")

    return ("", "")


def annotate_derived(all_notes: list[Note], idx: Index) -> None:
    """Two-pass: derive status for every note, with one fixpoint iteration so
    Superseded propagates through chains."""
    for _ in range(2):
        for n in all_notes:
            d, r = derive_status(n, idx)
            n.derived_status = d
            n.derived_reason = r


# ---------- Per-note rendering ------------------------------------------------

def render_status_badge(note: Note) -> str:
    base = note.status or "(unset)"
    if note.derived_status and note.derived_status != base:
        return f"**Status**: {note.derived_status} {note.derived_reason} _(in-note: `{base}`)_"
    return f"**Status**: {base}"


def render_related(note: Note, idx: Index, all_notes: list[Note]) -> str:
    lines: list[str] = []

    def link(n: Note, label: str | None = None) -> str:
        return f"[[{n.vault_link}|{label or n.stem}]]"

    if note.type_ == "algorithm":
        # Implemented by: PR notes whose algorithms include this stem
        prs = [n for n in all_notes if n.type_ == "pr-summary" and note.stem in n.get_list("algorithms")]
        if prs:
            lines.append("**Implemented by**: " + ", ".join(link(p, f"PR {p.get_str('pr')}") for p in sorted(prs, key=lambda x: x.date)))
        # Obeys decisions
        for d_stem in note.get_list("decisions"):
            d = idx.by_stem.get(d_stem)
            if d:
                lines.append(f"**Obeys decision**: {link(d, d_stem)}")
        # Tested by: runbooks whose algorithms include this stem
        rbs = [n for n in all_notes if n.type_ == "runbook" and (note.stem in n.get_list("algorithms") or not n.get_list("algorithms"))]
        # Restrict to same feature
        rbs = [n for n in rbs if n.feature == note.feature]
        if rbs:
            lines.append("**Tested by**: " + ", ".join(link(r) for r in sorted(rbs, key=lambda x: x.stem)))
        # Steps
        steps = [n for n in all_notes if n.type_ == "algorithm-step" and n.get_str("parent") == note.stem]
        if steps:
            steps.sort(key=lambda x: x.stem)
            lines.append("**Steps**:")
            for s in steps:
                lines.append(f"- {link(s)}")
        # Supersedes / Superseded by
        sup = note.get_str("supersedes")
        if sup:
            t = idx.by_stem.get(sup)
            lines.append(f"**Supersedes**: {link(t, sup) if t else f'`{sup}`'}")
        for s in idx.algo_supersedors.get(note.stem, []):
            lines.append(f"**Superseded by**: {link(s)}")

    elif note.type_ == "algorithm-step":
        parent_stem = note.get_str("parent")
        if parent_stem:
            p = idx.by_stem.get(parent_stem)
            if p:
                lines.append(f"**Parent**: {link(p, parent_stem)}")

    elif note.type_ == "decision":
        prs = [n for n in all_notes if n.type_ == "pr-summary" and note.stem in n.get_list("decisions")]
        if prs:
            lines.append("**Implemented by**: " + ", ".join(link(p, f"PR {p.get_str('pr')}") for p in sorted(prs, key=lambda x: x.date)))
        for a_stem in note.get_list("algorithms"):
            a = idx.by_stem.get(a_stem)
            if a:
                lines.append(f"**Affects algorithm**: {link(a, a_stem)}")
        sb = note.get_str("superseded_by")
        if sb:
            t = idx.by_stem.get(sb)
            lines.append(f"**Superseded by**: {link(t, sb) if t else f'`{sb}`'}")
        # Supersedes (other decisions naming this one as superseded_by)
        sups = [n for n in all_notes if n.type_ == "decision" and n.get_str("superseded_by") == note.stem]
        for s in sups:
            lines.append(f"**Supersedes**: {link(s)}")

    elif note.type_ == "pr-summary":
        for a_stem in note.get_list("algorithms"):
            a = idx.by_stem.get(a_stem)
            if a:
                lines.append(f"**Touches algorithm**: {link(a, a_stem)}")
        for d_stem in note.get_list("decisions"):
            d = idx.by_stem.get(d_stem)
            if d:
                lines.append(f"**Implements decision**: {link(d, d_stem)}")
        for r_num in note.get_list("reverts"):
            r = idx.by_pr_number.get(str(r_num))
            if r:
                lines.append(f"**Reverts**: {link(r, f'PR {r_num}')}")
        my_num = note.get_str("pr")
        for rev in idx.pr_reverters.get(my_num, []):
            rev_label = "PR " + rev.get_str("pr")
            lines.append(f"**Reverted by**: {link(rev, rev_label)}")

    elif note.type_ == "runbook":
        for a_stem in note.get_list("algorithms"):
            a = idx.by_stem.get(a_stem)
            if a:
                lines.append(f"**Exercises algorithm**: {link(a, a_stem)}")

    if not lines:
        return "_No related notes._"
    return "\n".join(lines)


# ---------- File writers ------------------------------------------------------

def replace_or_insert_section(text: str, marker: str, body: str, where: str = "append") -> str:
    """Replace content between AUTOGEN markers; insert if absent.
    `where`: "append" to add at end, "after-h1" to add right after first H1 line."""
    start = f"<!-- AUTOGEN:{marker} START -->"
    end = f"<!-- AUTOGEN:{marker} END -->"
    block = f"{start}\n{body.rstrip()}\n{end}"
    pattern = re.compile(re.escape(start) + r".*?" + re.escape(end), re.DOTALL)
    if pattern.search(text):
        return pattern.sub(block, text)
    if where == "after-h1":
        m = H1_RE.search(text)
        if m:
            insert_at = m.end()
            return text[:insert_at] + "\n\n" + block + text[insert_at:]
    if not text.endswith("\n"):
        text += "\n"
    if not text.endswith("\n\n"):
        text += "\n"
    return text + block + "\n"


def write_note_blocks(note: Note, idx: Index, all_notes: list[Note], dry_run: bool) -> bool:
    """Write status badge and related section into the note's body."""
    text = note.path.read_text()
    new = text
    new = replace_or_insert_section(new, "status", render_status_badge(note), where="after-h1")
    new = replace_or_insert_section(new, "related", render_related(note, idx, all_notes), where="append")
    return _write_if_changed(note.path, text, new, dry_run)


# ---------- Index renderers ---------------------------------------------------

def _status_suffix(note: Note) -> str:
    if note.derived_status and note.derived_status != note.status:
        return f" — {note.derived_status} {note.derived_reason}".strip()
    if note.status:
        return f" — {note.status}"
    return ""


def _list_notes(notes: list[Note], indent: str = "  ") -> list[str]:
    out = []
    for n in sorted(notes, key=lambda x: x.stem):
        out.append(f"{indent}- [[{n.vault_link}|{n.stem}]]{_status_suffix(n)}")
    return out


def render_active_features(features: dict[str, Feature]) -> str:
    actives = [f for f in features.values() if f.dir_name and any(
        f.active_notes_by_type(t) for t in ("algorithm", "decision", "pr-summary", "runbook")
    )]
    if not actives:
        return "_No active features._"
    lines: list[str] = []
    for feat in sorted(actives, key=lambda f: f.sort_key):
        lines.append(f"### {feat.display}")
        lines.append("")
        for sub, type_ in [("algorithms", "algorithm"), ("decisions", "decision"),
                            ("prs", "pr-summary"), ("runbook", "runbook")]:
            notes = feat.active_notes_by_type(type_)
            if not notes:
                continue
            lines.append(f"**{SUBDIR_LABEL[sub]}**")
            lines.extend(_list_notes(notes, indent=""))
            lines.append("")
        if feat.archived_notes():
            lines.append(f"_Archive: [[llmzone/work/10_projects/{feat.dir_name}/Archived]]_")
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def render_projects(features: dict[str, Feature]) -> str:
    actives = [f for f in features.values() if f.dir_name]
    if not actives:
        return "_No active features._"
    lines: list[str] = []
    for feat in sorted(actives, key=lambda f: f.sort_key):
        lines.append(f"### {feat.display}")
        for sub, type_ in [("algorithms", "algorithm"), ("decisions", "decision"),
                            ("prs", "pr-summary"), ("runbook", "runbook")]:
            notes = feat.active_notes_by_type(type_)
            if not notes:
                continue
            lines.append(f"- **{SUBDIR_LABEL[sub]}**:")
            for n in sorted(notes, key=lambda x: x.stem):
                lines.append(f"  - [[{n.vault_link}|{n.stem}]]{_status_suffix(n)}")
        if feat.archived_notes():
            lines.append(f"- **Archive**: [[llmzone/work/10_projects/{feat.dir_name}/Archived]]")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def render_archive_section(features: dict[str, Feature]) -> str:
    with_archive = []
    for f in features.values():
        archived = f.archived_notes()
        if archived:
            with_archive.append((f, archived))
    if not with_archive:
        return "_No archived items._"
    lines: list[str] = []
    for feat, archived in sorted(with_archive, key=lambda t: t[0].sort_key):
        lines.append(f"### {feat.display}")
        if feat.dir_name:
            lines.append(f"- Index: [[llmzone/work/10_projects/{feat.dir_name}/Archived]]")
        else:
            for n in sorted(archived, key=lambda x: (x.date, x.stem)):
                lines.append(f"- [[{n.vault_link}|{n.stem}]]")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def render_per_feature_archived(feat: Feature) -> str:
    archived = feat.archived_notes()
    if not archived:
        return "_None yet._"
    by_sub: dict[str, list[Note]] = defaultdict(list)
    for n in archived:
        try:
            parts = n.path.relative_to(ARCHIVE).parts
            sub = parts[-2] if len(parts) >= 2 else "other"
        except ValueError:
            sub = "other"
        by_sub[sub].append(n)
    lines: list[str] = []
    for sub in sorted(by_sub):
        label = SUBDIR_LABEL.get(sub, sub.capitalize())
        lines.append(f"**{label}**")
        for n in sorted(by_sub[sub], key=lambda x: (x.date, x.stem)):
            lines.append(f"- [[{n.vault_link}|{n.stem}]]")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


# ---------- Index file writers ------------------------------------------------

def ensure_file(path: Path, default: str) -> str:
    if path.exists():
        return path.read_text()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(default)
    return default


def _write_if_changed(path: Path, old: str, new: str, dry_run: bool) -> bool:
    if old == new:
        return False
    rel = path.relative_to(VAULT.parent)
    if dry_run:
        print(f"would update: {rel}")
    else:
        path.write_text(new)
        print(f"updated: {rel}")
    return True


def write_active_work(features: dict[str, Feature], dry_run: bool) -> bool:
    path = INDEX / "Active_Work.md"
    default = (
        "---\ntype: index\nscope: work\nzone: llmzone\nstatus: active\n"
        "tags: [llmzone, work, active]\n---\n\n# Active_Work\n\n"
        "Active features under `10_projects/`. Auto-generated by "
        "`llmzone/shared/scripts/index_rebuild.py` — do not edit between AUTOGEN markers.\n\n"
        "## Active features\n\n<!-- AUTOGEN:active-features START -->\n<!-- AUTOGEN:active-features END -->\n"
    )
    text = ensure_file(path, default)
    new = replace_or_insert_section(text, "active-features", render_active_features(features))
    return _write_if_changed(path, text, new, dry_run)


def write_map_of_contents(features: dict[str, Feature], dry_run: bool) -> bool:
    path = INDEX / "Map_of_Contents.md"
    default = (
        "---\ntype: index\nscope: work\nzone: llmzone\nstatus: active\n"
        "tags: [llmzone, work, moc]\n---\n\n# Map_of_Contents\n\n"
        "## Projects\n\n<!-- AUTOGEN:projects START -->\n<!-- AUTOGEN:projects END -->\n\n"
        "## Archive\n\n<!-- AUTOGEN:archive START -->\n<!-- AUTOGEN:archive END -->\n"
    )
    text = ensure_file(path, default)
    text2 = replace_or_insert_section(text, "projects", render_projects(features))
    text3 = replace_or_insert_section(text2, "archive", render_archive_section(features))
    return _write_if_changed(path, text, text3, dry_run)


def write_per_feature_archived(features: dict[str, Feature], dry_run: bool) -> int:
    changes = 0
    for feat in features.values():
        if not feat.dir_name:
            continue
        path = PROJECTS / feat.dir_name / "Archived.md"
        default = (
            f"---\ntype: index\nscope: work\nfeature: {feat.name}\nstatus: active\n"
            f"tags: [llmzone, work, archive, {feat.name.lower()}]\n---\n\n"
            f"# {feat.name} — Archived notes\n\n"
            f"Notes from this feature that have been moved to `50_archive/`. Auto-generated.\n\n"
            f"<!-- AUTOGEN:archived-notes START -->\n<!-- AUTOGEN:archived-notes END -->\n"
        )
        text = ensure_file(path, default)
        new = replace_or_insert_section(text, "archived-notes", render_per_feature_archived(feat))
        if _write_if_changed(path, text, new, dry_run):
            changes += 1
    return changes


# ---------- Validation (L1 warnings) -----------------------------------------

def validate(all_notes: list[Note]) -> int:
    """Print warnings to stderr. Returns count."""
    warnings = 0
    for n in all_notes:
        rel = n.path.relative_to(VAULT)
        # Tag check (required base tags)
        tags = n.get_list("tags")
        type_tag = n.type_
        feature_tag = n.feature.lower()
        if type_tag and type_tag not in tags:
            print(f"warn: {rel}: missing required tag `{type_tag}`", file=sys.stderr); warnings += 1
        if feature_tag and feature_tag not in tags:
            print(f"warn: {rel}: missing required tag `{feature_tag}`", file=sys.stderr); warnings += 1
        # Status mismatch
        if n.derived_status and n.derived_status != n.status:
            print(f"info: {rel}: in-note status `{n.status}` differs from derived `{n.derived_status}` ({n.derived_reason})", file=sys.stderr)
        # Algorithm-step parent existence
        if n.type_ == "algorithm-step":
            parent = n.get_str("parent")
            if not parent:
                print(f"warn: {rel}: algorithm-step missing `parent:` frontmatter", file=sys.stderr); warnings += 1
    return warnings


# ---------- Main --------------------------------------------------------------

def gh_sync_pr_notes(all_notes: list[Note], dry_run: bool) -> int:
    """For each PR note, fetch GitHub state and update in-note `status:` to match.
    Returns count of files updated. Skips PR notes with no `pr:` number."""
    if not gh_available():
        print("warn: --gh-sync requested but `gh` CLI not found on PATH", file=sys.stderr)
        return 0
    changes = 0
    for n in all_notes:
        if n.type_ != "pr-summary":
            continue
        pr_num = n.get_str("pr")
        if not pr_num:
            print(f"warn: {n.path.relative_to(VAULT)} has no `pr:` field, skipping gh sync", file=sys.stderr)
            continue
        text = n.path.read_text()
        repo = extract_repo_from_text(text)
        gh = gh_pr_view(pr_num, repo=repo)
        if gh is None:
            print(f"warn: gh fetch failed for PR #{pr_num} (repo {repo})", file=sys.stderr)
            continue
        new_status = gh_state_to_status(gh)
        new_branch = gh.get("headRefName", "") or ""
        old_status = n.status
        old_branch = n.get_str("branch")
        diffs = []
        if new_status and new_status != old_status:
            text = _set_frontmatter_value(text, "status", new_status)
            diffs.append(f"status={old_status}→{new_status}")
        if new_branch and new_branch != old_branch:
            text = _set_frontmatter_value(text, "branch", new_branch)
            diffs.append(f"branch={old_branch}→{new_branch}")
        if diffs:
            rel = n.path.relative_to(VAULT.parent)
            joined = ", ".join(diffs)
            if dry_run:
                print(f"would gh-sync: {rel} ({joined})")
            else:
                n.path.write_text(text)
                n.status = new_status
                n.frontmatter["status"] = new_status
                n.frontmatter["branch"] = new_branch
                print(f"gh-synced: {rel} ({joined})")
            changes += 1
    return changes


def _set_frontmatter_value(text: str, key: str, value: str) -> str:
    """Replace or insert a single-value frontmatter field. Preserves layout otherwise."""
    if not text.startswith("---\n"):
        return text
    end = text.find("\n---", 4)
    if end == -1:
        return text
    fm_text = text[4:end]
    body = text[end:]
    lines = fm_text.splitlines()
    new_line = f"{key}: {value}"
    for i, line in enumerate(lines):
        if line.split(":", 1)[0].strip() == key:
            lines[i] = new_line
            return "---\n" + "\n".join(lines) + body
    lines.append(new_line)
    return "---\n" + "\n".join(lines) + body


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--gh-sync", action="store_true",
                        help="Sync each PR note's status from GitHub before rebuilding.")
    args = parser.parse_args()

    if not WORK.is_dir():
        print(f"error: {WORK} not found", file=sys.stderr); return 1

    features, all_notes = discover()

    # gh-sync mutates frontmatter; do this BEFORE derivation so derived state sees fresh PR statuses.
    if args.gh_sync:
        gh_sync_pr_notes(all_notes, args.dry_run)
        # Re-discover to pick up status changes (cheap)
        features, all_notes = discover()

    idx = build_index(all_notes)
    annotate_derived(all_notes, idx)

    print(f"discovered {len(features)} feature(s), {len(all_notes)} note(s)")

    changed = 0
    # Per-note blocks first so derived state propagates into their files
    for n in all_notes:
        if write_note_blocks(n, idx, all_notes, args.dry_run):
            changed += 1
    if write_active_work(features, args.dry_run): changed += 1
    if write_map_of_contents(features, args.dry_run): changed += 1
    changed += write_per_feature_archived(features, args.dry_run)

    validate(all_notes)

    if changed == 0:
        print("no changes")
    else:
        print(f"{'would change' if args.dry_run else 'changed'} {changed} file(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
