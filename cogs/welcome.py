"""
Boas-vindas e auto-cargos.

- Quando alguém entra, envia um embed de boas-vindas no canal configurado.
- Atribui automaticamente um cargo ao novo membro (auto-role).

Configure tudo com /config-boasvindas e /config-autorole (só administradores).
"""

import discord
from discord import app_commands
from discord.ext import commands

import database

ACCENT = 0x2B2D31


class Welcome(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # -------------------------------------------------------------- #
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        cfg = database.get_config(member.guild.id)

        # Auto-cargo
        if cfg["autorole_id"]:
            role = member.guild.get_role(cfg["autorole_id"])
            if role:
                try:
                    await member.add_roles(role, reason="Auto-cargo de entrada")
                except discord.Forbidden:
                    pass

        # Mensagem de boas-vindas
        if cfg["welcome_channel_id"]:
            channel = member.guild.get_channel(cfg["welcome_channel_id"])
            if channel:
                template = cfg["welcome_message"] or (
                    "Seja bem-vindo(a), {mention}! 🎉\n"
                    "Você é o membro nº **{count}** por aqui."
                )
                text = template.replace("{mention}", member.mention) \
                               .replace("{user}", member.display_name) \
                               .replace("{server}", member.guild.name) \
                               .replace("{count}", str(member.guild.member_count))
                embed = discord.Embed(description=text, color=ACCENT)
                embed.set_thumbnail(url=member.display_avatar.url)
                try:
                    await channel.send(embed=embed)
                except discord.Forbidden:
                    pass

    # -------------------------------------------------------------- #
    @app_commands.command(
        name="config-boasvindas",
        description="Define o canal e a mensagem de boas-vindas.",
    )
    @app_commands.describe(
        canal="Canal onde as boas-vindas serão enviadas",
        mensagem="Texto. Use {mention}, {user}, {server} e {count} como variáveis.",
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def config_welcome(self, interaction: discord.Interaction,
                             canal: discord.TextChannel, mensagem: str = None):
        database.set_config(
            interaction.guild_id,
            welcome_channel_id=canal.id,
            welcome_message=mensagem,
        )
        await interaction.response.send_message(
            f"✅ Boas-vindas configuradas no canal {canal.mention}.", ephemeral=True
        )

    @app_commands.command(
        name="config-autorole",
        description="Define o cargo dado automaticamente a novos membros.",
    )
    @app_commands.describe(cargo="Cargo a ser atribuído (ou use nada para desligar)")
    @app_commands.checks.has_permissions(administrator=True)
    async def config_autorole(self, interaction: discord.Interaction,
                              cargo: discord.Role = None):
        database.set_config(
            interaction.guild_id, autorole_id=cargo.id if cargo else None
        )
        if cargo:
            msg = f"✅ Novos membros receberão o cargo **{cargo.name}**."
        else:
            msg = "✅ Auto-cargo desligado."
        await interaction.response.send_message(msg, ephemeral=True)

    # -------------------------------------------------------------- #
    async def cog_app_command_error(self, interaction: discord.Interaction, error):
        if isinstance(error, app_commands.MissingPermissions):
            msg = "❌ Apenas administradores podem configurar isto."
        else:
            msg = f"⚠️ Ocorreu um erro: `{error}`"
        if interaction.response.is_done():
            await interaction.followup.send(msg, ephemeral=True)
        else:
            await interaction.response.send_message(msg, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Welcome(bot))
