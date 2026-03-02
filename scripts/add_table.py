#!/usr/bin/env python3
"""Safely insert HWPX tables into section0.xml using string-based editing.

Generates table XML from JSON data and inserts it into section0.xml.
Automatically adds required styles (charPr/paraPr/borderFill/font) to header.xml
via add_style.py.

Table formatting follows government document standards:
  - Font: 맑은 고딕 10pt, 자간 -5%
  - Cell margins: 1.5mm left/right, 0.5mm top/bottom
  - Outer border: 0.4mm thick
  - Inner borders: 0.12mm thin
  - Header bottom: 0.4mm thick (emphasis)
  - Header background: #DCDCDC (연회색)
  - Line spacing: 130%

Usage:
    python add_table.py <unpacked_dir> \
        --data table_data.json \
        --insert-after "표 제목 텍스트" \
        --font "맑은 고딕" --font-size 10 \
        --header-bg "#DCDCDC"

table_data.json format:
{
    "columns": ["분류", "항목", "2024년", "2025년", "2026년"],
    "col_widths": [4819, 8674, 11566, 12529, 10602],
    "rows": [
        {"data": ["교수학습", "우리아이(AI)", "개발착수", "정식운영", "전교운영"], "category_span": 3},
        {"data": ["", "미래교사단", "101명선발", "콘텐츠개발", "고도화"]},
        ...
    ],
    "header_align": "CENTER",
    "category_align": "CENTER",
    "item_align": "CENTER",
    "content_align": "LEFT"
}
"""

import argparse
import json
import sys
from pathlib import Path

# Import add_style for header.xml modifications
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from add_style import add_table_styles  # noqa: E402

# Template body widths
BODY_WIDTH = {
    "report": 48190,
    "gonmun": 42520,
    "minutes": 42520,
    "draft": 42520,
}

# Cell margins in HWPUNIT (government standard)
# 1.5mm = 425 HWPUNIT (1mm ≈ 283.5 HWPUNIT)
# 0.5mm = 142 HWPUNIT
CELL_MARGIN_LR = 425   # left/right 1.5mm
CELL_MARGIN_TB = 142    # top/bottom 0.5mm

# Cell height: 10~12mm → 2835~3402 HWPUNIT (use 2835 as minimum)
CELL_HEIGHT = 2835


def _escape_xml(text: str) -> str:
    """Escape XML special characters."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def generate_table_xml(
    table_data: dict,
    style_ids: dict,
    body_width: int = 48190,
    table_id: str = "1430511950",
) -> str:
    """Generate HWPX table XML from structured data.

    Args:
        table_data: Dict with columns, rows, col_widths, alignment settings
        style_ids: Dict from add_table_styles() with charpr/parapr/borderfill IDs
        body_width: Total table width in HWPUNIT
        table_id: Unique ID for the table element

    Returns:
        Complete table XML wrapped in a paragraph
    """
    columns = table_data["columns"]
    rows = table_data["rows"]
    col_count = len(columns)
    total_rows = len(rows) + 1  # +1 for header row

    # Column widths
    col_widths = table_data.get("col_widths")
    if not col_widths:
        base_w = body_width // col_count
        col_widths = [base_w] * col_count
        col_widths[-1] = body_width - base_w * (col_count - 1)

    # Alignment settings
    header_align = table_data.get("header_align", "CENTER")
    category_align = table_data.get("category_align", "CENTER")
    item_align = table_data.get("item_align", "CENTER")
    content_align = table_data.get("content_align", "LEFT")

    # Style IDs
    cp_bold = style_ids["charpr_bold"]
    cp_normal = style_ids["charpr_normal"]
    pp_left = style_ids["parapr_left"]
    pp_center = style_ids["parapr_center"]
    pp_right = style_ids.get("parapr_right", pp_left)

    # Position-aware borderFill maps
    bf_map_header = style_ids["bf_map_header"]
    bf_map_body = style_ids["bf_map_body"]

    def _get_parapr(align: str) -> int:
        if align == "CENTER":
            return pp_center
        elif align == "RIGHT":
            return pp_right
        return pp_left

    # Track rowSpan state
    rowspan_remaining = [0] * col_count

    def make_cell(
        text: str,
        col: int,
        row: int,
        width: int,
        is_header: bool = False,
        is_category: bool = False,
        is_item: bool = False,
        row_span: int = 1,
    ) -> str:
        # Position-aware borderFill
        if is_header:
            bf = bf_map_header.get((0, col), bf_map_header.get((0, 0)))
        else:
            bf = bf_map_body.get((row, col), bf_map_body.get((1, 0)))

        if is_header:
            cp = cp_bold
            pp = _get_parapr(header_align)
        elif is_category:
            cp = cp_normal
            pp = _get_parapr(category_align)
        elif is_item:
            cp = cp_normal
            pp = _get_parapr(item_align)
        else:
            stripped = text.strip().replace(",", "").replace(".", "").replace("-", "").replace("%", "")
            if stripped.isdigit() and content_align == "LEFT":
                pp = pp_right
            else:
                pp = _get_parapr(content_align)
            cp = cp_normal

        escaped = _escape_xml(text)
        text_run = (
            f'<hp:run charPrIDRef="{cp}"><hp:t>{escaped}</hp:t></hp:run>'
            if text
            else f'<hp:run charPrIDRef="{cp}"><hp:t/></hp:run>'
        )

        header_attr = '1' if is_header else '0'
        return (
            f'<hp:tc name="" header="{header_attr}" hasMargin="0" protect="0" '
            f'editable="0" dirty="0" borderFillIDRef="{bf}">'
            f'<hp:subList id="" textDirection="HORIZONTAL" lineWrap="BREAK" '
            f'vertAlign="CENTER" linkListIDRef="0" linkListNextIDRef="0" '
            f'textWidth="0" textHeight="0" hasTextRef="0" hasNumRef="0">'
            f'<hp:p id="2147483648" paraPrIDRef="{pp}" styleIDRef="0" '
            f'pageBreak="0" columnBreak="0" merged="0">{text_run}</hp:p>'
            f'</hp:subList>'
            f'<hp:cellAddr colAddr="{col}" rowAddr="{row}"/>'
            f'<hp:cellSpan colSpan="1" rowSpan="{row_span}"/>'
            f'<hp:cellSz width="{width}" height="{CELL_HEIGHT}"/>'
            f'<hp:cellMargin left="{CELL_MARGIN_LR}" right="{CELL_MARGIN_LR}" '
            f'top="{CELL_MARGIN_TB}" bottom="{CELL_MARGIN_TB}"/>'
            f'</hp:tc>'
        )

    # Build table XML
    # Use the first body bf as default table borderFill (outer frame)
    default_bf = bf_map_body.get((1, 0), list(bf_map_body.values())[0] if bf_map_body else 3)

    table_xml = (
        f'<hp:tbl id="{table_id}" zOrder="0" numberingType="TABLE" '
        f'textWrap="TOP_AND_BOTTOM" textFlow="BOTH_SIDES" lock="0" '
        f'dropcapstyle="None" pageBreak="CELL" repeatHeader="1" '
        f'rowCnt="{total_rows}" colCnt="{col_count}" cellSpacing="0" '
        f'borderFillIDRef="{default_bf}" noAdjust="0">'
        f'<hp:sz width="{body_width}" widthRelTo="ABSOLUTE" '
        f'height="{CELL_HEIGHT}" heightRelTo="ABSOLUTE" protect="0"/>'
        f'<hp:pos treatAsChar="1" affectLSpacing="0" flowWithText="1" '
        f'allowOverlap="0" holdAnchorAndSO="0" vertRelTo="PARA" '
        f'horzRelTo="PARA" vertAlign="TOP" horzAlign="LEFT" '
        f'vertOffset="0" horzOffset="0"/>'
        f'<hp:outMargin left="0" right="0" top="283" bottom="283"/>'
        f'<hp:inMargin left="0" right="0" top="{CELL_MARGIN_TB}" bottom="{CELL_MARGIN_TB}"/>'
    )

    # Header row
    table_xml += "<hp:tr>"
    for c, col_name in enumerate(columns):
        table_xml += make_cell(col_name, c, 0, col_widths[c], is_header=True)
    table_xml += "</hp:tr>"

    # Data rows
    rowspan_remaining = [0] * col_count

    for r_idx, row_data in enumerate(rows):
        row_num = r_idx + 1
        data = row_data["data"]
        category_span = row_data.get("category_span", 0)

        table_xml += "<hp:tr>"

        for c in range(col_count):
            if rowspan_remaining[c] > 0:
                rowspan_remaining[c] -= 1
                continue

            cell_text = data[c] if c < len(data) else ""
            is_category = (c == 0 and col_count > 2)
            is_item = (c == 1 and col_count > 2)

            rs = 1
            if c == 0 and category_span > 1:
                rs = category_span
                rowspan_remaining[c] = category_span - 1

            table_xml += make_cell(
                cell_text, c, row_num, col_widths[c],
                is_category=is_category,
                is_item=is_item,
                row_span=rs,
            )

        table_xml += "</hp:tr>"

    table_xml += "</hp:tbl>"

    # Wrap in a paragraph
    para_xml = (
        f'<hp:p id="2147483648" paraPrIDRef="{pp_left}" styleIDRef="0" '
        f'pageBreak="0" columnBreak="0" merged="0">'
        f'<hp:run charPrIDRef="{cp_normal}">{table_xml}<hp:t/></hp:run></hp:p>'
    )

    return para_xml


def insert_table(
    unpacked_dir: Path,
    table_data: dict,
    insert_after: str | None = None,
    insert_before_sec_end: bool = False,
    font_name: str = "맑은 고딕",
    font_size: int = 1000,
    header_bg: str = "#DCDCDC",
    body_width: int = 48190,
    spacing: int = -5,
) -> dict:
    """Insert a table into section0.xml with automatic style management.

    Args:
        unpacked_dir: Path to unpacked HWPX directory
        table_data: Table data dict (columns, rows, etc.)
        insert_after: Anchor text to insert table after
        insert_before_sec_end: If True, insert before </hs:sec>
        font_name: Font name (default: "맑은 고딕")
        font_size: Font size in HWPUNIT (1000 = 10pt)
        header_bg: Header background color (default: "#DCDCDC")
        body_width: Table width in HWPUNIT
        spacing: 자간 in % (default: -5)

    Returns:
        Dict with style IDs used
    """
    columns = table_data["columns"]
    total_rows = len(table_data["rows"]) + 1
    total_cols = len(columns)

    # 1. Add styles to header.xml
    header_path = unpacked_dir / "Contents" / "header.xml"
    header_content = header_path.read_text(encoding="utf-8")

    header_content, style_ids = add_table_styles(
        header_content,
        font_name=font_name,
        font_size=font_size,
        header_bg=header_bg,
        spacing=spacing,
        total_rows=total_rows,
        total_cols=total_cols,
    )
    header_path.write_text(header_content, encoding="utf-8")

    # 2. Generate table XML
    table_xml = generate_table_xml(table_data, style_ids, body_width=body_width)

    # 3. Insert into section0.xml (string-based!)
    section_path = unpacked_dir / "Contents" / "section0.xml"
    section_content = section_path.read_text(encoding="utf-8")

    if insert_after:
        anchor_pos = section_content.find(insert_after)
        if anchor_pos == -1:
            print(f"WARNING: Anchor text '{insert_after}' not found", file=sys.stderr)
            close_tag = "</hs:sec>"
            pos = section_content.rfind(close_tag)
            section_content = section_content[:pos] + table_xml + section_content[pos:]
        else:
            close_pos = section_content.find("</hp:p>", anchor_pos)
            if close_pos != -1:
                insert_pos = close_pos + len("</hp:p>")
                section_content = (
                    section_content[:insert_pos] + table_xml + section_content[insert_pos:]
                )
    elif insert_before_sec_end:
        close_tag = "</hs:sec>"
        pos = section_content.rfind(close_tag)
        section_content = section_content[:pos] + table_xml + section_content[pos:]
    else:
        raise SystemExit("ERROR: Specify --insert-after or use --append")

    section_path.write_text(section_content, encoding="utf-8")
    print(
        f"OK: Table inserted ({total_cols} cols x {total_rows} rows, "
        f"font={font_name} {font_size // 100}pt, 자간={spacing}%, "
        f"cell margin={CELL_MARGIN_LR}/{CELL_MARGIN_TB})",
        file=sys.stderr,
    )

    # Return serializable subset
    return {
        k: v for k, v in style_ids.items()
        if isinstance(v, (int, str)) and not k.startswith("bf_")
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Insert HWPX table into section0.xml (string-based, no lxml)"
    )
    parser.add_argument("unpacked_dir", type=Path, help="Unpacked HWPX directory")
    parser.add_argument(
        "--data", type=Path, required=True,
        help="JSON file with table data",
    )
    parser.add_argument(
        "--insert-after", metavar="TEXT",
        help="Anchor text to insert table after",
    )
    parser.add_argument("--font", default="맑은 고딕", help="Font name (default: 맑은 고딕)")
    parser.add_argument("--font-size", type=int, default=10, help="Font size in pt (default: 10)")
    parser.add_argument("--header-bg", default="#DCDCDC", help="Header background color (default: #DCDCDC)")
    parser.add_argument(
        "--body-width", type=int, default=48190,
        help="Table width in HWPUNIT (report=48190, gonmun=42520)",
    )
    parser.add_argument(
        "--append", action="store_true",
        help="Append table before </hs:sec> (if --insert-after not given)",
    )
    args = parser.parse_args()

    if not args.data.is_file():
        raise SystemExit(f"ERROR: Data file not found: {args.data}")

    table_data = json.loads(args.data.read_text(encoding="utf-8"))

    if "columns" not in table_data:
        raise SystemExit("ERROR: table_data must have 'columns'")
    if "rows" not in table_data:
        raise SystemExit("ERROR: table_data must have 'rows'")

    insert_after = args.insert_after
    insert_before_sec_end = args.append and not insert_after

    if not insert_after and not insert_before_sec_end:
        raise SystemExit("ERROR: Specify --insert-after TEXT or --append")

    style_ids = insert_table(
        args.unpacked_dir,
        table_data,
        insert_after=insert_after,
        insert_before_sec_end=insert_before_sec_end,
        font_name=args.font,
        font_size=args.font_size * 100,
        header_bg=args.header_bg,
        body_width=args.body_width,
    )

    print(json.dumps(style_ids, indent=2))


if __name__ == "__main__":
    main()
