"""InfiniteCore Bot — Payments Cog (Prefix Commands)"""
import random
import datetime
import discord
from discord.ext import commands

from config import (
    CURRENCY, CURRENCY_SYMBOL, UPI_ID, PAYMENT_LOG_CHANNEL_ID,
    PAYMENT_MIN, PAYMENT_MAX
)
from embeds import ICEmbed, ok, err, warn, info, premium
from utils.helpers import now_iso, ts, is_admin, is_staff, send_log
from animations import progress


# ─── Payment Modal (self submit) ───
class PaymentModal(discord.ui.Modal, title="💳 Submit Payment"):
    amount = discord.ui.TextInput(label=f"Amount ({CURRENCY})", placeholder="499")
    method = discord.ui.TextInput(label="Payment Method", placeholder="UPI / Bank / Crypto")
    txn = discord.ui.TextInput(label="Transaction ID / UTR", placeholder="123456789")
    proof = discord.ui.TextInput(label="Screenshot URL (optional)", required=False)

    async def on_submit(self, i: discord.Interaction):
        await i.response.defer(ephemeral=True)
        try: amt = float(self.amount.value)
        except ValueError:
            return await i.followup.send(embed=err("Invalid Amount"), ephemeral=True)

        if amt < PAYMENT_MIN or amt > PAYMENT_MAX:
            return await i.followup.send(
                embed=err("Out of range",
                          f"{CURRENCY_SYMBOL}{PAYMENT_MIN} - {CURRENCY_SYMBOL}{PAYMENT_MAX}"),
                ephemeral=True)

        invoice = f"INV-{random.randint(100000, 999999)}"
        i.client.db.ex("""INSERT INTO payments
            (user_id,amount,currency,method,status,proof_url,txn,invoice_id,created_at)
            VALUES (?,?,?,?,?,?,?,?,?)""",
            (i.user.id, amt, CURRENCY, self.method.value, "pending",
             self.proof.value or "", self.txn.value, invoice, now_iso()))

        e = premium("Payment Submitted",
                    f"**Invoice:** `{invoice}`\n**Amount:** {CURRENCY_SYMBOL}{amt:.2f}\n"
                    f"**Method:** {self.method.value}\n**TXN:** `{self.txn.value}`\n\n"
                    "⏳ Awaiting staff verification.")
        await i.followup.send(embed=e, ephemeral=True)

        lg = ICEmbed(title="💳 New Payment", color=0xFEE75C)
        lg.add_field(name="User", value=i.user.mention, inline=True)
        lg.add_field(name="Invoice", value=invoice, inline=True)
        lg.add_field(name="Amount", value=f"{CURRENCY_SYMBOL}{amt:.2f}", inline=True)
        lg.add_field(name="Method", value=self.method.value, inline=True)
        lg.add_field(name="TXN", value=self.txn.value, inline=True)
        if self.proof.value:
            lg.add_field(name="Proof", value=self.proof.value, inline=False)
        await send_log(i.guild, PAYMENT_LOG_CHANNEL_ID, lg)


class Payments(commands.Cog, name="Payments"):
    def __init__(self, bot):
        self.bot = bot

    # ═══════════════════════════════════════════════
    #  !pay <amount> [user] [method] [txn] [proof]
    #  Examples:
    #    !pay 499
    #    !pay 499 @John
    #    !pay 499 @John UPI
    #    !pay 499 @John UPI 123456789
    #    !pay 499 @John UPI 123456789 https://img.url
    # ═══════════════════════════════════════════════
    @commands.command(name="pay", aliases=["payment", "invoice"])
    @commands.guild_only()
    async def pay_cmd(self, ctx: commands.Context, amount: float = None,
                      user: discord.Member = None, method: str = "UPI",
                      txn: str = "", proof: str = ""):
        # Help if no amount
        if amount is None:
            e = premium("💳 Payment Command",
                "**Usage:**\n"
                "`!pay <amount>` — self payment\n"
                "`!pay <amount> @user` — staff records for user\n"
                "`!pay <amount> @user <method>` — with method\n"
                "`!pay <amount> @user <method> <txn>` — with TXN\n"
                "`!pay <amount> @user <method> <txn> <proof_url>` — full\n\n"
                "**Examples:**\n"
                "`!pay 499`\n"
                "`!pay 499 @John UPI 123456789`\n"
                "`!pay 999 @Jane Razorpay TXN123 https://img.url`")
            return await ctx.send(embed=e)

        # Validate amount
        try:
            amount = float(amount)
        except (ValueError, TypeError):
            return await ctx.send(embed=err("Invalid Amount", "Example: `!pay 499`"))

        if amount < PAYMENT_MIN or amount > PAYMENT_MAX:
            return await ctx.send(embed=err("Out of range",
                f"Allowed: {CURRENCY_SYMBOL}{PAYMENT_MIN} - {CURRENCY_SYMBOL}{PAYMENT_MAX}"))

        # Determine target
        target = user or ctx.author
        is_staff_recording = (ctx.author.id != target.id)

        # If staff recording for another user → permission check
        if is_staff_recording and not is_staff(ctx.author):
            return await ctx.send(embed=err("Denied",
                "Only staff can record payments for other users."))

        invoice = f"INV-{random.randint(100000, 999999)}"
        status = "pending"

        self.bot.db.ex("""INSERT INTO payments
            (user_id,amount,currency,method,status,proof_url,txn,invoice_id,created_at)
            VALUES (?,?,?,?,?,?,?,?,?)""",
            (target.id, amount, CURRENCY, method, status,
             proof or "", txn or "", invoice, now_iso()))

        # Success embed
        e = premium("💳 Payment Recorded",
            f"**Invoice:** `{invoice}`\n"
            f"**User:** {target.mention}\n"
            f"**Amount:** {CURRENCY_SYMBOL}{amount:.2f}\n"
            f"**Method:** {method}\n"
            f"**TXN:** `{txn or '—'}`\n"
            f"**Recorded by:** {ctx.author.mention}\n"
            f"**Status:** ⏳ Pending verification")
        if proof:
            e.add_field(name="Proof", value=proof, inline=False)

        await ctx.send(embed=e)

        # Log
        lg = ICEmbed(title="💳 Payment Recorded", color=0xFEE75C)
        lg.add_field(name="Invoice", value=invoice, inline=True)
        lg.add_field(name="User", value=target.mention, inline=True)
        lg.add_field(name="Amount", value=f"{CURRENCY_SYMBOL}{amount:.2f}", inline=True)
        lg.add_field(name="Method", value=method, inline=True)
        lg.add_field(name="TXN", value=txn or "—", inline=True)
        lg.add_field(name="Recorded by", value=ctx.author.mention, inline=True)
        if proof:
            lg.add_field(name="Proof", value=proof, inline=False)
        await send_log(ctx.guild, PAYMENT_LOG_CHANNEL_ID, lg)

        # DM target user
        try:
            dm = premium("💳 Payment Recorded",
                f"An invoice of **{CURRENCY_SYMBOL}{amount:.2f}** has been recorded for you.\n"
                f"**Invoice:** `{invoice}`\n**Method:** {method}")
            await target.send(embed=dm)
        except:
            pass

    # ═══════════════════════════════════════════════
    #  !pay-me  — self payment via modal
    # ═══════════════════════════════════════════════
    @commands.command(name="pay-me", aliases=["payme"])
    @commands.guild_only()
    async def pay_me(self, ctx: commands.Context):
        # DMs me modal bhejna
        try:
            await ctx.author.send("Click below to submit payment:",
                                  view=PayMeButtonView())
            await ctx.message.add_reaction("📩")
        except:
            await ctx.send(embed=err("DM Blocked", "Enable DMs to receive the payment form."))

    # ═══════════════════════════════════════════════
    #  !pay-history
    # ═══════════════════════════════════════════════
    @commands.command(name="pay-history", aliases=["payhistory", "my-payments"])
    @commands.guild_only()
    async def pay_history(self, ctx: commands.Context):
        rows = self.bot.db.all(
            "SELECT * FROM payments WHERE user_id=? ORDER BY id DESC LIMIT 10",
            (ctx.author.id,))
        e = premium("💳 Payment History", f"Records: **{len(rows)}**")
        if not rows:
            e.description = "No payments yet."
        for r in rows:
            try:
                when = f"<t:{ts(datetime.datetime.fromisoformat(r['created_at']))}:R>"
            except:
                when = "—"
            status_emoji = {"pending": "⏳", "verified": "✅", "rejected": "❌"}.get(r["status"], "❔")
            e.add_field(
                name=f"{status_emoji} #{r['id']} — {CURRENCY_SYMBOL}{r['amount']:.2f}",
                value=f"Status: `{r['status']}` • {r['method']}\n"
                      f"Invoice: `{r.get('invoice_id', '—')}`\n{when}",
                inline=False)
        await ctx.send(embed=e)

    # ═══════════════════════════════════════════════
    #  !pay-verify <id> <approve|reject>
    # ═══════════════════════════════════════════════
    @commands.command(name="pay-verify", aliases=["payverify"])
    @commands.guild_only()
    async def pay_verify(self, ctx: commands.Context, payment_id: int = None, action: str = None):
        if not is_staff(ctx.author):
            return await ctx.send(embed=err("Denied"))

        if payment_id is None or action is None:
            return await ctx.send(embed=info("Usage",
                "`!pay-verify <payment_id> <approve|reject>`\n"
                "Example: `!pay-verify 5 approve`"))

        action = action.lower()
        if action not in ("approve", "reject"):
            return await ctx.send(embed=err("Invalid Action",
                "Use: `approve` or `reject`"))

        row = self.bot.db.one("SELECT * FROM payments WHERE id=?", (payment_id,))
        if not row:
            return await ctx.send(embed=err("Not Found", f"Payment #{payment_id}"))

        if row["status"] != "pending":
            return await ctx.send(embed=warn("Already Processed",
                f"Status: `{row['status']}`"))

        approve = action == "approve"
        status = "verified" if approve else "rejected"

        self.bot.db.ex(
            "UPDATE payments SET status=?, verified_by=?, verified_at=? WHERE id=?",
            (status, ctx.author.id, now_iso(), payment_id))

        if approve:
            msg = await progress(ctx, "Verifying & Provisioning", [
                "🔍 Fetching payment",
                "✅ Marking verified",
                "🚀 Triggering provisioning",
                "💾 Updating DB",
                "📩 Notifying user",
                "📋 Logging"])
        else:
            await ctx.send(embed=ok("Rejected", f"Payment #{payment_id} rejected."))

        # DM user
        try:
            u = await self.bot.fetch_user(row["user_id"])
            if approve:
                await u.send(embed=ok("Payment Verified",
                    f"Invoice `{row.get('invoice_id', '—')}` — "
                    f"{CURRENCY_SYMBOL}{row['amount']:.2f} verified.\nProvisioning started."))
            else:
                await u.send(embed=err("Payment Rejected",
                    f"Invoice `{row.get('invoice_id', '—')}` rejected. Contact support."))
        except:
            pass

        # Log
        lg = ICEmbed(title=f"💳 Payment {status.title()}",
                     color=0x57F287 if approve else 0xED4245)
        lg.add_field(name="Invoice", value=row.get("invoice_id", "—"), inline=True)
        lg.add_field(name="User", value=f"<@{row['user_id']}>", inline=True)
        lg.add_field(name="Amount", value=f"{CURRENCY_SYMBOL}{row['amount']:.2f}", inline=True)
        lg.add_field(name="Verified by", value=ctx.author.mention, inline=True)
        await send_log(ctx.guild, PAYMENT_LOG_CHANNEL_ID, lg)

    # ═══════════════════════════════════════════════
    #  !pay-setup-log-channel #channel
    # ═══════════════════════════════════════════════
    @commands.command(name="pay-setup-log-channel", aliases=["paysetuplog"])
    @commands.guild_only()
    async def pay_setup_log(self, ctx: commands.Context, channel: discord.TextChannel = None):
        if not is_admin(ctx.author):
            return await ctx.send(embed=err("Denied"))
        if channel is None:
            return await ctx.send(embed=info("Usage", "`!pay-setup-log-channel #channel`"))
        self.bot.db.ex("INSERT OR REPLACE INTO config (key,value) VALUES ('pay_log',?)",
                       (str(channel.id),))
        await ctx.send(embed=ok("Set", channel.mention))

    # ═══════════════════════════════════════════════
    #  !pay-setup-qr <url>
    # ═══════════════════════════════════════════════
    @commands.command(name="pay-setup-qr", aliases=["payqr", "qr"])
    @commands.guild_only()
    async def pay_setup_qr(self, ctx: commands.Context, url: str = None):
        if not is_admin(ctx.author):
            return await ctx.send(embed=err("Denied"))
        if url is None:
            return await ctx.send(embed=info("Usage", "`!pay-setup-qr <image_url>`"))
        e = premium("💳 Payment QR",
                    f"**UPI:** `{UPI_ID}`\n**Currency:** {CURRENCY}\n\nScan below to pay.")
        e.set_image(url=url)
        await ctx.send(embed=e)


# ─── Button to open payment modal via DM ───
class PayMeButtonView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)

    @discord.ui.button(label="Open Payment Form", emoji="💳", style=discord.ButtonStyle.success)
    async def open_form(self, i: discord.Interaction, b):
        await i.response.send_modal(PaymentModal())


async def setup(bot):
    await bot.add_cog(Payments(bot))
