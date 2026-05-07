#!/usr/bin/env python3
"""
Unwrap soft-wrapped markdown so that each paragraph and each list item is
one physical line. Per the vault's formatting rules: lines from "start to
full stop" should not contain linebreaks; Obsidian handles soft-wrapping
for display.

Preserved verbatim: YAML frontmatter, fenced code blocks (``` and ~~~,
including ``` mermaid), ATX headings (# .. ######), horizontal rules,
tables, and blank lines.

Idempotent: re-running on already-reflowed content is a no-op.
"""
import argparse
import re
import sys


def is_code_fence(line: str) -> bool:
    s = line.lstrip()
    return s.startswith("```") or s.startswith("~~~")


def code_fence_marker(line: str) -> str:
    s = line.lstrip()
    return s[:3]


def is_blank(line: str) -> bool:
    return line.strip() == ""


def is_heading(line: str) -> bool:
    return re.match(r"^#{1,6}\s", line) is not None


def is_table_row(line: str) -> bool:
    return line.lstrip().startswith("|")


def is_hr(line: str) -> bool:
    s = line.strip()
    return re.match(r"^[-*_]{3,}$", s) is not None


LIST_ITEM_RE = re.compile(r"^(\s*)([-*+]\s|\d+\.\s)(.*)$")


def is_list_item(line: str) -> bool:
    return LIST_ITEM_RE.match(line) is not None


def split_frontmatter(text: str):
    """Return (frontmatter_with_trailing_newline_or_empty, rest)."""
    if not text.startswith("---\n"):
        return "", text
    # Find the closing '---' line.
    m = re.match(r"^---\n.*?\n---\n", text, re.DOTALL)
    if not m:
        return "", text
    return m.group(0), text[m.end():]


def reflow_chunk(chunk: list) -> list:
    """Reflow a chunk of consecutive non-blank, non-special lines.
    Returns the new list of physical lines for this chunk."""
    groups = []  # list of (is_list_item, [lines])
    current = None
    for line in chunk:
        if is_list_item(line):
            if current is not None:
                groups.append(current)
            current = (True, [line])
        else:
            if current is None:
                current = (False, [line])
            else:
                current[1].append(line)
    if current is not None:
        groups.append(current)

    out_lines = []
    for is_li, lines in groups:
        if is_li:
            m = LIST_ITEM_RE.match(lines[0])
            assert m is not None  # is_list_item already checked
            indent, marker, first_content = m.group(1), m.group(2), m.group(3)
            parts = [first_content.rstrip()]
            for cont in lines[1:]:
                parts.append(cont.strip())
            joined = " ".join(p for p in parts if p)
            joined = re.sub(r" +", " ", joined).strip()
            out_lines.append(f"{indent}{marker}{joined}")
        else:
            joined = " ".join(line.strip() for line in lines)
            joined = re.sub(r" +", " ", joined).strip()
            out_lines.append(joined)
    return out_lines


def reflow_body(body: str) -> str:
    lines = body.split("\n")
    # Track trailing-newline behavior so we can preserve it.
    trailing_empty = body.endswith("\n")
    if trailing_empty:
        lines = lines[:-1]  # drop the empty string from terminal '\n'

    out = []
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        if is_blank(line):
            out.append(line)
            i += 1
            continue
        if is_code_fence(line):
            marker = code_fence_marker(line)
            out.append(line)
            i += 1
            while i < n and not lines[i].lstrip().startswith(marker):
                out.append(lines[i])
                i += 1
            if i < n:
                out.append(lines[i])
                i += 1
            continue
        if is_heading(line) or is_hr(line):
            out.append(line)
            i += 1
            continue
        if is_table_row(line):
            while i < n and is_table_row(lines[i]):
                out.append(lines[i])
                i += 1
            continue
        # General prose / list chunk.
        chunk = [line]
        i += 1
        while i < n:
            cur = lines[i]
            if (is_blank(cur) or is_code_fence(cur) or is_heading(cur)
                    or is_hr(cur) or is_table_row(cur)):
                break
            chunk.append(cur)
            i += 1
        out.extend(reflow_chunk(chunk))

    result = "\n".join(out)
    if trailing_empty:
        result += "\n"
    return result


def reflow(text: str) -> str:
    front, body = split_frontmatter(text)
    return front + reflow_body(body)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true",
                        help="Print which files would change; do not write")
    parser.add_argument("files", nargs="+", help="Markdown files to reflow")
    args = parser.parse_args()
    changed = 0
    for path in args.files:
        with open(path) as f:
            original = f.read()
        new = reflow(original)
        if new == original:
            print(f"unchanged {path}")
            continue
        changed += 1
        if args.dry_run:
            print(f"would reflow {path}")
        else:
            with open(path, "w") as f:
                f.write(new)
            print(f"reflowed {path}")
    suffix = " (dry run)" if args.dry_run else ""
    print(f"total: {changed} file(s){suffix}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
