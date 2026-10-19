"""Table extraction (pdfplumber, optional camelot fallback)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import IO, List, Optional, Sequence, Union

import re

import pandas as pd
import pdfplumber

PdfSource = Union[str, "os.PathLike[str]", IO[bytes]]


@dataclass
class ExtractedTable:
    page: int  # 1-based
    index: int  # table index on that page, 1-based
    df: pd.DataFrame

    @property
    def name(self) -> str:
        return f"p{self.page}_t{self.index}"


def parse_pages(spec: Optional[str], n_pages: int) -> List[int]:
    """Parse '1,3-5' into sorted 1-based page numbers, clipped to n_pages."""
    if not spec or spec.strip().lower() == "all":
        return list(range(1, n_pages + 1))
    pages = set()
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            a, b = part.split("-", 1)
            start = int(a) if a else 1
            end = int(b) if b else n_pages
            if start > end:
                raise ValueError(f"Invalid page range: {part}")
            pages.update(range(start, end + 1))
        else:
            pages.add(int(part))
    bad = [p for p in pages if p < 1]
    if bad:
        raise ValueError(f"Page numbers must be >= 1: {bad}")
    return sorted(p for p in pages if p <= n_pages)


def _clean(cell) -> str:
    if cell is None:
        return ""
    return " ".join(str(cell).split())


_NUM = re.compile(r"^[-+(]?[$€£₹]?\s*[\d,]*\.?\d+\s*%?\)?$")


def _looks_like_data(row: Sequence[str]) -> bool:
    """A header row shouldn't contain numeric cells (e.g. 'Subtotal | 560.00')."""
    return any(_NUM.match(c) for c in row if c)


def _to_df(rows: Sequence[Sequence], header: bool = True) -> Optional[pd.DataFrame]:
    rows = [[_clean(c) for c in r] for r in rows]
    rows = [r for r in rows if any(r)]
    if not rows:
        return None
    width = max(len(r) for r in rows)
    rows = [r + [""] * (width - len(r)) for r in rows]
    if header and len(rows) > 1 and not _looks_like_data(rows[0]):
        cols, seen = [], {}
        for i, c in enumerate(rows[0]):
            c = c or f"Column {i + 1}"
            if c in seen:
                seen[c] += 1
                c = f"{c}_{seen[c]}"
            else:
                seen[c] = 0
            cols.append(c)
        return pd.DataFrame(rows[1:], columns=cols)
    return pd.DataFrame(rows, columns=[f"Column {i + 1}" for i in range(width)])


def _camelot_tables(path: str, page: int) -> List[pd.DataFrame]:  # pragma: no cover
    try:
        import camelot  # type: ignore
    except ImportError:
        return []
    out = []
    for flavor in ("lattice", "stream"):
        try:
            tables = camelot.read_pdf(path, pages=str(page), flavor=flavor)
        except Exception:
            continue
        for t in tables:
            df = _to_df(t.df.values.tolist())
            if df is not None:
                out.append(df)
        if out:
            break
    return out


def extract_tables(
    source: PdfSource,
    pages: Optional[str] = None,
    header: bool = True,
    use_camelot: bool = False,
) -> List[ExtractedTable]:
    """Extract all tables from the selected pages.

    Strategy: pdfplumber 'lines' (ruled tables) first, then 'text' alignment
    for borderless tables. Optionally fall back to camelot if installed and
    a path (not a stream) was given.
    """
    results: List[ExtractedTable] = []
    with pdfplumber.open(source) as pdf:
        for pno in parse_pages(pages, len(pdf.pages)):
            page = pdf.pages[pno - 1]
            raw = page.extract_tables({"vertical_strategy": "lines", "horizontal_strategy": "lines"})
            raw = [t for t in raw if t and len(t) > 1]
            if not raw:
                raw = page.extract_tables({"vertical_strategy": "text", "horizontal_strategy": "text"})
                raw = [t for t in raw if t and len(t) > 1 and max(len(r) for r in t) > 1]
            dfs = [d for d in (_to_df(t, header) for t in raw) if d is not None]
            if not dfs and use_camelot and isinstance(source, (str,)):
                dfs = _camelot_tables(source, pno)
            for i, df in enumerate(dfs, 1):
                results.append(ExtractedTable(page=pno, index=i, df=df))
    return results


def merge_tables(tables: List[ExtractedTable]) -> List[ExtractedTable]:
    """Concatenate tables with identical headers on consecutive pages.

    Repeated header rows inside the continued table are dropped.
    """
    merged: List[ExtractedTable] = []
    last_page = None
    for t in tables:
        prev = merged[-1] if merged else None
        cols = list(t.df.columns)
        if (prev is not None and list(prev.df.columns) == cols
                and last_page is not None and t.page == last_page + 1
                and not cols[0].startswith("Column ")):
            df = t.df[~(t.df.astype(str).values == [str(c) for c in cols]).all(axis=1)]
            prev.df = pd.concat([prev.df, df], ignore_index=True)
        else:
            merged.append(ExtractedTable(page=t.page, index=t.index, df=t.df.copy()))
        last_page = t.page
    return merged
