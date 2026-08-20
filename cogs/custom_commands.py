"""
Comandos customizados.

O dono cria "respostas rápidas" que qualquer membro pode chamar:

    /cc-add   nome:regras   resposta:Leia o canal #regras 📜
    /cc-list
    /cc-remove nome:regras
    /cc        nome:regras     -> o bot responde com o texto salvo

Tudo fica salvo no banco, então sobrevive a reinicializações.
"""

import discord
from discord import app_commands
from discord.ext import commands

import database

ACCENT = 0x2B2D31


class CustomCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    cc = app_commands.Group(name="cc", description="Comandos customizados da comunidade")

    # -------------------------------------------------------------- #
    @cc.command(name="add", description="Cria ou atualiza um comando customizado.")
    @app_commands.describe(nome="Nome do comando (uma palavra)", resposta="O que o bot responde")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def add(self, interaction: discord.Interaction, nome: str, resposta: str):
        nome = nome.strip().lower().split()[0]
        database.add_custom_command(interaction.guild_id, nome, resposta)
        await interaction.response.send_message(
            f"✅ Comando **/{'cc run nome:'}{nome}** salvo.", ephemeral=True
        )

    @cc.command(name="remove", description="Remove um comando customizado.")
    @app_commands.describe(nome="Nome do comando a remover")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def remove(self, interaction: discord.Interaction, nome: str):
        ok = database.remove_custom_command(interaction.guild_id, nome)
        msg = f"🗑️ Comando **{nome}** removido." if ok else f"❌ Não encontrei **{nome}**."
        await interaction.response.send_message(msg, ephemeral=True)

    @cc.command(name="list", description="Lista todos os comandos customizados.")
    async def list_(self, interaction: discord.Interaction):
        rows = database.list_custom_commands(interaction.guild_id)
        if not rows:
            await interaction.response.send_message(
                "Ainda não há comandos customizados. Crie com **/cc add**.",
                ephemeral=True,
            )
            return
        names = ", ".join(f"`{r['name']}`" for r in rows)
        embed = discord.Embed(
            title="Comandos customizados", description=names, color=ACCENT
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @cc.command(name="run", description="Executa um comando customizado.")
    @app_commands.describe(nome="Nome do comando a executar")
    async def run(self, interaction: discord.Interaction, nome: str):
        row = database.get_custom_command(interaction.guild_id, nome)
        if not row:
            await interaction.response.send_message(
                f"❌ Não encontrei o comando **{nome}**.", ephemeral=True
            )
            return
        await interaction.response.send_message(row["response"])

    @run.autocomplete("nome")
    async def run_autocomplete(self, interaction: discord.Interaction, current: str):
        rows = database.list_custom_commands(interaction.guild_id)
        return [
            app_commands.Choice(name=r["name"], value=r["name"])
            for r in rows
            if current.lower() in r["name"]
        ][:25]

    # -------------------------------------------------------------- #
    async def cog_app_command_error(self, interaction: discord.Interaction, error):
        if isinstance(error, app_commands.MissingPermissions):
            msg = "❌ Você precisa da permissão **Gerenciar Servidor** para isto."
        else:
            msg = f"⚠️ Ocorreu um erro: `{error}`"
        if interaction.response.is_done():
            await interaction.followup.send(msg, ephemeral=True)
        else:
            await interaction.response.send_message(msg, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(CustomCommands(bot))
