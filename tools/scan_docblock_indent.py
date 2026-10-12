#!/usr/bin/env python3
"""Report PHP docblocks indented deeper than the declaration they document.

Tree convention: a docblock shares the indent of the declaration that follows
it. A class-level docblock that sits before the class keyword at column 0 is
correct and is never reported. Statement comments and code are out of scope.

Exit 0 when nothing is deeper. Exit 1 and print ``path:line`` findings otherwise.
"""

from __future__ import annotations

import sys
from pathlib import Path


def indent_tabs(line: str) -> int | None:
    """Leading tab count, or None when the line is indented with spaces."""
    stripped = line.lstrip("\t")
    if stripped[:1] == " ":
        return None
    return len(line) - len(stripped)


def is_class_keyword(line: str) -> bool:
    head = line.lstrip("\t").split(" ", 2)[0] if line.strip() else ""
    return head in {"class", "interface", "trait", "enum"} or line.lstrip("\t").startswith(
        ("final class ", "abstract class ", "readonly class ")
    )


def scan(path: Path) -> list[str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    findings: list[str] = []
    index = 0
    total = len(lines)
    while index < total:
        body = lines[index].lstrip("\t")
        if not body.startswith("/**"):
            index += 1
            continue
        start = index
        doc_indent = indent_tabs(lines[index])
        while index < total and "*/" not in lines[index]:
            index += 1
        if index >= total:
            break
        end = index
        cursor = end + 1
        while cursor < total and lines[cursor].strip() == "":
            cursor += 1
        if cursor >= total or doc_indent is None:
            index = end + 1
            continue
        declaration = lines[cursor]
        decl_indent = indent_tabs(declaration)
        # A class-level docblock before `class` stays at column 0.
        if is_class_keyword(declaration) and doc_indent == 0:
            index = end + 1
            continue
        if decl_indent is not None and doc_indent > decl_indent:
            findings.append(
                f"{path}:{start + 1}: docblock indent {doc_indent} > declaration indent {decl_indent} ({declaration.strip()[:72]})"
            )
        index = end + 1
    return findings


def roots(argv: list[str]) -> list[Path]:
    if argv:
        return [Path(item) for item in argv]
    return [Path("plugins"), Path("mu-plugins"), Path("tools")]


def main(argv: list[str]) -> int:
    findings: list[str] = []
    for root in roots(argv):
        if root.is_file():
            paths = [root]
        else:
            paths = sorted(root.rglob("*.php"))
        for path in paths:
            text = str(path)
            if "/vendor/" in text or "/node_modules/" in text:
                continue
            findings.extend(scan(path))
    if findings:
        print("\n".join(findings))
        print(f"{len(findings)} docblock(s) deeper than their declaration", file=sys.stderr)
        return 1
    print("docblock indent: 0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
