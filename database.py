import sqlite3
from contextlib import contextmanager

DB_PATH = "database.db"


@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_db():
    with get_db() as conn:
        # Таблица пользователей
        conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                full_name TEXT,
                age INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP
            )
        ''')

        # Таблица профиля пользователя
        conn.execute('''
            CREATE TABLE IF NOT EXISTS fitness_profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                height REAL NOT NULL,
                weight REAL NOT NULL,
                age INTEGER NOT NULL,
                gender TEXT NOT NULL,
                bmi REAL,
                bmi_category TEXT,
                activity TEXT,
                fitness_self TEXT,
                fitness_level TEXT,
                goal TEXT,
                daily_calories INTEGER DEFAULT 0,
                target_weight REAL,
                saved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        ''')

        # Таблица результатов тестов
        conn.execute('''
            CREATE TABLE IF NOT EXISTS fitness_tests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                test_date DATE NOT NULL DEFAULT CURRENT_DATE,
                pullups INTEGER,
                pushups INTEGER,
                benchpress INTEGER,
                plank INTEGER,
                run REAL,
                walking INTEGER,
                total_score INTEGER,
                level TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                UNIQUE(user_id, test_date)
            )
        ''')

        # Таблица истории изменений (С ВЕСОМ!)
        conn.execute('''
            CREATE TABLE IF NOT EXISTS fitness_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                date DATE NOT NULL DEFAULT CURRENT_DATE,
                weight REAL,
                fitness_score INTEGER,
                fitness_level TEXT,
                pullups INTEGER,
                pushups INTEGER,
                benchpress INTEGER,
                plank INTEGER,
                run REAL,
                walking INTEGER,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                UNIQUE(user_id, date)
            )
        ''')

        # Таблица истории веса
        conn.execute('''
            CREATE TABLE IF NOT EXISTS weight_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                date DATE NOT NULL DEFAULT CURRENT_DATE,
                weight REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, date),
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        ''')

        # Таблица дневника питания
        conn.execute('''
            CREATE TABLE IF NOT EXISTS nutrition_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                date DATE NOT NULL DEFAULT CURRENT_DATE,
                meal_type TEXT NOT NULL,
                food_name TEXT NOT NULL,
                grams INTEGER NOT NULL,
                calories INTEGER DEFAULT 0,
                protein REAL DEFAULT 0,
                fat REAL DEFAULT 0,
                carbs REAL DEFAULT 0,
                logged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        ''')

        conn.commit()


def execute_query(query: str, params=()):
    with get_db() as conn:
        cur = conn.execute(query, params)
        conn.commit()
        return cur.lastrowid


def fetch_one(query: str, params=()):
    with get_db() as conn:
        return conn.execute(query, params).fetchone()


def fetch_all(query: str, params=()):
    with get_db() as conn:
        return conn.execute(query, params).fetchall()