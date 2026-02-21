import discord
import random
import re
from discord.ext import commands


class RPG(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name='rolar', aliases=['dado', 'dice'], help='Rola um dado no formato XdY+Z.')
    async def rolar(self, ctx, comando: str):
        await self.processar_rolagem(ctx, comando)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author == self.bot.user:
            return

        if message.webhook_id:
            content = message.content.lower().strip()
            match = re.search(
                r'^(?:##\s*\w+\s*)?\s*(?:!rolar|!dado|!dice)\s+(\d+d\d+(?:[+-](?:\d+d\d+|\d+))*)',
                content,
                re.IGNORECASE | re.MULTILINE
            )

            if not match:
                return

            comando = match.group(1)
            await self.processar_rolagem(message, comando)

    async def processar_rolagem(self, origem, comando: str):
        comando = comando.replace(" ", "")

        dados_tokens = re.findall(r'[+-]?\d+d\d+', comando)
        if not dados_tokens:
            await self._responder(origem, "❌ **Formato inválido!** Use algo como `2d20+2+3d5`")
            return

        grupos_dados = []
        soma_dados = 0

        for token in dados_tokens:
            sinal = -1 if token.startswith("-") else 1
            token_limpo = token.lstrip("+-")

            qtd, faces = map(int, token_limpo.split("d"))

            if qtd > 100:
                await self._responder(origem, "❌ Não pode rolar mais de 100 dados de uma vez!")
                return
            if faces > 1000:
                await self._responder(origem, "❌ O dado não pode ter mais de 1000 lados!")
                return

            rolagens = [random.randint(1, faces) for _ in range(qtd)]
            soma_dados += sum(rolagens) * sinal

            grupos_dados.append({
                "token": token_limpo,
                "rolagens": rolagens,
                "sinal": sinal
            })

        modificadores = re.findall(r'[+-]\d+(?!d)', comando)
        modificador_total = sum(int(m) for m in modificadores)

        total = soma_dados + modificador_total

        prefixo = ""

        d20s = []
        for g in grupos_dados:
            if g["token"].endswith("d20"):
                d20s.extend(g["rolagens"])

        if len(d20s) == 1:
            if d20s[0] == 1:
                prefixo = "`FALHA CRÍTICA`"
            elif d20s[0] == 20:
                prefixo = "`SUCESSO CRÍTICO`"

        elif len(d20s) == 2:
            soma20 = sum(d20s)
            if soma20 == 2:
                prefixo = "`FALHA CRÍTICA DUPLA`"
            elif 3 <= soma20 <= 7:
                prefixo = "`FALHA CRÍTICA`"
            elif 35 <= soma20 <= 39:
                prefixo = "`SUCESSO CRÍTICO`"
            elif soma20 == 40:
                prefixo = "`SUCESSO CRÍTICO DUPLO`"

        elif len(d20s) == 3:
            soma20 = sum(d20s)
            if soma20 == 3:
                prefixo = "`FALHA CRÍTICA TRIPLA`"
            elif 4 <= soma20 <= 7:
                prefixo = "`FALHA CRÍTICA DUPLA`"
            elif 8 <= soma20 <= 14:
                prefixo = "`FALHA CRÍTICA`"
            elif 48 <= soma20 <= 55:
                prefixo = "`SUCESSO CRÍTICO`"
            elif 56 <= soma20 <= 59:
                prefixo = "`SUCESSO CRÍTICO DUPLO`"
            elif soma20 == 60:
                prefixo = "`SUCESSO CRÍTICO TRIPLO`"

        partes = []

        for g in grupos_dados:
            qtd, faces = map(int, g["token"].split("d"))

            rolls = ", ".join(
                f"**{r}**" if r == 1 or r == faces else str(r)
                for r in g["rolagens"]
            )
            partes.append(f"[{rolls}] {g['token']}")

        if modificador_total != 0:
            partes.append(str(modificador_total))

        resposta = f"` {total} ` ⟵ " + " + ".join(partes) + f" {prefixo}"
        await self._responder(origem, resposta)

    async def _responder(self, origem, mensagem: str):
        if isinstance(origem, commands.Context):
            await origem.send(mensagem)
        elif isinstance(origem, discord.Message):
            await origem.channel.send(mensagem, reference=origem)


async def setup(bot):
    await bot.add_cog(RPG(bot))
