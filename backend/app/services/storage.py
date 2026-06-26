import uuid
from pathlib import Path

# Local-disk storage for iteration 3. Swap for an S3-compatible backend
# before production — the call sites only depend on save()/read() below.
STORAGE_ROOT = Path(__file__).resolve().parent.parent.parent / "storage"


def save(org_id: uuid.UUID, filename: str, content: bytes) -> str:
    org_dir = STORAGE_ROOT / str(org_id)
    org_dir.mkdir(parents=True, exist_ok=True)

    path = org_dir / f"{uuid.uuid4()}_{filename}"
    path.write_bytes(content)
    return str(path.relative_to(STORAGE_ROOT))


def read(relative_path: str) -> bytes:
    return (STORAGE_ROOT / relative_path).read_bytes()
