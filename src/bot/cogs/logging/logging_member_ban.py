"""
Logs when a member gets banned.
"""

import datetime
import logging
import os

import discord
from discord.ext import commands

from src.bot.cogs import BaseCog

logger = logging.getLogger(__name__)


def embed_ban(some_member, audit_log_entry):
    """
    Embedding for user ban alerts.
    """
    embed = discord.Embed(
        title="",
        description=f"{some_member} was banned by: {audit_log_entry.user}. Reason: {audit_log_entry.reason}",
        color=discord.Color.red(),
        timestamp=datetime.datetime.now(datetime.timezone.utc),
    )
    return embed


class LoggingBans(BaseCog):
    """
    Simple listener to on_member_remove
    then checks the audit log for exact details
    """

    def __init__(self, bot):
        super().__init__(logger)

        self.bot = bot
        self.verification_role = self.bot.api.get_one_role("6")[0]["roles"][
            2
        ]  # Verification role ID
        self.mod_log = self.bot.api.get_one_log_setting("5")  # mod_log

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        """
        First we don't log bans for unapproved people.
        then we grab the guild, and from there read the last entry in the audit log.
        """
        if member.guild.id != int(os.getenv("MASTER_GUILD")) or member.guild.id is None:
            logger.warning(
                ">> on_member_remove fired, but not in master guild. Ignoring event."
            )
            return

        if self.verification_role in [role.id for role in member.roles]:
            return

        audit_log = [entry async for entry in member.guild.audit_logs(limit=1)][0]

        if self.mod_log[0]["status"] == "ok":
            if self.mod_log[0]["logging"][2] == "0":
                logger.debug(
                    f"log was triggered, but logging is disabled. API: {self.join_log}"
                )
                return
            logs_channel = await self.bot.fetch_channel(self.mod_log[0]["logging"][2])

            if str(audit_log.action) == "AuditLogAction.ban":
                if audit_log.target == member:
                    embed = embed_ban(member, audit_log)

                    await logs_channel.send(embed=embed)
                    return
        else:
            logger.critical(f"API error. API response not ok. -> {self.mod_log}")


async def setup(bot: commands.Bot) -> None:
    """boink"""
    await bot.add_cog(LoggingBans(bot))
