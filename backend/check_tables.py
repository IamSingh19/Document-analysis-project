import sqlite3

conn = sqlite3.connect('docmind.db')
cursor = conn.cursor()

# Get all tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()

print('\nTables in database:')
print('=' * 80)
for table in tables:
    print(f'- {table[0]}')
    cursor.execute(f'SELECT COUNT(*) FROM {table[0]}')
    count = cursor.fetchone()[0]
    print(f'  Records: {count}')
    
conn.close()
