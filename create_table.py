import mysql.connector

def get_db():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="hajato_admin"
    )

db = get_db()
cursor = db.cursor()

create_table_query = """
CREATE TABLE IF NOT EXISTS vendors (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    category VARCHAR(255) NOT NULL,
    rating FLOAT DEFAULT 0.0,
    status ENUM('Pending', 'Active', 'Rejected') DEFAULT 'Pending'
)
"""

cursor.execute(create_table_query)

# Insert sample data if empty
cursor.execute("SELECT COUNT(*) FROM vendors")
count = cursor.fetchone()[0]
if count == 0:
    cursor.execute("INSERT INTO vendors (name, category, rating, status) VALUES ('Katering Harmoni', 'Catering', 4.8, 'Active')")
    cursor.execute("INSERT INTO vendors (name, category, rating, status) VALUES ('Nusantara Decor', 'Decoration', 4.5, 'Active')")
    cursor.execute("INSERT INTO vendors (name, category, rating, status) VALUES ('Pending Vendor Test', 'Photography', 0.0, 'Pending')")

db.commit()
print("Vendors table created successfully.")
