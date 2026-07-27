import sqlite3
conn = sqlite3.connect("/opt/mobkomrobot/data.db")
conn.execute("INSERT OR REPLACE INTO users (user_id, role, username, name) VALUES (8592139483, 'admin', 'wget1337', 'Admin')")
conn.commit()
print("Admin set successfully")
conn.close()
