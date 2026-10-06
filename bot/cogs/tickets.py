"""InfiniteCore Bot — Ticket System Cog"""
import io
import random
import asyncio
import datetime

import discord
from discord import app_commands
from discord.ext import commands

from config import (
    TICKET_PREFIX, MAX_TICKETS_PER_USER, TICKET_CATEGORY_ID, TICKET_LOG_CHANNEL_ID,
    TICKET_TRANSCRIPT_CHANNEL_ID, TICKET_TRANSCRIPT_ENABLED, TICKET_TRANSCRIPT_FORMAT,
    TICKET_PING_STAFF, TICKET_RATING_ENABLED, TICKET_AI_GREETING, TICKET_AI_SUMMARY,
    TICKET_QUICK_REPLIES, TICKET_FEEDBACK_CHANNEL_ID,
    STAFF_ROLE_IDS, SUPPORT_ROLE_IDS, ADMIN_ROLE_IDS, BOT_NAME, BOT_VERSION
)
from embeds import ICEmbed, ok, err, warn, info, premium
from utils.helpers import now_iso, ts, is_admin, is_staff, send_log, ai_call

# ─── Config ───
TICKET_CATEGORIES = {
    "general":     {"emoji": "💬", "label": "General Support",  "desc": "General help",   "priority": "normal"},
    "payment":     {"emoji": "💳", "label": "Payment Issue",    "desc": "Billing & UPI",  "priority": "high"},
    "vps":         {"emoji": "🖥️", "label": "VPS Support",      "desc": "VPS help",       "priority": "high"},
    "minecraft":   {"emoji": "⛏️", "label": "Minecraft",        "desc": "MC help",        "priority": "normal"},
    "report":      {"emoji": "🚨", "label": "Report User",      "desc": "Report member",  "priority": "urgent"},
    "partnership": {"emoji": "🤝", "label": "Partnership",      "desc": "Business",       "priority": "low"},
    "other":       {"emoji": "📦", "label": "Other",            "desc": "Anything else",  "priority": "low"},
}
PRIORITY_COLORS = {"low": 0x95A5A6, "normal": 0x5865F2, "high": 0xE67E22, "urgent": 0xED4245}
PRIORITY_EMOJI  = {"low": "🟢", "normal": "🔵", "high": "🟠", "urgent": "🔴"}


# ─── Modals ───
class TicketModal(discord.ui.Modal):
    subject = discord.ui.TextInput(label="Subject", placeholder="Short summary", max_length=100)
    desc = discord.ui.TextInput(label="Description", style=discord.TextStyle.paragraph,
                                 placeholder="Describe in detail...", max_length=1800)

    def __init__(self, category_key: str):
        super().__init__(title=f"🎫 {TICKET_CATEGORIES[category_key]['label']}")
        self.category_key = category_key

    async def on_submit(self, i: discord.Interaction):
        await i.response.defer(ephemeral=True)
        cog = i.client.get_cog("Tickets")
        await cog.create_ticket(i, self.category_key, self.subject.value, self.desc.value)


class AddUserModal(discord.ui.Modal, title="➕ Add User to Ticket"):
    user_id = discord.ui.TextInput(label="User ID or Mention", placeholder="123456789 or @user")

    async def on_submit(self, i: discord.Interaction):
        raw = self.user_id.value.strip().replace("<@", "").replace(">", "").replace("!", "")
        try:
            uid = int(raw)
            member = i.guild.get_member(uid) or await i.guild.fetch_member(uid)
        except Exception:
            return await i.response.send_message(embed=err("Invalid User"), ephemeral=True)
        try:
            await i.channel.set_permissions(member, read_messages=True, send_messages=True, attach_files=True)
        except Exception as e:
            return await i.response.send_message(embed=err("Failed", str(e)), ephemeral=True)
        await i.response.send_message(embed=ok("User Added", member.mention))


class NoteModal(discord.ui.Modal, title="📝 Add Staff Note"):
    note = discord.ui.TextInput(label="Note", style=discord.TextStyle.paragraph, max_length=800)

    def __init__(self, channel_id):
        super().__init__()
        self.channel_id = channel_id

    async def on_submit(self, i: discord.Interaction):
        i.client.db.ex("INSERT INTO ticket_notes (channel_id,author_id,note,created_at) VALUES (?,?,?,?)",
                       (self.channel_id, i.user.id, self.note.value, now_iso()))
        await i.response.send_message(embed=ok("Note Saved"), ephemeral=True)


class RatingView(discord.ui.View):
    def __init__(self, ticket_id: int, staff_id: int):
        super().__init__(timeout=300)
        self.ticket_id = ticket_id
        self.staff_id = staff_id

    async def _rate(self, i: discord.Interaction, stars: int):
        i.client.db.ex("INSERT INTO ticket_ratings (ticket_id,staff_id,user_id,rating,created_at) VALUES (?,?,?,?,?)",
                       (self.ticket_id, self.staff_id, i.user.id, stars, now_iso()))
        await i.response.send_message(embed=ok("Thanks!", f"You rated **{stars}⭐**"), ephemeral=True)
        if TICKET_FEEDBACK_CHANNEL_ID:
            e = premium("⭐ New Rating",
                        f"**Ticket:** #{self.ticket_id}\n**Staff:** <@{self.staff_id}>\n"
                        f"**User:** {i.user.mention}\n**Rating:** {'⭐' * stars}")
            await send_log(i.guild, TICKET_FEEDBACK_CHANNEL_ID, e)
        try: await i.message.delete()
        except: pass

    @discord.ui.button(label="1", emoji="⭐", style=discord.ButtonStyle.secondary)
    async def r1(self, i, b): await self._rate(i, 1)
    @discord.ui.button(label="2", emoji="⭐", style=discord.ButtonStyle.secondary)
    async def r2(self, i, b): await self._rate(i, 2)
    @discord.ui.button(label="3", emoji="⭐", style=discord.ButtonStyle.secondary)
    async def r3(self, i, b): await self._rate(i, 3)
    @discord.ui.button(label="4", emoji="⭐", style=discord.ButtonStyle.secondary)
    async def r4(self, i, b): await self._rate(i, 4)
    @discord.ui.button(label="5", emoji="⭐", style=discord.ButtonStyle.success)
    async def r5(self, i, b): await self._rate(i, 5)


class PriorityView(discord.ui.View):
    def __init__(self, channel_id):
        super().__init__(timeout=60)
        self.channel_id = channel_id

    @discord.ui.select(placeholder="Set priority...",
        options=[discord.SelectOption(label="🟢 Low", value="low"),
                 discord.SelectOption(label="🔵 Normal", value="normal"),
                 discord.SelectOption(label="🟠 High", value="high"),
                 discord.SelectOption(label="🔴 Urgent", value="urgent")])
    async def sel(self, i: discord.Interaction, s: discord.ui.Select):
        pr = s.values[0]
        i.client.db.ex("UPDATE tickets SET priority=? WHERE channel_id=?", (pr, self.channel_id))
        await i.response.send_message(embed=ok("Priority", f"**{pr.upper()}**"), ephemeral=True)


class QuickReplyView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180)
        opts = [discord.SelectOption(label=r[:80], value=str(idx))
                for idx, r in enumerate(TICKET_QUICK_REPLIES[:25])]
        if opts:
            sel = discord.ui.Select(placeholder="⚡ Quick reply...", options=opts)
            sel.callback = self._cb
            self.add_item(sel)

    async def _cb(self, i: discord.Interaction):
        idx = int(i.data["values"][0])
        await i.channel.send(embed=ICEmbed(title="⚡ Quick Reply",
                                           description=TICKET_QUICK_REPLIES[idx],
                                           color=0x00B0F4))
        await i.response.send_message(embed=ok("Sent"), ephemeral=True)


class TicketControl(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Claim", emoji="🙋", style=discord.ButtonStyle.success, custom_id="tkt_claim")
    async def claim(self, i: discord.Interaction, b):
        if not is_staff(i.user):
            return await i.response.send_message(embed=err("Staff Only"), ephemeral=True)
        row = i.client.db.one("SELECT * FROM tickets WHERE channel_id=?", (i.channel.id,))
        if not row: return await i.response.send_message(embed=err("Not Found"), ephemeral=True)
        if row["claimed_by"]:
            return await i.response.send_message(embed=warn("Claimed", f"By <@{row['claimed_by']}>"), ephemeral=True)
        i.client.db.ex("UPDATE tickets SET claimed_by=? WHERE channel_id=?", (i.user.id, i.channel.id))
        await i.response.send_message(embed=ok("Claimed", i.user.mention))

    @discord.ui.button(label="Close", emoji="🔒", style=discord.ButtonStyle.danger, custom_id="tkt_close")
    async def close(self, i: discord.Interaction, b):
        row = i.client.db.one("SELECT * FROM tickets WHERE channel_id=?", (i.channel.id,))
        if not row: return await i.response.send_message(embed=err("Not Found"), ephemeral=True)
        if i.user.id != row["user_id"] and not is_staff(i.user):
            return await i.response.send_message(embed=err("Denied"), ephemeral=True)
        cog = i.client.get_cog("Tickets")
        await i.response.send_message(embed=ok("Closing", "5s me delete hoga..."))
        await cog.close_ticket(i.channel, i.user, reason="Manual")

    @discord.ui.button(label="Add", emoji="➕", style=discord.ButtonStyle.primary, custom_id="tkt_add")
    async def add_user(self, i: discord.Interaction, b):
        if not is_staff(i.user):
            return await i.response.send_message(embed=err("Staff Only"), ephemeral=True)
        await i.response.send_modal(AddUserModal())

    @discord.ui.button(label="Priority", emoji="🚩", style=discord.ButtonStyle.secondary, custom_id="tkt_priority")
    async def priority(self, i: discord.Interaction, b):
        if not is_staff(i.user):
            return await i.response.send_message(embed=err("Staff Only"), ephemeral=True)
        await i.response.send_message("Select:", view=PriorityView(i.channel.id), ephemeral=True)

    @discord.ui.button(label="Note", emoji="📝", style=discord.ButtonStyle.secondary, custom_id="tkt_note")
    async def note(self, i: discord.Interaction, b):
        if not is_staff(i.user):
            return await i.response.send_message(embed=err("Staff Only"), ephemeral=True)
        await i.response.send_modal(NoteModal(i.channel.id))


class TicketPanel(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        opts = [discord.SelectOption(label=m["label"], value=k, emoji=m["emoji"], description=m["desc"])
                for k, m in TICKET_CATEGORIES.items()]
        sel = discord.ui.Select(placeholder="🎫 Select a category...",
                                custom_id="tkt_panel_select", options=opts)
        sel.callback = self._cb
        self.add_item(sel)

    async def _cb(self, i: discord.Interaction):
        key = i.data["values"][0]
        if i.client.db.one("SELECT * FROM tickets_blacklist WHERE user_id=?", (i.user.id,)):
            return await i.response.send_message(embed=err("Blacklisted"), ephemeral=True)
        await i.response.send_modal(TicketModal(key))


# ─── Cog ───
class Tickets(commands.Cog, name="Tickets"):
    def __init__(self, bot):
        self.bot = bot

    # ─── Transcript builder ───
    async def _html_transcript(self, channel: discord.TextChannel, row) -> discord.File:
        parts = []
        async for m in channel.history(limit=2000, oldest_first=True):
            avatar = m.author.display_avatar.url
            content = (m.content or "").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>")
            attach = "".join(f'<div class="attach"><a href="{a.url}">📎 {a.filename}</a></div>' for a in m.attachments)
            embeds = ""
            for e in m.embeds:
                t = (e.title or "").replace("<", "&lt;")
                d = (e.description or "").replace("<", "&lt;").replace("\n", "<br>")
                if t or d:
                    embeds += f'<div class="embed"><b>{t}</b><br>{d}</div>'
            parts.append(f"""
            <div class="msg">
                <img src="{avatar}" class="avatar">
                <div class="body">
                    <div class="meta"><b>{m.author}</b> <span class="time">{m.created_at.strftime('%Y-%m-%d %H:%M')}</span></div>
                    <div class="content">{content}</div>
                    {attach}{embeds}
                </div>
            </div>""")
        html = f"""<!DOCTYPE html><html><head><meta charset="UTF-8">
<title>Transcript — {channel.name}</title>
<style>
body{{background:#2b2d31;color:#dbdee1;font-family:system-ui;padding:20px;max-width:900px;margin:auto}}
h1{{color:#5865F2;text-align:center}}
.msg{{display:flex;gap:12px;padding:12px;border-bottom:1px solid #1e1f22}}
.avatar{{width:40px;height:40px;border-radius:50%}}
.body{{flex:1}}
.meta b{{color:#fff}}
.time{{color:#949ba4;font-size:12px;margin-left:8px}}
.content{{margin-top:4px;word-wrap:break-word}}
.attach a{{color:#00a8fc;text-decoration:none;font-size:13px}}
.embed{{background:#1e1f22;border-left:3px solid #5865F2;padding:8px;margin-top:6px;border-radius:4px;font-size:13px}}
.footer{{text-align:center;color:#949ba4;font-size:12px;margin-top:30px}}
</style></head><body>
<h1>🎫 Ticket — {channel.name}</h1>
<p style="text-align:center;color:#949ba4">User: &lt;{row['user_id']}&gt; | Subject: {row['subject']} | Category: {row['category']}</p>
{''.join(parts)}
<div class="footer">Generated by {BOT_NAME} v{BOT_VERSION} • {datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}</div>
</body></html>"""
        return discord.File(io.BytesIO(html.encode()), filename=f"transcript-{channel.name}.html")

    async def _txt_transcript(self, channel) -> discord.File:
        lines = [f"Transcript #{channel.name}", "=" * 60]
        async for m in channel.history(limit=2000, oldest_first=True):
            lines.append(f"[{m.created_at:%Y-%m-%d %H:%M:%S}] {m.author}: {m.content}")
            for a in m.attachments:
                lines.append(f"    [attachment] {a.url}")
        return discord.File(io.BytesIO("\n".join(lines).encode()),
                            filename=f"transcript-{channel.name}.txt")

    async def create_ticket(self, i: discord.Interaction, category_key: str, subject: str, desc: str):
        g, u = i.guild, i.user
        meta = TICKET_CATEGORIES.get(category_key, TICKET_CATEGORIES["other"])

        if self.bot.db.one("SELECT * FROM tickets_blacklist WHERE user_id=?", (u.id,)):
            return await i.followup.send(embed=err("Blacklisted"), ephemeral=True)

        open_t = self.bot.db.all("SELECT * FROM tickets WHERE user_id=? AND status='open'", (u.id,))
        if len(open_t) >= MAX_TICKETS_PER_USER:
            return await i.followup.send(embed=err("Limit", f"Max {MAX_TICKETS_PER_USER} tickets."), ephemeral=True)

        ow = {
            g.default_role: discord.PermissionOverwrite(read_messages=False),
            u: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True),
            g.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True),
        }
        for rid in set(STAFF_ROLE_IDS + SUPPORT_ROLE_IDS + ADMIN_ROLE_IDS):
            r = g.get_role(rid)
            if r: ow[r] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        cat = g.get_channel(TICKET_CATEGORY_ID) if TICKET_CATEGORY_ID else None
        try:
            ch = await g.create_text_channel(
                name=f"{TICKET_PREFIX}-{u.name.lower()[:15]}-{random.randint(100,999)}",
                category=cat, overwrites=ow, topic=f"{u} | {meta['label']} | {subject}")
        except Exception as e:
            return await i.followup.send(embed=err("Failed", str(e)), ephemeral=True)

        self.bot.db.ex("""INSERT INTO tickets
            (channel_id,user_id,guild_id,subject,category,status,priority,created_at,last_activity)
            VALUES (?,?,?,?,?,?,?,?,?)""",
            (ch.id, u.id, g.id, subject, meta["label"], "open", meta["priority"], now_iso(), now_iso()))

        ping = u.mention
        if TICKET_PING_STAFF:
            if SUPPORT_ROLE_IDS: ping += f" <@&{SUPPORT_ROLE_IDS[0]}>"
            elif STAFF_ROLE_IDS: ping += f" <@&{STAFF_ROLE_IDS[0]}>"

        header = discord.Embed(
            title=f"{meta['emoji']} Ticket — {meta['label']}",
            description=(f"**User:** {u.mention}\n**Subject:** {subject}\n"
                         f"**Priority:** {PRIORITY_EMOJI[meta['priority']]} {meta['priority'].upper()}\n"
                         f"**ID:** `{ch.id}`"),
            color=PRIORITY_COLORS[meta['priority']])
        header.add_field(name="📄 Description", value=desc[:1000] or "*No description*", inline=False)
        header.set_thumbnail(url=u.display_avatar.url)
        header.set_footer(text=f"{BOT_NAME} • Ticket System")

        await ch.send(content=ping, embed=header, view=TicketControl())

        if TICKET_AI_GREETING:
            reply = await ai_call(
                f"Ticket category: {meta['label']}. Subject: {subject}. Description: {desc}.\n"
                f"Write a warm greeting + 2-3 diagnostic questions.",
                system="You are InfiniteCore support AI. Polite, focused.")
            if reply and not reply.startswith("AI "):
                await ch.send(embed=ICEmbed(title="🤖 AI Assistant", description=reply[:4000], color=0x00B0F4))

        if TICKET_QUICK_REPLIES:
            await ch.send(embed=ICEmbed(title="⚡ Quick Replies",
                                        description="Staff dropdown below.",
                                        color=0x00B0F4), view=QuickReplyView())

        await i.followup.send(embed=ok("Ticket Created", f"→ {ch.mention}"), ephemeral=True)

        lg = ICEmbed(title="🎫 Ticket Opened", color=0x00B0F4)
        lg.add_field(name="User", value=u.mention, inline=True)
        lg.add_field(name="Category", value=meta["label"], inline=True)
        lg.add_field(name="Channel", value=ch.mention, inline=True)
        lg.add_field(name="Subject", value=subject, inline=False)
        await send_log(g, TICKET_LOG_CHANNEL_ID, lg)

    async def close_ticket(self, channel: discord.TextChannel, closer: discord.Member, reason: str = "Closed"):
        row = self.bot.db.one("SELECT * FROM tickets WHERE channel_id=?", (channel.id,))
        if not row: return

        summary = ""
        if TICKET_AI_SUMMARY:
            summary = await ai_call(
                f"Summarize briefly. Subject: {row['subject']}",
                system="Concise ticket summarizer.")

        transcript_url = ""
        if TICKET_TRANSCRIPT_ENABLED:
            try:
                if TICKET_TRANSCRIPT_FORMAT.lower() == "html":
                    f = await self._html_transcript(channel, row)
                else:
                    f = await self._txt_transcript(channel)
                if TICKET_TRANSCRIPT_CHANNEL_ID:
                    tch = channel.guild.get_channel(TICKET_TRANSCRIPT_CHANNEL_ID)
                    if tch:
                        msg = await tch.send(
                            content=f"📄 `{channel.name}` | Closed by {closer.mention}",
                            file=f,
                            embed=ICEmbed(title="🎫 Transcript",
                                          description=f"**User:** <@{row['user_id']}>\n**Subject:** {row['subject']}\n**Category:** {row['category']}"))
                        transcript_url = msg.jump_url
            except Exception as e:
                print(f"transcript error: {e}")

        self.bot.db.ex("""UPDATE tickets SET status='closed', closed_at=?, ai_summary=?, transcript_url=?
                         WHERE channel_id=?""",
            (now_iso(), summary, transcript_url, channel.id))

        e = ok("Ticket Closing", "5s me delete...")
        if summary: e.add_field(name="🤖 AI Summary", value=summary[:1024], inline=False)
        if transcript_url: e.add_field(name="📄 Transcript", value=f"[View]({transcript_url})", inline=False)
        try: await channel.send(embed=e)
        except: pass

        try:
            u = await channel.guild.fetch_member(row["user_id"])
            if TICKET_RATING_ENABLED and row["claimed_by"]:
                dm = premium("🎫 Ticket Closed",
                             f"Your ticket **{row['subject']}** closed.\n\nPlease rate our support:")
                if transcript_url:
                    dm.add_field(name="Transcript", value=f"[Download]({transcript_url})", inline=False)
                await
