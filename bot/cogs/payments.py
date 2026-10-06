"""InfiniteCore Bot — Payments Cog"""
import random
import datetime
import discord
from discord import app_commands
from discord.ext import commands

from config import (
    CURRENCY, CURRENCY_SYMBOL, UPI_ID, PAYMENT_LOG_CHANNEL_ID,
    PAYMENT_MIN, PAYMENT_MAX
)
from embeds import ICEmbed, ok, err, warn, info, premium
from utils.helpers import now_iso, ts, is_admin, is_staff, send_log
from animations import progress


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
                embed=err("Out of range", f"{CURRENCY_SYMBOL}{PAYMENT_MIN} - {CURRENCY_SYMBOL}{PAYMENT_MAX}"),
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
        if self.proof.value: lg.add_field(name="Proof", value=self.proof.value, inline=False)
        await send_log(i.guild, PAYMENT_LOG_CHANNEL_ID, lg)


class Payments(commands.Cog, name="Payments"):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="pay", description="Submit a payment")
    async def pay(self, i: discord.Interaction):
        await i.response.send_modal(PaymentModal())

    @app_commands.command(name="pay-history", description="Your payment history")
    async def pay_history(self, i: discord.Interaction):
        rows = self.bot.db.all("SELECT * FROM payments WHERE user_id=? ORDER BY id DESC LIMIT 10",
                               (i.user.id,))
        e = premium("💳 Payment History", f"Records: **{len(rows)}**")
        if not rows: e.description = "No payments yet."
        for r in rows:
            try:
                when = datetime.datetime.fromisoformat(r["created_at"])
                rel = f"<t:{ts(when)}:R>"
            except:
                rel = "—"
            e.add_field(name=f"#{r['id']} — {CURRENCY_SYMBOL}{r['amount']:.2f}",
                        value=f"Status: `{r['status']}` • {r['method']}\n{rel}",
                        inline=False)
        await i.response.send_message(embed=e, ephemeral=True)

    @app_commands.command(name="pay-verify", description="Verify a payment (staff)")
    @app_commands.describe(payment_id="Payment ID", action="approve | reject")
    async def pay_verify(self, i: discord.Interaction, payment_id: int, action: str):
        if not is_staff(i.user):
            return await i.response.send_message(embed=err("Denied"), ephemeral=True)
        row = self.bot.db.one("SELECT * FROM payments WHERE id=?", (payment_id,))
        if not row:
            return await i.response.send_message(embed=err("Not Found"), ephemeral=True)

        approve = action.lower() == "approve"
        status = "verified" if approve else "rejected"
        self.bot.db.ex("UPDATE payments SET status=?, verified_by=?, verified_at=? WHERE id=?",
                       (status, i.user.id, now_iso(), payment_id))

        if approve:
            await progress(i, "Verifying & Provisioning", [
                "🔍 Fetching payment", "✅ Marking verified",
                "🚀 Triggering provisioning", "💾 Updating DB",
                "📩 Notifying user", "📋 Logging"])
        else:
            await i.response.send_message(embed=ok("Rejected", f"Payment #{payment_id}"))

        try:
            u = await self.bot.fetch_user(row["user_id"])
            if approve:
                await u.send(embed=ok("Payment Verified",
                                      f"{CURRENCY_SYMBOL}{row['amount']:.2f} verified. Provisioning started."))
            else:
                await u.send(embed=err("Payment Rejected", f"Payment #{payment_id} rejected."))
        except: pass

    @app_commands.command(name="pay-setup-log-channel", description="Set payment log channel")
    async def pay_setup_log(self, i: discord.Interaction, channel: discord.TextChannel):
        if not is_admin(i.user):
            return await i.response.send_message(embed=err("Denied"), ephemeral=True)
        self.bot.db.ex("INSERT OR REPLACE INTO config (key,value) VALUES ('pay_log',?)",
                       (str(channel.id),))
        await i.response.send_message(embed=ok("Set", channel.mention), ephemeral=True)

    @app_commands.command(name="pay-setup-qr", description="Show payment QR")
    async def pay_qr(self, i: discord.Interaction, url: str):
        if not is_admin(i.user):
            return await i.response.send_message(embed=err("Denied"), ephemeral=True)
        e = premium("💳 Payment QR",
                    f"**UPI:** `{UPI_ID}`\n**Currency:** {CURRENCY}\n\nScan below to pay.")
        e.set_image(url=url)
        await i.response.send_message(embed=e)


async def setup(bot):
    await bot.add_cog(Payments(bot))
