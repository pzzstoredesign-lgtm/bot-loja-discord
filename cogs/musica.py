"""
Música — toca do YouTube (e do Spotify via metadados -> YouTube) nos canais de voz.

Comandos:
    /musica play <busca ou link>   -> entra na sua call e toca / adiciona na fila
    /musica skip                   -> pula a atual
    /musica fila                   -> mostra a fila
    /musica pausar / retomar
    /musica parar                  -> para tudo e sai da call

Spotify: funciona sem API/credencial e sem premium — lê os nomes das faixas da
página pública do Spotify e toca o equivalente do YouTube (só playlists públicas).
"""

import asyncio
import json
import os
import re
import urllib.request

import discord
from discord import app_commands
from discord.ext import commands
import yt_dlp

RED = 0xE11228

YDL = yt_dlp.YoutubeDL({
    "format": "bestaudio/best",
    "noplaylist": True,
    "quiet": True,
    "no_warnings": True,
    "default_search": "ytsearch",
    "source_address": "0.0.0.0",
    "skip_download": True,
})
FFMPEG_BEFORE = "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5"
FFMPEG_OPTS = "-vn"


def _extract(query: str) -> dict:
    info = YDL.extract_info(query, download=False)
    if info and "entries" in info:
        info = info["entries"][0]
    return {"title": info.get("title", "áudio"),
            "stream": info["url"],
            "web": info.get("webpage_url", "")}


def _spotify_queries(url: str):
    """Lê os nomes das músicas de um link público do Spotify SEM API/credencial,
    usando a página de embed pública (props __NEXT_DATA__). Só playlists/álbuns/faixas públicos."""
    m = re.search(r"(track|playlist|album)[/:]([A-Za-z0-9]+)", url)
    if not m:
        return []
    kind, sid = m.group(1), m.group(2)
    embed = f"https://open.spotify.com/embed/{kind}/{sid}"
    req = urllib.request.Request(embed, headers={"User-Agent": "Mozilla/5.0"})
    html = urllib.request.urlopen(req, timeout=15).read().decode("utf-8", "ignore")
    mj = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.S)
    if not mj:
        return []
    entity = json.loads(mj.group(1))["props"]["pageProps"]["state"]["data"]["entity"]
    q = []
    tracks = entity.get("trackList") or []
    if tracks:
        for t in tracks:
            title = (t.get("title") or "").strip()
            artist = (t.get("subtitle") or "").strip()
            if title:
                q.append(f"{artist} - {title}".strip(" -"))
    else:
        title = (entity.get("title") or "").strip()
        artist = (entity.get("subtitle") or "").strip()
        if title:
            q.append(f"{artist} - {title}".strip(" -"))
    return q


class Player:
    def __init__(self, cog, guild, text_channel):
        self.cog = cog
        self.bot = cog.bot
        self.guild = guild
        self.text = text_channel
        self.queue = asyncio.Queue()
        self.next = asyncio.Event()
        self.current = None
        self.volume = 1.0
        self.task = self.bot.loop.create_task(self.loop())

    async def loop(self):
        await self.bot.wait_until_ready()
        while True:
            self.next.clear()
            try:
                track = await asyncio.wait_for(self.queue.get(), timeout=300)
            except asyncio.TimeoutError:
                return await self._destroy()
            vc = self.guild.voice_client
            if vc is None:
                return await self._destroy()
            try:
                src = discord.FFmpegPCMAudio(track["stream"],
                                            before_options=FFMPEG_BEFORE, options=FFMPEG_OPTS)
                src = discord.PCMVolumeTransformer(src, volume=self.volume)
                self.current = track
                vc.play(src, after=lambda e: self.bot.loop.call_soon_threadsafe(self.next.set))
                em = discord.Embed(description=f"▶ **tocando:** {track['title']}", color=RED)
                em.set_footer(text="彼岸花 · música")
                await self.text.send(embed=em)
            except Exception as e:
                await self.text.send(f"⚠️ erro ao tocar `{track['title']}`: `{e}`")
                self.next.set()
            await self.next.wait()
            self.current = None

    async def _destroy(self):
        vc = self.guild.voice_client
        if vc:
            await vc.disconnect(force=True)
        self.cog.players.pop(self.guild.id, None)


class Musica(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.players = {}

    def get_player(self, guild, text_channel):
        p = self.players.get(guild.id)
        if p is None:
            p = Player(self, guild, text_channel)
            self.players[guild.id] = p
        return p

    musica = app_commands.Group(name="musica", description="Toca músicas nos canais de voz")

    @musica.command(name="play", description="Toca (ou adiciona na fila) do YouTube/Spotify.")
    @app_commands.describe(busca="Nome da música ou link do YouTube/Spotify")
    async def play(self, interaction: discord.Interaction, busca: str):
        await interaction.response.defer()
        if not interaction.user.voice or not interaction.user.voice.channel:
            return await interaction.followup.send("❌ entre num canal de voz primeiro.")
        canal = interaction.user.voice.channel
        vc = interaction.guild.voice_client
        try:
            if vc is None:
                vc = await canal.connect(self_deaf=True)
            elif vc.channel != canal:
                await vc.move_to(canal)
        except Exception as e:
            return await interaction.followup.send(f"❌ não consegui entrar na call: `{e}`")

        is_spotify = "spotify.com" in busca or "spotify:" in busca
        if is_spotify:
            try:
                queries = await self.bot.loop.run_in_executor(None, _spotify_queries, busca)
            except Exception as e:
                return await interaction.followup.send(f"❌ erro ao ler o Spotify: `{e}`")
            if not queries:
                return await interaction.followup.send(
                    "❌ não achei músicas nesse link (a playlist precisa ser **pública**).")
        else:
            queries = [busca]

        player = self.get_player(interaction.guild, interaction.channel)
        add, primeiro = 0, None
        for q in queries[:50]:
            try:
                track = await self.bot.loop.run_in_executor(None, _extract, q)
                await player.queue.put(track)
                add += 1
                if primeiro is None:
                    primeiro = track["title"]
            except Exception:
                continue

        if add == 0:
            return await interaction.followup.send(
                "❌ não consegui pegar o áudio (o YouTube às vezes bloqueia o servidor). Tente outro termo/link.")
        if add == 1:
            await interaction.followup.send(f"✅ adicionado à fila: **{primeiro}**")
        else:
            await interaction.followup.send(f"✅ adicionadas **{add}** músicas à fila.")

    @musica.command(name="skip", description="Pula a música atual.")
    async def skip(self, interaction: discord.Interaction):
        vc = interaction.guild.voice_client
        if vc and (vc.is_playing() or vc.is_paused()):
            vc.stop()
            await interaction.response.send_message("⏭ pulada.")
        else:
            await interaction.response.send_message("❌ não tem nada tocando.", ephemeral=True)

    @musica.command(name="fila", description="Mostra a fila.")
    async def fila(self, interaction: discord.Interaction):
        p = self.players.get(interaction.guild_id)
        if not p:
            return await interaction.response.send_message("❌ fila vazia.", ephemeral=True)
        itens = list(p.queue._queue)
        desc = ""
        if p.current:
            desc += f"▶ **{p.current['title']}**\n\n"
        if itens:
            desc += "\n".join(f"`{i+1}.` {t['title']}" for i, t in enumerate(itens[:15]))
        else:
            desc += "_(sem próximas)_"
        embed = discord.Embed(title="fila", description=desc, color=RED)
        embed.set_footer(text="彼岸花 · música")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @musica.command(name="pausar", description="Pausa.")
    async def pausar(self, interaction: discord.Interaction):
        vc = interaction.guild.voice_client
        if vc and vc.is_playing():
            vc.pause()
            await interaction.response.send_message("⏸ pausado.")
        else:
            await interaction.response.send_message("❌ nada tocando.", ephemeral=True)

    @musica.command(name="retomar", description="Retoma.")
    async def retomar(self, interaction: discord.Interaction):
        vc = interaction.guild.voice_client
        if vc and vc.is_paused():
            vc.resume()
            await interaction.response.send_message("▶ retomado.")
        else:
            await interaction.response.send_message("❌ não está pausado.", ephemeral=True)

    @musica.command(name="parar", description="Para tudo e sai da call.")
    async def parar(self, interaction: discord.Interaction):
        p = self.players.get(interaction.guild_id)
        if p:
            await p._destroy()
        else:
            vc = interaction.guild.voice_client
            if vc:
                await vc.disconnect(force=True)
        await interaction.response.send_message("⏹ parei e saí da call.")


async def setup(bot: commands.Bot):
    await bot.add_cog(Musica(bot))
