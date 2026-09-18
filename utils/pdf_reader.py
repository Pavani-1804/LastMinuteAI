from pypdf import PdfReader

def extract_text(pdf_path):
    """
    Extracts text from PDF page by page with error boundary handling for large documents.
    """
    try:
        reader = PdfReader(pdf_path)
        text_parts = []
        for i, page in enumerate(reader.pages):
            try:
                page_text = page.extract_text()
                if page_text and page_text.strip():
                    text_parts.append(f"[Page {i+1}]\n{page_text.strip()}")
            except Exception as pe:
                print(f"Skipping unreadable page {i+1}: {pe}")
                continue
        return "\n\n".join(text_parts)
    except Exception as e:
        print(f"Error reading PDF with PyPDF: {e}")
        return ""

