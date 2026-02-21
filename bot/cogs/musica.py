import discord, yt_dlp, asyncio, random, re, os
from urllib.parse import urlparse
from youtubesearchpython import VideosSearch
from discord.ext import commands
from spotipy import Spotify
from spotipy.oauth2 import SpotifyClientCredentials
from dotenv import load_dotenv

load_dotenv()
CLIENT_ID = os.getenv("SP_CLIENT_ID")
CLIENT_SECRET = os.getenv("SP_CLIENT_SECRET")

queue = {}
sp = None

if CLIENT_ID and CLIENT_SECRET:
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

    def ensure_guild_queue(self, guild_id):
        if guild_id not in queue:
            queue[guild_id] = []

    def parse_spotify_resource(self, query):
        parsed = urlparse(query)
        path_parts = [part for part in parsed.path.split('/') if part]

        if len(path_parts) >= 3 and path_parts[0].startswith('intl-'):
            path_parts = path_parts[1:]

        if len(path_parts) < 2:
            return None, None

        resource_type = path_parts[-2]
        resource_id = path_parts[-1]

        if resource_type not in ('track', 'playlist', 'album'):
            return None, None

        return resource_type, resource_id

    def get_spotify_track_query(self, track):
        if not track:
            return None

        artists = track.get('artists', [])
        if not artists:
            return None

        track_name = track.get('name')
        artist_name = artists[0].get('name')
        if not track_name or not artist_name:
            return None

        return f"{track_name} {artist_name}"

    def fetch_spotify_playlist_items(self, playlist_id):
        playlist_items = []
        offset = 0

        while True:
            response = sp.playlist_items(
                playlist_id,
                offset=offset,
                limit=100,
                fields='items(track(name,artists(name))),next'
            )
            current_items = response.get('items', [])
            playlist_items.extend(current_items)

            if not response.get('next'):
                break

            offset += len(current_items)
            if not current_items:
                break

        return playlist_items

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
                    await self.play_next(ctx)
                    return
                if ctx.voice_client:
                    ffmpeg_options = {
                        'options': '-vn -nostdin',
                        "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5"
                    }
                    ctx.voice_client.play(
                        discord.FFmpegPCMAudio(url, **ffmpeg_options),
                        after=lambda e: self._schedule_after_song(ctx, e)
                        )
                    embed = discord.Embed(
                        description=f"Tocando agora: [**{song['title']}**]({song['true_url']})",
                        color=discord.Color(0x000001)
                        )
                    await ctx.send(embed=embed)



    def _schedule_after_song(self, ctx, error):
        future = asyncio.run_coroutine_threadsafe(self.after_song(ctx, error), self.bot.loop)

        def _log_future_exception(done_future):
            exc = done_future.exception()
            if exc:
                print(f'Erro ao executar after_song: {exc}')

        future.add_done_callback(_log_future_exception)

    def add_to_queue(self, ctx, info):
        self.ensure_guild_queue(ctx.guild.id)
        queue[ctx.guild.id].append({
            'true_url': self.current_url[ctx.guild.id],
            'url': info['url'],
            'title': info.get('title', 'Sem título'),
            'requested_by': ctx.author
            })
    async def after_song(self, ctx, error):
        guild_id = ctx.guild.id
        if error:
            print(f'Ocorreu um erro: {error}')
        
        if guild_id in self.loop_state and self.loop_state[guild_id]:
            queue[guild_id].insert(0, self.current_song[guild_id])
            await self.play_next(ctx)
        else:
            await self.play_next(ctx)

    def yt_search(self, query):
        try:
            search = VideosSearch(query, limit=1)
            result = search.result()['result'][0]
            url = result['link']
            return url
        except Exception as e:
            print(f"Erro na busca do YouTube: {e}")
            return None

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
        track = item.get('track')
        query = self.get_spotify_track_query(track)
        if not query:
            return

        url = self.yt_search(query)
        if not url:
            return

        self.ensure_guild_queue(ctx.guild.id)
        queue_entry = {
            'true_url': url,
            'url': url,
            'title': query,
            'requested_by': ctx.author
            }
        queue[ctx.guild.id].append(queue_entry)

    @commands.command(name='join', aliases=['j'], help='Coloca o bot na call.')
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

        try:
            await channel.connect()
        except discord.ClientException as e:
            print(f"Erro ao conectar: {e}")
            await ctx.send(f"❌ Erro ao conectar ao canal: {e}")
        except Exception as e:
            print(f"Erro desconhecido ao conectar: {e}")
            await ctx.send("❌ Ocorreu um erro inesperado ao tentar conectar ao canal.")

        if ctx.guild.me.voice and ctx.guild.me.voice.channel.type == discord.ChannelType.stage_voice:
            await ctx.guild.me.edit(suppress=False)

        await asyncio.sleep(1)

    @commands.command(name='play', aliases=['p'], help='Toca a música desejada usando a URL ou o nome da música.')
    async def play(self, ctx, *, query):
        if not ctx.voice_client or not ctx.voice_client.is_connected():
            try:
                await self.join(ctx)
            except discord.errors.ClientException as e:
                print(f"Erro ao conectar: {e}")
                await ctx.send(f"Erro ao conectar ao canal de voz: {e}")

        if 'spotify.com' in query:
            if not sp:
                embed = discord.Embed(
                    description='❌ Spotify não configurado. Defina SP_CLIENT_ID e SP_CLIENT_SECRET no .env.',
                    color=discord.Color(0x000001)
                    )
                return await ctx.send(embed=embed)

            if self.is_url(query):
                spotify_type, spotify_id = self.parse_spotify_resource(query)

                if spotify_type == 'track' and spotify_id:
                    try:
                        track = sp.track(spotify_id)
                    except Exception:
                        embed = discord.Embed(
                            description='❌ Não foi possível carregar essa música do Spotify.',
                            color=discord.Color(0x000001)
                            )
                        return await ctx.send(embed=embed)

                    track_query = self.get_spotify_track_query(track)
                    if not track_query:
                        embed = discord.Embed(
                            description='❌ Não foi possível interpretar essa música do Spotify.',
                            color=discord.Color(0x000001)
                            )
                        return await ctx.send(embed=embed)

                    url = self.yt_search(track_query)
                    if not url:
                        embed = discord.Embed(
                            description='❌ Não foi possível encontrar essa música no YouTube.',
                            color=discord.Color(0x000001)
                            )
                        return await ctx.send(embed=embed)
                    self.current_url[ctx.guild.id] = url
                    await self.start_play(ctx, url)

                elif spotify_type == 'playlist' and spotify_id:
                    try:
                        embed = discord.Embed(
                            description='🔄 Sua playlist está sendo adicionada... aguarde.',
                            color=discord.Color(0x000001)
                            )
                        await ctx.send(embed=embed)

                        playlist_items = self.fetch_spotify_playlist_items(spotify_id)

                        before_count = len(queue.get(ctx.guild.id, []))

                        for item in playlist_items:
                            await self.process_track(ctx, item)

                        added_count = len(queue.get(ctx.guild.id, [])) - before_count

                        if added_count == 0:
                            embed = discord.Embed(
                                description='❌ Não foi possível adicionar músicas dessa playlist.',
                                color=discord.Color(0x000001)
                                )
                            return await ctx.send(embed=embed)

                        embed = discord.Embed(
                            description=f'✅ Playlist adicionada!\nMúsicas adicionadas: **{added_count}**',
                            color=discord.Color(0x000001)
                            )
                        await ctx.send(embed=embed)

                        if not ctx.voice_client.is_playing() and not ctx.voice_client.is_paused():
                            await self.play_next(ctx)
                    except Exception:
                        embed = discord.Embed(
                            description='❌ Não foi possível carregar sua playlist do Spotify.',
                            color=discord.Color(0x000001)
                            )
                        await ctx.send(embed=embed)

                elif spotify_type == 'album' and spotify_id:
                    try:
                        embed = discord.Embed(
                            description='🔄 Seu álbum está sendo adicionado... aguarde.',
                            color=discord.Color(0x000001)
                            )
                        await ctx.send(embed=embed)

                        album = sp.album(spotify_id)
                        tracks = album.get('tracks', {}).get('items', [])

                        before_count = len(queue.get(ctx.guild.id, []))

                        for track in tracks:
                            await self.process_track(ctx, {'track': track})

                        added_count = len(queue.get(ctx.guild.id, [])) - before_count

                        if added_count == 0:
                            embed = discord.Embed(
                                description='❌ Não foi possível adicionar músicas desse álbum.',
                                color=discord.Color(0x000001)
                                )
                            return await ctx.send(embed=embed)

                        embed = discord.Embed(
                            description=f'✅ Álbum adicionado!\nMúsicas adicionadas: **{added_count}**',
                            color=discord.Color(0x000001)
                            )
                        await ctx.send(embed=embed)

                        if not ctx.voice_client.is_playing() and not ctx.voice_client.is_paused():
                            await self.play_next(ctx)
                    except Exception:
                        embed = discord.Embed(
                            description='❌ Não foi possível carregar seu álbum do Spotify.',
                            color=discord.Color(0x000001)
                            )
                        await ctx.send(embed=embed)

                else:
                    embed = discord.Embed(
                        description='URL do Spotify não suportada. Use track, playlist ou álbum.',
                        color=discord.Color(0x000001)
                        )
                    await ctx.send(embed=embed)
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

            try:
                url = self.yt_search(query)
            except:
                print('nao deu ytseaarch')

            self.current_url[ctx.guild.id] = url

            try:
                await self.start_play(ctx, url)
            except:
                print('nao deu startplay')

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
        await voice_client.disconnect()
        if voice_client:
            queue[guild_id].clear()
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
            queue_list.append(f"1 - **{self.current_song[ctx.guild.id].get('title', 'Sem título')}** *Tocando agora*")
            for i, title in enumerate(queue[ctx.guild.id]):
                queue_list.append(f"{i+2} - **{title.get('title', 'Sem título')}**")

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
