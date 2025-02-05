import discord
import os
import asyncio
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")  

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f'Bot {bot.user} está online!')

async def load_extension():
    for filename in os.listdir(r'.!/cogs'):
        if filename not in '__init__.py':
            if filename.endswith('.py'):
                await bot.load_extension(f'cogs.{filename[:-3]}')

async def main():
    await load_extension()
    await bot.start(TOKEN)

if __name__ == '__main__':
    asyncio.run(main())