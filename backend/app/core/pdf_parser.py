
#backend/app/core/pdf_parser.py
from typing import Union
from pathlib import Path
from PyPDF2 import PdfReader


class PDFParser:
    """Handles PDF and plain text extraction."""

    def extract_text(self, file: Union[Path, bytes]) -> str:
        if isinstance(file, Path):
            with open(file, "rb") as f:
                reader = PdfReader(f)
                return self._extract_all(reader)
        elif isinstance(file, bytes):
            from io import BytesIO
            reader = PdfReader(BytesIO(file))
            return self._extract_all(reader)
        else:
            raise ValueError("Unsupported file type for PDFParser.")
        
    def _extract_all(self, reader: PdfReader) -> str:
        text = ""
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
        return text.strip()
