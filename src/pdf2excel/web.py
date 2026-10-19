"""Streamlit demo UI. Run: streamlit run src/pdf2excel/web.py"""
import io
import zipfile

import streamlit as st

from pdf2excel.export import to_xlsx
from pdf2excel.extract import extract_tables

st.set_page_config(page_title="PDF → Excel/CSV", page_icon="📄")
st.title("📄 PDF tables → Excel / CSV")
st.caption("Free demo · text-based PDFs only · files are processed in memory and not stored")

up = st.file_uploader("Upload a PDF", type=["pdf"])
pages = st.text_input("Pages (e.g. all, 1, 1-3, 1,4-6)", value="all")
header = st.checkbox("First row is a header", value=True)

if up is not None:
    try:
        tables = extract_tables(io.BytesIO(up.getvalue()), pages=pages, header=header)
    except Exception as e:
        st.error(f"Could not process PDF: {e}")
        st.stop()
    if not tables:
        st.warning("No tables found. Scanned/image PDFs need OCR (Pro version).")
        st.stop()
    st.success(f"Found {len(tables)} table(s)")
    for t in tables:
        st.subheader(f"Page {t.page} · table {t.index}")
        st.dataframe(t.df, use_container_width=True)

    stem = up.name.rsplit(".", 1)[0]
    buf = io.BytesIO()
    to_xlsx(tables, buf)
    st.download_button("⬇️ Download Excel (.xlsx)", buf.getvalue(), f"{stem}.xlsx",
                       "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    zbuf = io.BytesIO()
    with zipfile.ZipFile(zbuf, "w") as z:
        for t in tables:
            z.writestr(f"{stem}_{t.name}.csv", t.df.to_csv(index=False))
    st.download_button("⬇️ Download CSV (.zip)", zbuf.getvalue(), f"{stem}_csv.zip", "application/zip")
