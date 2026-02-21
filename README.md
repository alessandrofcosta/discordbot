# Discord Bot

## Description

This is a Discord bot developed in Python using the `discord.py` library. It has various features, including general commands, music commands, and support for an RPG system.

## Features

All commands now work in both formats:
- Prefix command in chat (example: `!play`)
- Slash command (example: `/play`)

### General Commands

- `!hello` or `/hello` - The bot responds with a greeting message.
- `!help` or `/help` - Displays all available commands in an organized manner.

### Music Commands

- `!play <name/url>` or `/play <name/url>` - Plays a song from YouTube or Spotify.
- `!skip` or `/skip` - Skips the current song.
- `!stop` or `/stop` - Stops playback and disconnects the bot from the voice channel.
- `!queue` or `/queue` - Displays the song queue.
- `!shuffle` or `/shuffle` - Shuffles the song queue.
- `!loop` or `/loop` - Toggles looping for the current song.

### RPG Commands

- `!rolar <XdY+Z>` or `/rolar <XdY+Z>` - Rolls dice using expressions such as `2d20+2+1d6`.

## Installation

1. Clone this repository:
   ```sh
   git clone https://github.com/your-username/your-repository.git
   ```
2. Install dependencies:
   ```sh
   pip install -r requirements.txt
   ```
3. Configure environment variables (`.env`) for Spotify integration and your bot token.
4. Run the bot:
   ```sh
   python main.py
   ```

## Dependencies

- `discord.py`
- `yt-dlp`
- `spotipy`
- `python-dotenv`
- `youtube-search-python`

## Contribution

Feel free to open issues and pull requests for improvements and bug fixes!


