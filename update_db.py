import sqlite3

# 連接本地資料庫
conn = sqlite3.connect("focus_space.db")
cursor = conn.cursor()

try:
    # 嘗試新增 email 欄位
    cursor.execute("ALTER TABLE users ADD COLUMN email TEXT")
    print("✅ 成功！本地資料庫已新增 email 欄位。")
except sqlite3.OperationalError:
    print("⚠️ email 欄位可能已經存在，跳過此步驟。")

conn.commit()
conn.close()