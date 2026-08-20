"""
Camada de banco de dados (SQLite).

Guarda TODAS as configurações do servidor, comandos customizados e os produtos
da loja em um único arquivo `bot.db` — nada se perde quando o bot reinicia.
"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "bot.db"


def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Cria as tabelas na primeira execução (idempotente)."""
    with _connect() as conn:
        conn.executescript(
            """
            -- Configuração geral por servidor (guild)
            CREATE TABLE IF NOT EXISTS guild_config (
                guild_id      INTEGER PRIMARY KEY,
                welcome_channel_id INTEGER,
                welcome_message    TEXT,
                autorole_id        INTEGER,
                store_name         TEXT DEFAULT 'Minha Loja',
                store_currency     TEXT DEFAULT 'R$',
                store_color        TEXT DEFAULT '#2b2d31'
            );

            -- Comandos de barra customizados criados pelo dono
            CREATE TABLE IF NOT EXISTS custom_commands (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id  INTEGER NOT NULL,
                name      TEXT NOT NULL,
                response  TEXT NOT NULL,
                UNIQUE (guild_id, name)
            );

            -- Produtos / itens da loja
            CREATE TABLE IF NOT EXISTS store_items (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id    INTEGER NOT NULL,
                name        TEXT NOT NULL,
                description TEXT DEFAULT '',
                price       REAL DEFAULT 0,
                stock       INTEGER DEFAULT -1,   -- -1 = estoque ilimitado
                image_url   TEXT DEFAULT '',
                created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            -- Registro simples de advertências (warns) de moderação
            CREATE TABLE IF NOT EXISTS warnings (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id   INTEGER NOT NULL,
                user_id    INTEGER NOT NULL,
                moderator_id INTEGER NOT NULL,
                reason     TEXT DEFAULT 'Sem motivo informado',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        conn.commit()


# ------------------------------------------------------------------ #
# Configuração do servidor
# ------------------------------------------------------------------ #
def get_config(guild_id: int) -> sqlite3.Row:
    with _connect() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO guild_config (guild_id) VALUES (?)", (guild_id,)
        )
        conn.commit()
        return conn.execute(
            "SELECT * FROM guild_config WHERE guild_id = ?", (guild_id,)
        ).fetchone()


def set_config(guild_id: int, **fields):
    """Atualiza um ou mais campos de configuração do servidor."""
    if not fields:
        return
    get_config(guild_id)  # garante que a linha existe
    columns = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [guild_id]
    with _connect() as conn:
        conn.execute(f"UPDATE guild_config SET {columns} WHERE guild_id = ?", values)
        conn.commit()


# ------------------------------------------------------------------ #
# Comandos customizados
# ------------------------------------------------------------------ #
def add_custom_command(guild_id: int, name: str, response: str):
    with _connect() as conn:
        conn.execute(
            "INSERT INTO custom_commands (guild_id, name, response) VALUES (?, ?, ?) "
            "ON CONFLICT(guild_id, name) DO UPDATE SET response = excluded.response",
            (guild_id, name.lower(), response),
        )
        conn.commit()


def remove_custom_command(guild_id: int, name: str) -> bool:
    with _connect() as conn:
        cur = conn.execute(
            "DELETE FROM custom_commands WHERE guild_id = ? AND name = ?",
            (guild_id, name.lower()),
        )
        conn.commit()
        return cur.rowcount > 0


def get_custom_command(guild_id: int, name: str):
    with _connect() as conn:
        return conn.execute(
            "SELECT * FROM custom_commands WHERE guild_id = ? AND name = ?",
            (guild_id, name.lower()),
        ).fetchone()


def list_custom_commands(guild_id: int):
    with _connect() as conn:
        return conn.execute(
            "SELECT * FROM custom_commands WHERE guild_id = ? ORDER BY name",
            (guild_id,),
        ).fetchall()


# ------------------------------------------------------------------ #
# Loja
# ------------------------------------------------------------------ #
def add_item(guild_id: int, name: str, price: float, description: str = "",
             stock: int = -1, image_url: str = "") -> int:
    with _connect() as conn:
        cur = conn.execute(
            "INSERT INTO store_items (guild_id, name, description, price, stock, image_url) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (guild_id, name, description, price, stock, image_url),
        )
        conn.commit()
        return cur.lastrowid


def update_item(guild_id: int, item_id: int, **fields) -> bool:
    if not fields:
        return False
    columns = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [item_id, guild_id]
    with _connect() as conn:
        cur = conn.execute(
            f"UPDATE store_items SET {columns} WHERE id = ? AND guild_id = ?", values
        )
        conn.commit()
        return cur.rowcount > 0


def remove_item(guild_id: int, item_id: int) -> bool:
    with _connect() as conn:
        cur = conn.execute(
            "DELETE FROM store_items WHERE id = ? AND guild_id = ?",
            (item_id, guild_id),
        )
        conn.commit()
        return cur.rowcount > 0


def get_item(guild_id: int, item_id: int):
    with _connect() as conn:
        return conn.execute(
            "SELECT * FROM store_items WHERE id = ? AND guild_id = ?",
            (item_id, guild_id),
        ).fetchone()


def list_items(guild_id: int):
    with _connect() as conn:
        return conn.execute(
            "SELECT * FROM store_items WHERE guild_id = ? ORDER BY id",
            (guild_id,),
        ).fetchall()


# ------------------------------------------------------------------ #
# Advertências
# ------------------------------------------------------------------ #
def add_warning(guild_id: int, user_id: int, moderator_id: int, reason: str) -> int:
    with _connect() as conn:
        cur = conn.execute(
            "INSERT INTO warnings (guild_id, user_id, moderator_id, reason) "
            "VALUES (?, ?, ?, ?)",
            (guild_id, user_id, moderator_id, reason),
        )
        conn.commit()
        return cur.lastrowid


def list_warnings(guild_id: int, user_id: int):
    with _connect() as conn:
        return conn.execute(
            "SELECT * FROM warnings WHERE guild_id = ? AND user_id = ? ORDER BY created_at",
            (guild_id, user_id),
        ).fetchall()
