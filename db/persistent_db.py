import aiosqlite
from enum import Enum

DB_NAME = "views.db"

class ViewType(Enum):
    RANK = "rank"
    NA = "na-roles"
    JP = "jp-roles"

async def setup_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS views (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                view_type TEXT NOT NULL,
                embed_id INTEGER NOT NULL,
                UNIQUE (guild_id, view_type)
            )
        """)
        await db.execute("CREATE INDEX IF NOT EXISTS idx_views_guild_id ON views(guild_id)")
        await db.commit()

async def fetch_view(view_type: ViewType, guild_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("""
            SELECT id, guild_id, embed_id
            FROM views
            WHERE guild_id = ? AND view_type = ?
        """, (guild_id, view_type.value))
        return await cursor.fetchone()

async def upsert_view(view_type: ViewType, embed_id: int, guild_id: int, bot):
    # Get old embed_id if exists
    old = await fetch_view(view_type, guild_id)
    if old:
        old_message_id = old[2]
        try:
            guild = bot.get_guild(guild_id)
            if guild:
                for channel in guild.text_channels:
                    try:
                        msg = await channel.fetch_message(old_message_id)
                        await msg.delete()
                        break
                    except:
                        continue
        except:
            pass

    # Insert or replace in DB
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            INSERT INTO views (guild_id, view_type, embed_id)
            VALUES (?, ?, ?)
            ON CONFLICT(guild_id, view_type) DO UPDATE SET
                embed_id = excluded.embed_id
        """, (guild_id, view_type.value, embed_id))
        await db.commit()

async def delete_view(message_id: int, guild_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            DELETE FROM views WHERE embed_id = ? AND guild_id = ?
        """, (message_id, guild_id))
        await db.commit()

async def cleanup_views(bot):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT id, guild_id, view_type, embed_id FROM views")
        rows = await cursor.fetchall()

        for row in rows:
            row_id, guild_id, view_type, embed_id = row
            guild = bot.get_guild(guild_id)
            if not guild:
                # Guild not found (bot left or no longer in guild)
                await db.execute("DELETE FROM views WHERE id = ?", (row_id,))
                continue

            found = False
            for channel in guild.text_channels:
                try:
                    msg = await channel.fetch_message(embed_id)
                    found = True
                    break
                except:
                    continue

            if not found:
                # Message no longer exists, delete DB row
                await db.execute("DELETE FROM views WHERE id = ?", (row_id,))

        await db.commit()


async def custom_query(sql_stmt: str, *params: tuple) -> None | list[tuple]:
    """
    Args:
        `sql_stmt` The SQL statement to execute.
        `*params` Parameters for the SQL statement.

    Returns:
        `list[tuple]` For SELECT statements
        `None` For non-SELECT statements
    """
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(sql_stmt, params)
        if sql_stmt.strip().lower().startswith("select"):
            rows = await cursor.fetchall()
            await cursor.close()
            return rows
        else:
            await db.commit()
            await cursor.close()
            return None
