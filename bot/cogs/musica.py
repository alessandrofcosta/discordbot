import discord, yt_dlp, asyncio, random, re, os
from youtubesearchpython import VideosSearch
from discord.ext import commands
from spotipy import Spotify
from spotipy.oauth2 import SpotifyClientCredentials
from dotenv import load_dotenv

load_dotenv()
CLIENT_ID = os.getenv("SP_CLIENT_ID")
CLIENT_SECRET = os.getenv("SP_CLIENT_SECRET")    

queue = {}
sp = Spotify(auth_manager=SpotifyClientCredentials(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET)
    )

class Musica(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.current_song = {}
        self.current_url = {}
        self.loop_state = {}

    async def join(self, ctx):
        if not ctx.author.voice:
            embed = discord.Embed(
                description="Você precisa estar em um canal de voz para me chamar!",
                color=discord.Color(0x000001)
            )
            return await ctx.send(embed=embed)

        channel = ctx.author.voice.channel

        if not ctx.guild.me.guild_permissions.connect:
            return await ctx.send("❌ Não tenho permissão para entrar no canal de voz!")

        if not ctx.guild.me.guild_permissions.speak:
            return await ctx.send("❌ Não tenho permissão para falar no canal de voz!")

        await channel.connect()
        await asyncio.sleep(2)
        if not ctx.voice_client or not ctx.voice_client.is_connected():
            await ctx.send("Falha ao conectar ao canal de voz.")

    async def play_next(self, ctx):
        guild_id = ctx.guild.id
        if guild_id in queue and queue[guild_id]:
            song = queue[guild_id].pop(0)
            self.current_song[guild_id] = song

            if not ctx.voice_client:
                return
            
            ydl_opts = {
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                try:
                    info = ydl.extract_info(song['url'], download=False)
                    url = info['url']
                except Exception as e:
                    embed = discord.Embed(
                        description=f"Erro ao carregar a música: ```{e}```",
                        color=discord.Color(0x000001)
                        )
                    await ctx.send(embed=embed)
                    await self.play_next
                if ctx.voice_client:
                    ffmpeg_options = {
                        'options': '-vn',
                        "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5"
                    }
                    ctx.voice_client.play(
                        discord.FFmpegPCMAudio(url, **ffmpeg_options),after=lambda e: asyncio.create_task(self.after_song(ctx, e), self.bot.loop)
                        )
                    embed = discord.Embed(
                        description=f'Tocando agora: [**{song['title']}**]({self.current_url[guild_id]})',
                        color=discord.Color(0x000001)
                        )
                    await ctx.send(embed=embed)



    def add_to_queue(self, ctx, info):
        if ctx.guild.id not in queue:
            queue[ctx.guild.id] = []
        queue[ctx.guild.id].append({
            'true_url': self.current_url[ctx.guild.id],
            'url': info['url'],
            'title': info.get('title', 'Sem título'),
            'requested_by': ctx.author
            })
    def after_song(self, ctx, error):
        guild_id = ctx.guild.id
        if error:
            print(f'Ocorreu um erro: {error}')
        
        if guild_id in self.loop_state and self.loop_state[guild_id]:
            queue[guild_id].insert(0, self.current_song[guild_id])
            asyncio.run_coroutine_threadsafe(self.play_next(ctx), self.bot.loop)
        else:
            asyncio.run_coroutine_threadsafe(self.play_next(ctx), self.bot.loop)

    def yt_search(self, query):
            search = VideosSearch(query, limit=1)
            result = search.result()['result'][0]
            url = result['link']
            return url

    async def start_play(self, ctx, url):

        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        'extract_flat': 'in_playlist',
        'lazy_extractors': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

        if 'entries' in info:
            for entry in info['entries']:            
                self.add_to_queue(ctx, entry)

            embed = discord.Embed(
                description=f"✅ Playlist adicionada!\nTotal de músicas na fila: **{len(queue[ctx.guild.id])}**",
                color=discord.Color(0x000001)
                )
            await ctx.send(embed=embed)

            if not ctx.voice_client.is_playing() and not ctx.voice_client.is_paused():
                await self.play_next(ctx)
        else:
            self.add_to_queue(ctx, info)
            if not ctx.voice_client.is_playing() and not ctx.voice_client.is_paused():
                await self.play_next(ctx)
            else:
                embed = discord.Embed(
                    description=f"[**{info['title']}**]({info['url']}) foi adicionada à fila!",
                    color=discord.Color(0x000001)
                    )
                await ctx.send(embed=embed)

    def is_url(self, text):
        url_pattern = re.compile(
            r'^(https?:\/\/)?'
            r'([a-zA-Z0-9\-]+\.)+[a-zA-Z]{2,}'
            r'(:\d+)?(\/.*)?$'
        )
        return bool(url_pattern.match(text))
    
    async def process_track(self, ctx, item):
        track = item['track']
        query = f"{track['name']} {track['artists'][0]['name']}"
        url = self.yt_search(query)
        self.current_url[ctx.guild.id] = url
        queue_sp = {
            'true_url': self.current_url[ctx.guild.id],
            'url': url,
            'title': track['name'],
            'requested_by': ctx.author
        }
        self.add_to_queue(ctx, queue_sp)

    @commands.command(name='play', aliases=['p'], help='Toca a música desejada usando a URL ou o nome da música.')
    async def play(self, ctx, *, query):

        if not ctx.voice_client or not ctx.voice_client.is_connected():
            try:
                await self.join(ctx)
            except discord.errors.ClientException as e:
                print(f"Erro ao conectar: {e}")
                await ctx.send(f"Erro ao conectar ao canal de voz: {e}")

        if 'spotify.com' in query:
            if self.is_url(query):
                if 'track' in query:
                    track = sp.track(query)
                    query = f"{track['name']} {track['artists'][0]['name']}"
                    url = self.yt_search(query)
                    self.current_url[ctx.guild.id] = url
                    await self.start_play(ctx, url)

                elif 'playlist' in query:
                        embed = discord.Embed(
                            description='🔄 Sua playlist está sendo adicionada... aguarde.',
                            color=discord.Color(0x000001)
                        )
                        await ctx.send(embed=embed)

                        playlist = sp.playlist_items(query)['items']
                        
                        await asyncio.gather(*[self.process_track(ctx, item) for item in playlist])

                        embed = discord.Embed(
                            description=f'# ✅ Playlist adicionada!\nTotal de músicas na fila: **{len(playlist)}**',
                            color=discord.Color(0x000001)
                        )
                        await ctx.send(embed=embed)

                        if not ctx.voice_client.is_playing() and not ctx.voice_client.is_paused():
                            await self.play_next(ctx)

            else:
                embed = discord.Embed(
                    description='URL não suportado.',
                    color=discord.Color(0x000001)
                    )
                await ctx.send(embed=embed)

        elif self.is_url(query) == False:
            embed = discord.Embed(
                description=f'Procurando música: **{query}**...',
                color=discord.Color(0x000001)
                )
            await ctx.send(embed=embed)

            url = self.yt_search(query)

            self.current_url[ctx.guild.id] = url
            await self.start_play(ctx, url)

        else:
            self.current_url[ctx.guild.id] = query
            await self.start_play(ctx, query)
            
    
    @commands.command(name='skip', aliases=['s'], help='Pula a música que está atualmente tocando.')
    async def skip(self, ctx):
        voice_client = ctx.voice_client
        guild_id = ctx.guild.id

        if not voice_client or not voice_client.is_playing():
            embed = discord.Embed(
                description='Não há nenhuma música tocando no momento.',
                color=discord.Color(0x000001)
            )
            await ctx.send(embed=embed)
            return

        if self.loop_state.get(guild_id, False):
            self.loop_state[guild_id] = False

        embed = discord.Embed(
            description=f'[**{self.current_song[guild_id]["title"]}**]({self.current_url[guild_id]}) pulada!',
            color=discord.Color(0x000001)
        )
        await ctx.send(embed=embed)
        voice_client.stop()
            
    @commands.command(name='stop', help='Pare as músicas e desconecte o bot da call.')
    async def stop(self, ctx):
        voice_client = ctx.voice_client
        guild_id = ctx.guild.id
        if voice_client:
            queue[guild_id].clear()
            await voice_client.disconnect()
            embed = discord.Embed(
                description="⛔ Música parada e fila limpa.",
                color=discord.Color(0x000001)
                )
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(
                description='Eu nao estou em um canal de voz.',
                color=discord.Color(0x000001)
                )
            await ctx.send(embed=embed)

    @commands.command(name='queue', help='Use para ver a ordem das músicas.')
    async def queue(self, ctx):
        queue_list = []
        if ctx.voice_client and ctx.voice_client.is_playing():
            queue_list.append(f'1 - **{self.current_song[ctx.guild.id].get('title', 'Sem título')}** *Tocando agora*')
            for i, title in enumerate(queue[ctx.guild.id]):
                queue_list.append(f'{i+2} - **{title.get('title', 'Sem título')}**')

            queue_message = '\n'.join(queue_list)
            try:
                embed = discord.Embed(
                title="Lista de músicas:",
                description=queue_message,
                color=discord.Color(0x000001)
                )

                await ctx.send(embed=embed)
            except:
                embed = discord.Embed(
                    description='Sua queue é muito grande para ser enviada, aguarde atualizações que isso será corrigido.',
                    color=discord.Color(0x000001)
                    )
                await ctx.send(embed=embed)
        else:
            embed = discord.Embed(
                description='Sem músicas na lista, adicione usando "!play"',
                color=discord.Color(0x000001)
                )
            await ctx.send(embed=embed)

    @commands.command(name='shuffle', help='Mistura sua queue de músicas.')
    async def shuffle(self, ctx):
        random.shuffle(queue[ctx.guild.id])
        embed = discord.Embed(
            description='Sua queue foi aleatorizada.',
            color=discord.Color(0x000001)
            )
        await ctx.send(embed=embed)

    @commands.command(name='loop', help='Ativa/Desativa o loop da musica.')
    async def loop(self, ctx):
        guild_id = ctx.guild.id
        if guild_id not in self.loop_state:
            self.loop_state[guild_id] = False

        self.loop_state[guild_id] = not self.loop_state[guild_id]

        if self.loop_state[guild_id]:
            embed = discord.Embed(
                description="🔁 Loop ativado para a música atual.",
                color=discord.Color(0x000001)
                )
            await ctx.send(embed=embed)

        else:
            embed = discord.Embed(
                description="🔁 Loop desativado.",
                color=discord.Color(0x000001)
                )
            await ctx.send(embed=embed)

        

async def setup(bot):
    await bot.add_cog(Musica(bot))