import sqlite3

conn = sqlite3.connect("annonces.db")
c = conn.cursor()

c.execute('''
CREATE TABLE IF NOT EXISTS annonces (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    titre TEXT,
    entreprise TEXT,
    lieu TEXT,
    date_pub TEXT,
    url TEXT UNIQUE,
    last_seen TEXT
)
''')

conn.commit()
conn.close()
print("✅ Table annonces créée.")
