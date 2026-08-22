"""
Agenda — rotina saudável automática + compromissos do dia com ping na hora.

Todo dia, nos horários abaixo, o bot te marca no canal ・agenda.
Você também pode adicionar compromissos seus:

    /agenda add     hora:HH:MM  texto:...
    /agenda ver
    /agenda remover hora:HH:MM

Os compromissos ficam salvos como mensagens no próprio ・agenda, então
sobrevivem a reinicializações do bot.
"""

import datetime
import re
from zoneinfo import ZoneInfo

import discord
from discord import app_commands
from discord.ext import commands, tasks

RED = 0xFFFFFF
TZ = ZoneInfo("America/Sao_Paulo")
CANAL = "・agenda"
HHMM = re.compile(r"^([01]?\d|2[0-3]):[0-5]\d$")

# Rotina fixa para uma vida saudável (a partir das 12:15)
ROTINA = [
    ("12:15", "食", "hora de almoçar — sai do PC pra comer"),
    ("13:00", "絵", "trabalhar na PZZ Store design"),
    ("14:30", "休", "pausa: levanta, alonga, sai do PC uns 5 min"),
    ("14:45", "商", "trabalhar no TikTok Shop — ofertas e vídeos"),
    ("16:00", "犬", "brincar com a cachorra"),
    ("16:20", "金", "trabalhar nas contas monetizadas"),
    ("17:45", "運", "exercício / treino"),
    ("18:45", "食", "lanche — come algo leve"),
    ("19:15", "絵", "voltar pra PZZ Store design"),
    ("20:45", "休", "pausa longa: sai do PC e respira"),
    ("21:15", "食", "jantar"),
    ("22:00", "犬", "tempo com a cachorra e relaxar"),
    ("23:00", "眠", "desligar as telas e descansar"),
]


def canal(guild):
    return discord.utils.get(guild.text_channels, name=CANAL)


def norm(h):
    hh, mm = h.split(":")
    return f"{int(hh):02d}:{mm}"


class Agenda(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.custom = {}      # guild_id -> list de {hora, texto, msg_id}
        self._fired = {}      # "guild|hora|texto" -> data (evita repetir no mesmo dia)
        self.tick.start()

    def cog_unload(self):
        self.tick.cancel()

    # ---------------- carregar compromissos salvos ----------------
    async def _carregar(self, guild):
        ch = canal(guild)
        itens = []
        if ch is not None:
            async for msg in ch.history(limit=200):
                if (msg.author.id == self.bot.user.id and msg.embeds
                        and msg.embeds[0].footer and msg.embeds[0].footer.text == "compromisso"):
                    em = msg.embeds[0]
                    if em.title and HHMM.match(em.title):
                        itens.append({"hora": norm(em.title), "texto": em.description or "", "msg_id": msg.id})
        self.custom[guild.id] = itens

    # ---------------- loop principal ----------------
    @tasks.loop(seconds=30)
    async def tick(self):
        agora = datetime.datetime.now(TZ)
        hhmm = agora.strftime("%H:%M")
        hoje = agora.strftime("%Y-%m-%d")
        for guild in self.bot.guilds:
            ch = canal(guild)
            if ch is None:
                continue
            mention = f"<@{guild.owner_id}>"
            # rotina fixa
            for hora, emoji, texto in ROTINA:
                if hora == hhmm:
                    key = f"{guild.id}|{hora}|{texto}"
                    if self._fired.get(key) != hoje:
                        self._fired[key] = hoje
                        await ch.send(f"時 {mention} — **{hora}** · {emoji} {texto}")
            # compromissos personalizados
            for it in self.custom.get(guild.id, []):
                if it["hora"] == hhmm:
                    key = f"{guild.id}|{it['hora']}|{it['texto']}"
                    if self._fired.get(key) != hoje:
                        self._fired[key] = hoje
                        await ch.send(f"時 {mention} — **{it['hora']}** · {it['texto']}")

    @tick.before_loop
    async def _before(self):
        await self.bot.wait_until_ready()
        for guild in self.bot.guilds:
            await self._carregar(guild)

    # ---------------- comandos ----------------
    agenda = app_commands.Group(name="agenda", description="Rotina do dia e compromissos")

    @agenda.command(name="ver", description="Mostra a rotina do dia e seus compromissos.")
    async def ver(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        linhas = [f"`{h}` {e} {t}" for h, e, t in ROTINA]
        embed = discord.Embed(title="予定 ﹒ rotina do dia", description="\n".join(linhas), color=RED)
        extras = self.custom.get(interaction.guild_id, [])
        if extras:
            extras_ord = sorted(extras, key=lambda x: x["hora"])
            embed.add_field(name="seus compromissos",
                            value="\n".join(f"`{x['hora']}` {x['texto']}" for x in extras_ord),
                            inline=False)
        embed.set_footer(text="彼岸花 · o bot te marca em cada horário")
        await interaction.followup.send(embed=embed, ephemeral=True)

    @agenda.command(name="add", description="Adiciona um compromisso diário que te marca na hora.")
    @app_commands.describe(hora="Horário no formato HH:MM (ex.: 15:30)", texto="O compromisso")
    async def add(self, interaction: discord.Interaction, hora: str, texto: str):
        await interaction.response.defer(ephemeral=True)
        hora = hora.strip()
        if not HHMM.match(hora):
            await interaction.followup.send("❌ horário inválido. Use `HH:MM`, ex.: `15:30`.", ephemeral=True)
            return
        hora = norm(hora)
        ch = canal(interaction.guild)
        if ch is None:
            await interaction.followup.send("❌ não encontrei o canal `・agenda`.", ephemeral=True)
            return
        embed = discord.Embed(title=hora, description=texto, color=RED)
        embed.set_footer(text="compromisso")
        msg = await ch.send(embed=embed)
        self.custom.setdefault(interaction.guild_id, []).append(
            {"hora": hora, "texto": texto, "msg_id": msg.id})
        await interaction.followup.send(f"✅ marcado: **{hora}** · {texto} (te marco todo dia nesse horário)", ephemeral=True)

    @agenda.command(name="remover", description="Remove um compromisso pelo horário.")
    @app_commands.describe(hora="Horário do compromisso (HH:MM)")
    async def remover(self, interaction: discord.Interaction, hora: str):
        await interaction.response.defer(ephemeral=True)
        hora = norm(hora) if HHMM.match(hora.strip()) else hora.strip()
        ch = canal(interaction.guild)
        itens = self.custom.get(interaction.guild_id, [])
        alvo = [x for x in itens if x["hora"] == hora]
        if not alvo:
            await interaction.followup.send(f"❌ não achei compromisso às `{hora}`.", ephemeral=True)
            return
        for x in alvo:
            try:
                m = await ch.fetch_message(x["msg_id"])
                await m.delete()
            except Exception:
                pass
            itens.remove(x)
        await interaction.followup.send(f"🗑️ removido(s) {len(alvo)} compromisso(s) às `{hora}`.", ephemeral=True)

    async def cog_app_command_error(self, interaction, error):
        msg = f"⚠️ deu um erro: `{error}`"
        try:
            if interaction.response.is_done():
                await interaction.followup.send(msg, ephemeral=True)
            else:
                await interaction.response.send_message(msg, ephemeral=True)
        except Exception:
            pass


async def setup(bot: commands.Bot):
    await bot.add_cog(Agenda(bot))
