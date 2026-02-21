import sys
import types
import unittest
from unittest.mock import AsyncMock, patch


def _install_fake_dependencies():
    fake_discord = types.ModuleType("discord")

    class Embed:
        def __init__(self, title=None, description=None, color=None):
            self.title = title
            self.description = description
            self.color = color

    fake_discord.Embed = Embed
    fake_discord.Color = lambda value: value
    fake_discord.ChannelType = types.SimpleNamespace(stage_voice="stage_voice")
    fake_discord.FFmpegPCMAudio = object
    fake_discord.ClientException = Exception
    fake_discord.errors = types.SimpleNamespace(ClientException=Exception)

    commands_module = types.ModuleType("commands")

    class Cog:
        pass

    def command(*_args, **_kwargs):
        def decorator(func):
            return types.SimpleNamespace(callback=func)
        return decorator

    commands_module.Cog = Cog
    commands_module.command = command

    fake_ext = types.ModuleType("ext")
    fake_ext.commands = commands_module
    fake_discord.ext = fake_ext

    sys.modules["discord"] = fake_discord
    sys.modules["discord.ext"] = fake_ext
    sys.modules["discord.ext.commands"] = commands_module

    fake_yt_dlp = types.ModuleType("yt_dlp")
    fake_yt_dlp.YoutubeDL = object
    sys.modules["yt_dlp"] = fake_yt_dlp

    fake_youtube_search = types.ModuleType("youtubesearchpython")
    fake_youtube_search.VideosSearch = object
    sys.modules["youtubesearchpython"] = fake_youtube_search

    fake_spotipy = types.ModuleType("spotipy")
    fake_spotipy.Spotify = object
    sys.modules["spotipy"] = fake_spotipy

    fake_spotipy_oauth2 = types.ModuleType("spotipy.oauth2")
    fake_spotipy_oauth2.SpotifyClientCredentials = object
    sys.modules["spotipy.oauth2"] = fake_spotipy_oauth2

    fake_dotenv = types.ModuleType("dotenv")
    fake_dotenv.load_dotenv = lambda: None
    sys.modules["dotenv"] = fake_dotenv


_install_fake_dependencies()
from bot.cogs import musica as musica_module  # noqa: E402


class FakeVoiceClient:
    def __init__(self, playing=False, paused=False, connected=True):
        self._playing = playing
        self._paused = paused
        self._connected = connected

    def is_playing(self):
        return self._playing

    def is_paused(self):
        return self._paused

    def is_connected(self):
        return self._connected


class FakeCtx:
    def __init__(self, guild_id=1):
        self.guild = types.SimpleNamespace(id=guild_id)
        self.author = object()
        self.voice_client = FakeVoiceClient()
        self.sent_embeds = []

    async def send(self, embed=None, **kwargs):
        self.sent_embeds.append(embed)
        return embed


class TestSpotifyMusic(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        musica_module.queue.clear()
        self.cog = musica_module.Musica(bot=types.SimpleNamespace(loop=None))

    async def test_spotify_track_adds_youtube_url_and_starts_play(self):
        ctx = FakeCtx(guild_id=42)
        fake_sp = types.SimpleNamespace(
            track=lambda _url: {
                "name": "Numb",
                "artists": [{"name": "Linkin Park"}],
            }
        )

        with patch.object(musica_module, "sp", fake_sp), \
             patch.object(self.cog, "yt_search", return_value="https://youtube.com/watch?v=abc"), \
             patch.object(self.cog, "start_play", new=AsyncMock()) as start_play_mock:
            await self.cog.play.callback(self.cog, ctx, query="https://open.spotify.com/track/123")

        start_play_mock.assert_awaited_once_with(ctx, "https://youtube.com/watch?v=abc")
        self.assertEqual(self.cog.current_url[42], "https://youtube.com/watch?v=abc")

    async def test_spotify_playlist_enqueues_items_and_starts_next(self):
        ctx = FakeCtx(guild_id=99)

        class FakeSpotify:
            def playlist_items(self, _query, offset=0):
                if offset == 0:
                    return {
                        "items": [{"track": {"name": "Song A", "artists": [{"name": "Artist A"}]}}],
                        "next": True,
                    }
                return {
                    "items": [{"track": {"name": "Song B", "artists": [{"name": "Artist B"}]}}],
                    "next": None,
                }

        with patch.object(musica_module, "sp", FakeSpotify()), \
             patch.object(self.cog, "yt_search", side_effect=["https://yt/A", "https://yt/B"]), \
             patch.object(self.cog, "play_next", new=AsyncMock()) as play_next_mock:
            await self.cog.play.callback(self.cog, ctx, query="https://open.spotify.com/playlist/xyz")

        self.assertEqual(len(musica_module.queue[99]), 2)
        self.assertEqual(musica_module.queue[99][0]["url"], "https://yt/A")
        self.assertEqual(musica_module.queue[99][1]["url"], "https://yt/B")
        play_next_mock.assert_awaited_once_with(ctx)


if __name__ == "__main__":
    unittest.main()
