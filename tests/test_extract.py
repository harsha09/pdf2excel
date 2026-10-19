from pathlib import Path

import pytest

from pdf2excel import extract_tables, merge_tables, parse_pages
from pdf2excel.extract import ExtractedTable
import pandas as pd

S = Path(__file__).resolve().parent.parent / "samples"


def test_parse_pages():
    assert parse_pages(None, 3) == [1, 2, 3]
    assert parse_pages("all", 2) == [1, 2]
    assert parse_pages("1,3-4", 5) == [1, 3, 4]
    assert parse_pages("2-", 4) == [2, 3, 4]
    assert parse_pages("1-10", 2) == [1, 2]
    with pytest.raises(ValueError):
        parse_pages("3-1", 5)
    with pytest.raises(ValueError):
        parse_pages("0", 5)


def test_invoice():
    t = extract_tables(str(S / "sample_invoice.pdf"))
    assert len(t) == 2
    items = t[0].df
    assert list(items.columns) == ["Item", "Description", "Qty", "Unit Price", "Amount"]
    assert len(items) == 4
    assert items.iloc[0].tolist() == ["1", "Widget A", "10", "12.50", "125.00"]
    assert sum(float(a) for a in items["Amount"]) == 560.0
    assert list(t[1].df.columns) == ["Column 1", "Column 2"]
    assert t[1].df.iloc[0].tolist() == ["Subtotal", "560.00"]
    assert t[1].df.iloc[-1].tolist() == ["Total", "616.00"]
    assert len(t[1].df) == 3


def test_bank_statement_multipage_and_range():
    t = extract_tables(str(S / "sample_bank_statement.pdf"))
    assert [x.page for x in t] == [1, 2]
    assert sum(len(x.df) for x in t) == 40
    for x in t:
        assert list(x.df.columns) == ["Date", "Description", "Debit", "Credit", "Balance"]
    assert t[0].df.iloc[0]["Description"] == "Card purchase #001"
    only2 = extract_tables(str(S / "sample_bank_statement.pdf"), pages="2")
    assert len(only2) == 1 and only2[0].page == 2 and len(only2[0].df) == 15


def test_borderless_report():
    t = extract_tables(str(S / "sample_sales_report.pdf"))
    assert len(t) == 1
    df = t[0].df
    assert list(df.columns) == ["Region", "Q1", "Q2", "Q3", "Q4"]
    assert df["Region"].tolist() == ["North", "South", "East", "West"]
    assert df.iloc[2].tolist() == ["East", "1430", "1390", "1500", "1620"]


def test_no_header():
    t = extract_tables(str(S / "sample_sales_report.pdf"), header=False)
    assert t[0].df.iloc[0].tolist()[0] == "Region"
    assert len(t[0].df) == 5


def test_stream_input():
    with open(S / "sample_invoice.pdf", "rb") as f:
        assert len(extract_tables(f)) == 2


def test_merge_bank_statement():
    t = merge_tables(extract_tables(str(S / "sample_bank_statement.pdf")))
    assert len(t) == 1
    df = t[0].df
    assert len(df) == 40
    assert not (df["Date"] == "Date").any()
    assert df.iloc[-1]["Description"] == "Deposit ref 1040"


def test_merge_rules():
    h = ["A", "B"]
    mk = lambda p, rows, cols=h: ExtractedTable(p, 1, pd.DataFrame(rows, columns=cols))
    # repeated header row dropped
    out = merge_tables([mk(1, [["1", "2"]]), mk(2, [["A", "B"], ["3", "4"]])])
    assert len(out) == 1 and out[0].df.values.tolist() == [["1", "2"], ["3", "4"]]
    # non-consecutive pages, different headers, generic headers -> not merged
    assert len(merge_tables([mk(1, [["1", "2"]]), mk(3, [["3", "4"]])])) == 2
    assert len(merge_tables([mk(1, [["1", "2"]]), mk(2, [["3", "4"]], ["X", "Y"])])) == 2
    g = ["Column 1", "Column 2"]
    assert len(merge_tables([mk(1, [["1", "2"]], g), mk(2, [["3", "4"]], g)])) == 2
    # invoice: two tables on the same page stay separate
    assert len(merge_tables(extract_tables(str(S / "sample_invoice.pdf")))) == 2
