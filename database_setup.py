import sqlite3

def create_database():
    conn = sqlite3.connect('astah_bot.db')
    cursor = conn.cursor()

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS user_goals (
        user_id INTEGER PRIMARY KEY,
        pushups_10 INTEGER DEFAULT 0,
        points INTEGER DEFAULT 0
    )
    ''')

    conn.commit()
    conn.close()

if __name__ == "__main__":
    create_database()
