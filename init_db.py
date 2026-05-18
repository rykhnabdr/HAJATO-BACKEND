import mysql.connector
import hashlib

# koneksi ke MySQL
conn = mysql.connector.connect(
    host="localhost",
    user="root",
    password="",
    database="hajato_admin"
)

cursor = conn.cursor()

# buat tabel admin
cursor.execute("""
CREATE TABLE IF NOT EXISTS admin (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50),
    password VARCHAR(255)
)
""")

# hash password
password = "admin123"
hashed = hashlib.sha256(password.encode()).hexdigest()

# insert admin
cursor.execute("DELETE FROM admin")  # biar ga dobel
cursor.execute(
    "INSERT INTO admin (username, password) VALUES (%s, %s)",
    ("admin", hashed)
)

conn.commit()
conn.close()

print("Database siap + password sudah di-hash!")