"""
Run this ONCE on existing databases after switching to initial_squash.

Resets alembic_version to the initial_squash revision so that
'alembic upgrade head' works without revision-not-found errors.

Usage:
    python alembic/fix_alembic.py

On a fresh clone with an empty database this script is NOT needed.
"""

import sqlite3
import os

db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "ecommerce.db")

if not os.path.exists(db_path):
    print("No existing database found. Nothing to fix.")
    exit(0)

conn = sqlite3.connect(db_path)
try:
    cur = conn.execute("SELECT version_num FROM alembic_version")
    row = cur.fetchone()
    if row is None:
        print("alembic_version is empty. Stamping initial_squash...")
        conn.execute("INSERT INTO alembic_version (version_num) VALUES (?)", ("initial_squash",))
    elif row[0] == "initial_squash":
        print("Already stamped as initial_squash. Nothing to do.")
    else:
        print(f"Found old revision '{row[0]}'. Resetting to initial_squash...")
        conn.execute("DELETE FROM alembic_version")
        conn.execute("INSERT INTO alembic_version (version_num) VALUES (?)", ("initial_squash",))
    conn.commit()
    print("Done. You can now run 'alembic upgrade head'.")
except Exception as e:
    print(f"Error: {e}")
    exit(1)
finally:
    conn.close()
