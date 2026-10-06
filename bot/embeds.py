"""InfiniteCore Bot — Embed helpers"""
import datetime
import discord
import config as C

class ICEmbed(discord.Embed):
    def __init__(self, **kw):
        kw.setdefault("color", C.COLOR_PRIMARY)
        if C.UI_TIMESTAMP:
            kw.setdefault("timestamp", datetime.datetime.utcnow())
        super().__init__(**kw)
        if C.UI_FOOTER:
            self.set_footer(text=f"{C.BOT_NAME} v{C.BOT_VERSION}")
        if C.BOT_THUMB:
            try: self.set_thumbnail(url=C.BOT_THUMB)
            except: pass

def ok(t, d=""):      return ICEmbed(title=f"✅ {t}", description=d, color=C.COLOR_SUCCESS)
def err(t, d=""):     return ICEmbed(title=f"❌ {t}", description=d, color=C.COLOR_ERROR)
def warn(t, d=""):    return ICEmbed(title=f"⚠️ {t}", description=d, color=C.COLOR_WARNING)
def info(t, d=""):    return ICEmbed(title=f"ℹ️ {t}", description=d, color=C.COLOR_INFO)
def premium(t, d=""): return ICEmbed(title=f"💎 {t}", description=d, color=C.COLOR_PREMIUM)
