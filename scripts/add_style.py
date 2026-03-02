#!/usr/bin/env python3
"""Safely add charPr/paraPr/borderFill/font to header.xml using string-based editing.

All modifications are done via string operations (no lxml parsing) to preserve
the original XML structure exactly.

Usage:
    python add_style.py <unpacked_dir> \
        --add-font "맑은 고딕" \
        --add-charpr '{"height": 1000, "font": "맑은 고딕", "bold": false}' \
        --add-parapr '{"align": "LEFT"}' \
        --add-borderfill '{"bg_color": "#DCDCDC"}'
"""

import argparse
import json
import re
import sys
from pathlib import Path

# Validated font names for Hangul (한글 프로그램)
VALID_FONT_NAMES = {
    "맑은 고딕",       # NOT "맑은고딕"
    "함초롬돋움",       # NOT "함초롬 돋움"
    "함초롬바탕",       # NOT "함초롬 바탕"
    "HY헤드라인M",     # NOT "HY 헤드라인M"
    "휴먼명조",         # NOT "휴먼 명조"
    "한양중고딕",
    "양재 소슬",
    "한양신명조",
    "해서 약자",
    "명조",
    "바탕",
    "돋움",
    "굴림",
    "궁서",
    "Arial",
    "Times New Roman",
    "Calibri",
}

FONT_LANGS = ["HANGUL", "LATIN", "HANJA", "JAPANESE", "OTHER", "SYMBOL", "USER"]

# Table border constants (mm)
BORDER_THICK = "0.4 mm"   # 바깥 테두리, 헤더 하단
BORDER_THIN = "0.12 mm"   # 안쪽 구분선


def validate_font_name(name: str) -> None:
    """Warn if font name might be incorrect."""
    common_mistakes = {
        "맑은고딕": "맑은 고딕",
        "함초롬 돋움": "함초롬돋움",
        "함초롬 바탕": "함초롬바탕",
        "HY 헤드라인M": "HY헤드라인M",
        "휴먼 명조": "휴먼명조",
    }
    if name in common_mistakes:
        correct = common_mistakes[name]
        print(
            f"WARNING: Font name '{name}' is likely incorrect. "
            f"Did you mean '{correct}'?",
            file=sys.stderr,
        )


def get_next_id(content: str, tag: str) -> int:
    """Find the maximum existing ID for a tag and return next available ID."""
    ids = [int(m) for m in re.findall(rf'<hh:{tag} id="(\d+)"', content)]
    return max(ids) + 1 if ids else 0


def get_max_font_id(content: str, lang: str) -> int:
    """Find the maximum font ID within a specific language fontface."""
    pattern = rf'<hh:fontface lang="{lang}".*?</hh:fontface>'
    m = re.search(pattern, content, re.DOTALL)
    if not m:
        return -1
    ids = [int(x) for x in re.findall(r'<hh:font id="(\d+)"', m.group())]
    return max(ids) if ids else -1


def add_font(content: str, font_name: str, type_info: str | None = None) -> tuple[str, int]:
    """Add a font to all 7 fontface language categories.

    Returns (modified_content, new_font_id).
    """
    validate_font_name(font_name)

    # Determine font type
    font_type = "TTF"

    # Default typeInfo for common fonts
    if not type_info:
        type_info = (
            '<hh:typeInfo familyType="FCAT_GOTHIC" weight="6" proportion="4" '
            'contrast="0" strokeVariation="1" armStyle="1" letterform="1" '
            'midline="1" xHeight="1"/>'
        )

    # Find the next available font ID (use max across all languages)
    max_id = -1
    for lang in FONT_LANGS:
        lang_max = get_max_font_id(content, lang)
        if lang_max > max_id:
            max_id = lang_max
    new_id = max_id + 1

    font_xml = (
        f'<hh:font id="{new_id}" face="{font_name}" type="{font_type}" '
        f'isEmbedded="0">{type_info}</hh:font>'
    )

    for lang in FONT_LANGS:
        lang_pattern = rf'(<hh:fontface lang="{lang}" fontCnt=")(\d+)(".*?)(</hh:fontface>)'
        m = re.search(lang_pattern, content, re.DOTALL)
        if m:
            old_cnt = int(m.group(2))
            new_cnt = old_cnt + 1
            replacement = (
                f'{m.group(1)}{new_cnt}{m.group(3)}'
                f'{font_xml}{m.group(4)}'
            )
            content = content[:m.start()] + replacement + content[m.end():]

    print(f"  Added font '{font_name}' with id={new_id} to all {len(FONT_LANGS)} fontface categories", file=sys.stderr)
    return content, new_id


def add_charpr(
    content: str,
    height: int = 1000,
    font_id: int = 1,
    text_color: str = "#000000",
    bold: bool = False,
    italic: bool = False,
    border_fill_id: int = 2,
    spacing: int = -5,
    ratio: int = 100,
    rel_sz: int = 100,
) -> tuple[str, int]:
    """Add a new charPr to header.xml. Returns (modified_content, new_charpr_id).

    IMPORTANT: This creates the full charPr XML explicitly.
    Never use regex to copy-and-modify an existing charPr (Anti-pattern #2).

    Defaults: spacing=-5 (자간 -5%), ratio=100 (장평 100%).
    """
    new_id = get_next_id(content, "charPr")

    fi = str(font_id)
    sp = str(spacing)
    ra = str(ratio)
    rs = str(rel_sz)

    bold_xml = '<hh:bold value="1"/>' if bold else ""
    italic_xml = '<hh:italic value="1"/>' if italic else ""

    charpr_xml = (
        f'<hh:charPr id="{new_id}" height="{height}" textColor="{text_color}" '
        f'shadeColor="none" useFontSpace="0" useKerning="0" symMark="NONE" '
        f'borderFillIDRef="{border_fill_id}">'
        f'<hh:fontRef hangul="{fi}" latin="{fi}" hanja="{fi}" japanese="{fi}" '
        f'other="{fi}" symbol="{fi}" user="{fi}"/>'
        f'<hh:ratio hangul="{ra}" latin="{ra}" hanja="{ra}" japanese="{ra}" '
        f'other="{ra}" symbol="{ra}" user="{ra}"/>'
        f'<hh:spacing hangul="{sp}" latin="{sp}" hanja="{sp}" japanese="{sp}" '
        f'other="{sp}" symbol="{sp}" user="{sp}"/>'
        f'<hh:relSz hangul="{rs}" latin="{rs}" hanja="{rs}" japanese="{rs}" '
        f'other="{rs}" symbol="{rs}" user="{rs}"/>'
        f'<hh:offset hangul="0" latin="0" hanja="0" japanese="0" '
        f'other="0" symbol="0" user="0"/>'
        f'{bold_xml}{italic_xml}'
        f'<hh:underline type="NONE" shape="SOLID" color="#000000"/>'
        f'<hh:strikeout shape="NONE" color="#000000"/>'
        f'<hh:outline type="NONE"/>'
        f'<hh:shadow type="NONE" color="#B2B2B2" offsetX="10" offsetY="10"/>'
        f'</hh:charPr>'
    )

    content = content.replace(
        "</hh:charProperties>",
        f"{charpr_xml}</hh:charProperties>",
    )
    content = _update_item_cnt(content, "charProperties", "charPr")

    print(f"  Added charPr id={new_id} (height={height}, font={font_id}, bold={bold}, spacing={spacing})", file=sys.stderr)
    return content, new_id


def add_parapr(
    content: str,
    align: str = "JUSTIFY",
    line_spacing_type: str = "PERCENT",
    line_spacing_value: str = "160",
    margin_left: int = 0,
    margin_right: int = 0,
    indent: int = 0,
) -> tuple[str, int]:
    """Add a new paraPr to header.xml. Returns (modified_content, new_parapr_id)."""
    new_id = get_next_id(content, "paraPr")

    parapr_xml = (
        f'<hh:paraPr id="{new_id}" tabPrIDRef="0" condense="0" fontLineHeight="0" '
        f'snapToGrid="1" suppressLineNumbers="0" checked="0">'
        f'<hh:align horizontal="{align}" vertical="BASELINE"/>'
        f'<hh:heading type="NONE" idRef="0" level="0"/>'
        f'<hh:breakSetting breakLatinWord="KEEP_WORD" breakNonLatinWord="KEEP_WORD" '
        f'widowOrphan="0" keepWithNext="0" keepLines="0" pageBreakBefore="0" lineWrap="BREAK"/>'
        f'<hh:autoSpacing eAsianEng="0" eAsianNum="0"/>'
        f'<hh:margin>'
        f'<hc:intent value="{indent}" unit="HWPUNIT"/>'
        f'<hc:left value="{margin_left}" unit="HWPUNIT"/>'
        f'<hc:right value="{margin_right}" unit="HWPUNIT"/>'
        f'<hc:prev value="0" unit="HWPUNIT"/>'
        f'<hc:next value="0" unit="HWPUNIT"/>'
        f'</hh:margin>'
        f'<hh:lineSpacing type="{line_spacing_type}" value="{line_spacing_value}"/>'
        f'</hh:paraPr>'
    )

    content = content.replace(
        "</hh:paraProperties>",
        f"{parapr_xml}</hh:paraProperties>",
    )
    content = _update_item_cnt(content, "paraProperties", "paraPr")

    print(f"  Added paraPr id={new_id} (align={align}, lineSpacing={line_spacing_value})", file=sys.stderr)
    return content, new_id


def add_borderfill(
    content: str,
    bg_color: str | None = None,
    top_width: str = BORDER_THIN,
    bottom_width: str = BORDER_THIN,
    left_width: str = BORDER_THIN,
    right_width: str = BORDER_THIN,
    border_type: str = "SOLID",
    border_color: str = "#000000",
) -> tuple[str, int]:
    """Add a new borderFill to header.xml with per-side border widths.

    Returns (modified_content, new_borderfill_id).
    """
    new_id = get_next_id(content, "borderFill")

    fill_xml = ""
    if bg_color:
        fill_xml = (
            f'<hc:fillBrush>'
            f'<hc:winBrush faceColor="{bg_color}" hatchColor="#000000" alpha="0"/>'
            f'</hc:fillBrush>'
        )

    bf_xml = (
        f'<hh:borderFill id="{new_id}" threeD="0" shadow="0" centerLine="NONE" '
        f'breakCellSeparateLine="0">'
        f'<hh:slash type="NONE" Crooked="0" isCounter="0"/>'
        f'<hh:backSlash type="NONE" Crooked="0" isCounter="0"/>'
        f'<hh:leftBorder type="{border_type}" width="{left_width}" color="{border_color}"/>'
        f'<hh:rightBorder type="{border_type}" width="{right_width}" color="{border_color}"/>'
        f'<hh:topBorder type="{border_type}" width="{top_width}" color="{border_color}"/>'
        f'<hh:bottomBorder type="{border_type}" width="{bottom_width}" color="{border_color}"/>'
        f'<hh:diagonal type="SOLID" width="0.1 mm" color="#000000"/>'
        f'{fill_xml}'
        f'</hh:borderFill>'
    )

    content = content.replace(
        "</hh:borderFills>",
        f"{bf_xml}</hh:borderFills>",
    )
    content = _update_item_cnt(content, "borderFills", "borderFill")

    desc = f"bg={bg_color}" if bg_color else "no bg"
    sides = f"T={top_width}/B={bottom_width}/L={left_width}/R={right_width}"
    print(f"  Added borderFill id={new_id} ({desc}, {sides})", file=sys.stderr)
    return content, new_id


def _update_item_cnt(content: str, container_tag: str, child_tag: str) -> str:
    """Update the itemCnt attribute of a container to match actual child count."""
    count = len(re.findall(rf'<hh:{child_tag} id="', content))
    content = re.sub(
        rf'(<hh:{container_tag} itemCnt=")(\d+)(")',
        rf'\g<1>{count}\3',
        content,
    )
    return content


def get_cell_border_widths(
    row: int,
    col: int,
    total_rows: int,
    total_cols: int,
    is_header: bool,
) -> tuple[str, str, str, str]:
    """Determine per-side border widths based on cell position.

    Government table standard:
      - 바깥 테두리: 0.4mm (굵게)
      - 안쪽 구분선: 0.12mm (얇게)
      - 헤더 하단: 0.4mm (강조)

    Returns (top_width, bottom_width, left_width, right_width).
    """
    top = BORDER_THICK if row == 0 else BORDER_THIN
    bottom = BORDER_THICK if (row == total_rows - 1 or is_header) else BORDER_THIN
    left = BORDER_THICK if col == 0 else BORDER_THIN
    right = BORDER_THICK if col == total_cols - 1 else BORDER_THIN
    return top, bottom, left, right


def add_table_styles(
    content: str,
    font_name: str = "맑은 고딕",
    font_size: int = 1000,
    header_bg: str = "#DCDCDC",
    spacing: int = -5,
    total_rows: int = 4,
    total_cols: int = 5,
) -> tuple[str, dict]:
    """Add all styles needed for a table.

    Creates font, charPr (normal/bold), paraPr (LEFT/CENTER/RIGHT),
    and position-aware borderFills for proper outer/inner/header borders.

    Args:
        font_size: Default 1000 (10pt). Table text is smaller than body (15pt).
        header_bg: Default "#DCDCDC" (연회색).
        spacing: Default -5 (자간 -5%).
        total_rows: Total table rows (header + data) for border calculation.
        total_cols: Total columns for border calculation.

    Returns (modified_content, style_ids).
    """
    ids = {}

    # 1. Add font (if not already present)
    if f'face="{font_name}"' not in content:
        content, font_id = add_font(content, font_name)
        ids["font_id"] = font_id
    else:
        m = re.search(
            rf'<hh:fontface lang="HANGUL".*?</hh:fontface>',
            content,
            re.DOTALL,
        )
        if m:
            fm = re.search(rf'<hh:font id="(\d+)" face="{re.escape(font_name)}"', m.group())
            ids["font_id"] = int(fm.group(1)) if fm else 0
        else:
            ids["font_id"] = 0

    # 2. Add position-aware borderFills
    # Cache by (top, bottom, left, right, bg_color) to avoid duplicates
    bf_cache: dict[tuple, int] = {}

    def get_or_create_bf(
        top_w: str, bottom_w: str, left_w: str, right_w: str,
        bg: str | None = None,
    ) -> int:
        nonlocal content
        key = (top_w, bottom_w, left_w, right_w, bg)
        if key not in bf_cache:
            content, bf_id = add_borderfill(
                content, bg_color=bg,
                top_width=top_w, bottom_width=bottom_w,
                left_width=left_w, right_width=right_w,
            )
            bf_cache[key] = bf_id
        return bf_cache[key]

    # Pre-create borderFills for all cell positions
    # Header row
    bf_map_header: dict[tuple[int, int], int] = {}
    for c in range(total_cols):
        t, b, l, r = get_cell_border_widths(0, c, total_rows, total_cols, is_header=True)
        bf_map_header[(0, c)] = get_or_create_bf(t, b, l, r, bg=header_bg)

    # Body rows
    bf_map_body: dict[tuple[int, int], int] = {}
    for row in range(1, total_rows):
        for c in range(total_cols):
            t, b, l, r = get_cell_border_widths(row, c, total_rows, total_cols, is_header=False)
            bf_map_body[(row, c)] = get_or_create_bf(t, b, l, r)

    ids["bf_map_header"] = bf_map_header
    ids["bf_map_body"] = bf_map_body
    ids["bf_cache"] = bf_cache

    # 3. Add charPr (normal + bold) with spacing=-5
    content, cp_normal = add_charpr(
        content,
        height=font_size,
        font_id=ids["font_id"],
        bold=False,
        border_fill_id=2,
        spacing=spacing,
    )
    ids["charpr_normal"] = cp_normal

    content, cp_bold = add_charpr(
        content,
        height=font_size,
        font_id=ids["font_id"],
        bold=True,
        border_fill_id=2,
        spacing=spacing,
    )
    ids["charpr_bold"] = cp_bold

    # 4. Add paraPr (LEFT/CENTER/RIGHT) with 130% line spacing
    content, pp_left = add_parapr(content, align="LEFT", line_spacing_value="130")
    ids["parapr_left"] = pp_left

    content, pp_center = add_parapr(content, align="CENTER", line_spacing_value="130")
    ids["parapr_center"] = pp_center

    content, pp_right = add_parapr(content, align="RIGHT", line_spacing_value="130")
    ids["parapr_right"] = pp_right

    # Summary (without bf_map details for cleaner output)
    summary = {k: v for k, v in ids.items() if not k.startswith("bf_")}
    summary["bf_count"] = len(bf_cache)
    print(f"  Table styles added: {summary}", file=sys.stderr)
    return content, ids


def process_header(unpacked_dir: Path, operations: list[dict]) -> dict:
    """Process multiple operations on header.xml.

    Each operation is a dict with 'type' and type-specific params.
    Returns dict of all new IDs.
    """
    header_path = unpacked_dir / "Contents" / "header.xml"
    if not header_path.is_file():
        raise SystemExit(f"ERROR: header.xml not found: {header_path}")

    content = header_path.read_text(encoding="utf-8")
    all_ids = {}

    for op in operations:
        op_type = op["type"]
        if op_type == "add_font":
            content, fid = add_font(content, op["name"], op.get("type_info"))
            all_ids[f"font_{op['name']}"] = fid
        elif op_type == "add_charpr":
            content, cid = add_charpr(content, **{k: v for k, v in op.items() if k != "type"})
            all_ids[f"charpr_{cid}"] = cid
        elif op_type == "add_parapr":
            content, pid = add_parapr(content, **{k: v for k, v in op.items() if k != "type"})
            all_ids[f"parapr_{pid}"] = pid
        elif op_type == "add_borderfill":
            content, bid = add_borderfill(content, **{k: v for k, v in op.items() if k != "type"})
            all_ids[f"borderfill_{bid}"] = bid
        elif op_type == "add_table_styles":
            content, tids = add_table_styles(
                content,
                font_name=op.get("font_name", "맑은 고딕"),
                font_size=op.get("font_size", 1000),
                header_bg=op.get("header_bg", "#DCDCDC"),
            )
            all_ids.update(tids)

    header_path.write_text(content, encoding="utf-8")
    return all_ids


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Safely add styles to header.xml (string-based, no lxml)"
    )
    parser.add_argument("unpacked_dir", type=Path, help="Unpacked HWPX directory")
    parser.add_argument("--add-font", metavar="NAME", help="Add font to all fontface categories")
    parser.add_argument(
        "--add-charpr", metavar="JSON",
        help='Add charPr: \'{"height": 1000, "font_id": 6, "bold": false}\'',
    )
    parser.add_argument(
        "--add-parapr", metavar="JSON",
        help='Add paraPr: \'{"align": "LEFT"}\'',
    )
    parser.add_argument(
        "--add-borderfill", metavar="JSON",
        help='Add borderFill: \'{"bg_color": "#DCDCDC"}\'',
    )
    parser.add_argument(
        "--add-table-styles", action="store_true",
        help="Add all styles needed for a table (font + charPr + paraPr + borderFill)",
    )
    parser.add_argument("--font-name", default="맑은 고딕", help="Font name for table styles")
    parser.add_argument("--font-size", type=int, default=1000, help="Font size in HWPUNIT (default: 1000 = 10pt)")
    parser.add_argument("--header-bg", default="#DCDCDC", help="Header background color (default: #DCDCDC)")
    args = parser.parse_args()

    header_path = args.unpacked_dir / "Contents" / "header.xml"
    if not header_path.is_file():
        raise SystemExit(f"ERROR: header.xml not found: {header_path}")

    content = header_path.read_text(encoding="utf-8")
    results = {}

    if args.add_font:
        content, fid = add_font(content, args.add_font)
        results["font_id"] = fid

    if args.add_charpr:
        params = json.loads(args.add_charpr)
        content, cid = add_charpr(content, **params)
        results["charpr_id"] = cid

    if args.add_parapr:
        params = json.loads(args.add_parapr)
        content, pid = add_parapr(content, **params)
        results["parapr_id"] = pid

    if args.add_borderfill:
        params = json.loads(args.add_borderfill)
        content, bid = add_borderfill(content, **params)
        results["borderfill_id"] = bid

    if args.add_table_styles:
        content, tids = add_table_styles(
            content,
            font_name=args.font_name,
            font_size=args.font_size,
            header_bg=args.header_bg,
        )
        # Only include serializable keys
        results.update({k: v for k, v in tids.items() if not k.startswith("bf_")})

    header_path.write_text(content, encoding="utf-8")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
