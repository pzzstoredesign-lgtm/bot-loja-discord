"""
Envia um arquivo (e/ou um recado) do seu PC direto para um canal do Discord.

Uso basico (na pasta do bot):
    python enviar.py CAMINHO_DO_ARQUIVO
    python enviar.py CAMINHO_DO_ARQUIVO --canal trabalhos --titulo "Meu projeto"
    python enviar.py --canal ideias --texto "uma ideia sem arquivo"

Canais validos (use o nome sem o "・"):
    inicio, guia, trabalhos, prompts, ias, links, ideias, diario
"""
import argparse
import os

import discord
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))
TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID"))
RED = 0xE11228


def main():
    ap = argparse.ArgumentParser(description="Envia arquivo/recado para um canal do Discord.")
    ap.add_argument("arquivo", nargs="?", help="caminho do arquivo a enviar (opcional)")
    ap.add_argument("--canal", default="trabalhos", help="nome do canal (sem o '・')")
    ap.add_argument("--titulo", default=None, help="titulo do card (opcional)")
    ap.add_argument("--texto", default="", help="descricao/recado (opcional)")
    args = ap.parse_args()

    if not args.arquivo and not args.titulo and not args.texto:
        ap.error("informe um arquivo, ou --titulo/--texto.")

    intents = discord.Intents.default()
    client = discord.Client(intents=intents)

    @client.event
    async def on_ready():
        try:
            g = client.get_guild(GUILD_ID)
            alvo = "・" + args.canal.lstrip("・")
            ch = discord.utils.get(g.text_channels, name=alvo)
            if ch is None:
                print(f"ERRO: canal '{alvo}' nao encontrado.")
                return

            file = None
            if args.arquivo:
                if not os.path.isfile(args.arquivo):
                    print(f"ERRO: arquivo nao encontrado: {args.arquivo}")
                    return
                file = discord.File(args.arquivo)

            embed = None
            if args.titulo or args.texto:
                embed = discord.Embed(title=args.titulo, description=args.texto or None, color=RED)
                embed.set_footer(text="enviado do PC")

            await ch.send(embed=embed, file=file)
            print(f"OK: enviado para #{alvo}")
        finally:
            await client.close()

    client.run(TOKEN, log_handler=None)


if __name__ == "__main__":
    main()
