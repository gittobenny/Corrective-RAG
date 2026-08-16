import pymupdf

from backend.services.pdf_processor import extract_pdf, split_pages


def test_extract_and_split_pdf(tmp_path):
    path = tmp_path / "report.pdf"
    document = pymupdf.open()
    page = document.new_page()
    page.insert_text((72, 72), "Quarterly revenue increased by eighteen percent.")
    document.save(path)
    document.close()

    pages = extract_pdf(path)
    chunks = split_pages(pages, chunk_size=30, chunk_overlap=5)

    assert len(pages) == 1
    assert pages[0].metadata["page"] == 1
    assert "revenue" in pages[0].page_content
    assert len(chunks) >= 2
