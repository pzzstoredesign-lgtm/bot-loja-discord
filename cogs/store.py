"""
Painel de Loja — minimalista, bonito e persistente.

Você (dono) configura a loja e cadastra produtos; qualquer membro vê o
catálogo em um painel limpo, com navegação por botões.

Comandos do dono (permissão: Gerenciar Servidor):
    /loja config     nome / moeda / cor
    /loja add        cadastra um produto
    /loja edit       edita um produto pelo ID
    /loja remove     remove um produto pelo ID

Comando público:
    /loja ver        abre o catálogo (painel navegável)

Tudo é salvo no banco (bot.db) — nada se perde ao reiniciar.
"""

import discord
from discord import app_commands
from discord.ext import commands

import database


def parse_color(value: str, default: int = 0x2B2D31) -> int:
    """Converte '#rrggbb' ou 'rrggbb' em inteiro de cor. Cai no padrão se inválido."""
    if not value:
        return default
    try:
        return int(value.lstrip("#"), 16)
    except ValueError:
        return default


def money(value: float, currency: str) -> str:
    return f"{currency} {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def stock_label(stock: int) -> str:
    if stock < 0:
        return "♾️ disponível"
    if stock == 0:
        return "⛔ esgotado"
    return f"📦 {stock} em estoque"


# ------------------------------------------------------------------ #
# Painel navegável do catálogo
# ------------------------------------------------------------------ #
class StoreView(discord.ui.View):
    """Um produto por página, com botões ◀ ▶. Minimalista e limpo."""

    def __init__(self, items, cfg, author_id: int):
        super().__init__(timeout=180)
        self.items = items
        self.cfg = cfg
        self.author_id = author_id
        self.index = 0
        self._refresh_buttons()

    def _refresh_buttons(self):
        self.prev.disabled = self.index == 0
        self.next.disabled = self.index >= len(self.items) - 1

    def make_embed(self) -> discord.Embed:
        item = self.items[self.index]
        color = parse_color(self.cfg["store_color"])
        currency = self.cfg["store_currency"]

        embed = discord.Embed(
            title=item["name"],
            description=item["description"] or "​",
            color=color,
        )
        embed.add_field(name="Preço", value=money(item["price"], currency), inline=True)
        embed.add_field(name="Estoque", value=stock_label(item["stock"]), inline=True)
        if item["image_url"]:
            embed.set_image(url=item["image_url"])
        embed.set_author(name=self.cfg["store_name"] or "Loja")
        embed.set_footer(
            text=f"Produto {self.index + 1} de {len(self.items)}  •  ID {item['id']}"
        )
        return embed

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        # Só quem abriu o painel navega (mantém limpo para os outros).
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "Abra o seu próprio catálogo com **/loja ver** 🙂", ephemeral=True
            )
            return False
        return True

    @discord.ui.button(emoji="◀", style=discord.ButtonStyle.secondary)
    async def prev(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.index = max(0, self.index - 1)
        self._refresh_buttons()
        await interaction.response.edit_message(embed=self.make_embed(), view=self)

    @discord.ui.button(emoji="▶", style=discord.ButtonStyle.secondary)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.index = min(len(self.items) - 1, self.index + 1)
        self._refresh_buttons()
        await interaction.response.edit_message(embed=self.make_embed(), view=self)


# ------------------------------------------------------------------ #
# Cog
# ------------------------------------------------------------------ #
class Store(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    loja = app_commands.Group(name="loja", description="Painel e catálogo da loja")

    # ---------------------- Config ----------------------- #
    @loja.command(name="config", description="Personaliza o nome, a moeda e a cor da loja.")
    @app_commands.describe(
        nome="Nome exibido no topo do catálogo",
        moeda="Símbolo da moeda (ex.: R$, US$, €)",
        cor="Cor em hexadecimal, ex.: #5865F2",
    )
    @app_commands.checks.has_permissions(manage_guild=True)
    async def config(self, interaction: discord.Interaction,
                     nome: str = None, moeda: str = None, cor: str = None):
        fields = {}
        if nome is not None:
            fields["store_name"] = nome
        if moeda is not None:
            fields["store_currency"] = moeda
        if cor is not None:
            fields["store_color"] = cor
        if not fields:
            await interaction.response.send_message(
                "Informe pelo menos um: nome, moeda ou cor.", ephemeral=True
            )
            return
        database.set_config(interaction.guild_id, **fields)
        await interaction.response.send_message("✅ Loja atualizada.", ephemeral=True)

    # ---------------------- Add -------------------------- #
    @loja.command(name="add", description="Cadastra um novo produto na loja.")
    @app_commands.describe(
        nome="Nome do produto",
        preco="Preço (ex.: 19.90)",
        descricao="Descrição curta",
        estoque="Quantidade (-1 = ilimitado)",
        imagem="URL de uma imagem (opcional)",
    )
    @app_commands.checks.has_permissions(manage_guild=True)
    async def add(self, interaction: discord.Interaction, nome: str, preco: float,
                  descricao: str = "", estoque: int = -1, imagem: str = ""):
        item_id = database.add_item(
            interaction.guild_id, nome, preco, descricao, estoque, imagem
        )
        await interaction.response.send_message(
            f"✅ **{nome}** cadastrado com o ID **{item_id}**.", ephemeral=True
        )

    # ---------------------- Edit ------------------------- #
    @loja.command(name="edit", description="Edita um produto existente pelo ID.")
    @app_commands.describe(
        id="ID do produto (aparece no rodapé do catálogo)",
        nome="Novo nome",
        preco="Novo preço",
        descricao="Nova descrição",
        estoque="Novo estoque (-1 = ilimitado)",
        imagem="Nova URL de imagem",
    )
    @app_commands.checks.has_permissions(manage_guild=True)
    async def edit(self, interaction: discord.Interaction, id: int, nome: str = None,
                   preco: float = None, descricao: str = None, estoque: int = None,
                   imagem: str = None):
        fields = {}
        if nome is not None:
            fields["name"] = nome
        if preco is not None:
            fields["price"] = preco
        if descricao is not None:
            fields["description"] = descricao
        if estoque is not None:
            fields["stock"] = estoque
        if imagem is not None:
            fields["image_url"] = imagem
        if not fields:
            await interaction.response.send_message(
                "Informe pelo menos um campo para alterar.", ephemeral=True
            )
            return
        ok = database.update_item(interaction.guild_id, id, **fields)
        msg = f"✅ Produto **{id}** atualizado." if ok else f"❌ Não achei o produto {id}."
        await interaction.response.send_message(msg, ephemeral=True)

    # ---------------------- Remove ----------------------- #
    @loja.command(name="remove", description="Remove um produto pelo ID.")
    @app_commands.describe(id="ID do produto a remover")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def remove(self, interaction: discord.Interaction, id: int):
        ok = database.remove_item(interaction.guild_id, id)
        msg = f"🗑️ Produto **{id}** removido." if ok else f"❌ Não achei o produto {id}."
        await interaction.response.send_message(msg, ephemeral=True)

    # ---------------------- Ver -------------------------- #
    @loja.command(name="ver", description="Abre o catálogo da loja.")
    async def ver(self, interaction: discord.Interaction):
        cfg = database.get_config(interaction.guild_id)
        items = database.list_items(interaction.guild_id)
        if not items:
            embed = discord.Embed(
                title=cfg["store_name"] or "Loja",
                description="A vitrine ainda está vazia. Use **/loja add** para começar. 🛍️",
                color=parse_color(cfg["store_color"]),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        view = StoreView(items, cfg, interaction.user.id)
        await interaction.response.send_message(embed=view.make_embed(), view=view)

    # -------------------------------------------------------------- #
    async def cog_app_command_error(self, interaction: discord.Interaction, error):
        if isinstance(error, app_commands.MissingPermissions):
            msg = "❌ Você precisa da permissão **Gerenciar Servidor** para gerenciar a loja."
        else:
            msg = f"⚠️ Ocorreu um erro: `{error}`"
        if interaction.response.is_done():
            await interaction.followup.send(msg, ephemeral=True)
        else:
            await interaction.response.send_message(msg, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Store(bot))
