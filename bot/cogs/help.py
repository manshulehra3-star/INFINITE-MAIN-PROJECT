"""InfiniteCore Bot — Help Menu Cog (Premium)"""
import asyncio
import datetime

import discord
from discord import app_commands
from discord.ext import commands

from config import (
    BOT_NAME, BOT_VERSION, AI_MODEL, AI_HOST,
    CURRENCY, UPI_ID, MC_DEFAULT_VERSION,
    COLOR_PREMIUM, COLOR_PRIMARY, COLOR_INFO, COLOR_SUCCESS, COLOR_ERROR
)
from embeds import ICEmbed


HELP_PAGES = {
    "home": {
        "emoji": "🏠", "label": "Home", "color": COLOR_PREMIUM,
        "title": f"🏠 {BOT_NAME} Help Center",
        "description": (
            "**Welcome to the command center!**\n\n"
            "Use the **dropdown below** or the **buttons** to navigate.\n\n"
            f"> 🔹 Version **{BOT_VERSION}** • **31 files** • **Full automation**\n"
            "> 🔹 Tickets • AI • Payments • VPS • Minecraft\n"
            "> 🔹 Moderation • Community • Utility"
        ),
        "fields": [
            ("🎫 Tickets", "`/ticket setup|close|config|ai|stats`", True),
            ("🤖 AI", "`/ai <prompt>` • `@Bot <msg>`", True),
            ("💳 Payments", "`/pay` `/pay-history` `/pay-verify`", True),
            ("🖥️ VPS", "`/create-vps` `/manage` `/vps-list`", True),
            ("⛏️ Minecraft", "`/mc-create` `/mc-list` `/mc-delete`", True),
            ("📊 Utility", "`/help` `/ping` `/userinfo` `/avatar`", True),
        ],
    },
    "tickets": {
        "emoji": "🎫", "label": "Tickets", "color": COLOR_PRIMARY,
        "title": "🎫 Premium Ticket System",
        "description": "**Industry-grade support ticketing.**\n\nAI greeting • Priority routing • HTML transcripts • Ratings",
        "fields": [
            ("Setup", "`/ticket setup` — Deploy panel", True),
            ("Close", "`/ticket close` — Close current ticket", True),
            ("Config", "`/ticket config` — View settings", True),
            ("AI", "`/ticket ai` — AI ticket insights", True),
            ("Add", "`/ticket add` — Add member", True),
            ("Remove", "`/ticket remove` — Remove member", True),
            ("Priority", "`/ticket priority` — Set priority", True),
            ("Note", "`/ticket note` — Staff note", True),
            ("Stats", "`/ticket stats` — Statistics", True),
            ("Quick", "`/ticket quick` — Quick replies", True),
            ("Rename", "`/ticket-rename <name>`", True),
            ("Blacklist", "`/ticket-blacklist <user>`", True),
            ("Unblacklist", "`/ticket-unblacklist <user>`", True),
            ("Buttons", "Claim • Close • Add • Priority • Note", False),
            ("Transcript", "HTML file uploaded to log channel", False),
            ("Rating", "1-5⭐ after close → feedback channel", False),
        ],
    },
    "ai": {
        "emoji": "🤖", "label": "AI", "color": COLOR_INFO,
        "title": "🤖 InfiniteCore AI",
        "description": "**Local GPU/CPU AI** via Ollama. Zero API cost.",
        "fields": [
            ("Ask", "`/ai <prompt>` — Ask anything", True),
            ("Mention", "`@Bot <message>` — Auto reply", True),
            ("Ticket AI", "Auto greeting + close summary", True),
            ("AI Announce", "`/ai-announcement <topic>`", True),
            ("Model", f"`{AI_MODEL}`", True),
            ("Host", f"`{AI_HOST}`", True),
        ],
    },
    "payments": {
        "emoji": "💳", "label": "Payments", "color": COLOR_SUCCESS,
        "title": "💳 Payments & Billing",
        "description": "**Secure payment flow.** Screenshot → Staff verify → Auto-provisioning.",
        "fields": [
            ("Submit", "`/pay` — Modal submit", True),
            ("History", "`/pay-history` — Your payments", True),
            ("Verify", "`/pay-verify <id> <approve|reject>` (staff)", True),
            ("QR", "`/pay-setup-qr <url>`", True),
            ("Log Channel", "`/pay-setup-log-channel <#ch>`", True),
            ("Currency", f"`{CURRENCY}` • UPI: `{UPI_ID}`", True),
        ],
    },
    "plans": {
        "emoji": "📋", "label": "Plans & Promo", "color": COLOR_PREMIUM,
        "title": "📋 Plans • 🏷️ Promo",
        "description": "**Manage hosting plans and promo codes.**",
        "fields": [
            ("Add Plan", "`/plan-add <name> <price> <ram> <cpu> <disk> <days>`", True),
            ("Remove", "`/plan-remove <name>`", True),
            ("List", "`/plan-list`", True),
            ("New Promo", "`/promo-create <code> <discount> <uses> [days]`", True),
            ("Promo List", "`/promo-list`", True),
        ],
    },
    "vps": {
        "emoji": "🖥️", "label": "VPS", "color": COLOR_INFO,
        "title": "🖥️ VPS Management",
        "description": "**Full VPS lifecycle** with Pterodactyl integration.",
        "fields": [
            ("Create", "`/create-vps` — Provision new instance", True),
            ("Manage", "`/manage <vps_id> <start|stop|restart|reinstall>`", True),
            ("List", "`/vps-list` — Your instances", True),
            ("Delete", "`/vps-delete <vps_id>`", True),
            ("Backup", "`/vps-backup <vps_id>`", True),
            ("Suspend", "`/vps-suspension <vps_id> <true|false>` (staff)", True),
        ],
    },
    "pterodactyl": {
        "emoji": "🎛️", "label": "Pterodactyl", "color": COLOR_INFO,
        "title": "🎛️ Pterodactyl Integration",
        "description": "**Direct panel management.**",
        "fields": [
            ("Status", "`/ptero-status`", True),
            ("Nodes", "`/ptero-nodes` — List all nodes", True),
            ("Servers", "`/ptero-servers` — List all servers", True),
            ("Reinstall", "`/ptero-reinstall <id>`", True),
            ("Delete", "`/ptero-delete <id>`", True),
        ],
    },
    "minecraft": {
        "emoji": "⛏️", "label": "Minecraft", "color": COLOR_SUCCESS,
        "title": "⛏️ Minecraft Servers",
        "description": f"**Instant MC server provisioning.** Default version: `{MC_DEFAULT_VERSION}`",
        "fields": [
            ("Create", "`/mc-create` — New server modal", True),
            ("List", "`/mc-list` — Your servers", True),
            ("Delete", "`/mc-delete <server_id>`", True),
            ("Info", "`/mc-info <server_id>`", True),
            ("Types", "paper • vanilla • forge • fabric", True),
        ],
    },
    "moderation": {
        "emoji": "🛡️", "label": "Moderation", "color": COLOR_ERROR,
        "title": "🛡️ Moderation Tools",
        "description": "**Complete staff toolkit.** Every action logged with case ID.",
        "fields": [
            ("Kick", "`/kick <member> [reason]`", True),
            ("Ban", "`/ban <member> [reason] [days]`", True),
            ("Unban", "`/unban <user_id> [reason]`", True),
            ("Timeout", "`/timeout <member> <min> [reason]`", True),
            ("Warn", "`/warn <member> <reason>`", True),
            ("Warnings", "`/warnings <member>`", True),
            ("Clear Warns", "`/clear-warnings <member>`", True),
            ("Case", "`/case <number>`", True),
            ("Purge", "`/purge <1-100>`", True),
            ("Slowmode", "`/slowmode <seconds>`", True),
            ("Mod Stats", "`/modstats`", True),
        ],
    },
    "community": {
        "emoji": "🎉", "label": "Community", "color": COLOR_PREMIUM,
        "title": "🎉 Community & Engagement",
        "description": "**Giveaways, suggestions, polls, leveling.**",
        "fields": [
            ("Giveaway", "`/giveaway <prize> [hours] [winners]`", True),
            ("End Giveaway", "`/giveaway-end <message_id>`", True),
            ("Suggest", "`/suggest <text>`", True),
            ("Poll", "`/poll <question> <option1,option2,...>`", True),
            ("Rank", "`/rank [member]`", True),
            ("Leaderboard", "`/leaderboard`", True),
        ],
    },
    "utility": {
        "emoji": "🔧", "label": "Utility", "color": COLOR_INFO,
        "title": "🔧 Utility Tools",
        "description": "**Everyday helpers.**",
        "fields": [
            ("Remind", "`/remind <minutes> <message>`", True),
            ("Todo", "`/todo <add|list|done|clear>`", True),
            ("Userinfo", "`/userinfo [member]`", True),
            ("Serverinfo", "`/serverinfo`", True),
            ("Avatar", "`/avatar [member]`", True),
            ("Botinfo", "`/botinfo`", True),
            ("Ping", "`/ping`", True),
            ("Steal", "`/steal <emoji> <name>`", True),
        ],
    },
    "welcome": {
        "emoji": "👋", "label": "Welcome", "color": COLOR_SUCCESS,
        "title": "👋 Welcome & Announcements",
        "description": "**Greet your members with style.**",
        "fields": [
            ("Set Channel", "`/setup-welcome-channel <#channel>`", True),
            ("Edit Message", "`/welcome-edit <message>`", True),
            ("Preview", "`/welcome-animation`", True),
            ("Remove", "`/welcome-remove`", True),
            ("Info", "`/welcome-info`", True),
            ("Announce", "`/announcement <title> <message>`", True),
            ("AI Announce", "`/ai-announcement <topic>`", True),
            ("Links", "`/link-add|remove|list|edit`", True),
        ],
    },
    "owner": {
        "emoji": "👑", "label": "Owner", "color": COLOR_PREMIUM,
        "title": "👑 Owner Commands",
        "description": "**Restricted to bot owner.**",
        "fields": [
            ("Stats", "`/bot-stats` — Full statistics", True),
            ("Auto-Roll", "`/auto-roll <role>`", True),
            ("Roll Off", "`/auto-roll-remove`", True),
            ("Reload", "`/reload-cog <cog>`", True),
            ("Sync", "`/sync-cmds`", True),
            ("Backup", "`/backup-db`", True),
            ("Destroy", "`/server-destroy DESTROY`", True),
            ("Shutdown", "`/shutdown CONFIRM`", True),
        ],
    },
}

HELP_ORDER = ["home", "tickets", "ai", "payments", "plans", "vps",
              "pterodactyl", "minecraft", "moderation", "community",
              "utility", "welcome", "owner"]


def build_embed(page_key: str, user: discord.User) -> discord.Embed:
    page = HELP_PAGES[page_key]
    e = ICEmbed(
        title=page["title"],
        description=page["description"],
        color=page.get("color", COLOR_PRIMARY))
    for name, value, inline in page.get("fields", []):
        e.add_field(name=name, value=value, inline=inline)
    e.set_footer(
        text=f"{BOT_NAME} v{BOT_VERSION} • Page: {page_key.title()} • {user}",
        icon_url=user.display_avatar.url)
    return e


class HelpDropdown(discord.ui.Select):
    def __init__(self, current: str):
        opts = [
            discord.SelectOption(
                label=HELP_PAGES[k]["label"], value=k,
                emoji=HELP_PAGES[k]["emoji"],
                default=(k == current))
            for k in HELP_ORDER
        ]
        super().__init__(placeholder="🎯 Drag & drop to select a category...",
                         min_values=1, max_values=1, options=opts,
                         custom_id="help_dropdown_v1")

    async def callback(self, i: discord.Interaction):
        page = self.values[0]
        await i.response.defer()
        # Tiny spinner
        for _ in range(2):
            loading = ICEmbed(title=f"⏳ Loading {HELP_PAGES[page]['label']}...",
                              color=COLOR_INFO)
            try:
                await i.edit_original_response(embed=loading)
            except: pass
            await asyncio.sleep(0.15)
        await i.edit_original_response(embed=build_embed(page, i.user), view=HelpView(page))


class HelpNavButton(discord.ui.Button):
    def __init__(self, label, emoji, target, style=discord.ButtonStyle.secondary, row=1):
        cid = f"help_{target}_{label.lower().replace(' ', '_')}"
        super().__init__(label=label, emoji=emoji, style=style, row=row, custom_id=cid)
        self.target = target

    async def callback(self, i: discord.Interaction):
        if self.target == "__prev__":
            cur = self.view.current_page
            idx = HELP_ORDER.index(cur)
            page = HELP_ORDER[(idx - 1) % len(HELP_ORDER)]
        elif self.target == "__next__":
            cur = self.view.current_page
            idx = HELP_ORDER.index(cur)
            page = HELP_ORDER[(idx + 1) % len(HELP_ORDER)]
        else:
            page = self.target
        await i.response.defer()
        await i.edit_original_response(embed=build_embed(page, i.user), view=HelpView(page))


class HelpCloseButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Close", emoji="✖️", style=discord.ButtonStyle.danger,
                         row=1, custom_id="help_close")

    async def callback(self, i: discord.Interaction):
        try:
            await i.message.delete()
        except:
            await i.response.send_message("Closed.", ephemeral=True)


class HelpView(discord.ui.View):
    def __init__(self, current: str = "home"):
        super().__init__(timeout=300)
        self.current_page = current
        self.add_item(HelpDropdown(current))
        self.add_item(HelpNavButton("Prev", "◀️", "__prev__", discord.ButtonStyle.primary))
        self.add_item(HelpNavButton("Home", "🏠", "home", discord.ButtonStyle.success))
        self.add_item(HelpNavButton("Next", "▶️", "__next__", discord.ButtonStyle.primary))
        self.add_item(HelpCloseButton())

    async def on_timeout(self):
        for c in self.children:
            c.disabled = True


class Help(commands.Cog, name="Help"):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="help", description="📖 Interactive help menu")
    async def help_cmd(self, i: discord.Interaction):
        await i.response.send_message(
            embed=build_embed("home", i.user),
            view=HelpView("home"))


async def setup(bot):
    await bot.add_cog(Help(bot))
