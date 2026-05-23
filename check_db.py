import sqlite3

conn = sqlite3.connect("database.db")
cursor = conn.cursor()

cursor.execute("SELECT email, password FROM users")
rows = cursor.fetchall()

for r in rows:
    print(r)

conn.close()