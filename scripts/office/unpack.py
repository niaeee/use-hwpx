#!/usr/bin/env python3
"""Unpack an HWPX file into a directory with pretty-printed XML.

Usage:
    python unpack.py input.hwpx output_dir/
"""

import argparse
import os
import sys
from pathlib import Path
from zipfile import ZipFile

try:
    from lxml import etree
except ImportError:
    import subprocess

    print("lxml not found. Installing...", file=sys.stderr)
    subprocess.check_call(
        [sys.executable, "-m", "pip", "install", "lxml", "-q"],
    )
    from lxml import etree


def unpack(hwpx_path: str, output_dir: str) -> None:
    """Extract HWPX archive and pretty-print all XML files."""

    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    with ZipFile(hwpx_path, "r") as zf:
        for entry in zf.namelist():
            data = zf.read(entry)
            dest = output / entry
            dest.parent.mkdir(parents=True, exist_ok=True)

            if entry.endswith(".xml") or entry.endswith(".hpf"):
                try:
                    tree = etree.fromstring(data)
                    etree.indent(tree, space="  ")
                    pretty = etree.tostring(
                        tree,
                        pretty_print=True,
                        xml_declaration=True,
                        encoding="UTF-8",
                    )
                    dest.write_bytes(pretty)
                    continue
                except etree.XMLSyntaxError:
                    pass  # Fall through to raw write

            dest.write_bytes(data)

    print(f"Unpacked: {hwpx_path} -> {output_dir}")
    print(f"  Files: {len(list(output.rglob('*')))} entries")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Unpack HWPX file into a directory with pretty-printed XML"
    )
    parser.add_argument("input", help="Path to .hwpx file")
    parser.add_argument("output", help="Output directory path")
    args = parser.parse_args()

    if not os.path.isfile(args.input):
        print(f"ERROR: File not found: {args.input}", file=sys.stderr)
        print("  Check the file path and try again.", file=sys.stderr)
        sys.exit(1)

    if not args.input.lower().endswith('.hwpx'):
        print(
            f"WARNING: '{os.path.basename(args.input)}' does not have .hwpx extension.",
            file=sys.stderr,
        )
        print("  This tool supports .hwpx only, not .hwp (binary).", file=sys.stderr)

    try:
        unpack(args.input, args.output)
    except Exception as e:
        print(f"ERROR: Failed to unpack '{args.input}': {e}", file=sys.stderr)
        print("  The file may be corrupted or not a valid HWPX archive.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
