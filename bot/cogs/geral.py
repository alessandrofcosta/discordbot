import discord
from discord.ext import commands


class Geral(commands.Cog):
    def __init__(self, bot):
        self.bot = bot      

    @commands.command(name='hello', help='Diz olá!')
    async def hello(self, ctx):
        await ctx.send(f'Ola {ctx.author.mention}')
    
    @commands.command(name='help', help='Mostra todos os comandos disponiveis')
    async def help(self, ctx):
        embed = discord.Embed(title="Comandos", color=discord.Color(0x00000f))

        for cog_name, cog in self.bot.cogs.items():
            commands_list = cog.get_commands()
            if commands_list:
                commands_description = "\n".join([f"`{cmd.name}` - {cmd.help or 'Sem descrição'}" for cmd in commands_list])
                embed.add_field(name=cog_name, value=commands_description, inline=False)

        await ctx.send(embed=embed)        

async def setup(bot):
    bot.remove_command('help')
    await bot.add_cog(Geral(bot))