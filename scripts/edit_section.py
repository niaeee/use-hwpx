#!/usr/bin/env python3
"""Safely edit section0.xml using string-based operations (NO lxml).

lxml parsing destroys footer, tbl, header elements in section0.xml.
This script uses str.replace and re.sub to preserve the original XML structure.

Usage:
    python edit_section.py <unpacked_dir> \
        --replace "HY헤드라인M=보고서 제목" \
        --insert-after "표 제목" --paragraphs section_additions.json

    python edit_section.py <unpacked_dir> \
        --replace-title "AI 활용 업무보고"

    python edit_section.py <unpacked_dir> \
        --add-section-title "추진 배경" --after "메타데이터 라인"
"""

import argparse
import json
import re
import sys
from pathlib import Path

# Correct codepoint for report section symbol (Supplementary PUA-B)
# U+F03DA (4-byte UTF-8: F3 B0 8F 9A)
# NEVER use \\uF3DA (U+F3DA, BMP PUA, 3-byte) - it's a DIFFERENT character!
SECTION_SYMBOL = "\U000F03DA"  # 󰏚

# Type aliases for intuitive naming in bulk-insert / --paragraphs JSON
TYPE_ALIASES = {"detail": "sub", "item": "body", "remark": "note"}
KNOWN_TYPES = {"section_title", "body", "sub", "note", "blank"}


def _resolve_type(raw_type: str, index: int = -1) -> str:
    """Resolve type aliases and warn on unknown types."""
    resolved = TYPE_ALIASES.get(raw_type, raw_type)
    if resolved not in KNOWN_TYPES:
        loc = f" at paragraphs[{index}]" if index >= 0 else ""
        print(
            f"WARNING: Unknown type '{raw_type}'{loc}, falling back to default style",
            file=sys.stderr,
        )
    return resolved


def read_section(unpacked_dir: Path) -> str:
    """Read section0.xml as raw string."""
    section_path = unpacked_dir / "Contents" / "section0.xml"
    if not section_path.is_file():
        raise SystemExit(f"ERROR: section0.xml not found: {section_path}")
    return section_path.read_text(encoding="utf-8")


def write_section(unpacked_dir: Path, content: str) -> None:
    """Write section0.xml back."""
    section_path = unpacked_dir / "Contents" / "section0.xml"
    section_path.write_text(content, encoding="utf-8")


def replace_text(content: str, replacements: dict[str, str]) -> tuple[str, list[str]]:
    """Replace text in section0.xml including inside drawText elements.

    This replaces ALL occurrences of the old text with the new text,
    whether in normal <hp:t> tags or inside drawText <hp:t> tags.

    Returns (modified_content, list_of_replaced_keys).
    """
    replaced = []
    for old_text, new_text in replacements.items():
        if old_text in content:
            content = content.replace(old_text, new_text)
            replaced.append(old_text)
    return content, replaced


def replace_placeholders(content: str, replacements: dict[str, str]) -> tuple[str, list[str]]:
    """Replace {{KEY}} placeholders in section0.xml (including drawText).

    Returns (modified_content, list_of_replaced_keys).
    """
    replaced = []
    for key, value in replacements.items():
        placeholder = "{{" + key + "}}"
        if placeholder in content:
            content = content.replace(placeholder, value)
            replaced.append(key)

    not_found = set(replacements.keys()) - set(replaced)
    if not_found:
        print(
            f"WARNING: Placeholders not found: "
            f"{', '.join('{{' + k + '}}' for k in sorted(not_found))}",
            file=sys.stderr,
        )
    return content, replaced


def replace_drawtext_title(content: str, new_title: str) -> str:
    """Replace the title text inside drawText (report template).

    The report template has a drawText with "HY헤드라인M" as placeholder title.
    This replaces it with the actual report title.
    """
    # Find drawText block and replace the text inside <hp:t>...</hp:t>
    pattern = r'(<hp:drawText[^>]*>.*?<hp:t>)(.*?)(</hp:t>.*?</hp:drawText>)'
    m = re.search(pattern, content, re.DOTALL)
    if m:
        old_title = m.group(2)
        content = content[:m.start(2)] + new_title + content[m.end(2):]
        print(f"  Replaced drawText title: '{old_title}' -> '{new_title}'", file=sys.stderr)
    else:
        print("WARNING: drawText title not found in section0.xml", file=sys.stderr)
    return content


def make_paragraph_xml(
    text: str,
    para_pr_id: int = 0,
    char_pr_id: int = 0,
    style_id: int = 0,
    para_id: str = "2147483648",
) -> str:
    """Generate a simple paragraph XML string."""
    if text:
        run = f'<hp:run charPrIDRef="{char_pr_id}"><hp:t>{_escape_xml(text)}</hp:t></hp:run>'
    else:
        run = f'<hp:run charPrIDRef="{char_pr_id}"><hp:t/></hp:run>'

    return (
        f'<hp:p id="{para_id}" paraPrIDRef="{para_pr_id}" styleIDRef="{style_id}" '
        f'pageBreak="0" columnBreak="0" merged="0">{run}</hp:p>'
    )


def make_blank_line(para_id: str = "2147483648") -> str:
    """Generate a blank line paragraph."""
    return make_paragraph_xml("", para_id=para_id)


def make_section_title(
    title: str,
    symbol_char_pr: int = 7,
    title_char_pr: int = 8,
    para_pr: int = 16,
    para_id: str = "2147483648",
) -> str:
    """Generate a section title paragraph with the correct section symbol.

    Uses U+F03DA (SECTION_SYMBOL), NOT U+F3DA.
    """
    return (
        f'<hp:p id="{para_id}" paraPrIDRef="{para_pr}" styleIDRef="0" '
        f'pageBreak="0" columnBreak="0" merged="0">'
        f'<hp:run charPrIDRef="{symbol_char_pr}">'
        f'<hp:t>{SECTION_SYMBOL}</hp:t></hp:run>'
        f'<hp:run charPrIDRef="{title_char_pr}">'
        f'<hp:t> {_escape_xml(title)}</hp:t></hp:run></hp:p>'
    )


def make_body_paragraph(
    text: str,
    bullet: str = "❍",
    char_pr: int = 9,
    para_pr: int = 17,
    indent: str = "  ",
    para_id: str = "2147483648",
) -> str:
    """Generate a body paragraph with bullet (report template style)."""
    return make_paragraph_xml(
        f"{indent}{bullet} {text}",
        para_pr_id=para_pr,
        char_pr_id=char_pr,
        para_id=para_id,
    )


def make_sub_paragraph(
    text: str,
    char_pr: int = 9,
    para_pr: int = 17,
    para_id: str = "2147483648",
) -> str:
    """Generate a sub-item paragraph with dash (report template style)."""
    return make_paragraph_xml(
        f"    - {text}",
        para_pr_id=para_pr,
        char_pr_id=char_pr,
        para_id=para_id,
    )


def make_note_paragraph(
    text: str,
    char_pr: int = 10,
    para_pr: int = 17,
    para_id: str = "2147483648",
) -> str:
    """Generate a note paragraph with ※ (report template style)."""
    return make_paragraph_xml(
        f"      ※ {text}",
        para_pr_id=para_pr,
        char_pr_id=char_pr,
        para_id=para_id,
    )


# Nested context tags: anchor search skips matches inside these
_NESTED_OPEN_CLOSE = [
    ("<hp:tbl ", "</hp:tbl>"),
    ("<hp:footer ", "</hp:footer>"),
    ("<hp:header ", "</hp:header>"),
    ("<hp:drawText ", "</hp:drawText>"),
]


def _is_inside_nested(content: str, pos: int) -> bool:
    """Check if position is inside a nested context (table, footer, header, drawText)."""
    before = content[:pos]
    for open_tag, close_tag in _NESTED_OPEN_CLOSE:
        if before.count(open_tag) > before.count(close_tag):
            return True
    return False


def _find_anchor_outside_table(content: str, anchor_text: str, nth: int = 1) -> int:
    """Find nth occurrence of anchor_text NOT inside nested contexts.

    Args:
        nth: 1-based index. If multiple matches exist and nth=1, warns about ambiguity.

    Returns the position, or -1 if not found.
    """
    matches = []
    start = 0
    while True:
        pos = content.find(anchor_text, start)
        if pos == -1:
            break
        if not _is_inside_nested(content, pos):
            matches.append(pos)
        start = pos + len(anchor_text)

    if not matches:
        return -1
    if len(matches) > 1 and nth == 1:
        print(
            f"WARNING: '{anchor_text}' found {len(matches)} times outside nested contexts. "
            f"Use --after-nth N to specify. Using 1st match.",
            file=sys.stderr,
        )
    if nth > len(matches):
        print(f"WARNING: nth={nth} but only {len(matches)} match(es) found", file=sys.stderr)
        return -1
    return matches[nth - 1]


def _find_toplevel_p_blocks(content: str) -> list[tuple[int, int]]:
    """Find (start, end) of each top-level <hp:p>...</hp:p> block.

    Top-level = depth-1 <hp:p> (direct child of <hs:sec>).
    Returns list of (start_pos, end_pos) where end_pos points after </hp:p>.
    """
    blocks = []
    p_depth = 0
    block_start = -1
    pos = 0
    n = len(content)
    while pos < n:
        idx = content.find("<", pos)
        if idx == -1:
            break
        if content[idx:idx + 7] == "</hp:p>":
            p_depth -= 1
            if p_depth == 0 and block_start >= 0:
                blocks.append((block_start, idx + 7))
                block_start = -1
            pos = idx + 7
        elif content[idx:idx + 5] == "<hp:p" and idx + 5 < n and content[idx + 5] in (' ', '>'):
            p_depth += 1
            if p_depth == 1:
                block_start = idx
            pos = idx + 5
        else:
            pos = idx + 1
    return blocks


def insert_after_anchor(content: str, anchor_text: str, new_xml: str, nth: int = 1) -> str:
    """Insert new XML after the top-level <hp:p> containing anchor_text.

    Uses depth-aware parsing to find the correct top-level </hp:p> closure,
    even when anchor is inside nested structures (footer, subList, etc.).
    """
    anchor_pos = _find_anchor_outside_table(content, anchor_text, nth=nth)
    if anchor_pos == -1:
        print(f"WARNING: Anchor text '{anchor_text}' not found (outside nested contexts)", file=sys.stderr)
        return content

    for start, end in _find_toplevel_p_blocks(content):
        if start <= anchor_pos < end:
            content = content[:end] + new_xml + content[end:]
            print(f"  Inserted content after anchor '{anchor_text}'", file=sys.stderr)
            return content

    # Fallback: nearest </hp:p>
    close_pos = content.find("</hp:p>", anchor_pos)
    if close_pos == -1:
        print(f"WARNING: No closing </hp:p> found after anchor", file=sys.stderr)
        return content
    insert_pos = close_pos + len("</hp:p>")
    content = content[:insert_pos] + new_xml + content[insert_pos:]
    print(f"  Inserted content after anchor '{anchor_text}' (fallback)", file=sys.stderr)
    return content


def insert_before_anchor(content: str, anchor_text: str, new_xml: str, nth: int = 1) -> str:
    """Insert new XML before the top-level <hp:p> containing anchor_text."""
    anchor_pos = _find_anchor_outside_table(content, anchor_text, nth=nth)
    if anchor_pos == -1:
        print(f"WARNING: Anchor text '{anchor_text}' not found (outside nested contexts)", file=sys.stderr)
        return content

    for start, end in _find_toplevel_p_blocks(content):
        if start <= anchor_pos < end:
            content = content[:start] + new_xml + content[start:]
            print(f"  Inserted content before anchor '{anchor_text}'", file=sys.stderr)
            return content

    # Fallback: nearest <hp:p
    search_area = content[:anchor_pos]
    open_pos = search_area.rfind("<hp:p ")
    if open_pos == -1:
        print(f"WARNING: No opening <hp:p> found before anchor", file=sys.stderr)
        return content
    content = content[:open_pos] + new_xml + content[open_pos:]
    print(f"  Inserted content before anchor '{anchor_text}' (fallback)", file=sys.stderr)
    return content


def insert_before_closing_sec(content: str, new_xml: str) -> str:
    """Insert new XML before the closing </hs:sec> tag."""
    close_tag = "</hs:sec>"
    pos = content.rfind(close_tag)
    if pos == -1:
        print("WARNING: </hs:sec> not found", file=sys.stderr)
        return content

    content = content[:pos] + new_xml + content[pos:]
    return content


def _build_paragraphs_xml(para_list: list[dict]) -> str:
    """Build combined XML from a list of paragraph dicts (shared by bulk-insert and --paragraphs)."""
    xml = ""
    for i, p in enumerate(para_list):
        pt = _resolve_type(p.get("type", "text"), i)
        txt = p.get("text", "")
        if pt in ("section_title", "body", "sub", "note") and not txt:
            print(f"WARNING: paragraphs[{i}] type='{pt}' has no text, skipping", file=sys.stderr)
            continue
        if pt == "section_title":
            xml += make_section_title(txt)
        elif pt == "body":
            xml += make_body_paragraph(txt)
        elif pt == "sub":
            xml += make_sub_paragraph(txt)
        elif pt == "note":
            xml += make_note_paragraph(txt)
        elif pt == "blank":
            xml += make_blank_line()
        else:
            xml += make_paragraph_xml(
                txt,
                para_pr_id=p.get("paraPrIDRef", 0),
                char_pr_id=p.get("charPrIDRef", 0),
            )
    return xml


def _escape_xml(text: str) -> str:
    """Escape XML special characters."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Safely edit section0.xml using string operations (NO lxml)"
    )
    parser.add_argument("unpacked_dir", type=Path, help="Unpacked HWPX directory")
    parser.add_argument(
        "--replace", "-r", action="append", metavar="OLD=NEW",
        help="Replace text (including drawText). Repeatable.",
    )
    parser.add_argument(
        "--replace-placeholder", "-p", action="append", metavar="KEY=VALUE",
        help="Replace {{KEY}} placeholder. Repeatable.",
    )
    parser.add_argument(
        "--replace-title", metavar="TEXT",
        help="Replace drawText title (report template)",
    )
    parser.add_argument(
        "--insert-after", metavar="ANCHOR",
        help="Anchor text after which to insert paragraphs",
    )
    parser.add_argument(
        "--insert-before", metavar="ANCHOR",
        help="Anchor text before which to insert paragraphs",
    )
    parser.add_argument(
        "--paragraphs", type=Path, metavar="JSON_FILE",
        help="JSON file with paragraphs to insert",
    )
    parser.add_argument(
        "--add-section-title", metavar="TITLE",
        help="Add a section title paragraph (with correct section symbol)",
    )
    parser.add_argument(
        "--add-body", metavar="TEXT",
        help="Add a body paragraph with ❍ bullet",
    )
    parser.add_argument(
        "--add-sub", metavar="TEXT",
        help="Add a sub-item paragraph with - bullet",
    )
    parser.add_argument(
        "--add-note", metavar="TEXT",
        help="Add a note paragraph with ※",
    )
    parser.add_argument(
        "--after", metavar="ANCHOR",
        help="Anchor for --add-section-title/--add-body/--add-sub/--add-note",
    )
    parser.add_argument(
        "--after-nth", type=int, default=1, metavar="N",
        help="Use Nth match of anchor (1-based, default=1)",
    )
    parser.add_argument(
        "--bulk-insert", type=Path, metavar="JSON_FILE",
        help='JSON with {"insert_after": "anchor", "paragraphs": [...]}',
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Preview changes without writing to file",
    )
    args = parser.parse_args()

    content = read_section(args.unpacked_dir)

    # 1. Text replacements (including drawText)
    if args.replace:
        replacements = {}
        for item in args.replace:
            if "=" not in item:
                raise SystemExit(f"ERROR: Invalid --replace format: '{item}' (expected OLD=NEW)")
            old, new = item.split("=", 1)
            replacements[old] = new
        content, replaced = replace_text(content, replacements)
        if replaced:
            print(f"  Replaced {len(replaced)} text(s): {', '.join(replaced)}", file=sys.stderr)

    # 2. Placeholder replacements
    if args.replace_placeholder:
        replacements = {}
        for item in args.replace_placeholder:
            if "=" not in item:
                raise SystemExit(f"ERROR: Invalid format: '{item}' (expected KEY=VALUE)")
            key, value = item.split("=", 1)
            replacements[key.strip()] = value
        content, replaced = replace_placeholders(content, replacements)
        if replaced:
            print(f"  Replaced {len(replaced)} placeholder(s)", file=sys.stderr)

    # 3. Replace drawText title
    if args.replace_title:
        content = replace_drawtext_title(content, args.replace_title)

    # 3.5. Bulk insert sections from JSON (one-shot, avoids anchor collision)
    if args.bulk_insert:
        bulk = json.loads(args.bulk_insert.read_text(encoding="utf-8"))
        b_anchor = bulk.get("insert_after", "")
        paras = bulk.get("paragraphs", [])
        new_xml = _build_paragraphs_xml(paras)
        if b_anchor and new_xml:
            content = insert_after_anchor(content, b_anchor, new_xml, nth=args.after_nth)
            print(f"  Bulk-inserted {len(paras)} paragraph(s) after '{b_anchor}'", file=sys.stderr)
        elif new_xml:
            content = insert_before_closing_sec(content, new_xml)
            print(f"  Bulk-inserted {len(paras)} paragraph(s) before </hs:sec>", file=sys.stderr)

    # 4. Insert paragraphs from JSON
    if args.paragraphs:
        if not args.insert_after and not args.insert_before:
            raise SystemExit("ERROR: --paragraphs requires --insert-after or --insert-before")

        para_data = json.loads(args.paragraphs.read_text(encoding="utf-8"))
        new_xml = _build_paragraphs_xml(para_data)

        if args.insert_after:
            content = insert_after_anchor(content, args.insert_after, new_xml, nth=args.after_nth)
        elif args.insert_before:
            content = insert_before_anchor(content, args.insert_before, new_xml, nth=args.after_nth)

    # 5. Quick-add single paragraphs
    anchor = args.after
    nth = args.after_nth
    if args.add_section_title:
        xml = make_section_title(args.add_section_title)
        if anchor:
            content = insert_after_anchor(content, anchor, xml, nth=nth)
        else:
            content = insert_before_closing_sec(content, xml)

    if args.add_body:
        xml = make_body_paragraph(args.add_body)
        if anchor:
            content = insert_after_anchor(content, anchor, xml, nth=nth)
        else:
            content = insert_before_closing_sec(content, xml)

    if args.add_sub:
        xml = make_sub_paragraph(args.add_sub)
        if anchor:
            content = insert_after_anchor(content, anchor, xml, nth=nth)
        else:
            content = insert_before_closing_sec(content, xml)

    if args.add_note:
        xml = make_note_paragraph(args.add_note)
        if anchor:
            content = insert_after_anchor(content, anchor, xml, nth=nth)
        else:
            content = insert_before_closing_sec(content, xml)

    if args.dry_run:
        original = read_section(args.unpacked_dir)
        if content == original:
            print("DRY-RUN: No changes detected", file=sys.stderr)
        else:
            diff_bytes = len(content.encode("utf-8")) - len(original.encode("utf-8"))
            print(f"DRY-RUN: +{diff_bytes} bytes would be written (file NOT modified)", file=sys.stderr)
    else:
        write_section(args.unpacked_dir, content)
        print("OK: section0.xml updated", file=sys.stderr)


if __name__ == "__main__":
    main()
