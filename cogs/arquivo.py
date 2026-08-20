"""
Arquivo — automação do cofre pessoal.

Comandos que já mandam o conteúdo formatado para o canal certo:
    /trabalho  -> ・trabalhos  (aceita anexar um arquivo)
    /prompt    -> ・prompts
    /ia        -> ・ias
    /link      -> ・links
    /ideia     -> ・ideias
    /diario    -> ・diario

Todo dia às 00:00 (horário de São Paulo) o bot monta automaticamente um
resumo do dia que terminou — lista os trabalhos enviados em ・trabalhos e
conta prompts/ideias/links/ias — e posta no ・diario com a data.
O comando /resumo gera esse mesmo resumo na hora (para o dia atual).
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

    @app_commands.command(description="Registra uma entrada manual no ・diario.")
    @app_commands.describe(texto="O que rolou hoje")
    async def diario(self, interaction: discord.Interaction, texto: str):
        embed = discord.Embed(title=hoje_str(), description=texto, color=RED)
        embed.set_footer(text="diário")
        await self._enviar(interaction, "・diario", embed)

    @app_commands.command(description="Gera agora o resumo do dia e posta no ・diario.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def resumo(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        diario = canal(interaction.guild, "・diario")
        if diario is None:
            await interaction.followup.send("❌ não encontrei o canal `・diario`.", ephemeral=True)
            return
        agora = datetime.datetime.now(TZ)
        inicio = agora.replace(hour=0, minute=0, second=0, microsecond=0)
        embed = await self._montar_resumo(interaction.guild, inicio, agora, inicio)
        await diario.send(embed=embed)
        await interaction.followup.send(f"✅ resumo do dia postado em {diario.mention}", ephemeral=True)

    # ------------------------------------------------------------------ #
    # Resumo automático do dia
    # ------------------------------------------------------------------ #
    async def _contar(self, ch, inicio, fim) -> int:
        if ch is None:
            return 0
        n = 0
        async for _ in ch.history(after=inicio, before=fim, limit=None):
            n += 1
        return n

    async def _listar_trabalhos(self, ch, inicio, fim):
        itens = []
        if ch is None:
            return itens
        async for msg in ch.history(after=inicio, before=fim, limit=None, oldest_first=True):
            titulo, desc = None, ""
            if msg.embeds:
                em = msg.embeds[0]
                titulo = em.title
                desc = em.description or ""
            if not titulo:
                primeira = (msg.content or "").strip().split("\n")[0]
                titulo = primeira[:80] if primeira else "(sem título)"
            itens.append((titulo, desc))
        return itens

    async def _montar_resumo(self, guild, inicio, fim, data_label) -> discord.Embed:
        trabalhos = await self._listar_trabalhos(canal(guild, "・trabalhos"), inicio, fim)
        n_prompts = await self._contar(canal(guild, "・prompts"), inicio, fim)
        n_ideias = await self._contar(canal(guild, "・ideias"), inicio, fim)
        n_links = await self._contar(canal(guild, "・links"), inicio, fim)
        n_ias = await self._contar(canal(guild, "・ias"), inicio, fim)

        titulo = f"📓 {data_label.strftime('%d/%m/%Y')} · {DIAS[data_label.weekday()]}"
        tally = (f"🗂️ {len(trabalhos)} trabalhos · 🧠 {n_prompts} prompts · "
                 f"💡 {n_ideias} ideias · 🔗 {n_links} links · 🤖 {n_ias} ias")
        embed = discord.Embed(title=titulo, description=tally, color=RED)

        if trabalhos:
            linhas, total = [], 0
            for i, (t, d) in enumerate(trabalhos, 1):
                linha = f"**{i}.** {t}"
                if d:
                    d1 = " ".join(d.split())
                    if len(d1) > 80:
                        d1 = d1[:77] + "…"
                    linha += f" — {d1}"
                if total + len(linha) + 1 > 1000:
                    linhas.append(f"… +{len(trabalhos) - i + 1} mais")
                    break
                linhas.append(linha)
                total += len(linha) + 1
            corpo = "\n".join(linhas)
        else:
            corpo = "nenhum trabalho enviado."
        embed.add_field(name="trabalhos do dia", value=corpo, inline=False)
        embed.set_footer(text="resumo automático · 彼岸花")
        return embed

    @tasks.loop(time=datetime.time(hour=0, minute=0, tzinfo=TZ))
    async def diario_automatico(self):
        agora = datetime.datetime.now(TZ)
        fim = agora.replace(hour=0, minute=0, second=0, microsecond=0)
        inicio = fim - datetime.timedelta(days=1)
        for guild in self.bot.guilds:
            diario = canal(guild, "・diario")
            if diario is None:
                continue
            embed = await self._montar_resumo(guild, inicio, fim, inicio)
            await diario.send(embed=embed)

    @diario_automatico.before_loop
    async def _before(self):
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot):
    await bot.add_cog(Arquivo(bot))
