"""
Ma'lumotlar bazasi moduli.

ESLATMA (tuzatish haqida):
Avval bu fayl qisqartirilgan eski versiya edi (faqat 3 ta funksiya),
to'liq baza kodi esa xato bilan app/handlers/admin.py ichiga tushib
qolgan edi. Shu sabab bot umuman ishga tushmasdi. Endi butun baza kodi
shu yerda — handlerlar kutayotgan barcha funksiyalar bilan.

MUHIM: kino qatorlari (rows) quyidagi tartibda qaytadi:
    0 id | 1 code | 2 title | 3 aliases | 4 file_id | 5 category | 6 part | 7 views
Handlerlar aynan shu indekslarga tayanadi (masalan row[7] — ko'rishlar soni),
shuning uchun "SELECT *" emas, LEFT JOIN bilan views ham qo'shib olinadi.
"""

import os
import sqlite3

DB_PATH = "data/movies.db"

os.makedirs("data", exist_ok=True)

conn = sqlite3.connect(DB_PATH, check_same_thread=False)
cursor = conn.cursor()


def reload_connection():
    """Baza fayli tashqaridan almashtirilsa (masalan backupdan tiklansa)."""
    global conn, cursor

    try:
        conn.close()
    except Exception:
        pass

    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    cursor = conn.cursor()


# =========================
# JADVALLAR
# =========================

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

# Eski bazalarda bu ustunlar bo'lmasligi mumkin
cursor.execute("PRAGMA table_info(movies)")
_movie_columns = [row[1] for row in cursor.fetchall()]

if "category" not in _movie_columns:
    cursor.execute("ALTER TABLE movies ADD COLUMN category TEXT DEFAULT 'kino'")

if "part" not in _movie_columns:
    cursor.execute("ALTER TABLE movies ADD COLUMN part INTEGER DEFAULT 1")

conn.commit()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER UNIQUE,
    username TEXT,
    full_name TEXT
)
""")
conn.commit()

cursor.execute("""
CREATE TABLE IF NOT EXISTS channels(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    channel_id TEXT UNIQUE,
    channel_url TEXT,
    title TEXT
)
""")
conn.commit()

cursor.execute("""
CREATE TABLE IF NOT EXISTS settings(
    key TEXT PRIMARY KEY,
    value TEXT
)
""")
conn.commit()

cursor.execute("""
CREATE TABLE IF NOT EXISTS movie_views(
    code TEXT PRIMARY KEY,
    views INTEGER DEFAULT 0
)
""")
conn.commit()


# Barcha kino so'rovlari uchun umumiy SELECT (views bilan birga)
_SELECT = """
    SELECT m.id, m.code, m.title, m.aliases, m.file_id,
           m.category, m.part, COALESCE(v.views, 0) AS views
    FROM movies m
    LEFT JOIN movie_views v ON v.code = m.code
"""


# =========================
# FOYDALANUVCHILAR
# =========================

def add_user(user_id, username=None, full_name=None):
    cursor.execute(
        "INSERT OR IGNORE INTO users(user_id, username, full_name) VALUES(?, ?, ?)",
        (user_id, username, full_name),
    )
    conn.commit()


def count_users():
    cursor.execute("SELECT COUNT(*) FROM users")
    return cursor.fetchone()[0]


def get_all_user_ids():
    cursor.execute("SELECT user_id FROM users")
    return [row[0] for row in cursor.fetchall()]


# =========================
# KINOLAR
# =========================

def add_movie(code, title, aliases, file_id, category="kino", part=1):
    cursor.execute(
        """INSERT OR REPLACE INTO movies(code, title, aliases, file_id, category, part)
           VALUES(?, ?, ?, ?, ?, ?)""",
        (code, title, aliases, file_id, category, part),
    )
    conn.commit()


def get_movie_by_code(code):
    cursor.execute(_SELECT + " WHERE m.code = ?", (code,))
    return cursor.fetchone()


def get_movie(text):
    """Kod bo'yicha, bo'lmasa nom/alias bo'yicha bitta natija."""
    text = (text or "").strip()

    movie = get_movie_by_code(text)
    if movie:
        return movie

    cursor.execute(
        _SELECT + " WHERE LOWER(m.title) = LOWER(?) OR LOWER(m.aliases) LIKE LOWER(?)",
        (text, f"%{text}%"),
    )
    return cursor.fetchone()


def search_movies(text):
    """Erkin qidiruv: kod, nom yoki aliaslar bo'yicha bir nechta natija."""
    text = (text or "").strip()
    if not text:
        return []

    exact = get_movie_by_code(text)
    if exact:
        return [exact]

    like = f"%{text}%"
    cursor.execute(
        _SELECT + """
        WHERE LOWER(m.title) LIKE LOWER(?)
           OR LOWER(m.aliases) LIKE LOWER(?)
           OR LOWER(m.code) LIKE LOWER(?)
        ORDER BY m.title COLLATE NOCASE, m.part
        """,
        (like, like, like),
    )
    return cursor.fetchall()


def count_movies(category=None):
    if category:
        cursor.execute("SELECT COUNT(*) FROM movies WHERE category = ?", (category,))
    else:
        cursor.execute("SELECT COUNT(*) FROM movies")
    return cursor.fetchone()[0]


def get_all_movies(offset=0, limit=10, category=None):
    if category:
        cursor.execute(
            _SELECT + " WHERE m.category = ? ORDER BY m.id DESC LIMIT ? OFFSET ?",
            (category, limit, offset),
        )
    else:
        cursor.execute(
            _SELECT + " ORDER BY m.id DESC LIMIT ? OFFSET ?",
            (limit, offset),
        )
    return cursor.fetchall()


def get_random_movie(category=None):
    if category:
        cursor.execute(
            _SELECT + " WHERE m.category = ? ORDER BY RANDOM() LIMIT 1",
            (category,),
        )
    else:
        cursor.execute(_SELECT + " ORDER BY RANDOM() LIMIT 1")
    return cursor.fetchone()


def get_top_movies(limit=5):
    """Eng ko'p ko'rilganlar. Qator[7] — ko'rishlar soni."""
    cursor.execute(
        _SELECT + " WHERE COALESCE(v.views, 0) > 0 ORDER BY views DESC, m.id DESC LIMIT ?",
        (limit,),
    )
    return cursor.fetchall()


def update_movie(code, **kwargs):
    allowed = {"code", "title", "aliases", "file_id", "category", "part"}
    fields = {k: v for k, v in kwargs.items() if k in allowed and v is not None}
    if not fields:
        return

    sets = ", ".join(f"{k} = ?" for k in fields)
    cursor.execute(
        f"UPDATE movies SET {sets} WHERE code = ?",
        (*fields.values(), code),
    )
    conn.commit()


def delete_movie(code):
    cursor.execute("DELETE FROM movies WHERE code = ?", (code,))
    cursor.execute("DELETE FROM movie_views WHERE code = ?", (code,))
    conn.commit()


# =========================
# KO'RISHLAR
# =========================

def increment_views(code):
    cursor.execute(
        """INSERT INTO movie_views(code, views) VALUES(?, 1)
           ON CONFLICT(code) DO UPDATE SET views = views + 1""",
        (code,),
    )
    conn.commit()


# Eski nom bilan ham chaqirilishi mumkin
add_view = increment_views


def get_total_views():
    cursor.execute("SELECT COALESCE(SUM(views), 0) FROM movie_views")
    return cursor.fetchone()[0]


# =========================
# MAJBURIY OBUNA KANALLARI
# =========================

def add_channel(channel_id, channel_url, title):
    cursor.execute(
        "INSERT OR REPLACE INTO channels(channel_id, channel_url, title) VALUES(?, ?, ?)",
        (channel_id, channel_url, title),
    )
    conn.commit()


def get_channels():
    cursor.execute("SELECT id, channel_id, channel_url, title FROM channels ORDER BY id")
    return cursor.fetchall()


def get_channel(row_id):
    cursor.execute(
        "SELECT id, channel_id, channel_url, title FROM channels WHERE id = ?",
        (row_id,),
    )
    return cursor.fetchone()


def update_channel(row_id, channel_id=None, channel_url=None, title=None):
    fields = {}
    if channel_id is not None:
        fields["channel_id"] = channel_id
    if channel_url is not None:
        fields["channel_url"] = channel_url
    if title is not None:
        fields["title"] = title
    if not fields:
        return

    sets = ", ".join(f"{k} = ?" for k in fields)
    cursor.execute(
        f"UPDATE channels SET {sets} WHERE id = ?",
        (*fields.values(), row_id),
    )
    conn.commit()


def delete_channel(row_id):
    cursor.execute("DELETE FROM channels WHERE id = ?", (row_id,))
    conn.commit()


# =========================
# SOZLAMALAR
# =========================

def get_setting(key, default=None):
    cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
    row = cursor.fetchone()
    return row[0] if row else default


def set_setting(key, value):
    cursor.execute(
        """INSERT INTO settings(key, value) VALUES(?, ?)
           ON CONFLICT(key) DO UPDATE SET value = excluded.value""",
        (key, str(value)),
    )
    conn.commit()
