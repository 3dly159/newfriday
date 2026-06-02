import os
from core.agency.files import is_safe_path, truncate


def _read_pdf(path):
    try:
        from pypdf import PdfReader
        reader = PdfReader(path)
        return "\n".join((page.extract_text() or "") for page in reader.pages)
    except Exception as e:
        return f"Could not read PDF: {e}"


def read_document(path, max_chars=8000):
    """Read a text/markdown/PDF document (safe relative path), truncated."""
    if not is_safe_path(path):
        return f"Refused: '{path}' is not an allowed path."
    if not os.path.exists(path):
        return f"No such file: {path}"
    if path.lower().endswith(".pdf"):
        return truncate(_read_pdf(path), max_chars)
    try:
        with open(path, "r", errors="replace") as f:
            return truncate(f.read(), max_chars)
    except Exception as e:
        return f"Could not read {path}: {e}"


def search_in_document(path, query, max_hits=10):
    """Return matching lines (with line numbers) containing the query, case-insensitive."""
    if not is_safe_path(path):
        return [f"Refused: '{path}' is not an allowed path."]
    text = read_document(path, max_chars=200000)
    if text.startswith("Refused") or text.startswith("No such") or text.startswith("Could not"):
        return [text]
    q = query.lower()
    hits = []
    for i, line in enumerate(text.splitlines(), 1):
        if q in line.lower():
            hits.append(f"L{i}: {line.strip()[:160]}")
            if len(hits) >= max_hits:
                break
    return hits
