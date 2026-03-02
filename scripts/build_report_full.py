#!/usr/bin/env python3
"""One-click 8-section report builder.

Reads a single JSON config and runs the full pipeline:
  build_hwpx → unpack → bulk-insert → add_table(s) → pack → validate

Usage:
    python build_report_full.py --config report.json --output result.hwpx

Config JSON format:
{
  "meta": {
    "title": "보고서 제목",
    "date": "2026. 3. 2.(월)",
    "department": "정책기획팀",
    "position": "교육협력담당관",
    "author": "작성자",
    "contact": "052-XXX-XXXX"
  },
  "template_replacements": {
    "섹션1 제목": "추진 배경",
    "본문 내용1": "핵심 본문"
  },
  "sections": [
    {
      "title": "기대 효과",
      "items": [
        {"level": "body", "text": "항목"},
        {"level": "sub", "text": "세부"}
      ],
      "table": {
        "columns": ["A", "B"],
        "rows": [{"data": ["1", "2"]}]
      }
    }
  ]
}
"""

import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from build_hwpx import build  # noqa: E402
from edit_section import (  # noqa: E402
    _build_paragraphs_xml,
    insert_after_anchor,
    read_section,
    write_section,
)
from add_table import insert_table  # noqa: E402


def build_report(config: dict, output: Path) -> None:
    """Build a full report from config dict."""
    meta = config.get("meta", {})
    tmpl_repl = config.get("template_replacements", {})
    sections = config.get("sections", [])

    # Meta → template replacements
    meta_map = {
        "작성일": meta.get("date", ""),
        "부서": meta.get("department", ""),
        "직위": meta.get("position", ""),
        "작성자": meta.get("author", ""),
        "연락처": meta.get("contact", ""),
    }
    replacements = {k: v for k, v in {**meta_map, **tmpl_repl}.items() if v}

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        intermediate = tmp / "intermediate.hwpx"
        unpacked = tmp / "unpacked"

        # 1. Build base HWPX
        print("Step 1: Building base HWPX...", file=sys.stderr)
        build(
            template="report",
            header_override=None,
            section_override=None,
            title=meta.get("title"),
            creator=meta.get("author"),
            output=intermediate,
            replacements=replacements,
            replace_title=meta.get("title"),
        )

        # 2. Unpack
        print("Step 2: Unpacking...", file=sys.stderr)
        from office.unpack import unpack  # noqa: E402
        unpack(str(intermediate), str(unpacked))

        # 3. Bulk-insert additional sections
        if sections:
            print(f"Step 3: Inserting {len(sections)} section(s)...", file=sys.stderr)
            content = read_section(unpacked)

            # Find last anchor in template (섹션2's 표 제목 or 본문 내용2)
            last_anchor = tmpl_repl.get("표 제목", tmpl_repl.get("본문 내용2", ""))

            paras = []
            tables = []  # (anchor_text, table_data) pairs

            for sec in sections:
                title = sec.get("title", "")
                if title:
                    paras.append({"type": "section_title", "text": title})

                for item in sec.get("items", []):
                    level = item.get("level", "body")
                    paras.append({"type": level, "text": item.get("text", "")})

                # Track table anchor (last item text before table)
                if "table" in sec:
                    items = sec.get("items", [])
                    tbl_anchor = items[-1]["text"] if items else title
                    tables.append((tbl_anchor, sec["table"]))

            if paras and last_anchor:
                xml = _build_paragraphs_xml(paras)
                content = insert_after_anchor(content, last_anchor, xml)
                write_section(unpacked, content)
            elif paras:
                print("WARNING: No anchor found for section insertion", file=sys.stderr)

            # 4. Insert tables
            if tables:
                print(f"Step 4: Inserting {len(tables)} table(s)...", file=sys.stderr)
                for anchor, tdata in tables:
                    try:
                        insert_table(
                            unpacked, tdata,
                            insert_after=anchor,
                            body_width=48190,
                            fallback_append=True,
                        )
                    except SystemExit as e:
                        print(f"WARNING: Table insertion failed: {e}", file=sys.stderr)

        # 5. Pack
        print("Step 5: Packing...", file=sys.stderr)
        from office.pack import pack  # noqa: E402
        pack(str(unpacked), str(output))

        # 6. Validate
        print("Step 6: Validating...", file=sys.stderr)
        from validate import validate  # noqa: E402
        errors = validate(str(output))
        if errors:
            print(f"WARNING: {output} has issues:", file=sys.stderr)
            for e in errors:
                print(f"  - {e}", file=sys.stderr)
        else:
            print(f"VALID: {output}", file=sys.stderr)

    print(f"OK: {output}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="One-click 8-section report builder"
    )
    parser.add_argument(
        "--config", "-c", type=Path, required=True,
        help="JSON config file for the report",
    )
    parser.add_argument(
        "--output", "-o", type=Path, required=True,
        help="Output .hwpx file path",
    )
    args = parser.parse_args()

    if not args.config.is_file():
        raise SystemExit(f"ERROR: Config file not found: {args.config}")

    config = json.loads(args.config.read_text(encoding="utf-8"))
    build_report(config, args.output)


if __name__ == "__main__":
    main()
