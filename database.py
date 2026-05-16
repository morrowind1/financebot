import aiosqlite
from datetime import datetime

DB_NAME = "finance_bot.db"

async def init_db():
    async with aiosqlite.connect(DB_NAME) as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                amount REAL,
                description TEXT,
                category TEXT,
                date TEXT,
                satisfaction TEXT DEFAULT 'none',
                is_rounding INTEGER DEFAULT 0
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS user_settings (
                user_id INTEGER PRIMARY KEY,
                budget REAL DEFAULT 0.0,
                payday INTEGER DEFAULT 1,
                payday_month INTEGER DEFAULT 0,
                auto_round INTEGER DEFAULT 0
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS goals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                title TEXT,
                target_amount REAL,
                current_amount REAL DEFAULT 0.0
            )
        """)
        await conn.commit()

async def clear_user_data(user_id: int):
    async with aiosqlite.connect(DB_NAME) as conn:
        await conn.execute("DELETE FROM expenses WHERE user_id = ?", (user_id,))
        await conn.execute("UPDATE goals SET current_amount = 0.0 WHERE user_id = ?", (user_id,))
        await conn.commit()

async def delete_goal(goal_id: int):
    async with aiosqlite.connect(DB_NAME) as conn:
        await conn.execute("DELETE FROM goals WHERE id = ?", (goal_id,))
        await conn.commit()

async def get_user_settings(user_id: int):
    async with aiosqlite.connect(DB_NAME) as conn:
        conn.row_factory = aiosqlite.Row
        async with conn.execute("SELECT * FROM user_settings WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            if row: return dict(row)
            await conn.execute("INSERT INTO user_settings (user_id) VALUES (?)", (user_id,))
            await conn.commit()
            return {"budget": 0.0, "payday": 1, "payday_month": 0, "auto_round": 0}

async def set_user_budget(user_id: int, amount: float):
    async with aiosqlite.connect(DB_NAME) as conn:
        await conn.execute("UPDATE user_settings SET budget = ? WHERE user_id = ?", (amount, user_id))
        await conn.commit()

async def set_user_payday_full(user_id: int, day: int, month: int):
    async with aiosqlite.connect(DB_NAME) as conn:
        await conn.execute("UPDATE user_settings SET payday = ?, payday_month = ? WHERE user_id = ?", (day, month, user_id))
        await conn.commit()

async def set_auto_round(user_id: int, status: int):
    async with aiosqlite.connect(DB_NAME) as conn:
        await conn.execute("UPDATE user_settings SET auto_round = ? WHERE user_id = ?", (status, user_id))
        await conn.commit()

async def add_expense(user_id: int, amount: float, description: str, category: str):
    async with aiosqlite.connect(DB_NAME) as conn:
        date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        await conn.execute("INSERT INTO expenses (user_id, amount, description, category, date) VALUES (?, ?, ?, ?, ?)",
                           (user_id, amount, description, category, date_str))
        await conn.commit()

async def get_monthly_spent(user_id: int):
    async with aiosqlite.connect(DB_NAME) as conn:
        async with conn.execute("SELECT SUM(amount) FROM expenses WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row[0] else 0.0

async def get_stats_by_category(user_id: int):
    async with aiosqlite.connect(DB_NAME) as conn:
        async with conn.execute("SELECT category, SUM(amount) FROM expenses WHERE user_id = ? GROUP BY category", (user_id,)) as cursor:
            return await cursor.fetchall()

async def get_all_expenses_report(user_id: int):
    async with aiosqlite.connect(DB_NAME) as conn:
        async with conn.execute("SELECT date, category, description, amount, satisfaction FROM expenses WHERE user_id = ? ORDER BY id DESC", (user_id,)) as cursor:
            return await cursor.fetchall()

async def get_goals(user_id: int):
    async with aiosqlite.connect(DB_NAME) as conn:
        async with conn.execute("SELECT id, title, target_amount, current_amount FROM goals WHERE user_id = ?", (user_id,)) as cursor:
            return await cursor.fetchall()

async def add_goal(user_id: int, title: str, target: float):
    async with aiosqlite.connect(DB_NAME) as conn:
        await conn.execute("INSERT INTO goals (user_id, title, target_amount) VALUES (?, ?, ?)", (user_id, title, target))
        await conn.commit()

async def update_goal_amount(goal_id: int, amount: float):
    async with aiosqlite.connect(DB_NAME) as conn:
        await conn.execute("UPDATE goals SET current_amount = current_amount + ? WHERE id = ?", (amount, goal_id))
        await conn.commit()
