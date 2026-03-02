#!/usr/bin/env python3
"""Build an HWPX document from templates and XML overrides.

Assembles a valid HWPX file by:
1. Copying the base template
2. Optionally overlaying a document-type template (gonmun, report, minutes)
3. Optionally overriding header.xml and/or section0.xml with custom files
4. Optionally setting metadata (title, creator)
5. Validating XML well-formedness
6. Packaging as HWPX (ZIP with mimetype first, ZIP_STORED)

Usage:
    # Empty document from base template
    python build_hwpx.py --output result.hwpx

    # Using a document-type template
    python build_hwpx.py --template gonmun --output result.hwpx

    # Custom section XML override
    python build_hwpx.py --template gonmun --section my_section0.xml --output result.hwpx

    # Custom header and section
    python build_hwpx.py --header my_header.xml --section my_section0.xml --output result.hwpx

    # With metadata
    python build_hwpx.py --template gonmun --section my.xml --title "제목" --creator "작성자" --output result.hwpx

    # With placeholder replacement
    python build_hwpx.py --template gonmun --replace "수신자=OO학교장" --replace "제목=업무협조" --output result.hwpx

    # Replace report drawText title
    python build_hwpx.py --template report --replace-title "AI 활용 업무보고" --output report.hwpx
"""

import argparse
import re
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZIP_STORED, ZipFile

try:
    from lxml import etree
except ImportError:
    import subprocess

    print("lxml not found. Installing...", file=sys.stderr)
    subprocess.check_call(
        [sys.executable, "-m", "pip", "install", "lxml", "-q"],
    )
    from lxml import etree

# Resolve paths relative to this script
SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
TEMPLATES_DIR = SKILL_DIR / "templates"
BASE_DIR = TEMPLATES_DIR / "base"

AVAILABLE_TEMPLATES = ["gonmun", "report", "minutes", "draft"]


def parse_replacements(raw: list[str] | None) -> dict[str, str]:
    """Parse --replace KEY=VALUE arguments into a dict."""
    if not raw:
        return {}
    result: dict[str, str] = {}
    for item in raw:
        if "=" not in item:
            raise SystemExit(
                f"ERROR: Invalid --replace format: '{item}'\n"
                f"  Expected format: --replace \"키=값\" (e.g. --replace \"수신자=OO학교장\")"
            )
        key, value = item.split("=", 1)
        key = key.strip()
        if not key:
            raise SystemExit(
                f"ERROR: Empty key in --replace: '{item}'\n"
                f"  Expected format: --replace \"키=값\""
            )
        result[key] = value
    return result


def replace_placeholders(section_path: Path, replacements: dict[str, str]) -> list[str]:
    """Replace {{KEY}} placeholders in section0.xml.

    This uses string-based replacement which works everywhere including
    inside drawText elements. Returns list of replaced keys.
    """
    if not replacements:
        return []

    content = section_path.read_text(encoding="utf-8")
    replaced = []
    for key, value in replacements.items():
        placeholder = "{{" + key + "}}"
        if placeholder in content:
            content = content.replace(placeholder, value)
            replaced.append(key)

    section_path.write_text(content, encoding="utf-8")

    not_found = set(replacements.keys()) - set(replaced)
    if not_found:
        print(
            f"WARNING: Placeholders not found in section0.xml: "
            f"{', '.join('{{' + k + '}}' for k in sorted(not_found))}",
            file=sys.stderr,
        )

    return replaced


def replace_drawtext_title(section_path: Path, new_title: str) -> bool:
    """Replace the title inside drawText (report template).

    The report template has a drawText rect element containing the title
    (default: "HY헤드라인M"). This replaces that text with new_title.

    Returns True if replacement was made.
    """
    content = section_path.read_text(encoding="utf-8")
    pattern = r'(<hp:drawText[^>]*>.*?<hp:t>)(.*?)(</hp:t>.*?</hp:drawText>)'
    m = re.search(pattern, content, re.DOTALL)
    if m:
        old_title = m.group(2)
        content = content[:m.start(2)] + new_title + content[m.end(2):]
        section_path.write_text(content, encoding="utf-8")
        print(
            f"  Replaced drawText title: '{old_title}' -> '{new_title}'",
            file=sys.stderr,
        )
        return True
    else:
        print("WARNING: drawText title not found in section0.xml", file=sys.stderr)
        return False


def validate_xml(filepath: Path) -> None:
    """Check that an XML file is well-formed. Raises on error."""
    try:
        etree.parse(str(filepath))
    except etree.XMLSyntaxError as e:
        raise SystemExit(
            f"ERROR: Malformed XML in {filepath.name}: {e}\n"
            f"  File: {filepath}\n"
            f"  Fix the XML syntax error and try again."
        )


def update_metadata(content_hpf: Path, title: str | None, creator: str | None) -> None:
    """Update title and/or creator in content.hpf."""
    if not title and not creator:
        return

    tree = etree.parse(str(content_hpf))
    root = tree.getroot()
    ns = {"opf": "http://www.idpf.org/2007/opf/"}

    if title:
        title_el = root.find(".//opf:title", ns)
        if title_el is not None:
            title_el.text = title

    now = datetime.now(timezone.utc)
    iso_now = now.strftime("%Y-%m-%dT%H:%M:%SZ")

    for meta in root.findall(".//opf:meta", ns):
        name = meta.get("name", "")
        if creator and name == "creator":
            meta.text = creator
        elif creator and name == "lastsaveby":
            meta.text = creator
        elif name == "CreatedDate":
            meta.text = iso_now
        elif name == "ModifiedDate":
            meta.text = iso_now
        elif name == "date":
            meta.text = now.strftime("%Y년 %m월 %d일")

    etree.indent(root, space="  ")
    tree.write(
        str(content_hpf),
        pretty_print=True,
        xml_declaration=True,
        encoding="UTF-8",
    )


def pack_hwpx(input_dir: Path, output_path: Path) -> None:
    """Create HWPX archive with mimetype as first entry (ZIP_STORED)."""
    mimetype_file = input_dir / "mimetype"
    if not mimetype_file.is_file():
        raise SystemExit(f"Missing 'mimetype' in {input_dir}")

    all_files = sorted(
        p.relative_to(input_dir).as_posix()
        for p in input_dir.rglob("*")
        if p.is_file()
    )

    with ZipFile(output_path, "w", ZIP_DEFLATED) as zf:
        zf.write(mimetype_file, "mimetype", compress_type=ZIP_STORED)
        for rel_path in all_files:
            if rel_path == "mimetype":
                continue
            zf.write(input_dir / rel_path, rel_path, compress_type=ZIP_DEFLATED)


def validate_hwpx(hwpx_path: Path) -> list[str]:
    """Quick structural validation of the output HWPX."""
    errors: list[str] = []
    required = [
        "mimetype",
        "Contents/content.hpf",
        "Contents/header.xml",
        "Contents/section0.xml",
    ]

    try:
        from zipfile import BadZipFile
        zf = ZipFile(hwpx_path, "r")
    except BadZipFile:
        return [f"Not a valid ZIP: {hwpx_path}"]

    with zf:
        names = zf.namelist()
        for r in required:
            if r not in names:
                errors.append(f"Missing: {r}")

        if "mimetype" in names:
            content = zf.read("mimetype").decode("utf-8").strip()
            if content != "application/hwp+zip":
                errors.append(f"Bad mimetype content: {content}")
            if names[0] != "mimetype":
                errors.append("mimetype is not the first ZIP entry")
            info = zf.getinfo("mimetype")
            if info.compress_type != ZIP_STORED:
                errors.append("mimetype is not ZIP_STORED")

        for name in names:
            if name.endswith(".xml") or name.endswith(".hpf"):
                try:
                    etree.fromstring(zf.read(name))
                except etree.XMLSyntaxError as e:
                    errors.append(f"Malformed XML: {name}: {e}")

    return errors


def build(
    template: str | None,
    header_override: Path | None,
    section_override: Path | None,
    title: str | None,
    creator: str | None,
    output: Path,
    replacements: dict[str, str] | None = None,
    replace_title: str | None = None,
) -> None:
    """Main build logic."""

    if not BASE_DIR.is_dir():
        raise SystemExit(
            f"ERROR: Base template directory not found: {BASE_DIR}\n"
            f"  Ensure the templates/base/ directory exists relative to this script."
        )

    with tempfile.TemporaryDirectory() as tmpdir:
        work = Path(tmpdir) / "build"

        # 1. Copy base template
        shutil.copytree(BASE_DIR, work)

        # 2. Apply template overlay
        if template:
            overlay_dir = TEMPLATES_DIR / template
            if not overlay_dir.is_dir():
                raise SystemExit(
                    f"ERROR: Template '{template}' not found.\n"
                    f"  Available templates: {', '.join(AVAILABLE_TEMPLATES)}\n"
                    f"  Looked in: {TEMPLATES_DIR}"
                )
            for overlay_file in overlay_dir.iterdir():
                if overlay_file.is_file() and overlay_file.suffix == ".xml":
                    dest = work / "Contents" / overlay_file.name
                    shutil.copy2(overlay_file, dest)

            # 2-1. BinData overlay
            bindata_dir = overlay_dir / "BinData"
            if bindata_dir.is_dir():
                dest_bindata = work / "BinData"
                if dest_bindata.exists():
                    shutil.rmtree(dest_bindata)
                shutil.copytree(bindata_dir, dest_bindata)

            # 2-2. content.hpf overlay
            overlay_hpf = overlay_dir / "content.hpf"
            if overlay_hpf.is_file():
                shutil.copy2(overlay_hpf, work / "Contents" / "content.hpf")

        # 3. Apply custom overrides
        if header_override:
            if not header_override.is_file():
                raise SystemExit(
                    f"ERROR: Header file not found: {header_override}\n"
                    f"  Provide a valid path to a header.xml file."
                )
            shutil.copy2(header_override, work / "Contents" / "header.xml")

        if section_override:
            if not section_override.is_file():
                raise SystemExit(
                    f"ERROR: Section file not found: {section_override}\n"
                    f"  Provide a valid path to a section0.xml file."
                )
            shutil.copy2(section_override, work / "Contents" / "section0.xml")

        # 4. Replace placeholders in section0.xml
        section_file = work / "Contents" / "section0.xml"
        if replacements:
            replaced = replace_placeholders(section_file, replacements)
            if replaced:
                print(
                    f"  Replaced {len(replaced)} placeholder(s): "
                    f"{', '.join('{{' + k + '}}' for k in replaced)}",
                    file=sys.stderr,
                )

        # 4-1. Replace drawText title (report template)
        if replace_title:
            replace_drawtext_title(section_file, replace_title)

        # 4-2. Remove stale linesegarray layout cache
        # linesegarray contains character-position layout data that becomes
        # invalid when text length changes (e.g. after --replace).
        # Hangul recalculates these on open, so removing them is safe.
        if replacements or replace_title:
            raw = section_file.read_text(encoding="utf-8")
            cleaned = re.sub(
                r'\s*<hp:linesegarray>.*?</hp:linesegarray>',
                '',
                raw,
                flags=re.DOTALL,
            )
            if len(cleaned) != len(raw):
                section_file.write_text(cleaned, encoding="utf-8")
                print("  Removed stale linesegarray blocks", file=sys.stderr)

        # 5. Update metadata
        update_metadata(work / "Contents" / "content.hpf", title, creator)

        # 6. Validate all XML files
        for xml_file in work.rglob("*.xml"):
            validate_xml(xml_file)
        for hpf_file in work.rglob("*.hpf"):
            validate_xml(hpf_file)

        # 7. Pack
        pack_hwpx(work, output)

    # 8. Final validation
    errors = validate_hwpx(output)
    if errors:
        print(f"WARNING: {output} has issues:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
    else:
        print(f"VALID: {output}")
        print(f"  Template: {template or 'base'}")
        if header_override:
            print(f"  Header: {header_override}")
        if section_override:
            print(f"  Section: {section_override}")
        if replacements:
            print(f"  Replacements: {len(replacements)}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build HWPX document from templates and XML overrides"
    )
    parser.add_argument(
        "--template", "-t",
        choices=AVAILABLE_TEMPLATES,
        help="Document type template to use as overlay",
    )
    parser.add_argument(
        "--header",
        type=Path,
        help="Custom header.xml to override",
    )
    parser.add_argument(
        "--section",
        type=Path,
        help="Custom section0.xml to override",
    )
    parser.add_argument(
        "--title",
        help="Document title (updates content.hpf metadata)",
    )
    parser.add_argument(
        "--creator",
        help="Document creator (updates content.hpf metadata)",
    )
    parser.add_argument(
        "--replace", "-r",
        action="append",
        metavar="KEY=VALUE",
        help="Replace {{KEY}} with VALUE in section0.xml (repeatable)",
    )
    parser.add_argument(
        "--replace-title",
        metavar="TEXT",
        help="Replace the drawText title in report template (default: 'HY헤드라인M')",
    )
    parser.add_argument(
        "--output", "-o",
        type=Path,
        required=True,
        help="Output .hwpx file path",
    )
    args = parser.parse_args()

    replacements = parse_replacements(args.replace)

    build(
        template=args.template,
        header_override=args.header,
        section_override=args.section,
        title=args.title,
        creator=args.creator,
        output=args.output,
        replacements=replacements,
        replace_title=args.replace_title,
    )


if __name__ == "__main__":
    main()
