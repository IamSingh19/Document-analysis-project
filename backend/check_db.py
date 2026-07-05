import sqlite3

conn = sqlite3.connect('docmind.db')
cursor = conn.cursor()
cursor.execute('SELECT id, email, username, created_at FROM users')
rows = cursor.fetchall()

print('\nUsers in database:')
print('=' * 80)
for r in rows:
    print(f'ID: {r[0]}, Email: {r[1]}, Username: {r[2]}, Created: {r[3]}')

print(f'\nTotal users: {len(rows)}')
conn.close()
