"""Fix relative_path in documents table — strip 'upload/' prefix."""
import sqlite3
import os

db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "ecommerce.db")

if not os.path.exists(db_path):
    print("No database found.")
    exit(0)

conn = sqlite3.connect(db_path)
cur = conn.cursor()

# Find documents with wrong relative_path
rows = cur.execute(
    "SELECT id, relative_path FROM documents WHERE relative_path LIKE 'upload\\%' OR relative_path LIKE 'upload/%'"
).fetchall()

if not rows:
    # Try alternative: might already use forward slashes on some OS
    rows = cur.execute(
        "SELECT id, relative_path FROM documents WHERE relative_path LIKE ? OR relative_path LIKE ?",
        ("upload\\%", "upload/%"),
    ).fetchall()

print(f"Found {len(rows)} documents with wrong relative_path")

fixed = 0
for doc_id, old_path in rows:
    # Strip 'upload/' or 'upload\' prefix
    if old_path.startswith("upload/") or old_path.startswith("upload\\"):
        new_path = old_path[len("upload/"):] if old_path.startswith("upload/") else old_path[len("upload\\"):]
    else:
        new_path = old_path

    if old_path != new_path:
        cur.execute("UPDATE documents SET relative_path = ? WHERE id = ?", (new_path, doc_id))
        print(f"  {doc_id[:8]}...: {old_path} -> {new_path}")
        fixed += 1

conn.commit()
conn.close()

print(f"Fixed {fixed} document(s).")
