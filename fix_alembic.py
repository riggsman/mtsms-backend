import pymysql

# Connect to MySQL
conn = pymysql.connect(host='localhost', user='root', password='', database='mtsms')
cursor = conn.cursor()

# Fix column length
print("Fixing column length...")
cursor.execute("ALTER TABLE alembic_version MODIFY version_num VARCHAR(50)")
conn.commit()

# Delete all and insert single correct version
cursor.execute('DELETE FROM alembic_version')
cursor.execute("INSERT INTO alembic_version (version_num) VALUES ('20260423_add_leave_utility_requests')")
conn.commit()

# Verify
print("After:")
cursor.execute('SELECT * FROM alembic_version')
result = cursor.fetchall()
print(result)

if result and result[0][0] == '20260423_add_leave_utility_requests':
    print("\nSUCCESS: Alembic version correctly set!")
else:
    print(f"\nWarning: Got {result}")

conn.close()