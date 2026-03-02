#!/usr/bin/env python3
"""Extract text from an HWPX document using lxml.

No external dependencies beyond lxml — the hwpx package is NOT required.

Usage:
    python text_extract.py document.hwpx
    python text_extract.py document.hwpx --format markdown
    python text_extract.py document.hwpx --include-tables
"""

import argparse
import re
import sys
from pathlib import Path
from zipfile import BadZipFile, ZipFile

try:
    from lxml import etree
except ImportError:
    import subprocess

    print("lxml not found. Installing...", file=sys.stderr)
    subprocess.check_call(
        [sys.executable, "-m", "pip", "install", "lxml", "-q"],
    )
    from lxml import etree

NS = {
    "hp": "http://www.hancom.co.kr/hwpml/2011/paragraph",
    "hs": "http://www.hancom.co.kr/hwpml/2011/section",
}


def _get_run_text(run) -> str:
    """Extract concatenated text from all <hp:t> elements in a run."""
    parts = []
    for t in run.findall("hp:t", NS):
        if t.text:
            parts.append(t.text)
    return "".join(parts)


def _extract_para_text(p) -> str:
    """Extract full text from a paragraph, concatenating all runs."""
    parts = []
    for run in p.findall("hp:run", NS):
        txt = _get_run_text(run)
        if txt:
            parts.append(txt)
    return "".join(parts)


def _extract_table_texts(tbl) -> list[list[str]]:
    """Extract text from a table. Returns list of rows, each row a list of cell texts."""
    rows = []
    for tr in tbl.findall("hp:tr", NS):
        row = []
        for tc in tr.findall("hp:tc", NS):
            cell_parts = []
            sublist = tc.find("hp:subList", NS)
            if sublist is not None:
                for p in sublist.findall("hp:p", NS):
                    txt = _extract_para_text(p)
                    if txt.strip():
                        cell_parts.append(txt.strip())
            row.append(" ".join(cell_parts))
        rows.append(row)
    return rows


def _walk_paragraphs(section_root, *, include_tables: bool = False):
    """Yield (text, is_table_cell) tuples from a section."""
    sec = section_root.find(".//hs:sec", NS)
    if sec is None:
        sec = section_root

    for p in sec.findall("hp:p", NS):
        has_table = False
        for run in p.findall("hp:run", NS):
            tbl = run.find("hp:tbl", NS)
            if tbl is not None:
                has_table = True
                if include_tables:
                    for row in _extract_table_texts(tbl):
                        for cell_text in row:
                            if cell_text.strip():
                                yield (cell_text.strip(), True)

        txt = _extract_para_text(p)
        if txt.strip():
            yield (txt, False)


def _find_sections(zf: ZipFile) -> list[str]:
    """Find and sort section XML files in the archive."""
    return sorted(
        n for n in zf.namelist()
        if re.match(r"Contents/section\d+\.xml$", n)
    )


def extract_plain(hwpx_path: str, *, include_tables: bool = False) -> str:
    """Extract plain text from HWPX file."""
    lines: list[str] = []

    with ZipFile(hwpx_path, "r") as zf:
        section_files = _find_sections(zf)
        if not section_files:
            print(
                f"ERROR: Contents/section0.xml not found in '{hwpx_path}'",
                file=sys.stderr,
            )
            print(
                "  HWPX files must contain at least Contents/section0.xml",
                file=sys.stderr,
            )
            sys.exit(1)

        for sf in section_files:
            root = etree.fromstring(zf.read(sf))
            for text, _is_cell in _walk_paragraphs(
                root, include_tables=include_tables
            ):
                lines.append(text)

    return "\n".join(lines)


def extract_markdown(hwpx_path: str) -> str:
    """Extract text as Markdown with section separators."""
    sections_output: list[str] = []

    with ZipFile(hwpx_path, "r") as zf:
        section_files = _find_sections(zf)
        if not section_files:
            print(
                f"ERROR: Contents/section0.xml not found in '{hwpx_path}'",
                file=sys.stderr,
            )
            print(
                "  HWPX files must contain at least Contents/section0.xml",
                file=sys.stderr,
            )
            sys.exit(1)

        for sf in section_files:
            root = etree.fromstring(zf.read(sf))
            section_lines: list[str] = []
            for text, is_cell in _walk_paragraphs(
                root, include_tables=True
            ):
                if is_cell:
                    section_lines.append(f"  {text}")
                else:
                    section_lines.append(text)
            if section_lines:
                sections_output.append("\n".join(section_lines))

    return "\n\n---\n\n".join(sections_output)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract text from an HWPX document",
    )
    parser.add_argument("input", help="Path to .hwpx file")
    parser.add_argument(
        "--format", "-f",
        choices=["plain", "markdown"],
        default="plain",
        help="Output format (default: plain)",
    )
    parser.add_argument(
        "--include-tables",
        action="store_true",
        help="Include text from tables (plain mode only)",
    )
    parser.add_argument(
        "--output", "-o",
        help="Output file path (default: stdout)",
    )
    args = parser.parse_args()

    path = Path(args.input)
    if not path.is_file():
        print(f"ERROR: File not found: {args.input}", file=sys.stderr)
        print("  Check the file path and try again.", file=sys.stderr)
        sys.exit(1)

    if not path.suffix.lower() == ".hwpx":
        print(
            f"WARNING: '{path.name}' does not have .hwpx extension.",
            file=sys.stderr,
        )
        print(
            "  This tool supports .hwpx only, not .hwp (binary).",
            file=sys.stderr,
        )

    try:
        if args.format == "markdown":
            result = extract_markdown(args.input)
        else:
            result = extract_plain(
                args.input, include_tables=args.include_tables,
            )
    except BadZipFile:
        print(f"ERROR: Not a valid ZIP/HWPX file: {args.input}", file=sys.stderr)
        print("  The file may be corrupted or in .hwp (binary) format.", file=sys.stderr)
        sys.exit(1)

    if args.output:
        Path(args.output).write_text(result, encoding="utf-8")
        print(f"Extracted to: {args.output}", file=sys.stderr)
    else:
        print(result)


if __name__ == "__main__":
    main()
