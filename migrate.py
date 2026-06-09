import json
import sqlite3
import os

# Load old data
if not os.path.exists("visits.json"):
    print("لا يوجد ملف visits.json في المجلد الحالي.")
    exit()

with open("visits.json", "r", encoding="utf-8") as f:
    old_visits = json.load(f)

# Connect to new database
conn = sqlite3.connect("visits.db")
conn.execute("PRAGMA journal_mode=WAL;")
conn.execute("""
    CREATE TABLE IF NOT EXISTS visits (
        id TEXT PRIMARY KEY,
        created_at TEXT,
        name TEXT NOT NULL,
        age INTEGER,
        phone TEXT NOT NULL,
        visit_date TEXT NOT NULL,
        visit_time TEXT,
        doctor_name TEXT,
        branch TEXT DEFAULT 'La Cite',
        address TEXT NOT NULL,
        location_link TEXT,
        selected_labs_text TEXT,
        notes TEXT,
        labs_price_before REAL DEFAULT 0,
        labs_price_after REAL DEFAULT 0,
        transport_fee REAL DEFAULT 0,
        total_price REAL DEFAULT 0
    )
""")

# Insert each old visit
for v in old_visits:
    # Map old keys to new, add missing fields
    conn.execute("""
        INSERT OR REPLACE INTO visits (
            id, created_at, name, age, phone, visit_date, visit_time,
            doctor_name, branch, address, location_link,
            selected_labs_text, notes, labs_price_before,
            labs_price_after, transport_fee, total_price
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        v.get("id"),
        v.get("created_at"),
        v.get("name"),
        v.get("age"),
        v.get("phone"),
        v.get("visit_date"),
        v.get("visit_time"),
        v.get("doctor_name", ""),
        v.get("branch", "La Cite"),  # لم يكن موجوداً، سنضعه افتراضياً La Cite
        v.get("address"),
        v.get("location_link"),
        v.get("selected_labs_text", ""),
        v.get("notes"),
        v.get("labs_price_before", v.get("labs_price", 0)),
        v.get("labs_price_after", v.get("labs_price", 0)),
        v.get("transport_fee", v.get("visit_price", 0)),
        v.get("total_price", 0)
    ))

conn.commit()
conn.close()
print(f"تم ترحيل {len(old_visits)} زيارة بنجاح.")
