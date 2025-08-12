import discord
import random
import re
from discord.ext import commands
from discord.ui import View, Button, Modal, TextInput

class InputModal(Modal, title="Insira os valores"):
    dano = TextInput(label="Dano tomado", placeholder="Digite um número")
    vig_ea = TextInput(label="Vigor ou EA", placeholder="Digite um número")
    resis = TextInput(label="Resistencia", placeholder="Digite um número")

    async def on_submit(self, interaction: discord.Interaction):
        try:
            dano_valor = int(self.dano.value)
            vig_ea_valor = int(self.vig_ea.value)
            resis_valor = int(self.resis.value) * 10
            resis_bruto = ((vig_ea_valor * resis_valor) / 100)
            resultado = dano_valor - resis_bruto
            resultado = max(0, resultado)
            usuario = interaction.user.mention

            embed = discord.Embed(      
            description=
            f'`Dano`: {dano_valor}\n'
            f'`VIG/EA`: {vig_ea_valor}\n'
            f'`RES`: {self.resis.value}\n'

            f"\n{usuario}: O dano tomado foi de ***{resultado}***",
            color=discord.Color(0x000001)
            )   

            await interaction.response.send_message(embed=embed)
        except ValueError:
            usuario = interaction.user.mention
            embed = discord.Embed(
            description=f"{usuario}: Por favor, insira valores numéricos válidos.",
            color=discord.Color(0x000001)
            )
            await interaction.response.send_message(embed=embed)


class ResisBrutoModal(Modal, title="Insira os valores"):
    vig_ea = TextInput(label="Vigor ou EA", placeholder="Digite um número")
    resis = TextInput(label="Resistência", placeholder="Digite um número")

    async def on_submit(self, interaction: discord.Interaction):
        try:
            vig_ea_valor = int(self.vig_ea.value)
            resis_valor = int(self.resis.value) * 10
            resis_bruto = (vig_ea_valor * resis_valor) / 100
            usuario = interaction.user.mention

            embed = discord.Embed(
                description=
                f'`VIG/EA`: {vig_ea_valor}\n'
                f'`RES`: {int(self.resis.value)}\n'
                f'\n{usuario}: Você sofre menos ***{resis_bruto}*** de dano',
                color=discord.Color(0x000001)
            )

            await interaction.response.send_message(embed=embed)

        except ValueError:
            usuario = interaction.user.mention
            embed = discord.Embed(
            description=f"{usuario}: Por favor, insira valores numéricos válidos.",
            color=discord.Color(0x000001)
            )
            await interaction.response.send_message(embed=embed)

class ButtonView(View):
    def __init__(self):
        super().__init__()

    @discord.ui.button(label="Inserir Valores", style=discord.ButtonStyle.primary)
    async def button_callback(self, interaction: discord.Interaction, button: Button):
        modal = InputModal()
        await interaction.response.send_modal(modal)

class ResisBrutoView(View):
    def __init__(self):
        super().__init__()

    @discord.ui.button(label="Inserir Valores", style=discord.ButtonStyle.primary)
    async def button_callback(self, interaction: discord.Interaction, button: Button):
        modal = ResisBrutoModal()
        await interaction.response.send_modal(modal)

class RPG(commands.Cog):
    def __init__(self, bot):
        self.bot = bot      

    @commands.command(name='resist', aliases=['r'], help='Calcula o dano a ser tomado de acordo com sua resistencia. (KL)')
    async def resist(self, ctx):
        view = ButtonView()
        embed = discord.Embed(
        description="Clique no botão abaixo para calcular quanto dano voce ira tomar baseado na sua resistencia:",
        color=discord.Color(0x000001)
        )
        await ctx.send(embed=embed, view=view)

    @commands.command(name='resistbruto', aliases=['rb'], help='Calcula apenas a resistência bruta. (KL)')
    async def resisbruto(self, ctx):
        view = ResisBrutoView()
        embed = discord.Embed(
        description="Clique no botão abaixo para calcular a resistência bruta:",
        color=discord.Color(0x000001)
        )
        await ctx.send(embed=embed, view=view)

    @commands.command(name='rolar', aliases=['dado', 'dice'], help='Rola um dado no formato XdY+Z.')
    async def rolar(self, ctx, comando: str):
        await self.processar_rolagem(ctx, comando)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author == self.bot.user:
            return

        if message.webhook_id:
            content = message.content.lower().strip()
            match = re.search(r'^(?:##\s*\w+\s*)?\s*(?:!rolar|!dado|!dice)\s+(\d+d\d+(?:[+-]\d+){0,10})', content, re.IGNORECASE | re.MULTILINE)
            if not match:
                return

            comando = match.group(1)
            await self.processar_rolagem(message, comando)  # passa a mensagem, não o canal

    async def processar_rolagem(self, origem, comando: str):
        match = re.match(r"(\d+)d(\d+)((?:[+-]\d+){0,10})", comando)
        if not match:
            await self._responder(origem, "❌ **Formato inválido!** Use algo como `!rolar 2d20+3` ou `1d20+1+2+3`")
            return

        qtd, faces, modificadores = match.groups()
        qtd, faces = int(qtd), int(faces)

        if qtd > 100:
            await self._responder(origem, "❌ Não pode rolar mais de 100 dados de uma vez!")
            return
        if faces > 1000:
            await self._responder(origem, "❌ O dado não pode ter mais de 1000 lados!")
            return

        resultados = [random.randint(1, faces) for _ in range(qtd)]
        modificadores_lista = [int(m) for m in re.findall(r"[+-]\d+", modificadores)[:10]]
        modificador_total = sum(modificadores_lista)

        total = sum(resultados) + modificador_total
        resultados_formatados = [
            f"**{r}**" if r == faces or r == 1 else str(r)
            for r in resultados
        ]
        resultado_formatado = f"` {total} ` ⟵ [{', '.join(resultados_formatados)}] {comando}"

        await self._responder(origem, resultado_formatado)

    async def _responder(self, origem, mensagem: str):
        if isinstance(origem, commands.Context):
            await origem.send(mensagem)
        elif isinstance(origem, discord.Message):
            await origem.channel.send(mensagem, reference=origem)

async def setup(bot):
    await bot.add_cog(RPG(bot))