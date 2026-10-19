"""Command-line interface: pdf2excel input.pdf -o out.xlsx"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Optional

from .export import to_csv, to_xlsx
from .extract import extract_tables, merge_tables


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="pdf2excel", description="Extract tables from a text-based PDF to Excel or CSV.")
    ap.add_argument("input", help="input PDF file")
    ap.add_argument("-o", "--output", help="output file (.xlsx or .csv). Default: <input>.xlsx")
    ap.add_argument("--csv", action="store_true", help="write CSV (one file per table) instead of XLSX")
    ap.add_argument("-p", "--pages", default="all", help="pages, e.g. '1', '1-3', '1,4-6' (default: all)")
    ap.add_argument("--no-header", action="store_true", help="don't treat first row as header")
    ap.add_argument("--merge", action="store_true",
                    help="merge tables with identical headers on consecutive pages into one")
    ap.add_argument("--camelot", action="store_true", help="fallback to camelot if installed and nothing found")
    args = ap.parse_args(argv)

    src = Path(args.input)
    if not src.is_file():
        print(f"error: file not found: {src}", file=sys.stderr)
        return 2
    as_csv = args.csv or (args.output or "").lower().endswith(".csv")
    out = Path(args.output) if args.output else src.with_suffix(".csv" if as_csv else ".xlsx")

    try:
        tables = extract_tables(str(src), pages=args.pages, header=not args.no_header, use_camelot=args.camelot)
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    except Exception as e:  # malformed / encrypted PDFs
        print(f"error: could not read PDF: {e}", file=sys.stderr)
        return 1
    if args.merge:
        tables = merge_tables(tables)
    if not tables:
        print("No tables found. (Scanned/image PDFs need OCR — available in the Pro version.)", file=sys.stderr)
        return 1

    for t in tables:
        print(f"page {t.page} table {t.index}: {t.df.shape[0]} rows x {t.df.shape[1]} cols")
    if as_csv:
        for p in to_csv(tables, out):
            print(f"wrote {p}")
    else:
        to_xlsx(tables, out)
        print(f"wrote {out} ({len(tables)} sheet(s))")
    return 0


if __name__ == "__main__":
    sys.exit(main())
