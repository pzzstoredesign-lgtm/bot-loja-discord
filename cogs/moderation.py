"""
Moderação — comandos de barra para manter o servidor organizado.

/ban  /kick  /timeout  /clear  /warn  /warnings

Todos exigem as permissões apropriadas do Discord, então só a sua staff
consegue usá-los.
"""

import datetime

import discord
from discord import app_commands
from discord.ext import commands

import database

ACCENT = 0x2B2D31  # cinza-escuro elegante do Discord


class Moderation(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # -------------------------------------------------------------- #
    @app_commands.command(description="Bane um membro do servidor.")
    @app_commands.describe(membro="Quem banir", motivo="Motivo do banimento")
    @app_commands.checks.has_permissions(ban_members=True)
    async def ban(self, interaction: discord.Interaction, membro: discord.Member,
                  motivo: str = "Sem motivo informado"):
        await membro.ban(reason=f"{interaction.user}: {motivo}")
        embed = discord.Embed(
            title="Membro banido",
            description=f"**{membro}** foi banido.\n**Motivo:** {motivo}",
            color=ACCENT,
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(description="Expulsa um membro do servidor.")
    @app_commands.describe(membro="Quem expulsar", motivo="Motivo da expulsão")
    @app_commands.checks.has_permissions(kick_members=True)
    async def kick(self, interaction: discord.Interaction, membro: discord.Member,
                   motivo: str = "Sem motivo informado"):
        await membro.kick(reason=f"{interaction.user}: {motivo}")
        embed = discord.Embed(
            title="Membro expulso",
            description=f"**{membro}** foi expulso.\n**Motivo:** {motivo}",
            color=ACCENT,
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(description="Silencia um membro por um tempo (timeout).")
    @app_commands.describe(
        membro="Quem silenciar",
        minutos="Duração em minutos (1 a 40320)",
        motivo="Motivo",
    )
    @app_commands.checks.has_permissions(moderate_members=True)
    async def timeout(self, interaction: discord.Interaction, membro: discord.Member,
                      minutos: app_commands.Range[int, 1, 40320],
                      motivo: str = "Sem motivo informado"):
        until = discord.utils.utcnow() + datetime.timedelta(minutes=minutos)
        await membro.timeout(until, reason=f"{interaction.user}: {motivo}")
        embed = discord.Embed(
            title="Membro silenciado",
            description=(
                f"**{membro}** ficará em silêncio por **{minutos} min**.\n"
                f"**Motivo:** {motivo}"
            ),
            color=ACCENT,
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(description="Apaga uma quantidade de mensagens do canal.")
    @app_commands.describe(quantidade="Quantas mensagens apagar (1 a 100)")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def clear(self, interaction: discord.Interaction,
                    quantidade: app_commands.Range[int, 1, 100]):
        await interaction.response.defer(ephemeral=True)
        deleted = await interaction.channel.purge(limit=quantidade)
        await interaction.followup.send(
            f"🧹 Apaguei **{len(deleted)}** mensagens.", ephemeral=True
        )

    @app_commands.command(description="Adverte um membro e registra a advertência.")
    @app_commands.describe(membro="Quem advertir", motivo="Motivo da advertência")
    @app_commands.checks.has_permissions(moderate_members=True)
    async def warn(self, interaction: discord.Interaction, membro: discord.Member,
                   motivo: str = "Sem motivo informado"):
        database.add_warning(interaction.guild_id, membro.id, interaction.user.id, motivo)
        total = len(database.list_warnings(interaction.guild_id, membro.id))
        embed = discord.Embed(
            title="Advertência registrada",
            description=(
                f"**{membro}** recebeu uma advertência.\n"
                f"**Motivo:** {motivo}\n"
                f"**Total de advertências:** {total}"
            ),
            color=ACCENT,
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(description="Mostra as advertências de um membro.")
    @app_commands.describe(membro="De quem ver as advertências")
    @app_commands.checks.has_permissions(moderate_members=True)
    async def warnings(self, interaction: discord.Interaction, membro: discord.Member):
        warns = database.list_warnings(interaction.guild_id, membro.id)
        if not warns:
            await interaction.response.send_message(
                f"**{membro}** não tem advertências. ✨", ephemeral=True
            )
            return
        embed = discord.Embed(
            title=f"Advertências de {membro.display_name}",
            color=ACCENT,
        )
        for i, w in enumerate(warns, 1):
            embed.add_field(
                name=f"#{i} — {w['created_at'][:10]}",
                value=w["reason"],
                inline=False,
            )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # -------------------------------------------------------------- #
    async def cog_app_command_error(self, interaction: discord.Interaction, error):
        if isinstance(error, app_commands.MissingPermissions):
            msg = "❌ Você não tem permissão para usar este comando."
        elif isinstance(error, discord.Forbidden):
            msg = ("❌ Não consigo executar essa ação. Verifique se o cargo do bot "
                   "está **acima** do membro e tem as permissões necessárias.")
        else:
            msg = f"⚠️ Ocorreu um erro: `{error}`"
        if interaction.response.is_done():
            await interaction.followup.send(msg, ephemeral=True)
        else:
            await interaction.response.send_message(msg, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Moderation(bot))
