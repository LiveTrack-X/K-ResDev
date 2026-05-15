from __future__ import annotations

from pathlib import Path

TEXT_ENCODINGS = ("utf-8-sig", "utf-8", "cp949", "euc-kr")


def read_text_file(path: str | Path, limit: int | None = None) -> str:
    data = Path(path).read_bytes()
    if limit is not None:
        data = data[:limit]
    for encoding in TEXT_ENCODINGS:
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")
