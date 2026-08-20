"""
Arquivo — automação do cofre pessoal.

Comandos que já mandam o conteúdo formatado para o canal certo:
    /trabalho  -> ・trabalhos  (aceita anexar um arquivo)
    /prompt    -> ・prompts
    /ia        -> ・ias
    /link      -> ・links
    /ideia     -> ・ideias
    /diario    -> ・diario

Além disso, todo dia às 08:00 (horário de São Paulo) o bot posta
automaticamente o cabeçalho da data no ・diario.
"""

import datetime
from zoneinfo import ZoneInfo

import discord
from discord import app_commands
from discord.ext import commands, tasks

RED = 0xE11228
TZ = ZoneInfo("America/Sao_Paulo")
DIAS = ["segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo"]


def canal(guild: discord.Guild, nome: str):
    for c in guild.text_channels:
        if c.name == nome:
            return c
    return None


def hoje_str() -> str:
    agora = datetime.datetime.now(TZ)
    return f"{agora.strftime('%d/%m/%Y')} · {DIAS[agora.weekday()]}"


class Arquivo(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.diario_automatico.start()

    def cog_unload(self):
        self.diario_automatico.cancel()

    async def _enviar(self, interaction: discord.Interaction, nome_canal: str,
                      embed: discord.Embed, file: discord.File | None = None):
        ch = canal(interaction.guild, nome_canal)
        if ch is None:
            await interaction.response.send_message(
                f"❌ não encontrei o canal `{nome_canal}`.", ephemeral=True)
            return
        if file is not None:
            await ch.send(embed=embed, file=file)
        else:
            await ch.send(embed=embed)
        await interaction.response.send_message(f"✅ enviado para {ch.mention}", ephemeral=True)

    # ------------------------------------------------------------------ #
    @app_commands.command(description="Envia um projeto/trabalho para ・trabalhos (aceita arquivo).")
    @app_commands.describe(titulo="Nome do trabalho", descricao="Descrição curta",
                           arquivo="Arquivo do trabalho (opcional)")
    async def trabalho(self, interaction: discord.Interaction, titulo: str,
                       descricao: str = "", arquivo: discord.Attachment = None):
        embed = discord.Embed(title=titulo, description=descricao or None, color=RED)
        embed.set_author(name=interaction.user.display_name,
                         icon_url=interaction.user.display_avatar.url)
        embed.set_footer(text=f"trabalho · {hoje_str()}")
        f = None
        if arquivo is not None:
            f = await arquivo.to_file()
            if arquivo.content_type and arquivo.content_type.startswith("image"):
                embed.set_image(url=f"attachment://{f.filename}")
        await self._enviar(interaction, "・trabalhos", embed, f)

    @app_commands.command(description="Salva um prompt em ・prompts.")
    @app_commands.describe(titulo="Nome do prompt", conteudo="O prompt completo", tags="Tags (opcional)")
    async def prompt(self, interaction: discord.Interaction, titulo: str,
                     conteudo: str, tags: str = ""):
        embed = discord.Embed(title=titulo, description=f"```\n{conteudo[:3900]}\n```", color=RED)
        if tags:
            embed.add_field(name="tags", value=tags, inline=False)
        embed.set_footer(text=f"prompt · {hoje_str()}")
        await self._enviar(interaction, "・prompts", embed)

    @app_commands.command(description="Registra uma ferramenta de IA em ・ias.")
    @app_commands.describe(nome="Nome da IA", uso="Pra que você usa", link="Link (opcional)")
    async def ia(self, interaction: discord.Interaction, nome: str, uso: str = "", link: str = ""):
        desc = uso
        if link:
            desc = (desc + "\n" if desc else "") + link
        embed = discord.Embed(title=nome, description=desc or None, color=RED)
        embed.set_footer(text=f"ia · {hoje_str()}")
        await self._enviar(interaction, "・ias", embed)

    @app_commands.command(description="Salva um link em ・links.")
    @app_commands.describe(url="O link", nota="Nota curta (opcional)")
    async def link(self, interaction: discord.Interaction, url: str, nota: str = ""):
        embed = discord.Embed(description=f"[{nota or url}]({url})", color=RED)
        embed.set_footer(text=f"link · {hoje_str()}")
        await self._enviar(interaction, "・links", embed)

    @app_commands.command(description="Anota uma ideia em ・ideias.")
    @app_commands.describe(texto="A ideia")
    async def ideia(self, interaction: discord.Interaction, texto: str):
        embed = discord.Embed(description=texto, color=RED)
        embed.set_footer(text=f"ideia · {hoje_str()}")
        await self._enviar(interaction, "・ideias", embed)

    @app_commands.command(description="Registra uma entrada no ・diario.")
    @app_commands.describe(texto="O que rolou hoje")
    async def diario(self, interaction: discord.Interaction, texto: str):
        embed = discord.Embed(title=hoje_str(), description=texto, color=RED)
        embed.set_footer(text="diário")
        await self._enviar(interaction, "・diario", embed)

    # ------------------------------------------------------------------ #
    @tasks.loop(time=datetime.time(hour=8, minute=0, tzinfo=TZ))
    async def diario_automatico(self):
        for guild in self.bot.guilds:
            ch = canal(guild, "・diario")
            if ch:
                embed = discord.Embed(title=f"— {hoje_str()} —", color=RED)
                await ch.send(embed=embed)

    @diario_automatico.before_loop
    async def _before(self):
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot):
    await bot.add_cog(Arquivo(bot))
