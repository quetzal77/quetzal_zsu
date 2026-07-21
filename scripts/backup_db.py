"""Створює знімок data/quetzal_zsu.db у data/backups/.

Використовує sqlite3 Connection.backup() (а не копію файлу), тому безпечно
запускати навіть коли сервер працює одночасно з БД.

Використання:
    python scripts/backup_db.py [нотатка]

Приклад:
    python scripts/backup_db.py "перед імпортом 28 дивізії"
"""

import re
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

# Консолі Windows (cmd/PowerShell 5.1 з дефолтним cp1252) не завжди мають
# UTF-8 як кодування stdout, а повідомлення тут кириличні.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "quetzal_zsu.db"
BACKUP_DIR = BASE_DIR / "data" / "backups"
KEEP_LAST = 30


def _slug(text: str) -> str:
    text = text.strip().lower()
    text = re.sub(r"[^a-z0-9а-яіїєґ]+", "-", text)
    return text.strip("-")[:50]


def main() -> None:
    if not DB_PATH.exists():
        print(f"Не знайдено {DB_PATH}", file=sys.stderr)
        sys.exit(1)

    note = " ".join(sys.argv[1:]).strip()
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    name = f"quetzal_zsu_{timestamp}"
    if note:
        name += f"_{_slug(note)}"
    dest_path = BACKUP_DIR / f"{name}.db"

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    src = sqlite3.connect(DB_PATH)
    dest = sqlite3.connect(dest_path)
    try:
        src.backup(dest)
    finally:
        dest.close()
        src.close()

    print(f"Бекап збережено: {dest_path}")
    _prune()


def _prune() -> None:
    backups = sorted(BACKUP_DIR.glob("quetzal_zsu_*.db"), key=lambda p: p.stat().st_mtime)
    excess = backups[:-KEEP_LAST] if len(backups) > KEEP_LAST else []
    for old in excess:
        old.unlink()
        print(f"Видалено старий бекап: {old.name}")


if __name__ == "__main__":
    main()
