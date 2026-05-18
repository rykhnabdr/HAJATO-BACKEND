import mysql.connector

db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="",
    database="hajato_admin"
)
cursor = db.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS orders (
    id INT AUTO_INCREMENT PRIMARY KEY,
    order_number VARCHAR(50) NOT NULL,
    customer_name VARCHAR(255) NOT NULL,
    vendor_name VARCHAR(255) NOT NULL,
    date DATE NOT NULL,
    amount DECIMAL(15,2) NOT NULL,
    status ENUM('Pending', 'Completed', 'Cancelled') DEFAULT 'Pending'
)
""")

# Insert mock orders if empty
cursor.execute("SELECT COUNT(*) FROM orders")
if cursor.fetchone()[0] == 0:
    cursor.execute("INSERT INTO orders (order_number, customer_name, vendor_name, date, amount, status) VALUES ('#ORD-2026', 'Budi Santoso', 'Katering Harmoni', '2026-04-24', 15000000, 'Completed')")
    cursor.execute("INSERT INTO orders (order_number, customer_name, vendor_name, date, amount, status) VALUES ('#ORD-2027', 'Siti Aminah', 'Nusantara Decor', '2026-04-25', 8500000, 'Pending')")
    cursor.execute("INSERT INTO orders (order_number, customer_name, vendor_name, date, amount, status) VALUES ('#ORD-2028', 'Andi Wijaya', 'Abadi Photography', '2026-04-26', 4200000, 'Completed')")

db.commit()
print("Orders table created and seeded.")
