"""InfiniteCore Bot — Music Cog (Full Featured)"""
import os
import re
import math
import time
import asyncio
import datetime
from typing import Optional
from collections import deque

import discord
from discord import app_commands
from discord.ext import commands

from config import BOT_NAME, BOT_VERSION
from embeds import ICEmbed, ok, err, warn, info, premium

# ─── Optional imports (soft fail) ───
try:
    import yt_dlp
    YTDL_OK = True
except ImportError:
    YTDL_OK = False

try:
    import nacl  # noqa
    NACL_OK = True
except ImportError:
    NACL_OK = False

try:
    import spotipy
    from spotipy.oauth2 import SpotifyClientCredentials
    SPOTIFY_LIB_OK = True
except ImportError:
    SPOTIFY_LIB_OK = False


# ─── Config ───
MUSIC_ENABLED    = os.getenv("MUSIC_ENABLED", "true").lower() == "true"
DEFAULT_VOLUME   = int(os.getenv("MUSIC_DEFAULT_VOLUME", 50))
MAX_QUEUE        = int(os.getenv("MUSIC_MAX_QUEUE", 100))
YT_COOKIES       = os.getenv("MUSIC_YT_COOKIES_PATH", "")
SPOTIFY_ID       = os.getenv("MUSIC_SPOTIFY_CLIENT_ID", "")
SPOTIFY_SECRET   = os.getenv("MUSIC_SPOTIFY_CLIENT_SECRET", "")
LEAVE_TIMEOUT    = int(os.getenv("MUSIC_LEAVE_TIMEOUT_SECONDS", 180))
MUSIC_COLOR      = int(os.getenv("MUSIC_EMBED_COLOR", "0x1DB954"), 16)
LYRICS_API       = os.getenv("MUSIC_LYRICS_API", "https://api.lyrics.ovh/v1")

FFMPEG_OPTS = {
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -nostdin",
    "options": "-vn -loglevel warning",
}

YTDL_OPTS = {
    "format": "bestaudio/best",
    "noplaylist": False,
    "quiet": True,
    "no_warnings": True,
    "default_search": "ytsearch",
    "source_address": "0.0.0.0",
    "extract_flat": False,
    "nocheckcertificate": True,
    "ignoreerrors": False,
    "logtostderr": False,
    "geo_bypass": True,
}
if YT_COOKIES and os.path.exists(YT_COOKIES):
    YTDL_OPTS["cookiefile"] = YT_COOKIES

YTDL = yt_dlp.YoutubeDL(YTDL_OPTS) if YTDL_OK else None

# ─── Spotify client ───
_spotify = None
if SPOTIFY_LIB_OK and SPOTIFY_ID and SPOTIFY_SECRET:
    try:
        _spotify = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
            client_id=SPOTIFY_ID, client_secret=SPOTIFY_SECRET))
    except: _spotify = None

URL_RE = re.compile(r"^https?://", re.IGNORECASE)
SPOTIFY_TRACK_RE  = re.compile(r"open\.spotify\.com/track/([A-Za-z0-9]+)")
SPOTIFY_PLAYLIST_RE = re.compile(r"open\.spotify\.com/playlist/([A-Za-z0-9]+)")


# ─── Track object ───
class Track:
    __slots__ = ("title", "url", "stream_url", "duration", "thumbnail",
                 "webpage_url", "requester", "source")
    def __init__(self, title, url, stream_url, duration, thumbnail, webpage_url, requester, source="youtube"):
        self.title = title
        self.url = url
        self.stream_url = stream_url
        self.duration = duration
        self.thumbnail = thumbnail
        self.webpage_url = webpage_url
        self.requester = requester
        self.source = source


# ─── Guild player state ───
class GuildPlayer:
    def __init__(self):
        self.queue: deque[Track] = deque()
        self.current: Optional[Track] = None
        self.voice_client: Optional[discord.VoiceClient] = None
        self.volume = DEFAULT_VOLUME / 100
        self.loop_mode = "off"  # off | song | queue
        self.last_activity = time.time()
        self.text_channel: Optional[discord.TextChannel] = None
        self.control_msg: Optional[discord.Message] = None
        self.stopping = False


_players: dict[int, GuildPlayer] = {}


def get_player(guild_id: int) -> GuildPlayer:
    if guild_id not in _players:
        _players[guild_id] = GuildPlayer()
    return _players[guild_id]


# ─── Extraction helpers ───
async def extract(query: str, requester: discord.User):
    """Return list of Track objects."""
    if not YTDL_OK:
        return []
    loop = asyncio.get_event_loop()

    # Spotify track
    m = SPOTIFY_TRACK_RE.search(query)
    if m and _spotify:
        try:
            tr = await loop.run_in_executor(None, _spotify.track, m.group(1))
            q = f"{tr['name']} {tr['artists'][0]['name']}"
            results = await extract(q, requester)
            return results
        except: pass

    # Spotify playlist
    m = SPOTIFY_PLAYLIST_RE.search(query)
    if m and _spotify:
        try:
            pl = await loop.run_in_executor(None, _spotify.playlist_items, m.group(1))
            out = []
            for item in pl["items"][:25]:
                t = item.get("track")
                if not t: continue
                q = f"{t['name']} {t['artists'][0]['name']}"
                sub = await extract(q, requester)
                if sub: out.append(sub[0])
            return out
        except: pass

    # yt-dlp extraction
    try:
        if URL_RE.match(query):
            data = await loop.run_in_executor(None, lambda: YTDL.extract_info(query, download=False))
        else:
            data = await loop.run_in_executor(None, lambda: YTDL.extract_info(f"ytsearch1:{query}", download=False))

        if not data: return []
        if "entries" in data:
            data = data["entries"][0] if data["entries"] else None
            if not data: return []

        title = data.get("title", "Unknown")
        duration = data.get("duration") or 0
        thumb = data.get("thumbnail") or ""
        webpage = data.get("webpage_url") or query

        # Pick best audio-only format
        stream = None
        for f in (data.get("formats") or []):
            if f.get("acodec") != "none" and f.get("vcodec") == "none":
                stream = f.get("url"); break
        if not stream:
            stream = data.get("url")

        source = "soundcloud" if "soundcloud" in webpage else "youtube"
        return [Track(title, query, stream, duration, thumb, webpage, requester, source)]
    except Exception as e:
        print(f"[music extract] {e}")
        return []


# ─── Now Playing embed + buttons ───
class MusicControls(discord.ui.View):
    def __init__(self, guild_id: int):
        super().__init__(timeout=None)
        self.guild_id = guild_id

    def _p(self): return get_player(self.guild_id)
    def _vc(self): return self._p().voice_client

    def _ok_user(self, i: discord.Interaction) -> bool:
        vc = self._vc()
        if not vc: return False
        if not i.user.voice or i.user.voice.channel != vc.channel: return False
        return True

    @discord.ui.button(emoji="⏯️", style=discord.ButtonStyle.primary, custom_id="m_pause")
    async def pause_btn(self, i, b):
        if not self._ok_user(i):
            return await i.response.send_message("Join my VC first!", ephemeral=True)
        vc = self._vc()
        if vc.is_playing():
            vc.pause(); await i.response.send_message("⏸️ Paused", ephemeral=True)
        elif vc.is_paused():
            vc.resume(); await i.response.send_message("▶️ Resumed", ephemeral=True)

    @discord.ui.button(emoji="⏭️", style=discord.ButtonStyle.secondary, custom_id="m_skip")
    async def skip_btn(self, i, b):
        if not self._ok_user(i):
            return await i.response.send_message("Join my VC first!", ephemeral=True)
        vc = self._vc()
        if vc: vc.stop()
        await i.response.send_message("⏭️ Skipped", ephemeral=True)

    @discord.ui.button(emoji="🔀", style=discord.ButtonStyle.secondary, custom_id="m_shuffle")
    async def shuffle_btn(self, i, b):
        if not self._ok_user(i):
            return await i.response.send_message("Join my VC first!", ephemeral=True)
        import random
        p = self._p()
        lst = list(p.queue); random.shuffle(lst); p.queue = deque(lst)
        await i.response.send_message("🔀 Shuffled", ephemeral=True)

    @discord.ui.button(emoji="🔁", style=discord.ButtonStyle.secondary, custom_id="m_loop")
    async def loop_btn(self, i, b):
        if not self._ok_user(i):
            return await i.response.send_message("Join my VC first!", ephemeral=True)
        p = self._p()
        cycle = {"off": "song", "song": "queue", "queue": "off"}
        p.loop_mode = cycle.get(p.loop_mode, "off")
        await i.response.send_message(f"🔁 Loop: **{p.loop_mode}**", ephemeral=True)

    @discord.ui.button(emoji="⏹️", style=discord.ButtonStyle.danger, custom_id="m_stop")
    async def stop_btn(self, i, b):
        if not self._ok_user(i):
            return await i.response.send_message("Join my VC first!", ephemeral=True)
        p = self._p()
        p.queue.clear(); p.loop_mode = "off"
        if p.voice_client: p.voice_client.stop()
        await i.response.send_message("⏹️ Stopped", ephemeral=True)

    @discord.ui.button(emoji="🔉", style=discord.ButtonStyle.secondary, custom_id="m_vdown")
    async def vol_down(self, i, b):
        if not self._ok_user(i):
            return await i.response.send_message("Join my VC first!", ephemeral=True)
        p = self._p()
        p.volume = max(0.0, p.volume - 0.1)
        if p.voice_client and p.voice_client.source:
            p.voice_client.source.volume = p.volume
        await i.response.send_message(f"🔉 {int(p.volume*100)}%", ephemeral=True)

    @discord.ui.button(emoji="🔊", style=discord.ButtonStyle.secondary, custom_id="m_vup")
    async def vol_up(self, i, b):
        if not self._ok_user(i):
            return await i.response.send_message("Join my VC first!", ephemeral=True)
        p = self._p()
        p.volume = min(2.0, p.volume + 0.1)
        if p.voice_client and p.voice_client.source:
            p.voice_client.source.volume = p.volume
        await i.response.send_message(f"🔊 {int(p.volume*100)}%", ephemeral=True)


def _nowplaying_embed(track: Track, player: GuildPlayer) -> discord.Embed:
    e = ICEmbed(title="🎵 Now Playing", description=f"**[{track.title}]({track.webpage_url})**", color=MUSIC_COLOR)
    if track.thumbnail:
        try: e.set_thumbnail(url=track.thumbnail)
        except: pass
    dur = str(datetime.timedelta(seconds=track.duration)) if track.duration else "Live"
    e.add_field(name="Duration", value=f"`{dur}`", inline=True)
    e.add_field(name="Source", value=f"`{track.source}`", inline=True)
    e.add_field(name="Volume", value=f"`{int(player.volume*100)}%`", inline=True)
    e.add_field(name="Loop", value=f"`{player.loop_mode}`", inline=True)
    e.add_field(name="Queue", value=f"`{len(player.queue)}`", inline=True)
    e.set_footer(text=f"Requested by {track.requester}", icon_url=track.requester.display_avatar.url)
    return e


# ─── Playback engine ───
async def _play_next(guild: discord.Guild):
    p = get_player(guild.id)
    if p.stopping:
        return
    vc = p.voice_client
    if not vc or not vc.is_connected():
        return

    # Handle loop
    if p.current and p.loop_mode == "song":
        p.queue.appendleft(p.current)
    elif p.current and p.loop_mode == "queue":
        p.queue.append(p.current)
    p.current = None

    if not p.queue:
        p.last_activity = time.time()
        return

    track = p.queue.popleft()
    p.current = track
    p.last_activity = time.time()

    try:
        source = discord.PCMVolumeTransformer(
            discord.FFmpegPCMAudio(track.stream_url, **FFMPEG_OPTS),
            volume=p.volume)
    except Exception as e:
        print(f"[ffmpeg] {e}")
        return await _play_next(guild)

    def _after(err):
        if err: print(f"[after] {err}")
        fut = asyncio.run_coroutine_threadsafe(_play_next(guild), guild._state._get_client().loop)
        try: fut.result(timeout=5)
        except: pass

    vc.play(source, after=_after)

    # Update nowplaying message if exists
    if p.text_channel:
        try:
            e = _nowplaying_embed(track, p)
            view = MusicControls(guild.id)
            if p.control_msg:
                try:
                    await p.control_msg.edit(embed=e, view=view)
                except:
                    p.control_msg = await p.text_channel.send(embed=e, view=view)
            else:
                p.control_msg = await p.text_channel.send(embed=e, view=view)
        except: pass


# ─── Cog ───
class Music(commands.Cog, name="Music"):
    def __init__(self, bot):
        self.bot = bot

    async def _ensure_join(self, i: discord.Interaction) -> Optional[discord.VoiceClient]:
        if not i.user.voice or not i.user.voice.channel:
            await i.followup.send(embed=err("Join a VC first"), ephemeral=True)
            return None
        vc = i.guild.voice_client
        target_ch = i.user.voice.channel
        if vc and vc.channel != target_ch:
            await vc.move_to(target_ch)
        elif not vc:
            try:
                vc = await target_ch.connect(self_deaf=True)
            except Exception as e:
                await i.followup.send(embed=err("Cannot join", str(e)), ephemeral=True)
                return None
        p = get_player(i.guild.id)
        p.voice_client = vc
        p.text_ch
