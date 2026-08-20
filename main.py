"""
Bot da Loja — arquivo principal.

Carrega o token, inicializa o banco de dados, registra os cogs
(moderação, boas-vindas, comandos customizados, loja) e sincroniza
os comandos de barra (/).

Rode com:  python main.py
"""

import asyncio
import logging
import os

import discord
from discord.ext import commands
from dotenv import load_dotenv

import database

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("bot")

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = os.getenv("GUILD_ID")

# Intents: precisamos de "members" (boas-vindas/auto-cargo) e "message_content"
# está desligado porque só usamos comandos de barra (/), mais moderno e seguro.
intents = discord.Intents.default()
intents.members = True

COGS = (
    "cogs.moderation",
    "cogs.welcome",
    "cogs.custom_commands",
    "cogs.store",
    "cogs.arquivo",
)


class StoreBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents, help_command=None)

    async def setup_hook(self):
        database.init_db()
        for ext in COGS:
            await self.load_extension(ext)
            log.info("Cog carregado: %s", ext)

        # Sincroniza os comandos de barra
        if GUILD_ID:
            guild = discord.Object(id=int(GUILD_ID))
            self.tree.copy_global_to(guild=guild)
            synced = await self.tree.sync(guild=guild)
            log.info("Sincronizados %d comandos no servidor %s", len(synced), GUILD_ID)
        else:
            synced = await self.tree.sync()
            log.info("Sincronizados %d comandos globalmente", len(synced))

    async def on_ready(self):
        log.info("Conectado como %s (ID: %s)", self.user, self.user.id)
        await self.change_presence(activity=discord.CustomActivity(name="leviticus"))


def main():
    if not TOKEN:
        raise SystemExit(
            "ERRO: defina DISCORD_TOKEN no arquivo .env "
            "(copie o .env.example para .env e preencha o token)."
        )
    bot = StoreBot()
    asyncio.run(_run(bot))


async def _run(bot: StoreBot):
    async with bot:
        await bot.start(TOKEN)


if __name__ == "__main__":
    main()
