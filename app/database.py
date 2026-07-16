import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "quetzal_zsu.db"

# SQLite's default BINARY collation sorts by Unicode code point, which misorders
# Ukrainian-specific letters: Є/І/Ї (U+0404/0406/0407) sit below "А" (U+0410) and
# Ґ (U+0490) sits above "Я" (U+042F), so e.g. "Івано-Франківська" would sort before
# "Автономна" instead of after "Запорізька". This collation sorts by the letter's
# position in the actual Ukrainian alphabet instead.
_UKRAINIAN_ALPHABET = "АБВГҐДЕЄЖЗИІЇЙКЛМНОПРСТУФХЦЧШЩЬЮЯ"
_UKRAINIAN_ORDER = {ch: i for i, ch in enumerate(_UKRAINIAN_ALPHABET)}
_UKRAINIAN_ORDER.update({ch.lower(): i for i, ch in enumerate(_UKRAINIAN_ALPHABET)})


def _ukrainian_sort_key(value: str):
    # Characters outside the Ukrainian alphabet (digits, punctuation, Latin) keep
    # their relative order via code point, placed after all alphabet letters.
    return [(_UKRAINIAN_ORDER[ch], 0) if ch in _UKRAINIAN_ORDER else (1000, ord(ch)) for ch in value]


def _ukrainian_collation(a: str, b: str) -> int:
    ka, kb = _ukrainian_sort_key(a), _ukrainian_sort_key(b)
    return (ka > kb) - (ka < kb)


def get_db():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    con.create_collation("UKRAINIAN", _ukrainian_collation)
    try:
        yield con
    finally:
        con.close()
