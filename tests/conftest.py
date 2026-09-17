from pathlib import Path

import pytest

from backend.core.config import settings
from backend.db.database import init_db


@pytest.fixture
def isolated_storage(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    data_dir = tmp_path / "data"
    uploads_dir = data_dir / "uploads"
    chroma_dir = data_dir / "chroma"
    database_path = data_dir / "database" / "sovereign.db"
    for path in (uploads_dir, chroma_dir, database_path.parent):
        path.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(settings, "data_dir", data_dir)
    monkeypatch.setattr(settings, "uploads_dir", uploads_dir)
    monkeypatch.setattr(settings, "chroma_dir", chroma_dir)
    monkeypatch.setattr(settings, "sqlite_db_path", database_path)
    init_db()
    return data_dir
