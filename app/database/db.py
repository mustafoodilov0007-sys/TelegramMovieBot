import sqlite3

DB_PATH = "data/movies.db"

conn = None
cursor = None


def _init_connection():
    global conn, cursor
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS movies(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE,
        title TEXT,
        aliases TEXT,
        file_id TEXT,
        category TEXT DEFAULT 'kino',
        part INTEGER DEFAULT 1
    )
    """)
    conn.commit()

    # Eski bazalarda bo'lmagan ustunlarni qo'shish (migratsiya)
    cursor.execute("PRAGMA table_info(movies)")
    columns = [row[1] for row in cursor.fetchall()]
    if "category" not in columns:
        cursor.execute("ALTER TABLE movies ADD COLUMN category TEXT DEFAULT 'kino'")
    if "part" not in columns:
        cursor.execute("ALTER TABLE movies ADD COLUMN part INTEGER DEFAULT 1")
    if "views" not in columns:
        cursor.execute("ALTER TABLE movies ADD COLUMN views INTEGER DEFAULT 0")
    conn.commit()

    # Obunachilar (start bosgan foydalanuvchilar) — reklama/xabar yuborish uchun
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users(
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        full_name TEXT,
        joined_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)
    conn.commit()

    # Sozlamalar (masalan: majburiy obuna kanali) — admin panelidan o'zgartiriladi
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS settings(
        key TEXT PRIMARY KEY,
        value TEXT
    )
    """)
    conn.commit()


_init_connection()


def reload_connection():
    """Baza fayli tashqaridan almashtirilganda (masalan /restore) ulanishni yangilaydi."""
    global conn
    if conn:
        conn.close()
    _init_connection()


def add_movie(code, title, aliases, file_id, category="kino", part=1):
    cursor.execute(
        "INSERT INTO movies(code,title,aliases,file_id,category,part) VALUES(?,?,?,?,?,?)",
        (code, title, aliases, file_id, category, part)
    )
    conn.commit()


def get_movie_by_code(code):
    cursor.execute("SELECT * FROM movies WHERE code=?", (code,))
    return cursor.fetchone()


def search_movies(text):
    """Kod bo'yicha aniq moslik yoki nom/alias bo'yicha qisman moslikni qaytaradi."""
    like = f"%{text.lower()}%"
    cursor.execute(
        "SELECT * FROM movies WHERE code=? OR LOWER(title) LIKE ? OR LOWER(aliases) LIKE ? "
        "ORDER BY title, part",
        (text, like, like)
    )
    return cursor.fetchall()


def get_movie(text):
    results = search_movies(text)
    return results[0] if results else None


def get_all_movies(offset=0, limit=8):
    cursor.execute(
        "SELECT * FROM movies ORDER BY title, part LIMIT ? OFFSET ?",
        (limit, offset)
    )
    return cursor.fetchall()


def count_movies():
    cursor.execute("SELECT COUNT(*) FROM movies")
    return cursor.fetchone()[0]


def update_movie(code, **fields):
    allowed = {"code", "title", "aliases", "file_id", "category", "part"}
    sets, values = [], []
    for key, value in fields.items():
        if key in allowed:
            sets.append(f"{key}=?")
            values.append(value)
    if not sets:
        return
    values.append(code)
    cursor.execute(f"UPDATE movies SET {', '.join(sets)} WHERE code=?", values)
    conn.commit()


def delete_movie(code):
    cursor.execute("DELETE FROM movies WHERE code=?", (code,))
    conn.commit()


def increment_views(code):
    """Video ko'rsatilganda/yuklab olinganda chaqiriladi."""
    cursor.execute("UPDATE movies SET views = views + 1 WHERE code=?", (code,))
    conn.commit()


def get_top_movies(limit=5):
    """Eng ko'p ko'rilgan kino/multfilmlar ro'yxati, ketma-ketlikda."""
    cursor.execute(
        "SELECT * FROM movies WHERE views > 0 ORDER BY views DESC, title LIMIT ?",
        (limit,)
    )
    return cursor.fetchall()


def get_random_movie():
    cursor.execute("SELECT * FROM movies ORDER BY RANDOM() LIMIT 1")
    return cursor.fetchone()


def get_total_views():
    cursor.execute("SELECT COALESCE(SUM(views), 0) FROM movies")
    return cursor.fetchone()[0]


# ---------- Foydalanuvchilar (obunachilar) ----------

def add_user(user_id, username, full_name):
    cursor.execute(
        """
        INSERT INTO users(user_id, username, full_name) VALUES(?,?,?)
        ON CONFLICT(user_id) DO UPDATE SET username=excluded.username, full_name=excluded.full_name
        """,
        (user_id, username, full_name)
    )
    conn.commit()


def get_all_user_ids():
    cursor.execute("SELECT user_id FROM users")
    return [row[0] for row in cursor.fetchall()]


def count_users():
    cursor.execute("SELECT COUNT(*) FROM users")
    return cursor.fetchone()[0]


# ---------- Sozlamalar (majburiy obuna kanali va h.k.) ----------

def get_setting(key, default=None):
    cursor.execute("SELECT value FROM settings WHERE key=?", (key,))
    row = cursor.fetchone()
    return row[0] if row else default


def set_setting(key, value):
    cursor.execute(
        """
        INSERT INTO settings(key, value) VALUES(?,?)
        ON CONFLICT(key) DO UPDATE SET value=excluded.value
        """,
        (key, value)
    )
    conn.commit()


def delete_setting(key):
    cursor.execute("DELETE FROM settings WHERE key=?", (key,))
    conn.commit()
