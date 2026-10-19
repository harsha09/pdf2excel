"""Generate SYNTHETIC sample PDFs (all names/numbers are fictional)."""
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

OUT = Path(__file__).resolve().parent.parent / "samples"
SS = getSampleStyleSheet()
GRID = TableStyle([
    ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
    ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
])


def doc(name):
    return SimpleDocTemplate(str(OUT / name), pagesize=A4, invariant=1)


def invoice():
    items = [["Item", "Description", "Qty", "Unit Price", "Amount"],
             ["1", "Widget A", "10", "12.50", "125.00"],
             ["2", "Gadget B", "3", "40.00", "120.00"],
             ["3", "Support hours", "5", "60.00", "300.00"],
             ["4", "Shipping", "1", "15.00", "15.00"]]
    totals = [["Subtotal", "560.00"], ["Tax 10%", "56.00"], ["Total", "616.00"]]
    t2 = Table(totals)
    t2.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.5, colors.black)]))
    t1 = Table(items)
    t1.setStyle(GRID)
    doc("sample_invoice.pdf").build([
        Paragraph("INVOICE #INV-0001 (SYNTHETIC SAMPLE)", SS["Title"]),
        Paragraph("Acme Example Co. → Bill to: Jane Placeholder, 123 Fake Street, Sampletown", SS["Normal"]),
        Spacer(1, 12), t1, Spacer(1, 18), t2])


def statement():
    rows = [["Date", "Description", "Debit", "Credit", "Balance"]]
    bal = 1000.00
    import random
    rnd = random.Random(42)
    for d in range(1, 41):
        amt = round(rnd.uniform(5, 300), 2)
        if d % 4 == 0:
            bal += amt
            rows.append([f"2026-01-{(d % 28) + 1:02d}", f"Deposit ref {1000 + d}", "", f"{amt:,.2f}", f"{bal:,.2f}"])
        else:
            bal -= amt
            rows.append([f"2026-01-{(d % 28) + 1:02d}", f"Card purchase #{d:03d}", f"{amt:,.2f}", "", f"{bal:,.2f}"])
    p1, p2 = rows[:26], [rows[0]] + rows[26:]
    story = [Paragraph("Fictional Bank of Nowhere — Statement (SYNTHETIC SAMPLE)", SS["Title"]),
             Paragraph("Account holder: John Doe-Example · Account: 0000-0000-1234", SS["Normal"]), Spacer(1, 12)]
    for i, chunk in enumerate((p1, p2)):
        t = Table(chunk)
        t.setStyle(GRID)
        story.append(t)
        if i == 0:
            story.append(PageBreak())
    doc("sample_bank_statement.pdf").build(story)


def report():
    """Borderless (whitespace-aligned) table to exercise text strategy."""
    rows = [["Region", "Q1", "Q2", "Q3", "Q4"],
            ["North", "1200", "1350", "1100", "1500"],
            ["South", "900", "950", "1020", "1110"],
            ["East", "1430", "1390", "1500", "1620"],
            ["West", "800", "870", "910", "990"]]
    t = Table(rows, colWidths=[90, 70, 70, 70, 70])
    doc("sample_sales_report.pdf").build([
        Paragraph("Quarterly Sales Report (SYNTHETIC SAMPLE)", SS["Title"]), Spacer(1, 12), t])


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    invoice(); statement(); report()
    print("wrote samples to", OUT)
