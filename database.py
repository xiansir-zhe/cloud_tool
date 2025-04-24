import sqlite3

# 初始化数据库并创建表
def init_db():
    conn = sqlite3.connect('auth.db')
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        username TEXT NOT NULL PRIMARY KEY,
        password TEXT NOT NULL
    )
    ''')
    cursor.execute('INSERT OR IGNORE INTO users (username, password) VALUES (?, ?)', ('admin', 'Welcome2tencent'))
    conn.commit()
    conn.close()

# 验证密码
def verify_password(input_password):
    conn = sqlite3.connect('auth.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE username=? AND password=?', ('admin', input_password))
    result = cursor.fetchone() is not None
    conn.close()
    return result 