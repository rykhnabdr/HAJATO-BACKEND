import mysql.connector

db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="",
    database="hajato_admin"
)
cursor = db.cursor()

# Add email and phone to vendors
try:
    cursor.execute("ALTER TABLE vendors ADD COLUMN email VARCHAR(255)")
    cursor.execute("ALTER TABLE vendors ADD COLUMN phone VARCHAR(20)")
except Exception as e:
    print(f"Vendor alter ignored (might already exist): {e}")

# Create users table
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255),
    phone VARCHAR(20),
    status ENUM('Active', 'Banned') DEFAULT 'Active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

# Insert mock user
cursor.execute("SELECT COUNT(*) FROM users")
if cursor.fetchone()[0] == 0:
    cursor.execute("INSERT INTO users (name, email, phone, status) VALUES ('Budi Santoso', 'budi@example.com', '08123456789', 'Active')")
    cursor.execute("INSERT INTO users (name, email, phone, status) VALUES ('Siti Aminah', 'siti@example.com', '08987654321', 'Active')")

# Update mock vendors with email
cursor.execute("UPDATE vendors SET email='vendor@example.com', phone='08111222333' WHERE email IS NULL")

db.commit()
print("DB setup complete.")
