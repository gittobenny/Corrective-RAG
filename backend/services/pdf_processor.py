#extraction and chunking

from pathlib import Path

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
import pymupdf


class InvalidPdfError(ValueError):
    """Raised when an uploaded PDF cannot produce searchable text."""


def extract_pdf(path: Path) -> list[Document]:
    pages: list[Document] = []
    try:
        with pymupdf.open(path) as pdf:
            if pdf.needs_pass:
                raise InvalidPdfError("Encrypted PDFs are not supported")
            for page_index, page in enumerate(pdf):
                text = page.get_text("text", sort=True).strip()
                if text:
                    pages.append(
                        Document(
                            page_content=text,
                            metadata={"page": page_index + 1},
                        )
                    )
    except InvalidPdfError:
        raise
    except Exception as error:
        raise InvalidPdfError("The uploaded file is not a readable PDF") from error

    if not pages:
        raise InvalidPdfError(
            "The PDF contains no extractable text; scanned PDFs require OCR"
        )
    return pages


def split_pages(
    pages: list[Document], *, chunk_size: int, chunk_overlap: int
) -> list[Document]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        add_start_index=True,
    )
    return splitter.split_documents(pages)
