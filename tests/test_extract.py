from pathlib import Path

import pytest

from pdf2excel import extract_tables, parse_pages

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
    assert t[1].df.iloc[-1].tolist() == ["Total", "616.00"]


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
