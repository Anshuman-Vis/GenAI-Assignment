import hashlib
import re

def chunks(text: str, source: str, metadata: dict, size: int, overlap: int):
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []
    if overlap >= size:
        raise ValueError("CHUNK_OVERLAP must be smaller than CHUNK_SIZE")
    out, start, ordinal = [], 0, 0
    while start < len(text):
        end = min(len(text), start + size)
        if end < len(text):
            boundary = max(text.rfind(". ", start, end), text.rfind(" ", start, end))
            if boundary > start + size // 2:
                end = boundary + 1
        body = text[start:end].strip()
        digest = hashlib.sha256(f"{source}|{ordinal}|{body}".encode()).hexdigest()[:20]
        out.append({"id": digest, "text": body, "source": source, "ordinal": ordinal, **metadata})
        ordinal += 1
        if end == len(text): break
        start = end - overlap
    return out
