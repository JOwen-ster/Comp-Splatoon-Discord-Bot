import aiosqlite
from enum import Enum
from typing import Optional, List, Tuple, Union
from utils.loggingsetup import getlog

DB_NAME = "views.db"

class ViewType(Enum):
    RANK = "rank"
    NA = "na"
    JP = "jp"

async def setup_db() -> None:
    getlog().info("Setting up the database...")
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS views (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                channel_id INTEGER NOT NULL,
                message_id INTEGER NOT NULL,
                view_type TEXT NOT NULL,
                UNIQUE (guild_id, view_type)
            )
        """)
        getlog().info("Created 'views' table with UNIQUE constraint if it didn't exist.")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_views_guild_id ON views(guild_id)")
        getlog().info("Ensured index on guild_id.")
        await db.commit()
    getlog().info("Database setup complete.")


async def fetch_view(view_type: ViewType, guild_id: int) -> Optional[Tuple[int, int, int, int]]:
    getlog().info(f"Fetching view for guild_id={guild_id} and view_type={view_type.value}...")
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("""
            SELECT id, guild_id, channel_id, message_id
            FROM views
            WHERE guild_id = ? AND view_type = ?
        """, (guild_id, view_type.value)) as cursor:
            row = await cursor.fetchone()
    if row:
        getlog().info(f"Found view in DB: {row}")
    else:
        getlog().info("No view found.")
    return row

async def fetch_all_views() -> List[Tuple[int, int, str, int]]:
    getlog().info("Fetching all views from the database...")
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT guild_id, channel_id, view_type, message_id FROM views") as cursor:
            rows = await cursor.fetchall()
    getlog().info(f"Fetched {len(rows)} views.")
    return rows

async def insert_view(view_type: ViewType, guild_id: int, channel_id: int, message_id: int, bot) -> None:
    getlog().info(f"Inserting/updating view: guild_id={guild_id}, view_type={view_type.value}, channel_id={channel_id}, message_id={message_id}")

    old = await fetch_view(view_type, guild_id)
    if old:
        _, _, old_channel_id, old_message_id = old
        getlog().info(f"Old view exists. Deleting old message: channel_id={old_channel_id}, message_id={old_message_id}")
        try:
            guild = bot.get_guild(guild_id)
            if guild:
                channel = guild.get_channel(old_channel_id)
                if channel:
                    try:
                        msg = await channel.fetch_message(old_message_id)
                        await msg.delete()
                        getlog().info("Old message deleted successfully.")
                    except Exception as e:
                        getlog().error(f"Failed to delete old message: {e}")
        except Exception as e:
            getlog().error(f"Exception while deleting old message: {e}")

    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            INSERT INTO views (guild_id, channel_id, message_id, view_type)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(guild_id, view_type) DO UPDATE SET
                channel_id = excluded.channel_id,
                message_id = excluded.message_id
        """, (guild_id, channel_id, message_id, view_type.value))
        await db.commit()
    getlog().info("View inserted/updated in DB.")

async def delete_view(message_id: int, guild_id: int) -> None:
    getlog().info(f"Deleting view from DB: guild_id={guild_id}, message_id={message_id}")
    async with aiosqlite.connect(DB_NAME) as db:
        res = await db.execute("DELETE FROM views WHERE message_id = ? AND guild_id = ?", (message_id, guild_id))
        await db.commit()
    getlog().info(f"{res}")

async def custom_query(sql_stmt: str, *params) -> Union[None, List[Tuple]]:
    getlog().info(f"Running custom query: {sql_stmt} with params: {params}")
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(sql_stmt, params) as cursor:
            if sql_stmt.strip().lower().startswith("select"):
                rows = await cursor.fetchall()
                getlog().info(f"Custom select query returned {len(rows)} rows.")
                return rows
            else:
                await db.commit()
                getlog().info("Custom non-select query executed and committed.")
                return None

async def print_all_views() -> None:
    getlog().info("Printing all views from the database:")
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT * FROM views") as cursor:
            rows = await cursor.fetchall()

        if not rows:
            getlog().info("Database is empty.")
            print("Database is empty.")
            return

        async with db.execute("PRAGMA table_info(views)") as col_cursor:
            columns_info = await col_cursor.fetchall()

        columns = [col[1] for col in columns_info]

        header = " | ".join(columns)
        getlog().info(f"Columns: {header}")
        print(header)
        print("-" * 50)

        for row in rows:
            line = " | ".join(str(item) for item in row)
            getlog().info(f"Row: {line}")
            print(line)
