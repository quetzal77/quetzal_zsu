"""Створити або оновити пароль редактора порталу.

Використання:
    python create_user.py <username>
"""

import argparse
import getpass
import sqlite3
import sys

from app.auth import hash_password
from app.database import DB_PATH


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("username")
    args = parser.parse_args()

    password = getpass.getpass("Пароль: ")
    confirm = getpass.getpass("Повторіть пароль: ")
    if password != confirm:
        print("Паролі не збігаються.")
        sys.exit(1)
    if not password:
        print("Пароль не може бути порожнім.")
        sys.exit(1)

    con = sqlite3.connect(DB_PATH)
    con.execute(
        """INSERT INTO users (username, password_hash) VALUES (?, ?)
           ON CONFLICT(username) DO UPDATE SET password_hash = excluded.password_hash""",
        (args.username, hash_password(password)),
    )
    con.commit()
    con.close()
    print(f"Готово: користувача '{args.username}' створено/оновлено.")


if __name__ == "__main__":
    main()
